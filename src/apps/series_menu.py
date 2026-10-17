"""Choices of the series mode: asked on screen, or taken from the config with ``--no-menu``.

Defaults of the menu are the config keys ``gsmap_folder``, ``series_region``
(points, box, shape), ``points_file``, ``min_lon`` .. ``max_lat``,
``shapefile``, ``start_date``, ``end_date`` (rain-day dates),
``series_outputs`` and ``time_zone``; an answer changes this run only. Also
read: ``day_start_hour``, ``daily_date_label``, ``output_folder``, ``region_margin_deg``,
``series_max_values`` (without the menu, stop above this many hourly values).
Menu answers and config values are checked by the same functions
(``utils.settings``).
"""

from datetime import datetime
from pathlib import Path

from apps.extract_points import read_points_file
from apps.extract_series import OUTPUTS, SELECTIONS, ZONES, SeriesChoice, estimate, product_label, select_cells
from core.local_time import local_offset_hours
from core.reader import MONTH_FILE, find_month_files, grid_axes
from core.shapefile import read_shapefile
from utils.settings import (BOX_KEYS, SettingsError, check, check_box, check_date, check_file, check_gsmap_folder,
                            check_number, check_output_folder, int_key, read_daily_settings, read_margin)

SELECTION_LABELS = {"points": "titik koordinat (CSV name,lat,lon)", "box": "box (min/max lon dan lat)",
                    "shape": "batas luar (total bounds) shapefile"}
OUTPUT_LABELS = {"hourly": "jam-jaman", "daily": "harian", "monthly": "bulanan", "yearly": "tahunan"}


class Cancelled(Exception):
    """The user answered no to the last question."""


def _ask(question: str, default: str, check, interactive: bool, key: str):
    """Ask until ``check`` accepts the answer (Enter = default = config ``key``); without a menu, check the default once."""
    while True:
        try:
            answer = input(f"{question} [{default}]: ").strip() if interactive else ""
        except EOFError:   # input closed (e.g. Ctrl+Z): stop quietly
            raise Cancelled() from None
        text = answer or default
        try:
            if not text:
                raise ValueError("empty; fill it in the config or type a value")
            return check(text)
        except (ValueError, SettingsError, FileNotFoundError) as exc:
            if not interactive:
                raise SettingsError(f"config key '{key}' = {default!r}: {exc}") from None
            print(f"  ! {exc}")


def _pick(text: str, options: list, *, many: bool):
    """Numbers (1-based) or names of ``options``; comma-separated when ``many``."""
    parts = [p.strip() for p in text.split(",") if p.strip()] if many else [text.strip()]
    out = []
    for p in parts:
        if p.isdigit() and 1 <= int(p) <= len(options):
            out.append(options[int(p) - 1])
        elif p in options:
            out.append(p)
        else:
            raise ValueError(f"{p!r}: choose a number 1..{len(options)} or a name from the list")
    if not out or len(set(out)) != len(out):
        raise ValueError("choose at least one option, each once")
    return out if many else out[0]


def _points_file(text: str) -> str:
    path = check_file(text)
    read_points_file(path)
    return str(path)


def _shapefile(text: str) -> str:
    path = check_file(text)
    read_shapefile(path)
    return str(path)


def _available_months(folder) -> list[str]:
    """YYYY-MM of every monthly file under ``folder``, sorted."""
    return sorted(f"{m.group(1)}-{m.group(2)}" for f in Path(folder).rglob("*.nc") if (m := MONTH_FILE.search(f.name)))


