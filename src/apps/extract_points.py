"""Hourly and daily rain at points: the value of the GSMaP grid cell holding each point (no interpolation).

Points come from a CSV file (``path_points``) with columns ``name``, ``lat``,
``lon`` (decimal degrees, south and west negative). Points in the same
0.1-degree cell get identical series; ``points_cells.csv`` names them.

Output in ``<path_out>/points_output/``:
``points_cells.csv`` (cell of each point), ``rain_points_hourly.csv``
(mm per hour, local end-of-hour labels, missing hours empty) and
``rain_points_daily.csv`` (fixed-day totals, see ``core.series.compute_daily_totals``;
empty when an hour of the day is missing).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from core.local_time import to_local_end_labels
from core.reader import read_points
from core.series import compute_daily_totals, make_regular_hourly


def read_points_file(path) -> pd.DataFrame:
    """The point list, checked: columns name, lat, lon; unique names; numbers in range."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"config key 'path_points': {path} not found")
    pts = pd.read_csv(path, dtype={"name": str})
    missing = {"name", "lat", "lon"} - set(pts.columns)
    if missing:
        raise ValueError(f"{path} needs the columns name, lat, lon; missing {sorted(missing)}")
    if pts.empty:
        raise ValueError(f"{path} holds no points")
    pts["name"] = pts["name"].str.strip()
    if pts["name"].isna().any() or (pts["name"] == "").any() or pts["name"].duplicated().any():
        raise ValueError(f"{path}: every point needs its own, non-empty name")
    for col, lim in (("lat", 90), ("lon", 180)):
        pts[col] = pd.to_numeric(pts[col], errors="coerce")
        if pts[col].isna().any() or (pts[col].abs() > lim).any():
            raise ValueError(f"{path}: column {col} must hold numbers within +-{lim} (decimal degrees)")
    return pts[["name", "lat", "lon"]]


def run_points(config, files, start_date, end_date, day_start_hour: int, date_label: str) -> None:
    pts = read_points_file(config.get("path_points"))
    print(f"{len(pts)} points from {config.get('path_points')}, {len(files)} monthly files")
    times, values, cell_lat, cell_lon = read_points(files, pts["lat"], pts["lon"], start_date, end_date)

    cells = pts.assign(cell_lat=np.round(np.asarray(cell_lat, np.float64), 2),
                       cell_lon=np.round(np.asarray(cell_lon, np.float64), 2))
    key = cells["cell_lat"].astype(str) + "," + cells["cell_lon"].astype(str)
    cells["same_cell_as"] = [" ".join(cells["name"][(key == k) & (cells["name"] != n)]) for k, n in zip(key, cells["name"])]
    for _, r in cells[cells["same_cell_as"] != ""].iterrows():
        print(f"  note: {r['name']} shares its grid cell ({r.cell_lat}, {r.cell_lon}) with {r.same_cell_as}: identical series")

    hourly = pd.DataFrame(values, index=to_local_end_labels(times, config.get("wilayah_waktu")),
                          columns=list(pts["name"]))
    hourly.index.name = "time"
    hourly = make_regular_hourly(hourly)
    daily = compute_daily_totals(hourly, day_start_hour=day_start_hour, date_label=date_label)

    out = Path(config.get("path_out")) / "points_output"
    out.mkdir(parents=True, exist_ok=True)
    cells.to_csv(out / "points_cells.csv", index=False)
    hourly.to_csv(out / "rain_points_hourly.csv", float_format="%.3f", date_format="%Y-%m-%d %H:%M")
    daily.to_csv(out / "rain_points_daily.csv", float_format="%.2f", date_format="%Y-%m-%d")

    missing_hours = int(hourly.isna().all(axis=1).sum())
    print(f"hourly: {hourly.index[0]} .. {hourly.index[-1]} ({config.get('wilayah_waktu')}, end of hour), "
          f"{len(hourly)} hours, {missing_hours} missing")
    print(f"daily ({day_start_hour:02d}-{day_start_hour:02d}, dated by window {date_label}): "
          f"{daily.index[0].date()} .. {daily.index[-1].date()}, {len(daily)} days, "
          f"{int(daily.isna().any(axis=1).sum())} incomplete")
    print(f"✅ Point series written to: {out}")
