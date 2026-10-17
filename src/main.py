from core.local_time import rain_day_utc_window
from core.reader import cells_in_box, find_month_files, grid_axes, read_netcdf
from core.shapefile import read_shapefile
from utils.config_reader import read_config
from utils.settings import SettingsError, read_settings
from utils.analysis_settings import read_analysis_settings

from apps.extract_csv import export_csv
from apps.visualize import plot_map  # nanti
from apps.thiessen_analysis import polygon_thiesen
from apps.hourly_series import load_hourly_series
from apps.frequency_analysis import run_frequency_analysis
from apps.hourly_characteristics import run_hourly_characteristics
from apps.extract_series import run_series
from apps.series_menu import Cancelled, ask_series_choice


def run_analysis(settings, analysis):
    """Frequency analysis, intensity and hourly characteristics of the extracted hourly series."""
    hourly, unit = load_hourly_series(settings)
    out_dir = settings.output_folder / "analysis_output"
    print(f"Analysis of {len(hourly.columns)} {unit} series, {hourly.index[0]} .. {hourly.index[-1]} "
          f"({int(hourly.isna().all(axis=1).sum())} hours missing)")
    run_frequency_analysis(hourly, unit, analysis, out_dir)
    run_hourly_characteristics(hourly, unit, analysis, out_dir)


def run_pipeline(mode="extract", config_path="config/input.txt", menu=True):
    # ========================
    # konfigurasi
    # ========================
    config = read_config(config_path)
    print(f"Config: {config_path}")

    # Series: region, period, outputs and zone chosen on screen (defaults from the config)
    if mode == "series":
        try:
            choice = ask_series_choice(config, interactive=menu)
            run_series(choice)
        except Cancelled:
            print("Dibatalkan.")
        except (ValueError, FileNotFoundError) as exc:   # SettingsError is a ValueError
            print(f"\nGalat: {exc}")
            if not menu:
                raise SystemExit(1)
        return

    # Settings are checked before any data is read
    try:
        settings = read_settings(config, need_shapefile=(mode == "thiessen"))
        analysis = read_analysis_settings(config) if mode in ("analysis", "all") else None
    except SettingsError as exc:
        print(f"\nGalat config ({config_path}): {exc}")
        raise SystemExit(1)
    print("Settings:")
    print(settings.describe())
    if analysis is not None:
        print("Analysis settings:")
        print(analysis.describe())

    # start_date .. end_date are local rain days; read the UTC hours they hold
    start_date, end_date = rain_day_utc_window(settings.start_date, settings.end_date, settings.day_start_hour,
                                               settings.daily_date_label, settings.time_zone)
    print(f"  period: rain days {settings.start_date} .. {settings.end_date} ({settings.time_zone}) = "
          f"UTC {start_date:%Y-%m-%d %H:%M} .. {end_date:%Y-%m-%d %H:%M} (start of hour)")

    list_nc_files, missing_months = find_month_files(settings.gsmap_folder, start_date, end_date)
    if missing_months:
        print(f"  no file for {len(missing_months)} month(s): {' '.join(missing_months)}")
    if not list_nc_files:
        raise FileNotFoundError(f"no monthly .nc file under {settings.gsmap_folder} for "
                                f"{settings.start_date} .. {settings.end_date}")

    # ========================
    # menentukan extent
    # ========================
    if settings.shapefile is not None:
        minx, miny, maxx, maxy = read_shapefile(settings.shapefile).total_bounds
        extent = [minx-0.1, maxx+0.15, miny-0.15, maxy+0.1]
    else:
        extent = list(settings.box)
    lat_axis, lon_axis = grid_axes(list_nc_files[0])
    try:
        cells_in_box(lat_axis, lon_axis, *extent)
    except ValueError as exc:
        print(f"\nGalat config ({config_path}): region of 'shapefile' / min_lon..max_lat: {exc}")
        raise SystemExit(1)

    # ========================
    # Baca file NetCDF
    # ========================
    data_subset, times, XX_subset, YY_subset = read_netcdf(list_nc_files, start_date, end_date, extent=extent)

    # ========================
    # MODE CONTROL
    # ========================
    if mode == "extract":
        export_csv(data_subset, times, XX_subset, YY_subset, settings)

    elif mode == "visualize":

        plot_map(data_subset, times, XX_subset, YY_subset, settings)

    elif mode == 'thiessen':
        export_csv(data_subset, times, XX_subset, YY_subset, settings)
        polygon_thiesen(settings)

    elif mode == "analysis":
        export_csv(data_subset, times, XX_subset, YY_subset, settings)
        if settings.shapefile is not None:
            polygon_thiesen(settings)
        run_analysis(settings, analysis)

    elif mode == "all":
        export_csv(data_subset, times, XX_subset, YY_subset, settings)

        plot_map(data_subset, times, XX_subset, YY_subset, settings)
        if settings.shapefile is not None:
            polygon_thiesen(settings)
        run_analysis(settings, analysis)
