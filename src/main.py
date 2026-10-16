from datetime import datetime, timedelta
from pathlib import Path
import geopandas as gpd

from utils.config_reader import read_config
from core.reader import find_month_files, read_netcdf

from apps.extract_csv import export_csv
from apps.visualize import plot_map  # nanti
from apps.thiessen_analysis import polygon_thiesen
from apps.hourly_series import has_shapefile, load_hourly_series
from apps.frequency_analysis import run_frequency_analysis
from apps.hourly_characteristics import run_hourly_characteristics
from apps.extract_series import run_series
from apps.series_menu import Cancelled, ask_series_choice
from utils.analysis_settings import read_analysis_settings


def run_analysis(config, settings):
    """Frequency analysis, intensity and hourly characteristics of the extracted hourly series."""
    hourly, unit = load_hourly_series(config)
    out_dir = Path(config.get("path_out")) / "analysis_output"
    print(f"Analysis of {len(hourly.columns)} {unit} series, {hourly.index[0]} .. {hourly.index[-1]} "
          f"({int(hourly.isna().all(axis=1).sum())} hours missing)")
    run_frequency_analysis(hourly, unit, settings, out_dir)
    run_hourly_characteristics(hourly, unit, settings, out_dir)


def run_pipeline(mode="extract", config_path="config/input.txt", menu=True):
    # ========================
    # konfigurasi
    # ========================
    config = read_config(config_path)
    print(f"Config: {config_path}")

    # Series: product, region, period, outputs and zone chosen on screen (defaults from the config)
    if mode == "series":
        try:
            choice = ask_series_choice(config, interactive=menu,
                                       last_path=Path(config_path).parent / "series_last.txt")
            run_series(choice)
        except Cancelled:
            print("Dibatalkan.")
        except (ValueError, FileNotFoundError) as exc:   # SettingsError is a ValueError
            print(f"\nGalat: {exc}")
            if not menu:
                raise SystemExit(1)
        return

    # Settings are checked before any data is read
    settings = None
    if mode in ("thiessen", "analysis", "all"):
        if mode == "thiessen" and not has_shapefile(config):
            raise ValueError(f"mode thiessen needs a shapefile: set path_shp in {config_path}")
        settings = read_analysis_settings(config)
        print(f"Analysis settings ({config_path}):")
        print(settings.describe())
    # start_date .. end_date: UTC dates of the data, both whole days included
    start_date = datetime.strptime(config.get("start_date"), "%Y-%m-%d")
    end_date = datetime.strptime(config.get("end_date"), "%Y-%m-%d") + timedelta(hours=23)
    for key in ("path_nc", "path_out", "wilayah_waktu"):
        print(f"  {key}: {config.get(key)}")
    print(f"  period (UTC): {start_date:%Y-%m-%d %H:%M} .. {end_date:%Y-%m-%d %H:%M}")

    list_nc_files, missing_months = find_month_files(config.get("path_nc"), start_date, end_date)
    if missing_months:
        print(f"  no file for {len(missing_months)} month(s): {' '.join(missing_months)}")
    if not list_nc_files:
        raise FileNotFoundError("Tidak ada file NetCDF yang ditemukan untuk rentang tanggal yang diberikan.")


    # ========================
    # menentukan extent
    # ========================
    if config.get("path_shp") and config.get("path_shp") != "None":
        gdf = gpd.read_file(config.get("path_shp"))

        if gdf.crs is None:
            raise ValueError("Shapefile tidak memiliki CRS")

        if gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)

        minx, miny, maxx, maxy = gdf.total_bounds
        extent = [minx-0.1, maxx+0.15, miny-0.15, maxy+0.1]

    else:
        extent = [
            float(config.get("min_lon")),
            float(config.get("max_lon")),
            float(config.get("min_lat")),
            float(config.get("max_lat"))
        ]

    # ========================
    # Baca file NetCDF
    # ========================
    data_subset, times, XX_subset, YY_subset = read_netcdf(list_nc_files, start_date, end_date, extent=extent)
    if data_subset is None or times is None:
        raise ValueError("Tidak ada data yang ditemukan dalam rentang tanggal yang diberikan.")



    # ========================
    # MODE CONTROL
    # ========================
    if mode == "extract":
        export_csv(data_subset, times, XX_subset, YY_subset, config.get("path_out"), config)

    elif mode == "visualize":

        plot_map(data_subset, times, XX_subset, YY_subset, config)

    elif mode == 'thiessen':
        export_csv(data_subset, times, XX_subset, YY_subset, config.get("path_out"), config)
        polygon_thiesen(config)

    elif mode == "analysis":
        export_csv(data_subset, times, XX_subset, YY_subset, config.get("path_out"), config)
        if has_shapefile(config):
            polygon_thiesen(config)
        run_analysis(config, settings)

    elif mode == "all":
        export_csv(data_subset, times, XX_subset, YY_subset, config.get("path_out"), config)

        plot_map(data_subset, times, XX_subset, YY_subset, config)
        if has_shapefile(config):
            polygon_thiesen(config)
        run_analysis(config, settings)
