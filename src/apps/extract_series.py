"""Rain series of a GSMaP product at points, in a box, or in the bounds of a shapefile.

Region:
``points``  the cell holding each point of a CSV file (name, lat, lon);
``box``     every cell overlapping min_lon..max_lon, min_lat..max_lat;
``shape``   every cell overlapping the total bounds of a shapefile.
No interpolation: each column is one 0.1-degree cell (``cells.csv``).

Time: local labels marking the END of each hour, UTC + time zone + 1 h
(``core.local_time``). The period is given as rain-day dates: day D runs
from ``day_start_hour`` on D to the same hour on D+1 (``daily_date_label``
start) and the hours outside these days are cut, so the first and last day
are whole in every time zone.

Outputs (any of): ``hourly`` (mm per hour), ``daily`` (fixed-day totals),
``monthly`` and ``yearly`` (sums of the days of each calendar month / year
of the day dates). A day with a missing hour, and a month or year with a
missing day or not wholly inside the period, is left empty: totals are never
taken over incomplete data.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from apps.extract_points import read_points_file
from core.local_time import (TIME_ZONE_HOURS, local_offset_hours, rain_day_labels, rain_day_utc_window,
                             to_local_end_labels)
from core.reader import cells_in_box, find_month_files, grid_axes, grid_cells, read_window
from core.series import compute_daily_totals
from core.shapefile import read_shapefile

SELECTIONS = ("points", "box", "shape")
OUTPUTS = ("hourly", "daily", "monthly", "yearly")
ZONES = tuple(TIME_ZONE_HOURS)


@dataclass
class SeriesChoice:
    """Everything one series run uses; printed and written to ``choices.txt``."""

    product: str
    """Label of the product from its folder name (``product_label``), e.g. ``STD_V8_GA``."""
    path_nc: str
    selection: str
    start: date
    """First rain day (local)."""
    end: date
    """Last rain day (local)."""
    outputs: list
    zone: str
    day_start_hour: int
    date_label: str
    points_file: str | None = None
    box: tuple | None = None
    """(min_lon, max_lon, min_lat, max_lat)."""
    shapefile: str | None = None
    path_out: str = ""
    notes: list = field(default_factory=list)

    def describe(self) -> str:
        where = {"points": f"points from {self.points_file}",
                 "box": "box lon {0}..{1}, lat {2}..{3}".format(*self.box) if self.box else "",
                 "shape": f"total bounds of {self.shapefile}"}[self.selection]
        off = local_offset_hours(self.zone)
        return "\n".join([
            f"  product   : {self.product} ({self.path_nc})",
            f"  region    : {self.selection}: {where}",
            f"  period    : rain days {self.start} .. {self.end} "
            f"({self.day_start_hour:02d}.00-{self.day_start_hour:02d}.00 {self.zone}, dated by window {self.date_label})",
            f"  time zone : {self.zone} = UTC + {off} h ({off - 1} h zone + 1 h: label = end of the hour)",
            f"  outputs   : {', '.join(self.outputs)}",
            f"  output to : {self.output_dir()}",
        ])

    def output_dir(self) -> Path:
        name = f"{self.product.replace('/', '_')}_{self.selection}_{self.start:%Y%m%d}_{self.end:%Y%m%d}_{self.zone}"
        return Path(self.path_out) / "series_output" / name


def product_label(folder) -> str:
    """Name of the product for the output folder: ``STD_V8_GA`` for ``.../STD/V8/GA/NC``, else the folder name."""
    folder = Path(folder).resolve()
    return "_".join(folder.parts[-4:-1]) if folder.name == "NC" else folder.name


def select_cells(choice: SeriesChoice, lat_axis, lon_axis) -> pd.DataFrame:
    """One row per output column: name, row, col, cell centre (and the point for ``points``)."""
    if choice.selection == "points":
        pts = read_points_file(choice.points_file)
        i, j = grid_cells(lat_axis, lon_axis, pts["lat"].to_numpy(), pts["lon"].to_numpy())
        cells = pts.assign(row=i, col=j, cell_lat=np.round(lat_axis[i], 2), cell_lon=np.round(lon_axis[j], 2))
        key = list(zip(i, j))
        cells["same_cell_as"] = [" ".join(n2 for n2, k2 in zip(cells["name"], key) if k2 == k and n2 != n)
                                 for n, k in zip(cells["name"], key)]
        return cells
    if choice.selection == "box":
        min_lon, max_lon, min_lat, max_lat = choice.box
    else:
        gdf = read_shapefile(choice.shapefile)
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in gdf.total_bounds)
        choice.notes.append(f"shapefile total bounds: lon {min_lon:.4f}..{max_lon:.4f}, lat {min_lat:.4f}..{max_lat:.4f}")
    rows, cols = cells_in_box(lat_axis, lon_axis, min_lon, max_lon, min_lat, max_lat)
    r, c = np.meshgrid(rows, cols, indexing="ij")
    r, c = r.ravel(), c.ravel()
    clat, clon = np.round(lat_axis[r], 2), np.round(lon_axis[c], 2)
    return pd.DataFrame({"name": [f"{a:.2f}_{b:.2f}" for a, b in zip(clat, clon)], "row": r, "col": c,
                         "cell_lat": clat, "cell_lon": clon})


def day_window_labels(choice: SeriesChoice) -> tuple[pd.Timestamp, pd.Timestamp]:
    """First and last local end-of-hour label of the rain days start .. end."""
    return rain_day_labels(choice.start, choice.end, choice.day_start_hour, choice.date_label)


def strict_totals(daily: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Sum of the days of each calendar month (``MS``) or year (``YS``); NaN unless every day is present."""
    periods = daily.index.to_period("M" if freq == "MS" else "Y")
    expected = pd.Series(periods.days_in_month if freq == "MS" else [366 if p.is_leap_year else 365 for p in periods],
                         index=daily.index).groupby(periods).first()
    total = daily.groupby(periods).sum(min_count=1)
    complete = daily.notna().groupby(periods).sum().eq(expected, axis=0)
    out = total.where(complete)
    out.index = out.index.astype(str)
    out.index.name = "month" if freq == "MS" else "year"
    return out


