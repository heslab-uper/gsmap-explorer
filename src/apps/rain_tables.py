"""The rain tables of one hourly series: hourly, daily, monthly, yearly and the annual maximum daily rain.

One place for the rules of every output (extract and thiessen use it):

- ``rain_hourly.csv``  mm per hour, local end-of-hour labels; missing hours empty
- ``rain_daily.csv``   fixed-day totals (``day_start_hour``, dated by ``daily_date_label``);
                       empty when an hour of the day is missing
- ``rain_monthly.csv`` / ``rain_yearly.csv``  sums of the days; empty unless every day of the
                       month / year (from ``year_start_month``) is present and inside the period
- ``rain_max_daily.csv``  largest daily rain of each year (from ``year_start_month``), taken when
                       at least ``min_valid_fraction`` of its days are present; with
                       ``rain_max_daily_date.csv`` (its date) and ``rain_max_daily_valid.csv``
                       (fraction of the days present)
"""

from pathlib import Path

import pandas as pd

from core.series import compute_annual_maxima, compute_daily_totals, strict_totals

RAIN_OUTPUTS = ("hourly", "daily", "monthly", "yearly", "max_daily")


def rain_tables(hourly: pd.DataFrame, settings) -> dict:
    """{output: table} for every output of ``RAIN_OUTPUTS`` (max_daily: values, date, valid)."""
    daily = compute_daily_totals(hourly, day_start_hour=settings.day_start_hour, date_label=settings.daily_date_label)
    tables = {"hourly": hourly, "daily": daily,
              "monthly": strict_totals(daily, "MS"),
              "yearly": strict_totals(daily, "YS", settings.year_start_month)}
    if len(daily) >= 2:
        m = compute_annual_maxima(daily, year_start_month=settings.year_start_month,
                                  min_valid_fraction=settings.min_valid_fraction)
        tables["max_daily"] = m.values
        tables["max_daily_date"] = m.times
        tables["max_daily_valid"] = m.valid_fraction
    return tables


def write_rain_tables(hourly: pd.DataFrame, settings, out: Path, prefix: str = "rain") -> list[Path]:
    """Write the outputs of ``settings.rain_outputs`` as ``<prefix>_<output>.csv`` in ``out``; returns the files."""
    out.mkdir(parents=True, exist_ok=True)
    tables = rain_tables(hourly, settings)
    fmt = {"hourly": ("%.3f", "%Y-%m-%d %H:%M"), "daily": ("%.2f", "%Y-%m-%d"), "monthly": ("%.1f", None),
           "yearly": ("%.1f", None), "max_daily": ("%.2f", None), "max_daily_date": (None, "%Y-%m-%d"),
           "max_daily_valid": ("%.3f", None)}
    names = []
    for kind in settings.rain_outputs:
        names += [kind] + ([f"{kind}_date", f"{kind}_valid"] if kind == "max_daily" else [])
    written = []
    for name in names:
        if name not in tables:   # max_daily of a period shorter than two days
            print(f"  note: {prefix}_{name}: period too short, not written")
            continue
        float_format, date_format = fmt[name]
        path = out / f"{prefix}_{name}.csv"
        tables[name].to_csv(path, float_format=float_format, date_format=date_format)
        written.append(path)
    return written
