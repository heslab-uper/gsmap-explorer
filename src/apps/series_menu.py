"""Choices of the series mode: asked on screen, or taken from the config with ``--no-menu``.

Defaults of the menu: the answers of the last menu run (``series_last.txt``
next to the config file, not in the repository), else the config keys
``gsmap_data_folder`` (a folder of products, each with an ``NC`` folder, or a
folder of monthly .nc files), ``gsmap_product`` (e.g. ``STD/V8/GA``),
``series_selection`` (points, box, shape), ``path_points``, ``min_lon`` ..
``max_lat``, ``path_shp``, ``start_date``, ``end_date`` (rain-day dates),
``series_outputs``, ``wilayah_waktu``. Also read: ``day_start_hour``,
``daily_date_label``, ``path_out``, ``series_confirm_values`` (without the
menu, stop above this many hourly values).
"""

from datetime import date, datetime
from pathlib import Path

from apps.extract_points import read_points_file
from apps.extract_series import OUTPUTS, SELECTIONS, ZONES, SeriesChoice, estimate, find_products, select_cells
from core.local_time import local_offset_hours
from core.reader import MONTH_FILE, find_month_files, grid_axes
from utils.analysis_settings import SettingsError, read_daily_settings
from utils.config_reader import read_config

PORTAL = "https://heslab-uper.com/data/hujan-satelit"

LAST_KEYS = ("gsmap_data_folder", "gsmap_product", "series_selection", "path_points", "min_lon", "max_lon",
             "min_lat", "max_lat", "path_shp", "start_date", "end_date", "series_outputs", "wilayah_waktu")
"""Answers remembered for the next menu run."""

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


def _data_folder(text: str) -> tuple[str, dict]:
    """A folder of products ({label: NC folder}) or of monthly .nc files ({label: the folder})."""
    folder = Path(text)
    if not folder.is_dir():
        raise FileNotFoundError(f"folder {text} not found")
    products = find_products(folder)
    if products:
        return text, products
    if any(MONTH_FILE.search(f.name) for f in folder.rglob("*.nc")):
        label = "_".join(folder.resolve().parts[-4:-1]) if folder.name == "NC" else folder.resolve().name
        return text, {label: folder}
    raise FileNotFoundError(f"no GSMaP monthly .nc file (*_YYYY_MM.nc or *_YYYYMM.nc) in {text}; "
                            f"download them from {PORTAL} into data/raw, or type the folder that holds them")


def _available_months(path_nc) -> list[str]:
    """YYYY-MM of every monthly file under ``path_nc``, sorted."""
    return sorted(f"{m.group(1)}-{m.group(2)}" for f in Path(path_nc).rglob("*.nc") if (m := MONTH_FILE.search(f.name)))


def read_last(path: Path) -> dict:
    """Answers of the last menu run, or {} (no file yet)."""
    return {k: v for k, v in read_config(path).items() if k in LAST_KEYS} if path.is_file() else {}


def write_last(path: Path, choice: SeriesChoice, data_folder: str) -> None:
    values = {"gsmap_data_folder": data_folder, "gsmap_product": choice.product, "series_selection": choice.selection,
              "start_date": f"{choice.start}", "end_date": f"{choice.end}",
              "series_outputs": ",".join(choice.outputs), "wilayah_waktu": choice.zone}
    if choice.points_file:
        values["path_points"] = choice.points_file
    if choice.box:
        values.update(zip(("min_lon", "max_lon", "min_lat", "max_lat"), (f"{v:g}" for v in choice.box)))
    if choice.shapefile:
        values["path_shp"] = choice.shapefile
    lines = ["# Last answers of the series menu (gsmap-explorer); defaults of the next run.",
             "# Written by the program, not in the repository; delete it to go back to config/input.txt."]
    path.write_text("\n".join(lines + [f"{k} = {v}" for k, v in values.items()]) + "\n", encoding="utf-8")


def ask_series_choice(config, *, interactive: bool, last_path: Path | None = None) -> SeriesChoice:
    """All choices of one series run (see the module docstring)."""
    day_start_hour, date_label = read_daily_settings(config)
    say = print if interactive else (lambda *args: None)
    print("=" * 60)
    print("  EKSTRAKSI DERET HUJAN GSMaP" + ("" if interactive else "  (dari config, tanpa menu)"))
    print("=" * 60)
    last = read_last(last_path) if interactive and last_path else {}
    if last:
        say(f"(bawaan = pilihan terakhir, {last_path}; Enter = pakai)")
    config = {**config, **last}

    # 1. data folder and product
    data_folder, products = _ask("\nFolder data GSMaP", config.get("gsmap_data_folder") or "data/raw",
                                 _data_folder, interactive, "gsmap_data_folder")
    names = list(products)
    if len(names) > 1:
        say(f"\nProduk GSMaP di {data_folder}:")
        for k, n in enumerate(names, 1):
            say(f"  {k:2d}. {n}")
        default = config.get("gsmap_product") if config.get("gsmap_product") in names else names[0]
        product = _ask("Pilih produk (nomor atau nama)", default, lambda t: _pick(t, names, many=False),
                       interactive, "gsmap_product")
    else:
        product = names[0]
        say(f"  produk: {product}")
    path_nc = str(products[product])
    months = _available_months(path_nc)
    say(f"  data tersedia: {months[0]} .. {months[-1]} ({len(months)} bulan)")

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
        raise FileNotFoundError(f"no monthly .nc file under {path_nc} for {start} .. {end}; "
                                f"the folder holds {months[0]} .. {months[-1]}")
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
        if last_path:
            write_last(last_path, choice, data_folder)
    elif n_values > limit:
        raise ValueError(f"{n_values / 1e6:.1f} million hourly values exceed series_confirm_values = {limit:g}; "
                         f"run with the menu to confirm, or choose a smaller region or period")
    return choice
