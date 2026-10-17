"""One run of gsmap-explorer: extract, visualize or thiessen (README, config/input.txt)."""

from dataclasses import replace

from apps.extract import extract_bounds, run_extract
from apps.rain_grid import RainGrid
from apps.thiessen_analysis import run_thiessen
from apps.visualize import plot_maps
from core.local_time import rain_day_utc_window
from core.reader import cells_in_box, find_month_files, grid_axes, read_netcdf
from utils.config_reader import read_config_with_local
from utils.relief import download_relief
from utils.settings import SettingsError, add_margin, read_map_settings, read_settings, shapes_bounds

MODES = ("extract", "visualize", "thiessen")


def _stop(config_path, message):
    print(f"\nGalat config ({config_path}): {message}")
    raise SystemExit(1)


def run_pipeline(mode="extract", config_path="config/input.txt", menu=True):
    """Check the config, show what will be done, ask (unless ``menu`` is False), read the data, run the mode."""
    try:
        config, local_path, local_keys = read_config_with_local(config_path)
    except (OSError, ValueError) as exc:      # missing file, key given twice
        _stop(config_path, exc)
    print(f"Config: {config_path}")
    if local_path is not None:
        print(f"  local config {local_path}: {', '.join(local_keys)}")

    # Settings are checked before any data is read
    try:
        settings = read_settings(config, extract=(mode in ("extract", "visualize")), thiessen=(mode == "thiessen"))
        maps = read_map_settings(config)
    except SettingsError as exc:
        _stop(config_path, exc)
    print("Settings:")
    print(settings.describe())
    print(maps.describe())

    # region read: extract_region (extract, visualize) or all shapefiles (thiessen), + region_margin_deg
    region = shapes_bounds(settings.shapes) if mode == "thiessen" else extract_bounds(settings)
    extent = list(add_margin(region, settings.margin))

    # start_date .. end_date are local rain days; read the UTC hours they hold
    start_date, end_date = rain_day_utc_window(settings.start_date, settings.end_date, settings.day_start_hour,
                                               settings.daily_date_label, settings.time_zone)
    list_nc_files, missing_months = find_month_files(settings.gsmap_folder, start_date, end_date)
    if missing_months:
        print(f"  no file for {len(missing_months)} month(s): {' '.join(missing_months)}")
    if not list_nc_files:
        _stop(config_path, f"no monthly .nc file under {settings.gsmap_folder} for "
                           f"{settings.start_date} .. {settings.end_date}")
    lat_axis, lon_axis = grid_axes(list_nc_files[0])
    try:
        rows, cols = cells_in_box(lat_axis, lon_axis, *extent)
    except ValueError as exc:
        _stop(config_path, f"region of {'shape_<name>' if mode == 'thiessen' else 'extract_region'}: {exc}")

    hours = int((end_date - start_date).total_seconds() // 3600) + 1
    what = {"extract": f"extract_region = {settings.extract_region}", "visualize": f"maps {', '.join(maps.outputs)}",
            "thiessen": f"{len(settings.shapes)} shapefile(s)"}[mode]
    print(f"\nRingkasan: {mode} ({what})")
    print(f"  wilayah dibaca : lon {extent[0]:.2f}..{extent[1]:.2f}, lat {extent[2]:.2f}..{extent[3]:.2f} "
          f"(margin {settings.margin:g})")
    print(f"  periode        : hari hujan {settings.start_date} .. {settings.end_date} ({settings.time_zone}) "
          f"= UTC {start_date:%Y-%m-%d %H:%M} .. {end_date:%Y-%m-%d %H:%M}")
    print(f"  ukuran         : {len(rows) * len(cols)} sel x {hours} jam = "
          f"{len(rows) * len(cols) * hours / 1e6:.1f} juta nilai jam-an")
    print(f"  keluaran       : {settings.output_folder}")
    if menu:
        try:
            answer = input("Lanjut? [Y/n]: ").strip().lower()
        except EOFError:
            answer = "n"
        if answer in ("n", "no", "tidak", "t"):
            print("Dibatalkan.")
            return

    if maps.relief_download and mode == "visualize":
        try:
            download_relief(maps.relief_file)
        except (OSError, ValueError) as exc:   # network, disk, unexpected file: the relief is optional
            print(f"  note: relief download failed ({exc}); maps without relief, tried again next run")
            maps = replace(maps, relief_file=None, relief_download=False)

    data_subset, times, lon, lat = read_netcdf(list_nc_files, start_date, end_date, extent=extent)
    grid = RainGrid.from_read(data_subset, times, lon, lat, settings)

    if mode == "extract":
        run_extract(grid, settings, maps, extent)
    elif mode == "visualize":
        plot_maps(grid, settings, maps, extent)
    else:
        run_thiessen(grid, settings, maps, extent)
