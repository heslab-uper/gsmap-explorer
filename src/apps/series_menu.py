"""Choices of the series mode: asked on screen with the config values as defaults, or taken from the config.

Config keys (defaults of the menu; used as they are with ``--no-menu``):
``gsmap_archive_root`` (folder holding NOW, NRT, STD; ``None`` = use ``path_nc``),
``gsmap_product`` (e.g. ``STD/V8/GA``), ``series_selection`` (points, box, shape),
``path_points``, ``min_lon`` .. ``max_lat``, ``path_shp``, ``start_date``,
``end_date`` (rain-day dates), ``series_outputs``, ``wilayah_waktu``,
``day_start_hour``, ``daily_date_label``, ``path_out``,
``series_confirm_values`` (ask before writing more hourly values than this).
"""

from datetime import date, datetime
from pathlib import Path

from apps.extract_points import read_points_file
from apps.extract_series import OUTPUTS, SELECTIONS, ZONES, SeriesChoice, estimate, find_products, select_cells
from core.local_time import local_offset_hours
from core.reader import find_month_files, grid_axes
from utils.analysis_settings import SettingsError, read_daily_settings

SELECTION_LABELS = {"points": "titik koordinat (CSV name,lat,lon)", "box": "box (min/max lon dan lat)",
                    "shape": "batas luar (total bounds) shapefile"}
OUTPUT_LABELS = {"hourly": "jam-jaman", "daily": "harian", "monthly": "bulanan", "yearly": "tahunan"}


class Cancelled(Exception):
    """The user answered no to the last question."""


def _ask(question: str, default: str, check, interactive: bool, key: str):
    """Ask until ``check`` accepts the answer (Enter = default = config ``key``); without a menu, check the default once."""
    while True:
        answer = input(f"{question} [{default}]: ").strip() if interactive else ""
        try:
            return check(answer or default)
        except (ValueError, SettingsError, FileNotFoundError) as exc:
            if not interactive:
                raise SettingsError(f"config key '{key}' = {default!r}: {exc}") from None
            print(f"  ! {exc}")


def _date(text: str) -> date:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{text!r} is not a date YYYY-MM-DD") from None


def _number(text: str, lo: float, hi: float) -> float:
    try:
        x = float(text)
    except ValueError:
        raise ValueError(f"{text!r} is not a number") from None
    if not lo <= x <= hi:
        raise ValueError(f"{x} is outside {lo}..{hi}")
    return x


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


def _existing_file(text: str) -> str:
    if not Path(text).is_file():
        raise FileNotFoundError(f"{text} not found")
    return text


