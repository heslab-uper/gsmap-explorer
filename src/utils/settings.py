"""Settings shared by the modes, read from the config and checked before any data is read.

Every choice comes from the config (no defaults in code). A missing or
invalid key raises ``SettingsError`` naming the key. Relative paths are
taken from the folder of run.py (``utils.config_reader.resolve_path``).

The ``check_*`` functions take the text of one value and return it parsed
(or raise ``ValueError``); the series menu checks its answers with the same
functions.
"""

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from core.local_time import TIME_ZONE_HOURS
from core.reader import MONTH_FILE
from utils.config_reader import PROGRAM_DIR, resolve_path
from utils.relief import relief_path


class SettingsError(ValueError):
    """A config key is missing or invalid; the message names the key."""


# ---- one value ---------------------------------------------------------------

def check_gsmap_folder(text: str) -> Path:
    """Folder of one GSMaP product holding monthly files, directly or in year subfolders."""
    folder = resolve_path(text)
    if not folder.is_dir():
        raise FileNotFoundError(f"folder {folder} not found")
    if not any(MONTH_FILE.search(f.name) for f in folder.rglob("*.nc")):
        raise FileNotFoundError(f"no monthly GSMaP file (*_YYYYMM.nc or *_YYYY_MM.nc) in {folder} "
                                f"or its subfolders")
    return folder


def check_output_folder(text: str) -> Path:
    """Output folder; inside the program folder only under data/ (ignored by git), so results never reach GitHub."""
    folder = resolve_path(text)
    if folder.exists() and not folder.is_dir():
        raise ValueError(f"{folder} exists and is not a folder")
    inside = folder.resolve().is_relative_to(PROGRAM_DIR)
    if inside and not folder.resolve().is_relative_to(PROGRAM_DIR / "data"):
        raise ValueError(f"{folder} is inside the program folder but not under data/; "
                         f"use data/... (not in git) or a folder outside {PROGRAM_DIR}")
    return folder


def check_file(text: str) -> Path:
    path = resolve_path(text)
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")
    return path


def check_date(text: str) -> date:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{text!r} is not a date YYYY-MM-DD") from None


def check_number(text: str, lo: float, hi: float) -> float:
    try:
        x = float(text)
    except ValueError:
        raise ValueError(f"{text!r} is not a number") from None
    if not lo <= x <= hi:
        raise ValueError(f"{x:g} is outside {lo}..{hi}")
    return x


def check_time_zone(text: str) -> str:
    if text not in TIME_ZONE_HOURS:
        raise ValueError(f"{text!r}: use one of {list(TIME_ZONE_HOURS)}")
    return text


# ---- one key -----------------------------------------------------------------

LOCAL_KEYS = ("gsmap_folder", "basemap_relief_file")
"""Keys holding paths of one computer: they belong in config/input.local.txt."""

LOCAL_HINT = "set it in config/input.local.txt (a copy of config/input.local.example.txt)"


def get(cfg: dict, key: str) -> str:
    v = cfg.get(key)
    if v is None or v == "":
        hint = f"; {LOCAL_HINT}" if key in LOCAL_KEYS else ""
        raise SettingsError(f"config key '{key}' is missing or empty{hint}")
    return v


def optional(cfg: dict, key: str) -> str | None:
    """The value, or None when the key is empty. The key itself must be present."""
    if key not in cfg:
        raise SettingsError(f"config key '{key}' is missing (leave it empty when not used)")
    return cfg[key] or None


def check(cfg: dict, key: str, func, *args):
    """``func(value, *args)``; its error becomes a SettingsError naming the key."""
    v = get(cfg, key)
    try:
        return func(v, *args)
    except (ValueError, FileNotFoundError) as exc:
        raise SettingsError(f"config key '{key}' = {v!r}: {exc}") from None


def int_key(cfg, key, lo, hi=None) -> int:
    v = get(cfg, key)
    try:
        n = int(v)
    except ValueError:
        raise SettingsError(f"config key '{key}' = {v!r}; expected an integer") from None
    if n < lo or (hi is not None and n > hi):
        raise SettingsError(f"config key '{key}' = {n}; expected {lo}..{hi if hi is not None else ''}")
    return n


def float_key(cfg, key, lo, hi, *, lo_open=True) -> float:
    v = get(cfg, key)
    try:
        x = float(v)
    except ValueError:
        raise SettingsError(f"config key '{key}' = {v!r}; expected a number") from None
    if x < lo or (lo_open and x == lo) or x > hi:
        raise SettingsError(f"config key '{key}' = {x}; expected {'>' if lo_open else '>='} {lo} and <= {hi}")
    return x


def choice_key(cfg, key, allowed):
    v = get(cfg, key)
    if v not in allowed:
        raise SettingsError(f"config key '{key}' = {v!r}; use one of {list(allowed)}")
    return v


def list_key(cfg, key) -> list[str]:
    items = [p.strip() for p in get(cfg, key).split(",") if p.strip()]
    if len(set(items)) != len(items):
        raise SettingsError(f"config key '{key}' repeats a value: {items}")
    return items