def ask_series_choice(config, *, interactive: bool) -> SeriesChoice:
    """All choices of one series run (see the module docstring)."""
    day_start_hour, date_label = read_daily_settings(config)
    output_folder = check(config, "output_folder", check_output_folder)
    limit = int_key(config, "series_max_values", 1)
    margin = read_margin(config)
    say = print if interactive else (lambda *args: None)
    print("=" * 60)
    print("  EKSTRAKSI DERET HUJAN GSMaP" + ("" if interactive else "  (dari config, tanpa menu)"))
    print("=" * 60)

    # 1. data folder (one product)
    folder = _ask("\nFolder data GSMaP (satu produk)", config.get("gsmap_folder", ""), check_gsmap_folder,
                  interactive, "gsmap_folder")
    product = product_label(folder)
    months = _available_months(folder)
    say(f"  produk: {product}; data tersedia: {months[0]} .. {months[-1]} ({len(months)} bulan)")

    # 2. region
    say("\nWilayah:")
    for k, s in enumerate(SELECTIONS, 1):
        say(f"  {k}. {SELECTION_LABELS[s]}")
    selection = _ask("Pilih wilayah", config.get("series_region", ""),
                     lambda t: _pick(t, list(SELECTIONS), many=False), interactive, "series_region")
    choice_kw = {}
    if selection == "points":
        choice_kw["points_file"] = _ask("  Berkas titik", config.get("points_file", ""), _points_file,
                                        interactive, "points_file")
    elif selection == "box":
        box = [_ask(f"  {key}", config.get(key, ""), lambda t, lo=lo, hi=hi: check_number(t, lo, hi), interactive, key)
               for key, lo, hi in BOX_KEYS]
        choice_kw["box"] = check_box(box)
    else:
        choice_kw["shapefile"] = _ask("  Shapefile", config.get("shapefile", ""), _shapefile, interactive, "shapefile")

    # 3. period
    say(f"\nPeriode = tanggal hari hujan ({day_start_hour:02d}.00-{day_start_hour:02d}.00 waktu lokal):")
    start = _ask("  Tanggal awal (YYYY-MM-DD)", config.get("start_date", ""), check_date, interactive, "start_date")
    end = _ask("  Tanggal akhir (YYYY-MM-DD)", config.get("end_date", ""), check_date, interactive, "end_date")
    if end < start:
        raise SettingsError(f"end date {end} is before start date {start}")

    # 4. outputs
    say("\nKeluaran:")
    for k, o in enumerate(OUTPUTS, 1):
        say(f"  {k}. {OUTPUT_LABELS[o]}")
    outputs = _ask("Pilih keluaran (mis. 1,2,3,4)", config.get("series_outputs", ""),
                   lambda t: _pick(t, list(OUTPUTS), many=True), interactive, "series_outputs")

    # 5. time zone (+1 h: the label marks the end of the recorded hour)
    say("\nZona waktu (label = akhir jam pencatatan, jadi zona + 1 jam):")
    for k, z in enumerate(ZONES, 1):
        off = local_offset_hours(z)
        say(f"  {k}. {z}: UTC + {off - 1} jam zona + 1 jam = UTC + {off} jam")
    zone = _ask("Pilih zona", config.get("time_zone", ""), lambda t: _pick(t, list(ZONES), many=False),
                interactive, "time_zone")

    choice = SeriesChoice(product=product, path_nc=str(folder), selection=selection, start=start, end=end,
                          outputs=[o for o in OUTPUTS if o in outputs], zone=zone, day_start_hour=day_start_hour,
                          date_label=date_label, margin=margin, path_out=str(output_folder), **choice_kw)

    # size check and confirmation
    files, _ = find_month_files(folder, datetime.combine(start, datetime.min.time()),
                                datetime.combine(end, datetime.min.time()))
    if not files:
        raise FileNotFoundError(f"no monthly .nc file under {folder} for {start} .. {end}; "
                                f"the folder holds {months[0]} .. {months[-1]}")
    lat, lon = grid_axes(files[0])
    n_cells = len(select_cells(choice, lat, lon))
    hours, n_values = estimate(choice, n_cells)
    print("\nRingkasan:")
    print(choice.describe())
    print(f"  ukuran    : {n_cells} kolom x {hours} jam = {n_values / 1e6:.1f} juta nilai jam-an")
    if interactive:
        if input("Lanjut? [Y/n]: ").strip().lower() in ("n", "no", "tidak", "t"):
            raise Cancelled()
    elif n_values > limit:
        raise ValueError(f"{n_values / 1e6:.1f} million hourly values exceed series_max_values = {limit}; "
                         f"run with the menu to confirm, or choose a smaller region or period")
    return choice
