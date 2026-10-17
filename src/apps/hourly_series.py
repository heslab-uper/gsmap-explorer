"""The hourly series the analyses run on: shapefile regions (shapefile given) or grid points (no shapefile)."""

import pandas as pd

from core.series import make_regular_hourly


def load_hourly_series(settings) -> tuple[pd.DataFrame, str]:
    """Hourly rain (mm) on a regular local end-of-hour index, and what the columns are.

    With a shapefile: ``hujan_area_hourly.csv`` (one column per region,
    written by the thiessen step); without: ``hujan_grid.csv`` (one column per
    grid point). Hours missing from the data are NaN rows.
    """
    csv_dir = settings.output_folder / "csv_output"
    if settings.shapefile is not None:
        path, unit = csv_dir / "hujan_area_hourly.csv", "region"
    else:
        path, unit = csv_dir / "hujan_grid.csv", "grid point"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; it is written by the extract/thiessen step")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [str(c) for c in df.columns]
    df.index.name = "time"
    return make_regular_hourly(df), unit