def read_daily_settings(cfg: dict) -> tuple[int, str]:
    """``day_start_hour`` and ``daily_date_label``, checked (every mode)."""
    return int_key(cfg, "day_start_hour", 0, 23), choice_key(cfg, "daily_date_label", ("start", "end"))


def read_margin(cfg: dict) -> float:
    """``region_margin_deg``: degrees added on every side of the box or shapefile bounds."""
    return float_key(cfg, "region_margin_deg", 0, 5, lo_open=False)


def add_margin(bounds, margin: float) -> tuple:
    """(min_lon, max_lon, min_lat, max_lat) widened by ``margin`` degrees on every side."""
    min_lon, max_lon, min_lat, max_lat = bounds
    return (min_lon - margin, max_lon + margin, min_lat - margin, max_lat + margin)


BOX_KEYS = (("min_lon", -180, 180), ("max_lon", -180, 180), ("min_lat", -90, 90), ("max_lat", -90, 90))


def check_box(box) -> tuple:
    if not (box[0] < box[1] and box[2] < box[3]):
        raise SettingsError(f"config keys min_lon..max_lat = {tuple(box)}: "
                            f"min_lon < max_lon and min_lat < max_lat required")
    return tuple(box)


def read_box(cfg: dict) -> tuple:
    """(min_lon, max_lon, min_lat, max_lat), checked."""
    return check_box([check(cfg, key, check_number, lo, hi) for key, lo, hi in BOX_KEYS])


# ---- shapefiles: shape_<name> = <path> | <id field> -------------------------

@dataclass(frozen=True)
class Shape:
    name: str
    """The part after shape_ (a-z, 0-9, _): names the output folder of this shapefile."""
    path: Path
    id_field: str
    """Column naming each region; polygons with the same value form one region."""


def read_shapes(cfg: dict) -> list:
    """Every ``shape_<name> = <path> | <id field>`` key (config/input.local.txt), checked: file, CRS, id field.

    May be empty; the modes that need a shapefile say so.
    """
    from core.shapefile import read_shapefile

    shapes = []
    for key, value in cfg.items():
        if not key.startswith("shape_"):
            continue
        name = key[len("shape_"):]
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise SettingsError(f"config key '{key}': the name after shape_ uses a-z, 0-9 and _ only")
        if value.count("|") != 1:
            raise SettingsError(f"config key '{key}' = {value!r}; expected <path> | <id field>")
        text, field = (p.strip() for p in value.split("|"))
        path = resolve_path(text)
        if not path.is_file():
            raise SettingsError(f"config key '{key}': {path} not found")
        try:
            read_shapefile(path, field)
        except ValueError as exc:
            raise SettingsError(f"config key '{key}': {exc}") from None
        shapes.append(Shape(name, path, field))
    return shapes


def shapes_bounds(shapes: list) -> tuple:
    """(min_lon, max_lon, min_lat, max_lat) of all shapefiles together, EPSG:4326."""
    from core.shapefile import read_shapefile

    b = [read_shapefile(s.path).total_bounds for s in shapes]
    return (min(x[0] for x in b), max(x[2] for x in b), min(x[1] for x in b), max(x[3] for x in b))


# ---- the modes extract, visualize, thiessen ----------------------------------

@dataclass(frozen=True)
class Settings:
    gsmap_folder: Path
    output_folder: Path
    box: tuple
    """(min_lon, max_lon, min_lat, max_lat)."""
    margin: float
    """``region_margin_deg``: added on every side of the box or the shapefile bounds."""
    time_zone: str
    start_date: date
    """First rain day (local)."""
    end_date: date
    """Last rain day (local)."""
    day_start_hour: int
    daily_date_label: str
    year_start_month: int
    """First month of a year for the yearly rain and the annual maximum (1 = calendar year)."""
    min_valid_fraction: float
    """An annual maximum is taken when at least this fraction of the days of the year is present."""
    rain_outputs: list
    """Tables written by extract and thiessen (``apps.rain_tables.RAIN_OUTPUTS``)."""
    shapes: list
    """Shapefiles of the shape_<name> keys (``Shape``), possibly empty."""
    extract_region: str
    """Mode extract: box, shape (each shape_<name>) or points (points_file)."""
    points_file: Path | None
    """CSV name,lat,lon of extract_region = points (checked only then)."""

    def describe(self) -> str:
        return "\n".join(f"  {k}: {v}" for k, v in asdict(self).items())


def read_rain_outputs(cfg: dict) -> list:
    from apps.rain_tables import RAIN_OUTPUTS
    outputs = list_key(cfg, "rain_outputs")
    if not outputs or any(o not in RAIN_OUTPUTS for o in outputs):
        raise SettingsError(f"config key 'rain_outputs' = {outputs}; use one or more of {list(RAIN_OUTPUTS)}")
    return [o for o in RAIN_OUTPUTS if o in outputs]


EXTRACT_REGIONS = ("box", "shape", "points")


