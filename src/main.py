"""One run of gsmap-explorer: extract, visualize or thiessen (README, config/input.txt)."""

from dataclasses import dataclass, replace
from datetime import datetime

from apps.extract import extract_bounds, run_extract
from apps.rain_grid import RainGrid
from apps.thiessen_analysis import run_thiessen
from apps.visualize import plot_maps
from core.local_time import rain_day_utc_window
from core.reader import centre_cells, find_month_files, read_netcdf
from utils.config_reader import read_config_with_local
from utils.relief import download_relief
from utils.settings import SettingsError, add_margin, read_map_settings, read_settings, shapes_bounds

MODES = ("extract", "visualize", "thiessen")


class PlanError(ValueError):
    """The config is valid but cannot run on these data (no file in the period, region outside the grid)."""


@dataclass
class RunPlan:
    mode: str
    settings: object
    maps: object
    extent: list
    """Region read: min_lon, max_lon, min_lat, max_lat (region + margin)."""
    start_utc: datetime
    end_utc: datetime
    files: list
    missing_months: list
    cells: int
    hours: int

    def summary(self) -> list[str]:
        """The lines shown before a run (console and page)."""
        s = self.settings
        what = {"extract": f"extract_region = {s.extract_region}", "visualize": f"maps {', '.join(self.maps.outputs)}",
                "thiessen": f"{len(s.shapes)} shapefile(s)"}[self.mode]
        e = self.extent
        lines = [f"Ringkasan: {self.mode} ({what})",
                 f"  wilayah dibaca : lon {e[0]:.2f}..{e[1]:.2f}, lat {e[2]:.2f}..{e[3]:.2f} (margin {s.margin:g})",
                 f"  periode        : hari hujan {s.start_date} .. {s.end_date} ({s.time_zone}) "
                 f"= UTC {self.start_utc:%Y-%m-%d %H:%M} .. {self.end_utc:%Y-%m-%d %H:%M}",
                 f"  ukuran         : {self.cells} sel x {self.hours} jam = "
                 f"{self.cells * self.hours / 1e6:.1f} juta nilai jam-an",
                 f"  keluaran       : {s.output_folder}"]
        if self.missing_months:
            lines.append(f"  tanpa berkas   : {len(self.missing_months)} bulan ({' '.join(self.missing_months[:6])}"
                         f"{' ...' if len(self.missing_months) > 6 else ''})")
        return lines


def prepare_run(config: dict, mode: str) -> RunPlan:
    """Check the config for ``mode`` and work out what the run reads, without reading the data.

    Raises SettingsError (a key is missing or wrong) or PlanError (no data for it).
    """
    if mode not in MODES:
        raise SettingsError(f"mode {mode!r}; use one of {list(MODES)}")
    settings = read_settings(config, extract=(mode in ("extract", "visualize")), thiessen=(mode == "thiessen"))
    maps = read_map_settings(config)

    # region read: extract_region (extract, visualize) or all shapefiles (thiessen), + region_margin_deg
    region = shapes_bounds(settings.shapes) if mode == "thiessen" else extract_bounds(settings)
    extent = list(add_margin(region, settings.margin))

    # start_date .. end_date are local rain days; read the UTC hours they hold
    start_utc, end_utc = rain_day_utc_window(settings.start_date, settings.end_date, settings.day_start_hour,
                                             settings.daily_date_label, settings.time_zone)
    files, missing = find_month_files(settings.gsmap_folder, start_utc, end_utc)
    if not files:
        raise PlanError(f"no monthly .nc file under {settings.gsmap_folder} for "
                        f"{settings.start_date} .. {settings.end_date}")
    try:
        _, _, rows, cols = centre_cells(files[0], extent)   # the same cells read_netcdf reads
    except ValueError as exc:
        raise PlanError(f"region of {'shape_<name>' if mode == 'thiessen' else 'extract_region'}: {exc}") from None
    hours = int((end_utc - start_utc).total_seconds() // 3600) + 1
    return RunPlan(mode, settings, maps, extent, start_utc, end_utc, files, missing, len(rows) * len(cols), hours)


def _stop(config_path, message):
    print(f"\nGalat config ({config_path}): {message}")
    raise SystemExit(1)


def execute(plan: RunPlan) -> None:
    """Read the data of ``plan`` and run its mode."""
    maps = plan.maps
    if maps.relief_download and plan.mode == "visualize":
        try:
            download_relief(maps.relief_file)
        except (OSError, ValueError) as exc:   # network, disk, unexpected file: the relief is optional
            print(f"  note: relief download failed ({exc}); maps without relief, tried again next run")
            maps = replace(maps, relief_file=None, relief_download=False)
    settings = plan.settings
    data_subset, times, lon, lat = read_netcdf(plan.files, plan.start_utc, plan.end_utc, extent=plan.extent)
    grid = RainGrid.from_read(data_subset, times, lon, lat, settings)
    if plan.mode == "extract":
        run_extract(grid, settings, maps, plan.extent)
    elif plan.mode == "visualize":
        plot_maps(grid, settings, maps, plan.extent)
    else:
        run_thiessen(grid, settings, maps, plan.extent)


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
        plan = prepare_run(config, mode)
    except (SettingsError, PlanError) as exc:
        _stop(config_path, exc)
    print("Settings:")
    print(plan.settings.describe())
    print(plan.maps.describe())
    print()
    print("\n".join(plan.summary()))
    if menu:
        try:
            answer = input("Lanjut? [Y/n]: ").strip().lower()
        except EOFError:
            answer = "n"
        if answer in ("n", "no", "tidak", "t"):
            print("Dibatalkan.")
            return
    execute(plan)