def ask_series_choice(config, *, interactive: bool) -> SeriesChoice:
    """All choices of one series run (see the module docstring)."""
    day_start_hour, date_label = read_daily_settings(config)
    say = print if interactive else (lambda *args: None)
    print("=" * 60)
    print("  EKSTRAKSI DERET HUJAN GSMaP" + ("" if interactive else "  (dari config, tanpa menu)"))
    print("=" * 60)

    # 1. product
    root = config.get("gsmap_archive_root")
    if root and root != "None":
        products = find_products(root)
        if not products:
            raise FileNotFoundError(f"config key 'gsmap_archive_root': no NC folder under {root}")
        names = list(products)
        say(f"\nProduk GSMaP di {root}:")
        for k, n in enumerate(names, 1):
            say(f"  {k:2d}. {n}")
        default = config.get("gsmap_product") or names[0]
        product = _ask("Pilih produk (nomor atau nama)", default, lambda t: _pick(t, names, many=False), interactive, "gsmap_product")
        path_nc = str(products[product])
    else:
        path_nc = config.get("path_nc")
        if not path_nc or not Path(path_nc).is_dir():
            raise FileNotFoundError(f"config key 'path_nc': folder {path_nc} not found")
        product = Path(path_nc).name

    # 2. region
    say("\nWilayah:")
    for k, s in enumerate(SELECTIONS, 1):
        say(f"  {k}. {SELECTION_LABELS[s]}")
    selection = _ask("Pilih wilayah", config.get("series_selection") or "points",
                     lambda t: _pick(t, list(SELECTIONS), many=False), interactive, "series_selection")
    choice_kw = {}
    if selection == "points":
        choice_kw["points_file"] = _ask("  Berkas titik", config.get("path_points") or "config/points.csv",
                                        lambda t: (read_points_file(t), t)[1], interactive, "path_points")
    elif selection == "box":
        box = []
        for key, lo, hi in (("min_lon", -180, 180), ("max_lon", -180, 180), ("min_lat", -90, 90), ("max_lat", -90, 90)):
            box.append(_ask(f"  {key}", config.get(key) or "", lambda t, lo=lo, hi=hi: _number(t, lo, hi), interactive, key))
        if not (box[0] < box[1] and box[2] < box[3]):
            raise ValueError(f"box: min_lon < max_lon and min_lat < max_lat required, got {box}")
        choice_kw["box"] = tuple(box)
    else:
        choice_kw["shapefile"] = _ask("  Shapefile", config.get("path_shp") or "", _existing_file, interactive, "path_shp")

    # 3. period
    say(f"\nPeriode = tanggal hari hujan ({day_start_hour:02d}.00-{day_start_hour:02d}.00 waktu lokal):")
    start = _ask("  Tanggal awal (YYYY-MM-DD)", config.get("start_date") or "", _date, interactive, "start_date")
    end = _ask("  Tanggal akhir (YYYY-MM-DD)", config.get("end_date") or "", _date, interactive, "end_date")
    if end < start:
        raise ValueError(f"end date {end} is before start date {start}")

    # 4. outputs
    say("\nKeluaran:")
    for k, o in enumerate(OUTPUTS, 1):
        say(f"  {k}. {OUTPUT_LABELS[o]}")
    outputs = _ask("Pilih keluaran (mis. 1,2,3,4)", config.get("series_outputs") or "hourly,daily,monthly,yearly",
                   lambda t: _pick(t, list(OUTPUTS), many=True), interactive, "series_outputs")

    # 5. time zone (+1 h: the label marks the end of the recorded hour)
    say("\nZona waktu (label = akhir jam pencatatan, jadi zona + 1 jam):")
    for k, z in enumerate(ZONES, 1):
        off = local_offset_hours(z)
        say(f"  {k}. {z}: UTC + {off - 1} jam zona + 1 jam = UTC + {off} jam")
    zone = _ask("Pilih zona", config.get("wilayah_waktu") or "WIB", lambda t: _pick(t, list(ZONES), many=False),
                interactive, "wilayah_waktu")

    choice = SeriesChoice(product=product, path_nc=path_nc, selection=selection, start=start, end=end,
                          outputs=[o for o in OUTPUTS if o in outputs], zone=zone, day_start_hour=day_start_hour,
                          date_label=date_label, path_out=config.get("path_out") or "data/output", **choice_kw)

    # size check and confirmation
    files, _ = find_month_files(path_nc, datetime.combine(start, datetime.min.time()),
                                datetime.combine(end, datetime.min.time()))
    if not files:
        raise FileNotFoundError(f"no monthly .nc file under {path_nc} for {start} .. {end}")
    lat, lon = grid_axes(files[0])
    n_cells = len(select_cells(choice, lat, lon))
    hours, n_values = estimate(choice, n_cells)
    print("\nRingkasan:")
    print(choice.describe())
    print(f"  ukuran    : {n_cells} kolom x {hours} jam = {n_values / 1e6:.1f} juta nilai jam-an")
    limit = float(config.get("series_confirm_values") or 50e6)
    if interactive:
        if input("Lanjut? [Y/n]: ").strip().lower() in ("n", "no", "tidak", "t"):
            raise Cancelled()
    elif n_values > limit:
        raise ValueError(f"{n_values / 1e6:.1f} million hourly values exceed series_confirm_values = {limit:g}; "
                         f"run with the menu to confirm, or choose a smaller region or period")
    return choice
