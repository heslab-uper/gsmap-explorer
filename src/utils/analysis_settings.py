"""Settings of the analysis modes, read from the config and checked before any computation.

Every choice comes from the config (no defaults in code). A missing or
invalid key raises ``SettingsError`` naming the key.
"""

from dataclasses import asdict, dataclass

from core.frequency import IDF_FORMULAS, PLOTTING_POSITIONS
from utils.settings import SettingsError, choice_key, float_key, get, int_key, list_key

DISTRIBUTION_NAMES = {
    "Normal": "normal",
    "LogNormal": "lognormal",
    "Gumbel": "gumbel",
    "LogPearson3": "log_pearson3",
}
"""Names in ``distribution_list`` -> internal names."""


@dataclass(frozen=True)
class AnalysisSettings:
    day_start_hour: int
    """Local hour (time_zone, end-of-hour label) at which the fixed day starts and ends."""
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


def _numbers(cfg, key, *, integer: bool, gt: float) -> list:
    out = []
    for p in list_key(cfg, key):
        try:
            x = int(p) if integer else float(p)
        except ValueError:
            raise SettingsError(f"config key '{key}': {p!r} is not {'an integer' if integer else 'a number'}") from None
        if x <= gt:
            raise SettingsError(f"config key '{key}': {x} must be > {gt}")
        out.append(x)
    return sorted(out)


def read_analysis_settings(cfg: dict) -> AnalysisSettings:
    """Check the analysis keys of the config and return them."""
    dist = []
    for name in list_key(cfg, "distribution_list"):
        if name not in DISTRIBUTION_NAMES:
            raise SettingsError(f"config key 'distribution_list': {name!r}; use names from {list(DISTRIBUTION_NAMES)}")
        dist.append(DISTRIBUTION_NAMES[name])
    choice_key(cfg, "distribution_selection", ("ks_chisquare",))

    classes = get(cfg, "chi_square_classes")
    if classes != "sturges":
        classes = int_key(cfg, "chi_square_classes", 3)

    methods = list_key(cfg, "intensity_methods")
    if not methods or any(m not in ("mononobe", "idf") for m in methods):
        raise SettingsError(f"config key 'intensity_methods' = {methods}; use mononobe and/or idf")
    formulas = list_key(cfg, "idf_formulas")
    if not formulas or any(f not in IDF_FORMULAS for f in formulas):
        raise SettingsError(f"config key 'idf_formulas' = {formulas}; use values of {list(IDF_FORMULAS)}")
    idf_durations = _numbers(cfg, "idf_durations_hours", integer=True, gt=0)
    if "idf" in methods and len(idf_durations) < 3:
        raise SettingsError("config key 'idf_durations_hours' needs at least 3 durations for intensity_methods idf")
    output_durations = _numbers(cfg, "intensity_durations_minutes", integer=False, gt=0)
    if len(output_durations) < 3:
        raise SettingsError("config key 'intensity_durations_minutes' needs at least 3 durations")

    return AnalysisSettings(
        day_start_hour=int_key(cfg, "day_start_hour", 0, 23),
        daily_date_label=choice_key(cfg, "daily_date_label", ("start", "end")),
        year_start_month=int_key(cfg, "year_start_month", 1, 12),
        min_valid_fraction=float_key(cfg, "min_valid_fraction", 0, 1),
        min_years=int_key(cfg, "min_years", 4),
        distributions=dist,
        return_periods=_numbers(cfg, "return_periods", integer=False, gt=1),
        alpha=float_key(cfg, "alpha", 0, 0.5),
        chi_square_classes=classes,
        chi_square_parameters_subtracted=int_key(cfg, "chi_square_parameters_subtracted", 0, 3),
        plotting_position=choice_key(cfg, "plotting_position", PLOTTING_POSITIONS),
        intensity_methods=methods,
        idf_formulas=formulas,
        idf_durations_hours=idf_durations,
        output_durations_minutes=output_durations,
        wet_hour_threshold_mm=float_key(cfg, "wet_hour_threshold_mm", 0, 1000),
        event_min_dry_gap_hours=int_key(cfg, "event_min_dry_gap_hours", 1),
    )
