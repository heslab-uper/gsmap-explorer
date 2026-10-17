import numpy as np
from scipy.spatial import Delaunay
from shapely.geometry import MultiPoint, box
from shapely import voronoi_polygons
import pandas as pd
import geopandas as gpd
from pathlib import Path
from matplotlib import pyplot as plt
from pyproj import Geod

from core.series import compute_daily_totals, make_regular_hourly
from core.shapefile import read_shapefile


# # import testing
# import sys
# import os
# sys.path.append(os.path.abspath("D:/OneDrive/5_Code/2_Code_Automation/gsmap-explorer/src"))
# from utils.config_reader import read_config



geod = Geod(ellps="WGS84")

def geodesic_area(poly):
    area, _ = geod.geometry_area_perimeter(poly)
    return abs(area)


def polygon_thiesen (settings):
    csv_dir = settings.output_folder / "csv_output"
    path_koordinat = csv_dir / "koordinat.csv"
    df_koordinat = pd.read_csv(path_koordinat)
    points_name = df_koordinat['name'].values
    points = df_koordinat[['lon', 'lat']].values
    path_hujan = csv_dir / "hujan_grid.csv"

    df_hujan = pd.read_csv(path_hujan, index_col=0, parse_dates=True)
    # regions: watersheds or administrative areas; same id value = one region
    das_field = settings.shapefile_id_field
    subdas = read_shapefile(settings.shapefile, das_field)
    bounds = subdas.total_bounds

    print ("polygon thiesen processing...")

    mp = MultiPoint(points)
    vor = voronoi_polygons(mp, extend_to=box(*bounds))

    # voronoi_polygons does not return the polygons in the order of the points:
    # name each polygon by the grid point lying in it, never by position
    cells = gpd.GeoDataFrame(geometry=list(vor.geoms), crs=subdas.crs)
    stations = gpd.GeoDataFrame({"station": points_name},
                                geometry=gpd.points_from_xy(points[:, 0], points[:, 1]), crs=subdas.crs)
    owner = gpd.sjoin(stations, cells, how="left", predicate="within")
    if owner["index_right"].isna().any() or owner["index_right"].duplicated().any() or len(owner) != len(cells):
        raise ValueError("Thiessen polygons do not match the grid points one to one")
    thiessen = gpd.GeoDataFrame({"station": owner["station"].to_numpy()},
                                geometry=cells.geometry.loc[owner["index_right"].astype(int)].to_numpy(),
                                crs=subdas.crs)


    thiessen = gpd.overlay(
        thiessen,
        subdas[[das_field, "geometry"]],
        how="intersection"
    )

    
    thiessen = thiessen.sort_values(
        by=[das_field, "station"]
    ).reset_index(drop=True)

    
    thiessen["area_m2"] = thiessen.geometry.apply(
        geodesic_area
    )


    sub_das_values = thiessen[das_field].unique()

    # regions inside the same GSMaP cell(s) get identical rain: say so (resolution 0.1 degree)
    cells_of = thiessen.groupby(das_field)["station"].agg(lambda s: frozenset(s))
    for cells, ids in cells_of.groupby(cells_of).groups.items():
        if len(ids) > 1:
            print(f"  note: regions {', '.join(str(i) for i in ids)} use the same grid cell(s) "
                  f"{', '.join(sorted(cells))}: identical areal rain")
    results = []
    df_hujan = df_hujan.sort_index()


    areal_dict = {}

    for sub_das in sub_das_values:

        print(f"Processing region: {sub_das}")

        thiessen_subdas = (
            thiessen[thiessen[das_field] == sub_das]
            .sort_values("station")
            .reset_index(drop=True)
        )

        stations = thiessen_subdas["station"].values

        hujan_subdas = df_hujan[stations]

        area = thiessen_subdas["area_m2"].values

        area_rain = (
            hujan_subdas.mul(area, axis=1)
            .sum(axis=1)
            / area.sum()
        )

        areal_dict[sub_das] = area_rain

    df_areal = pd.DataFrame(
        areal_dict,
        index=df_hujan.index
    )

    # Fixed day from day_start_hour to the same hour next day, local time (owner 2026-10-15: 07-07)
    df_areal = make_regular_hourly(df_areal)
    df_areal_daily = compute_daily_totals(df_areal, day_start_hour=settings.day_start_hour,
                                          date_label=settings.daily_date_label)
    df_areal_monthly = df_areal_daily.resample("ME").sum(min_count=1)
    df_max_daily_yearly = df_areal_daily.resample("YE").max()


    df_areal.to_csv(csv_dir / "hujan_area_hourly.csv")
    df_areal_daily.to_csv(csv_dir / "hujan_area_daily.csv")
    df_areal_monthly.to_csv(csv_dir / "hujan_area_monthly.csv")
    df_max_daily_yearly.to_csv(csv_dir / "hujan_max_daily_yearly.csv")








# ## testing

# config = read_config("config/input.txt")
# polygon_thiesen(config)