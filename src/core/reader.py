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


def read_points(file_path_list, lats, lons, start_date, end_date):
    """Hourly rain of the grid cell holding each point, from monthly GSMaP files.

    Only the small window of rows and columns holding all points is read.
    Masked cells become NaN. Times are the UTC start-of-hour stamps of the
    files, kept from ``start_date`` to ``end_date`` inclusive.

    Returns
    -------
    times : numpy.ndarray of datetime (UTC), values : (n_times, n_points) float64,
    cell_lat, cell_lon : centre of each point's cell (from the first file).
    """
    lats, lons = np.asarray(lats, np.float64), np.asarray(lons, np.float64)
    times_all, data_all, cell_lat, cell_lon = [], [], None, None
    for file_path in file_path_list:
        with Dataset(file_path, 'r') as nc:
            lat_axis, lon_axis = nc.variables['lat'][:], nc.variables['lon'][:]
            i, j = grid_cells(lat_axis, lon_axis, lats, lons)
            if cell_lat is None:
                cell_lat, cell_lon = np.asarray(lat_axis)[i], np.asarray(lon_axis)[j]
            times = _times(nc)
            keep = (times >= start_date) & (times <= end_date)
            if not keep.any():
                continue
            i0, i1, j0, j1 = int(i.min()), int(i.max()), int(j.min()), int(j.max())
            window = nc.variables['precipitation'][:, i0:i1 + 1, j0:j1 + 1]
            window = np.ma.filled(np.ma.asarray(window, dtype=np.float64), np.nan)
            times_all.append(times[keep])
            data_all.append(window[keep][:, i - i0, j - j0])
            print(f"  read {Path(file_path).name}: {int(keep.sum())} hours")
    if not times_all:
        raise ValueError("no data in the period start_date..end_date in the files found")
    times_all, data_all = np.concatenate(times_all), np.concatenate(data_all, axis=0)
    unique_times, unique_idx = np.unique(times_all, return_index=True)
    return unique_times, data_all[unique_idx], cell_lat, cell_lon


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