def read_settings(cfg: dict, *, extract: bool = False, thiessen: bool = False) -> Settings:
    """Check the shared keys of the config and return them (``extract``, ``thiessen``: also what that mode needs)."""
    shapes = read_shapes(cfg)
    extract_region = choice_key(cfg, "extract_region", EXTRACT_REGIONS)
    points_file = None
    if extract and extract_region == "shape" and not shapes:
        raise SettingsError(f"extract_region = shape needs at least one key shape_<name> = <path> | <id field>; "
                            f"{LOCAL_HINT}")
    if thiessen and not shapes:
        raise SettingsError(f"mode thiessen needs at least one key shape_<name> = <path> | <id field>; {LOCAL_HINT}")
    if extract and extract_region == "points":
        from apps.extract_points import read_points_file
        points_file = check(cfg, "points_file", check_file)
        try:
            read_points_file(points_file)
        except (ValueError, FileNotFoundError) as exc:
            raise SettingsError(f"config key 'points_file': {exc}") from None
    start, end = check(cfg, "start_date", check_date), check(cfg, "end_date", check_date)
    if end < start:
        raise SettingsError(f"config key 'end_date' = {end} is before start_date = {start}")
    day_start_hour, date_label = read_daily_settings(cfg)
    return Settings(
        gsmap_folder=check(cfg, "gsmap_folder", check_gsmap_folder),
        output_folder=check(cfg, "output_folder", check_output_folder),
        box=read_box(cfg),
        margin=read_margin(cfg),
        time_zone=check(cfg, "time_zone", check_time_zone),
        start_date=start,
        end_date=end,
        day_start_hour=day_start_hour,
        daily_date_label=date_label,
        year_start_month=int_key(cfg, "year_start_month", 1, 12),
        min_valid_fraction=float_key(cfg, "min_valid_fraction", 0, 1),
        rain_outputs=read_rain_outputs(cfg),
        shapes=shapes,
        extract_region=extract_region,
        points_file=points_file,
    )


# ---- maps --------------------------------------------------------------------

MAP_OUTPUTS = ("hourly", "daily", "monthly", "yearly")


@dataclass(frozen=True)
class MapSettings:
    outputs: list
    """Maps of the visualize mode, from ``MAP_OUTPUTS``."""
    levels: dict
    """Class bounds per map: {"hourly": [...], "daily": ..., "monthly": ..., "yearly": ...}."""
    names: dict
    """Category name of each class per map (one per bound: bound i .. bound i+1, the last open), or []."""
    label_max: int
    """Grid points or shapefile regions are labelled only up to this many (0 = never)."""
    relief_file: Path | None
    """Shaded relief raster drawn under the map, or None."""
    relief_download: bool
    """``relief_file`` is missing and is downloaded before the data are read (``utils.relief``)."""
    cities: int
    """Largest Natural Earth places in the map labelled (0 = none)."""

    def describe(self) -> str:
        return "\n".join(f"  map {k}: {v}" for k, v in asdict(self).items())


def read_levels(cfg: dict, key: str) -> list[float]:
    """Class bounds: at least 3 numbers > 0, strictly increasing."""
    out = []
    for p in list_key(cfg, key):
        try:
            out.append(float(p))
        except ValueError:
            raise SettingsError(f"config key '{key}': {p!r} is not a number") from None
    if len(out) < 3 or out[0] <= 0 or any(b <= a for a, b in zip(out, out[1:])):
        raise SettingsError(f"config key '{key}' = {out}; expected at least 3 numbers > 0, increasing")
    return out


def read_names(cfg: dict, kind: str, n: int) -> list[str]:
    """``map_names_<kind>``: empty, or one name per class (as many as the class bounds)."""
    key = f"map_names_{kind}"
    if optional(cfg, key) is None:
        return []
    names = [p.strip() for p in cfg[key].split(",")]
    if len(names) != n or any(not x for x in names):
        raise SettingsError(f"config key '{key}' has {len(names)} name(s); map_levels_{kind} has {n} classes")
    return names


def read_map_settings(cfg: dict) -> MapSettings:
    """Check the map keys of the config and return them."""
    outputs = list_key(cfg, "map_outputs")
    if not outputs or any(o not in MAP_OUTPUTS for o in outputs):
        raise SettingsError(f"config key 'map_outputs' = {outputs}; use one or more of {list(MAP_OUTPUTS)}")
    relief_text = optional(cfg, "basemap_relief_file")
    relief, download = None, False
    if relief_text:
        try:
            relief, download = relief_path(resolve_path(relief_text))
        except (ValueError, FileNotFoundError) as exc:   # the relief is optional: never stop for it
            print(f"  note: basemap_relief_file = {relief_text!r}: {exc}; maps without relief")
    levels = {o: read_levels(cfg, f"map_levels_{o}") for o in MAP_OUTPUTS}
    return MapSettings(
        outputs=[o for o in MAP_OUTPUTS if o in outputs],
        levels=levels,
        names={o: read_names(cfg, o, len(levels[o])) for o in MAP_OUTPUTS},
        label_max=int_key(cfg, "map_label_max", 0),
        relief_file=relief,
        relief_download=download,
        cities=int_key(cfg, "map_cities", 0),
    )
