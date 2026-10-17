"""Mode extract: rain of the grid cells of a box, of the regions of each shapefile, or at points.

``extract_region`` (config):

- ``box``     every cell of min_lon..max_lat + region_margin_deg; one column per cell
- ``shape``   for each ``shape_<name>``: every cell sharing an area with its polygons
              (the margin cells are read but not written); one folder per shapefile
- ``points``  the cell holding each point of ``points_file`` (name, lat, lon); one column per point

Cells are named by their centre, ``<lat>_<lon>`` (e.g. ``-7.85_110.45``): the same cell has
the same name in every run. Output in ``<output_folder>/extract_output/<box|points|name>/``:
the rain tables of ``rain_outputs`` (``apps.rain_tables``), ``cells.csv``, ``map.png`` and
``choices.txt``.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import box as cell_box

from apps.extract_points import read_points_file
from apps.rain_tables import write_rain_tables
from core.reader import grid_cells
from core.shapefile import read_shapefile
from utils.settings import add_margin, shapes_bounds


def extract_bounds(settings) -> tuple:
    """(min_lon, max_lon, min_lat, max_lat) of what extract reads, before the margin."""
    if settings.extract_region == "shape":
        return shapes_bounds(settings.shapes)
    if settings.extract_region == "points":
        pts = read_points_file(settings.points_file)
        return (pts.lon.min(), pts.lon.max(), pts.lat.min(), pts.lat.max())
    return settings.box


def cell_table(grid) -> pd.DataFrame:
    """One row per column of ``grid.hourly`` (same order): name, centre, and its cell as a box."""
    lon2, lat2 = np.meshgrid(grid.lon, grid.lat)
    t = pd.DataFrame({"cell_lat": lat2.ravel(), "cell_lon": lon2.ravel()})
    t["name"] = [f"{a:.2f}_{b:.2f}" for a, b in zip(t.cell_lat, t.cell_lon)]
    dlon = abs(grid.lon[1] - grid.lon[0]) if len(grid.lon) > 1 else 0.1
    dlat = abs(grid.lat[1] - grid.lat[0]) if len(grid.lat) > 1 else 0.1
    t["geometry"] = [cell_box(x - dlon / 2, y - dlat / 2, x + dlon / 2, y + dlat / 2)
                     for x, y in zip(t.cell_lon, t.cell_lat)]
    return t


def cells_in_regions(cells: pd.DataFrame, regions, id_field: str) -> pd.DataFrame:
    """Cells sharing an area with the regions (not only an edge or a rounding sliver), and the region ids of each."""
    groups = regions.dissolve(by=id_field)
    rows = []
    for k, geom in zip(cells.index, cells.geometry):
        ids = [str(rid) for rid, g in zip(groups.index, groups.geometry)
               if g.intersects(geom) and g.intersection(geom).area > 1e-6 * geom.area]
        if ids:
            rows.append((k, " ".join(ids)))
    return pd.DataFrame(rows, columns=["column", "regions"])


def _write(grid, settings, maps, extent, out: Path, columns: list, table: pd.DataFrame, what: str,
           regions=None, id_field=None, labels=None) -> None:
    hourly = grid.hourly[columns].set_axis(list(table.name), axis=1)
    hourly.index.name = "time"
    written = write_rain_tables(hourly, settings, out)
    table.drop(columns=["geometry"], errors="ignore").round({"cell_lat": 2, "cell_lon": 2}) \
        .to_csv(out / "cells.csv", index=False)

    from apps.visualize import plot_extract_map
    plot_extract_map(grid, settings, maps, extent, table, out / "map.png", regions=regions, id_field=id_field,
                     labels=labels)
    missing = int(hourly.isna().all(axis=1).sum())
    summary = [f"{what}: {len(table)} column(s)",
               f"hourly {hourly.index[0]} .. {hourly.index[-1]} ({settings.time_zone}), {missing} hour(s) missing",
               "files: " + ", ".join(p.name for p in written) + ", cells.csv, map.png"]
    (out / "choices.txt").write_text(
        f"gsmap-explorer extract {datetime.now():%Y-%m-%d %H:%M}\n"
        f"  data      : {settings.gsmap_folder}\n"
        f"  period    : rain days {settings.start_date} .. {settings.end_date} ({settings.time_zone}, "
        f"{settings.day_start_hour:02d}.00, dated by window {settings.daily_date_label})\n"
        f"  margin    : {settings.margin:g} degree; year from month {settings.year_start_month}, "
        f"annual maximum when >= {settings.min_valid_fraction:g} of the days\n"
        + "\n".join("  " + s for s in summary) + "\n", encoding="utf-8")
    for s in summary[:2]:
        print(f"  {s}")
    print(f"✅ Extract: {out}")


def run_extract(grid, settings, maps, extent) -> None:
    """Write the extract of ``settings.extract_region`` (see the module docstring)."""
    root = settings.output_folder / "extract_output"
    cells = cell_table(grid)
    region = settings.extract_region

    if region == "box":
        _write(grid, settings, maps, extent, root / "box", list(cells.index), cells,
               "box " + "lon {0:g}..{1:g}, lat {2:g}..{3:g}".format(*settings.box) + f" + {settings.margin:g} degree")

    elif region == "points":
        pts = read_points_file(settings.points_file)
        i, j = grid_cells(grid.lat, grid.lon, pts["lat"].to_numpy(), pts["lon"].to_numpy())
        columns = list(i * len(grid.lon) + j)
        table = pts.assign(cell_lat=grid.lat[i], cell_lon=grid.lon[j])
        key = list(zip(i, j))
        table["same_cell_as"] = [" ".join(n2 for n2, k2 in zip(table.name, key) if k2 == k and n2 != n)
                                 for n, k in zip(table.name, key)]
        for _, r in table[table.same_cell_as != ""].iterrows():
            print(f"  note: point {r['name']} shares its cell with {r.same_cell_as}: identical series")
        _write(grid, settings, maps, extent, root / "points", columns, table,
               f"points of {settings.points_file}", labels=list(table.name))

    else:   # shape
        for shape in settings.shapes:
            regions = read_shapefile(shape.path, shape.id_field)
            member = cells_in_regions(cells, regions, shape.id_field)
            if member.empty:
                print(f"  note: {shape.name}: no grid cell shares an area with its polygons; nothing written")
                continue
            table = cells.loc[member.column].assign(regions=member.regions.to_numpy())
            shape_extent = add_margin((regions.total_bounds[0], regions.total_bounds[2],
                                       regions.total_bounds[1], regions.total_bounds[3]), settings.margin)
            _write(grid, settings, maps, shape_extent, root / shape.name, list(member.column), table,
                   f"{shape.name} ({shape.path.name} | {shape.id_field})", regions=regions, id_field=shape.id_field)
