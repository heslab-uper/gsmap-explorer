"""Point list for the series mode: a CSV file with columns ``name``, ``lat``, ``lon``.

Decimal degrees, south and west negative. Each point takes the value of the
GSMaP grid cell holding it (no interpolation); points in the same 0.1-degree
cell get identical series.
"""

from pathlib import Path

import pandas as pd


def read_points_file(path) -> pd.DataFrame:
    """The point list, checked: columns name, lat, lon; unique names; numbers in range."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
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
    return pts[["name", "lat", "lon"]].reset_index(drop=True)
