"""The hourly series the analyses run on: sub-watersheds (shapefile given) or grid points (no shapefile)."""

from pathlib import Path

import pandas as pd

from core.series import make_regular_hourly


def has_shapefile(config) -> bool:
    shp = config.get("path_shp")
    return bool(shp) and shp != "None"


def load_hourly_series(config) -> tuple[pd.DataFrame, str]:
    """Hourly rain (mm) on a regular local end-of-hour index, and what the columns are.

    With a shapefile: ``hujan_area_hourly.csv`` (one column per sub-watershed,
    written by the thiessen step); without: ``hujan_grid.csv`` (one column per
    grid point). Hours missing from the data are NaN rows.
    """
    csv_dir = Path(config.get("path_out")) / "csv_output"
    if has_shapefile(config):
        path, unit = csv_dir / "hujan_area_hourly.csv", "sub-watershed"
    else:
        path, unit = csv_dir / "hujan_grid.csv", "grid point"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; it is written by the extract/thiessen step")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [str(c) for c in df.columns]
    df.index.name = "time"
    return make_regular_hourly(df), unit
