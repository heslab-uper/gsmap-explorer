"""Polygon shapefile of the regions (watersheds, sub-watersheds or administrative areas)."""

import geopandas as gpd


def read_shapefile(path, id_field: str | None = None) -> gpd.GeoDataFrame:
    """The polygons in WGS 1984 degrees (EPSG:4326).

    The file must carry a CRS (its .prj); any CRS is converted. ``id_field``,
    when given, must be a column of the attribute table: it names each region,
    and polygons with the same value form one region.
    """
    try:
        gdf = gpd.read_file(path)
    except RuntimeError as exc:   # pyogrio DataSourceError: e.g. the .shx or .dbf beside the .shp is missing
        raise ValueError(f"{path} cannot be read ({exc}); a shapefile needs its .shx, .dbf and .prj "
                         f"with the same name in the same folder") from exc
    if gdf.crs is None:
        raise ValueError(f"{path} has no CRS (no .prj file); add the .prj or save the shapefile again with its CRS")
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    if gdf.empty:
        raise ValueError(f"{path} holds no polygons")
    if id_field is not None:
        if id_field not in gdf.columns:
            columns = [c for c in gdf.columns if c != "geometry"]
            raise ValueError(f"{path} has no column '{id_field}'; columns: {columns}")
        if gdf[id_field].isna().any():
            raise ValueError(f"{path}: column '{id_field}' is empty for {int(gdf[id_field].isna().sum())} polygon(s)")
    return gdf