def estimate(choice: SeriesChoice, n_cells: int) -> tuple[int, int]:
    """(hours, values) of the hourly table, for the size check before reading."""
    first, last = day_window_labels(choice)
    hours = int((last - first) / pd.Timedelta(hours=1)) + 1
    return hours, hours * n_cells


def run_series(choice: SeriesChoice) -> Path:
    """Read, cut to the rain days, aggregate and write the chosen outputs; returns the output folder."""
    first_label, last_label = day_window_labels(choice)
    utc_first, utc_last = rain_day_utc_window(choice.start, choice.end, choice.day_start_hour, choice.date_label,
                                              choice.zone)
    files, missing = find_month_files(choice.path_nc, utc_first, utc_last)
    if missing:
        choice.notes.append(f"no file for {len(missing)} month(s): {' '.join(missing)}")
        print(f"  no file for {len(missing)} month(s): {' '.join(missing)}")
    if not files:
        raise FileNotFoundError(f"no monthly .nc file under {choice.path_nc} for {choice.start} .. {choice.end}")

    lat_axis, lon_axis = grid_axes(files[0])
    cells = select_cells(choice, lat_axis, lon_axis)
    rows, cols = np.unique(cells["row"]), np.unique(cells["col"])
    print(f"{len(cells)} column(s) from {len(rows)} x {len(cols)} cells, {len(files)} monthly files")
    times, block = read_window(files, rows, cols, utc_first, utc_last)
    values = block[:, np.searchsorted(rows, cells["row"]), np.searchsorted(cols, cells["col"])]

    hourly = pd.DataFrame(values, index=to_local_end_labels(times, choice.zone), columns=list(cells["name"]))
    full = pd.date_range(first_label, last_label, freq="h", name="time")
    hourly = hourly[(hourly.index >= first_label) & (hourly.index <= last_label)].reindex(full)
    daily = compute_daily_totals(hourly, day_start_hour=choice.day_start_hour, date_label=choice.date_label)

    out = choice.output_dir()
    out.mkdir(parents=True, exist_ok=True)
    cells.drop(columns=["row", "col"]).to_csv(out / "cells.csv", index=False)
    if "hourly" in choice.outputs:
        hourly.to_csv(out / "rain_hourly.csv", float_format="%.3f", date_format="%Y-%m-%d %H:%M")
    if "daily" in choice.outputs:
        daily.to_csv(out / "rain_daily.csv", float_format="%.2f", date_format="%Y-%m-%d")
    if "monthly" in choice.outputs:
        strict_totals(daily, "MS").to_csv(out / "rain_monthly.csv", float_format="%.1f")
    if "yearly" in choice.outputs:
        strict_totals(daily, "YS").to_csv(out / "rain_yearly.csv", float_format="%.1f")

    missing_hours = int(hourly.isna().all(axis=1).sum())
    incomplete_days = int(daily.isna().any(axis=1).sum())
    data_last = hourly.dropna(how="all").index.max()
    summary = [f"hourly labels {hourly.index[0]} .. {hourly.index[-1]} ({choice.zone}), "
               f"{len(hourly)} hours, {missing_hours} missing (last hour with data: {data_last})",
               f"daily {daily.index[0].date()} .. {daily.index[-1].date()}, {len(daily)} days, {incomplete_days} incomplete"]
    for s in summary:
        print("  " + s)
    for _, r in cells[cells.get("same_cell_as", pd.Series("", index=cells.index)).fillna("") != ""].iterrows():
        print(f"  note: {r['name']} shares its cell ({r.cell_lat:.2f}, {r.cell_lon:.2f}) with {r.same_cell_as}")
    (out / "choices.txt").write_text(
        f"gsmap-explorer series run {datetime.now():%Y-%m-%d %H:%M}\n" + choice.describe() + "\n"
        + "\n".join("  " + s for s in summary + choice.notes) + "\n", encoding="utf-8")
    print(f"✅ Series written to: {out}")
    return out
