import datetime
import re
from pathlib import Path

from netCDF4 import Dataset, num2date
import numpy as np

MONTH_FILE = re.compile(r"(\d{4})_?(\d{2})\.nc$")
"""Monthly file name ending: ``..._YYYY_MM.nc`` (portal) or ``..._YYYYMM.nc`` (archive)."""

# Names in the GSMaP monthly .nc files: fixed by the files' format, not user choices.
NC_PRECIPITATION = "precipitation"
NC_TIME = "time"
NC_LAT = "lat"
NC_LON = "lon"


def _var(nc, name):
    """Variable ``name`` of an open file; a missing one is an error naming the file."""
    if name not in nc.variables:
        raise ValueError(f"{nc.filepath()}: no variable '{name}' (has {sorted(nc.variables)}); "
                         f"not a GSMaP monthly file of this format")
    return nc.variables[name]


def find_month_files(path_nc, start_date, end_date) -> tuple[list[str], list[str]]:
    """Monthly .nc files of the months from start_date to end_date, searched in ``path_nc`` and its subfolders.

    Returns the files in month order and the months (YYYY-MM) without a file.
    Two files for the same month is an error (two products in one folder).
    """
    by_month = {}
    for f in sorted(Path(path_nc).rglob("*.nc")):
        m = MONTH_FILE.search(f.name)
        if not m:
            continue
        ym = f"{m.group(1)}-{m.group(2)}"
        if ym in by_month:
            raise ValueError(f"two files for {ym} under {path_nc}: {by_month[ym]} and {f}; keep one product per folder")
        by_month[ym] = str(f)
    files, missing = [], []
    y, mo = start_date.year, start_date.month
    while (y, mo) <= (end_date.year, end_date.month):
        ym = f"{y:04d}-{mo:02d}"
        (files.append(by_month[ym]) if ym in by_month else missing.append(ym))
        y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
    return files, missing


def _times(nc) -> np.ndarray:
    time_var = _var(nc, NC_TIME)
    times = num2date(time_var[:], units=time_var.units, calendar=getattr(time_var, 'calendar', 'standard'))
    return np.array([datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second) for t in times])


def grid_cells(lat_axis, lon_axis, lats, lons) -> tuple[np.ndarray, np.ndarray]:
    """Row and column of the grid cell holding each point (nearest cell centre, axes from the file).

    Raises ValueError for a point farther than half a cell from every centre (outside the grid).
    """
    lat_axis, lon_axis = np.asarray(lat_axis, np.float64), np.asarray(lon_axis, np.float64)
    i = np.abs(lat_axis[None, :] - np.asarray(lats)[:, None]).argmin(axis=1)
    j = np.abs(lon_axis[None, :] - np.asarray(lons)[:, None]).argmin(axis=1)
    half_lat, half_lon = np.abs(np.diff(lat_axis)).max() / 2, np.abs(np.diff(lon_axis)).max() / 2
    outside = (np.abs(lat_axis[i] - lats) > half_lat + 1e-6) | (np.abs(lon_axis[j] - lons) > half_lon + 1e-6)
    if outside.any():
        k = int(np.nonzero(outside)[0][0])
        raise ValueError(f"point {k + 1} ({lats[k]}, {lons[k]}) is outside the grid "
                         f"(lat {lat_axis.min():.2f}..{lat_axis.max():.2f}, lon {lon_axis.min():.2f}..{lon_axis.max():.2f})")
    return i, j


def grid_axes(file_path) -> tuple[np.ndarray, np.ndarray]:
    """``lat`` and ``lon`` cell centres of a GSMaP file (float64; lat may run north to south)."""
    with Dataset(file_path, 'r') as nc:
        return np.asarray(_var(nc, NC_LAT)[:], np.float64), np.asarray(_var(nc, NC_LON)[:], np.float64)


def cells_in_box(lat_axis, lon_axis, min_lon, max_lon, min_lat, max_lat) -> tuple[np.ndarray, np.ndarray]:
    """Rows and columns of every cell that overlaps the box (cell edges = centre +- half a step).

    A box smaller than one cell still gets the cell(s) it touches. Raises
    ValueError when the box misses the grid.
    """
    half_lat, half_lon = np.abs(np.diff(lat_axis)).max() / 2, np.abs(np.diff(lon_axis)).max() / 2
    rows = np.nonzero((lat_axis + half_lat > min_lat) & (lat_axis - half_lat < max_lat))[0]
    cols = np.nonzero((lon_axis + half_lon > min_lon) & (lon_axis - half_lon < max_lon))[0]
    if rows.size == 0 or cols.size == 0:
        raise ValueError(f"box lon {min_lon}..{max_lon}, lat {min_lat}..{max_lat} is outside the grid "
                         f"(lat {lat_axis.min():.2f}..{lat_axis.max():.2f}, lon {lon_axis.min():.2f}..{lon_axis.max():.2f})")
    return rows, cols


