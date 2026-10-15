"""Settings of the analysis modes, read from config/input.txt and checked before any computation.

Every choice comes from the config (no defaults in code). A missing or
invalid key raises ``SettingsError`` naming the key.
"""

from dataclasses import asdict, dataclass

from core.frequency import IDF_FORMULAS, PLOTTING_POSITIONS

DISTRIBUTION_NAMES = {
    "Normal": "normal",
    "LogNormal": "lognormal",
    "Gumbel": "gumbel",
    "LogPearson3": "log_pearson3",
}
"""Names in ``distribution_list`` -> internal names."""


class SettingsError(ValueError):
    """A config key is missing or invalid; the message names the key."""


@dataclass(frozen=True)
class AnalysisSettings:
    day_start_hour: int
    """Local hour (wilayah_waktu) at which the fixed day starts and ends."""
    daily_date_label: str
    year_start_month: int
    min_valid_fraction: float
    min_years: int
    distributions: list
    return_periods: list
    alpha: float
    chi_square_classes: object
    """An integer >= 3, or ``"sturges"`` (1 + 3.322 log10 n, rounded, per series)."""
    chi_square_parameters_subtracted: int
    plotting_position: str
    intensity_methods: list
    idf_formulas: list
    idf_durations_hours: list
    output_durations_minutes: list
    wet_hour_threshold_mm: float
    event_min_dry_gap_hours: int

    def describe(self) -> str:
        return "\n".join(f"  {k}: {v}" for k, v in asdict(self).items())


def _get(cfg: dict, key: str) -> str:
    v = cfg.get(key)
    if v is None or v == "":
        raise SettingsError(f"config key '{key}' is missing or empty in config/input.txt")
    return v


def _list(cfg, key) -> list[str]:
    items = [p.strip() for p in _get(cfg, key).split(",") if p.strip()]
    if len(set(items)) != len(items):
        raise SettingsError(f"config key '{key}' repeats a value: {items}")
    return items


def _int(cfg, key, lo, hi=None) -> int:
    v = _get(cfg, key)
    try:
        n = int(v)
    except ValueError:
        raise SettingsError(f"config key '{key}' = {v!r}; expected an integer") from None
    if n < lo or (hi is not None and n > hi):
        raise SettingsError(f"config key '{key}' = {n}; expected {lo}..{hi if hi is not None else ''}")
    return n


def _float(cfg, key, lo, hi, *, lo_open=True) -> float:
    v = _get(cfg, key)
    try:
        x = float(v)
    except ValueError:
        raise SettingsError(f"config key '{key}' = {v!r}; expected a number") from None
    if x < lo or (lo_open and x == lo) or x > hi:
        raise SettingsError(f"config key '{key}' = {x}; expected {'>' if lo_open else '>='} {lo} and <= {hi}")
    return x


def _choice(cfg, key, allowed):
    v = _get(cfg, key)
    if v not in allowed:
        raise SettingsError(f"config key '{key}' = {v!r}; use one of {list(allowed)}")
    return v


def _numbers(cfg, key, *, integer: bool, gt: float) -> list:
    out = []
    for p in _list(cfg, key):
        try:
            x = int(p) if integer else float(p)
        except ValueError:
            raise SettingsError(f"config key '{key}': {p!r} is not {'an integer' if integer else 'a number'}") from None
        if x <= gt:
            raise SettingsError(f"config key '{key}': {x} must be > {gt}")
        out.append(x)
    return sorted(out)


def read_daily_settings(cfg: dict) -> tuple[int, str]:
    """``day_start_hour`` and ``daily_date_label``, checked (used by points, thiessen and analysis)."""
    return _int(cfg, "day_start_hour", 0, 23), _choice(cfg, "daily_date_label", ("start", "end"))


def read_analysis_settings(cfg: dict) -> AnalysisSettings:
    """Check the analysis keys of the config and return them."""
    dist = []
    for name in _list(cfg, "distribution_list"):
        if name not in DISTRIBUTION_NAMES:
            raise SettingsError(f"config key 'distribution_list': {name!r}; use names from {list(DISTRIBUTION_NAMES)}")
        dist.append(DISTRIBUTION_NAMES[name])
    _choice(cfg, "distribution_selection", ("ks_chisquare",))

    classes = _get(cfg, "chi_square_classes")
    if classes != "sturges":
        classes = _int(cfg, "chi_square_classes", 3)

    methods = _list(cfg, "intensity_methods")
    if not methods or any(m not in ("mononobe", "idf") for m in methods):
        raise SettingsError(f"config key 'intensity_methods' = {methods}; use mononobe and/or idf")
    formulas = _list(cfg, "idf_formulas")
    if not formulas or any(f not in IDF_FORMULAS for f in formulas):
        raise SettingsError(f"config key 'idf_formulas' = {formulas}; use values of {list(IDF_FORMULAS)}")
    idf_durations = _numbers(cfg, "idf_durations_hours", integer=True, gt=0)
    if "idf" in methods and len(idf_durations) < 3:
        raise SettingsError("config key 'idf_durations_hours' needs at least 3 durations for intensity_methods idf")
    output_durations = _numbers(cfg, "duration_minutes", integer=False, gt=0)
    if len(output_durations) < 3:
        raise SettingsError("config key 'duration_minutes' needs at least 3 durations")

    return AnalysisSettings(
        day_start_hour=_int(cfg, "day_start_hour", 0, 23),
        daily_date_label=_choice(cfg, "daily_date_label", ("start", "end")),
        year_start_month=_int(cfg, "year_start_month", 1, 12),
        min_valid_fraction=_float(cfg, "min_valid_fraction", 0, 1),
        min_years=_int(cfg, "min_years", 4),
        distributions=dist,
        return_periods=_numbers(cfg, "return_periods", integer=False, gt=1),
        alpha=_float(cfg, "alpha", 0, 0.5),
        chi_square_classes=classes,
        chi_square_parameters_subtracted=_int(cfg, "chi_square_parameters_subtracted", 0, 3),
        plotting_position=_choice(cfg, "plotting_position", PLOTTING_POSITIONS),
        intensity_methods=methods,
        idf_formulas=formulas,
        idf_durations_hours=idf_durations,
        output_durations_minutes=output_durations,
        wet_hour_threshold_mm=_float(cfg, "wet_hour_threshold_mm", 0, 1000),
        event_min_dry_gap_hours=_int(cfg, "event_min_dry_gap_hours", 1),
    )
