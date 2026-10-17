"""Mode thiessen: areal rain of the regions of every shapefile (Thiessen polygons of the grid points)."""

from datetime import datetime

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod
from shapely import voronoi_polygons
from shapely.geometry import MultiPoint, box

from apps.rain_tables import write_rain_tables
from core.shapefile import read_shapefile
from utils.settings import add_margin

geod = Geod(ellps="WGS84")

def geodesic_area(poly):
    area, _ = geod.geometry_area_perimeter(poly)
    return abs(area)


def thiessen_weights(points, keys, regions, id_field, names=None) -> pd.DataFrame:
    """Thiessen weights of grid points in regions: one row per (region, point) piece.

    ``points``: (n, 2) lon, lat; ``keys``: one key per point (returned in
    column ``column``); ``regions``: polygons in EPSG:4326, same ``id_field``
    value = one region. Columns: region, column, area_m2 (geodesic), fraction
    (of the region). Regions using the same point(s) are reported.
    """
    names = names or {k: str(k) for k in keys}
    points = np.asarray(points, dtype=float)
    vor = voronoi_polygons(MultiPoint(points), extend_to=box(*regions.total_bounds))

    # voronoi_polygons does not return the polygons in the order of the points:
    # name each polygon by the grid point lying in it, never by position
    cells = gpd.GeoDataFrame(geometry=list(vor.geoms), crs=regions.crs)
    stations = gpd.GeoDataFrame({"column": list(keys)},
                                geometry=gpd.points_from_xy(points[:, 0], points[:, 1]), crs=regions.crs)
    owner = gpd.sjoin(stations, cells, how="left", predicate="within")
    if owner["index_right"].isna().any() or owner["index_right"].duplicated().any() or len(owner) != len(cells):
        raise ValueError("Thiessen polygons do not match the grid points one to one")
    thiessen = gpd.GeoDataFrame({"column": owner["column"].to_numpy()},
                                geometry=cells.geometry.loc[owner["index_right"].astype(int)].to_numpy(),
                                crs=regions.crs)
    pieces = gpd.overlay(thiessen, regions[[id_field, "geometry"]], how="intersection")
    pieces["area_m2"] = pieces.geometry.apply(geodesic_area)
    pieces = pieces.rename(columns={id_field: "region"})
    pieces = pieces.groupby(["region", "column"], as_index=False)["area_m2"].sum()
    # slivers of rounding along shared edges (< 1e-6 of the region) are not real pieces
    pieces = pieces[pieces["area_m2"] > 1e-6 * pieces.groupby("region")["area_m2"].transform("sum")]
    pieces["fraction"] = pieces["area_m2"] / pieces.groupby("region")["area_m2"].transform("sum")

    # regions inside the same GSMaP cell(s) get identical rain: say so (resolution 0.1 degree)
    cells_of = pieces.groupby("region")["column"].agg(lambda s: frozenset(s))
    for used, ids in cells_of.groupby(cells_of).groups.items():
        if len(ids) > 1:
            print(f"  note: regions {', '.join(str(i) for i in ids)} use the same grid cell(s) "
                  f"{', '.join(sorted(names[c] for c in used))}: identical areal rain")
    return pieces.sort_values(["region", "column"]).reset_index(drop=True)


def areal_rain(hourly: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """Weighted mean of the cells of each region; empty where a cell with a weight > 0 is missing."""
    w = weights.pivot_table(index="region", columns="column", values="fraction", fill_value=0.0)
    values = hourly[w.columns].to_numpy(dtype=float)
    missing = np.isnan(values)
    areal = np.nan_to_num(values) @ w.to_numpy().T
    areal[(missing.astype(float) @ (w.to_numpy().T > 0)) > 0] = np.nan   # NaN x 0 must not empty other regions
    out = pd.DataFrame(areal, index=hourly.index, columns=[str(r) for r in w.index])
    out.index.name = "time"
    return out


def run_thiessen(grid, settings, maps, extent) -> None:
    """Areal rain (Thiessen) of the regions of every shape_<name>, in <output_folder>/thiessen_output/<name>/.

    The grid points within the shapefile bounds + region_margin_deg weigh by the geodesic area of their
    Thiessen polygon inside each region. Files: the rain tables of rain_outputs (one column per value of
    the id field), weights.csv, map.png, choices.txt.
    """
    from apps.extract import cell_table
    from apps.visualize import plot_extract_map

    cells = cell_table(grid)
    for shape in settings.shapes:
        out = settings.output_folder / "thiessen_output" / shape.name
        regions = read_shapefile(shape.path, shape.id_field)
        tb = regions.total_bounds
        view = add_margin((tb[0], tb[2], tb[1], tb[3]), settings.margin)
        near = cells[cells.cell_lon.between(view[0], view[1]) & cells.cell_lat.between(view[2], view[3])]
        print(f"Thiessen {shape.name} ({shape.path.name} | {shape.id_field}): {len(near)} grid point(s) around it")
        weights = thiessen_weights(near[["cell_lon", "cell_lat"]].to_numpy(), list(near.index), regions,
                                   shape.id_field, names=dict(zip(near.index, near.name)))
        areal = areal_rain(grid.hourly, weights)
        written = write_rain_tables(areal, settings, out)
        weights.assign(cell=weights["column"].map(cells["name"]))[["region", "cell", "area_m2", "fraction"]] \
            .to_csv(out / "weights.csv", index=False, float_format="%.6f")
        used = cells.loc[sorted(weights["column"].unique())]
        plot_extract_map(grid, settings, maps, view, used, out / "map.png", regions=regions, id_field=shape.id_field,
                         title="Thiessen")
        summary = [f"{shape.name} ({shape.path.name} | {shape.id_field}): {areal.shape[1]} region(s), "
                   f"{len(used)} grid cell(s) weighted",
                   f"hourly {areal.index[0]} .. {areal.index[-1]} ({settings.time_zone}), "
                   f"{int(areal.isna().all(axis=1).sum())} hour(s) missing",
                   "files: " + ", ".join(p.name for p in written) + ", weights.csv, map.png"]
        (out / "choices.txt").write_text(
            f"gsmap-explorer thiessen {datetime.now():%Y-%m-%d %H:%M}\n"
            f"  data      : {settings.gsmap_folder}\n"
            f"  period    : rain days {settings.start_date} .. {settings.end_date} ({settings.time_zone}, "
            f"{settings.day_start_hour:02d}.00, dated by window {settings.daily_date_label})\n"
            f"  margin    : {settings.margin:g} degree; year from month {settings.year_start_month}, "
            f"annual maximum when >= {settings.min_valid_fraction:g} of the days\n"
            + "\n".join("  " + s for s in summary) + "\n", encoding="utf-8")
        for s in summary[:2]:
            print(f"  {s}")
        print(f"✅ Thiessen: {out}")