def read_window(file_path_list, rows, cols, start_date, end_date):
    """Hourly rain of the block of grid rows x columns, from monthly GSMaP files.

    Only the block spanning ``rows`` and ``cols`` is read from each file.
    Every file must have the axes of the first one. Masked cells become NaN.
    Times are the UTC start-of-hour stamps of the files, kept from
    ``start_date`` to ``end_date`` inclusive.

    Returns
    -------
    times : numpy.ndarray of datetime (UTC)
    values : (n_times, len(rows), len(cols)) float64
    """
    rows, cols = np.asarray(rows), np.asarray(cols)
    i0, i1, j0, j1 = int(rows.min()), int(rows.max()), int(cols.min()), int(cols.max())
    ref = grid_axes(file_path_list[0])
    times_all, data_all = [], []
    for file_path in file_path_list:
        with Dataset(file_path, 'r') as nc:
            lat, lon = np.asarray(_var(nc, NC_LAT)[:], np.float64), np.asarray(_var(nc, NC_LON)[:], np.float64)
            if lat.shape != ref[0].shape or lon.shape != ref[1].shape or \
                    np.abs(lat - ref[0]).max() > 1e-3 or np.abs(lon - ref[1]).max() > 1e-3:
                raise ValueError(f"{file_path}: lat/lon axes differ from {file_path_list[0]}")
            times = _times(nc)
            keep = (times >= start_date) & (times <= end_date)
            if not keep.any():
                continue
            block = _var(nc, NC_PRECIPITATION)[:, i0:i1 + 1, j0:j1 + 1]
            block = np.ma.filled(np.ma.asarray(block, dtype=np.float64), np.nan)
            times_all.append(times[keep])
            data_all.append(block[keep][:, rows - i0][:, :, cols - j0])
            print(f"  read {Path(file_path).name}: {int(keep.sum())} hours")
    if not times_all:
        raise ValueError("no data in the period in the files found")
    times_all, data_all = np.concatenate(times_all), np.concatenate(data_all, axis=0)
    unique_times, unique_idx = np.unique(times_all, return_index=True)
    return unique_times, data_all[unique_idx]


def read_netcdf(file_path_list, start_date, end_date, extent):
    """Hourly rain of every grid cell whose centre lies in ``extent``, axes read from the files.

    ``extent`` = (min_lon, max_lon, min_lat, max_lat), bounds included. The
    axes come from the first file (``lat`` may run north to south and keeps
    its order); every file must have the same axes (``read_window``).
    The axes are rounded to 2 decimals before the cells are chosen, as in the
    series mode: the float32 axes of the archive are written with np.arange
    and drift up to about 2e-4 degree from the x.x5 centres of the 0.1-degree
    grid. A grid whose centres need more decimals is not supported.

    Returns
    -------
    values : (n_times, n_lat, n_lon) float64, NaN for masked cells
    times : numpy.ndarray of datetime, UTC start-of-hour stamps
    lon, lat : cell centres of the columns and rows
    """
    min_lon, max_lon, min_lat, max_lat = extent
    lat_axis, lon_axis = (np.round(a, 2) for a in grid_axes(file_path_list[0]))
    rows = np.nonzero((lat_axis >= min_lat) & (lat_axis <= max_lat))[0]
    cols = np.nonzero((lon_axis >= min_lon) & (lon_axis <= max_lon))[0]
    if rows.size == 0 or cols.size == 0:
        raise ValueError(f"no grid cell centre in lon {min_lon}..{max_lon}, lat {min_lat}..{max_lat} "
                         f"(grid lat {lat_axis.min():.2f}..{lat_axis.max():.2f}, "
                         f"lon {lon_axis.min():.2f}..{lon_axis.max():.2f})")
    times, values = read_window(file_path_list, rows, cols, start_date, end_date)
    return values, times, lon_axis[cols], lat_axis[rows]
