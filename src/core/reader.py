import datetime
import re
from pathlib import Path

from netCDF4 import Dataset, num2date
import numpy as np

MONTH_FILE = re.compile(r"(\d{4})_?(\d{2})\.nc$")
"""Monthly file name ending: ``..._YYYY_MM.nc`` (portal) or ``..._YYYYMM.nc`` (archive)."""


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
    time_var = nc.variables['time']
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
        return np.asarray(nc.variables['lat'][:], np.float64), np.asarray(nc.variables['lon'][:], np.float64)


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
            lat, lon = np.asarray(nc.variables['lat'][:], np.float64), np.asarray(nc.variables['lon'][:], np.float64)
            if lat.shape != ref[0].shape or lon.shape != ref[1].shape or \
                    np.abs(lat - ref[0]).max() > 1e-3 or np.abs(lon - ref[1]).max() > 1e-3:
                raise ValueError(f"{file_path}: lat/lon axes differ from {file_path_list[0]}")
            times = _times(nc)
            keep = (times >= start_date) & (times <= end_date)
            if not keep.any():
                continue
            block = nc.variables['precipitation'][:, i0:i1 + 1, j0:j1 + 1]
            block = np.ma.filled(np.ma.asarray(block, dtype=np.float64), np.nan)
            times_all.append(times[keep])
            data_all.append(block[keep][:, rows - i0][:, :, cols - j0])
            print(f"  read {Path(file_path).name}: {int(keep.sum())} hours")
    if not times_all:
        raise ValueError("no data in the period in the files found")
    times_all, data_all = np.concatenate(times_all), np.concatenate(data_all, axis=0)
    unique_times, unique_idx = np.unique(times_all, return_index=True)
    return unique_times, data_all[unique_idx]


def read_netcdf(file_path_list, start_date=None, end_date=None, extent=None):
    times_all = []
    data_all = []
    XX = np.arange(90.05, 150.06, 0.1) 
    YY = np.arange(15.05, -15.06, -0.1) 

    min_lon, max_lon, min_lat, max_lat = extent
    lon_mask = (XX >= min_lon) & (XX <= max_lon)
    lat_mask = (YY >= min_lat) & (YY <= max_lat)

    


    for file_path in file_path_list:
        with Dataset(file_path, 'r') as nc:
            time_var = nc.variables['time']
            times = num2date(
            time_var[:],
            units=time_var.units,
            calendar=getattr(time_var, 'calendar', 'standard'))
            
            times = np.array([datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
                for t in times
            ])

            # times = np.array(times)  # Convert to numpy array for easier slicing
            min_time = np.min(times)
            max_time = np.max(times)

            data = nc.variables['precipitation'][:,:,:]
            mask = np.ones(data.shape[0], dtype=bool)
            data = data[:, lat_mask, :][:, :, lon_mask]
            # netCDF4 returns a MaskedArray: masked cells (_FillValue) become NaN, not the raw fill value
            data = np.ma.filled(np.ma.asarray(data, dtype=np.float64), np.nan)

            if start_date is not None:
                mask &= (times >= start_date)
            if end_date is not None:
                mask &= (times <= end_date)

            if not np.any(mask):
                continue  
            times_all.append(times[mask])
            data_all.append(data[mask, :, :])
        
            # nc.close()

    if len (times_all) == 0:
        return np.array([]), np.array([])
    
    times_all = np.concatenate(times_all)
    data_all = np.concatenate(data_all, axis=0)

    sort_idx = np.argsort(times_all)
    times_all = times_all[sort_idx]
    data_all = data_all[sort_idx, :, :]

    unique_times, unique_idx = np.unique(times_all, return_index=True)
    unique_data = data_all[unique_idx, :, :]
    
    return unique_data, unique_times, XX[lon_mask], YY[lat_mask]


