"""Hourly series: regular index, window sums, fixed-day totals, annual maxima.

A series is a ``pandas.DataFrame`` on a regular, strictly increasing hourly
``DatetimeIndex`` (local time, each label marking the END of its hour) with
one column per region or grid point. Missing hours are NaN rows and are never
filled; a window, day or year holding NaN gives NaN (years: see
``compute_annual_maxima``).

``compute_window_sums``, ``compute_period_totals`` and
``compute_annual_maxima`` are ported from heslab-stats 0.3.0
(``series``, commit f0773d6, 2026-10-12); ``compute_daily_totals`` follows
heslab-design-rainfall (``analysis.compute_daily_totals``).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

HOUR = pd.Timedelta(hours=1)


def make_regular_hourly(values: pd.DataFrame) -> pd.DataFrame:
    """Same series on every hour from its first to its last label; added hours are NaN.

    GSMaP hours absent from the .nc files are the only gaps that can be
    detected (the archive stores "no data" as 0), so they must become NaN
    rows here, not zeros.
    """
    values = values.sort_index()
    if values.index.has_duplicates:
        raise ValueError("hourly series has duplicate time labels")
    full = pd.date_range(values.index[0], values.index[-1], freq="h", name=values.index.name)
    if not full.isin(values.index).sum() == len(values.index):
        raise ValueError("time labels are not on whole hours")
    return values.reindex(full)


def _check_series(values: pd.DataFrame) -> np.ndarray:
    if not isinstance(values.index, pd.DatetimeIndex):
        raise TypeError(f"index must be a DatetimeIndex, got {type(values.index).__name__}")
    if len(values.index) >= 2:
        steps = np.diff(values.index.asi8)
        if (steps <= 0).any():
            raise ValueError("index must be strictly increasing")
        if (steps != steps[0]).any():
            raise ValueError("index is not regular; add missing steps as NaN rows")
    return values.to_numpy(dtype=np.float64)


def compute_window_sums(values: pd.DataFrame, n: int) -> pd.DataFrame:
    """Sum of every ``n`` consecutive rows, labelled at the window's last row.

    NaN for the first n - 1 rows and wherever the window holds NaN.
    """
    arr = _check_series(values)
    out = np.full(arr.shape, np.nan)
    if arr.shape[0] >= n:
        out[n - 1:] = sliding_window_view(arr, n, axis=0).sum(axis=-1)
    return pd.DataFrame(out, index=values.index, columns=values.columns)


def compute_period_totals(values: pd.DataFrame, ends, *, length: int) -> pd.DataFrame:
    """Sum of the ``length`` rows ending at each label in ``ends`` (NaN where any row is NaN)."""
    arr = _check_series(values)
    ends = pd.DatetimeIndex(ends)
    locs = values.index.get_indexer(ends)
    if (locs < 0).any():
        raise ValueError(f"end {ends[locs < 0][0]} is not in the index")
    if (locs - length + 1 < 0).any():
        raise ValueError("a period starts before the first row")
    out = np.empty((ends.size, arr.shape[1]))
    for i, k in enumerate(locs):
        out[i] = arr[k - length + 1:k + 1].sum(axis=0)
    return pd.DataFrame(out, index=ends, columns=values.columns)


def compute_daily_totals(hourly: pd.DataFrame, *, day_start_hour: int, date_label: str) -> pd.DataFrame:
    """Fixed-day totals: 24 hours from ``day_start_hour`` to the same hour next day.

    With end-of-hour labels the day holds the hours labelled day_start + 1 h
    .. next day_start (07-07: labels 08:00 D .. 07:00 D+1). Index = the date
    the window starts (``date_label = "start"``) or ends (``"end"``), 00:00.
    Only whole windows inside the series are returned.
    """
    idx = hourly.index
    ends = idx[(idx.hour == day_start_hour) & (idx.minute == 0)]
    ends = ends[idx.get_indexer(ends) >= 23]
    totals = compute_period_totals(hourly, ends, length=24)
    shift = pd.Timedelta(days=1) if date_label == "start" else pd.Timedelta(0)
    totals.index = pd.DatetimeIndex(ends.normalize() - shift, name="date")
    return totals


@dataclass(frozen=True)
class AnnualMaxima:
    """Annual maxima of each column; index = year (int)."""

    values: pd.DataFrame
    """Largest value of the year; NaN when the year is too incomplete."""
    times: pd.DataFrame
    """Label of the first row reaching the maximum; NaT when ``values`` is NaN."""
    valid_fraction: pd.DataFrame
    """Non-NaN rows of the year / rows a whole year holds."""


def compute_annual_maxima(values: pd.DataFrame, *, year_start_month: int,
                          min_valid_fraction: float) -> AnnualMaxima:
    """Largest value of each year, taken only when the year is complete enough.

    A year runs from the first day of ``year_start_month`` to the same day a
    year later and is labelled by the calendar year it starts in. Rows count
    by their label (window sums in the year their window ends). The maximum
    is taken over the non-NaN rows when ``valid_fraction >= min_valid_fraction``,
    otherwise NaN. Years cut by the start or end of the series count the
    missing part as missing.
    """
    arr = _check_series(values)
    index = values.index
    if len(index) < 2:
        raise ValueError("values must hold at least two rows")
    step = index[1] - index[0]
    first = index[0].year if index[0].month >= year_start_month else index[0].year - 1
    last = index[-1].year if index[-1].month >= year_start_month else index[-1].year - 1
    years = list(range(first, last + 1))
    out_max = np.full((len(years), arr.shape[1]), np.nan)
    out_frac = np.zeros((len(years), arr.shape[1]))
    out_time = np.full((len(years), arr.shape[1]), pd.NaT, dtype=object)
    for row, year in enumerate(years):
        start = pd.Timestamp(year=year, month=year_start_month, day=1)
        end = pd.Timestamp(year=year + 1, month=year_start_month, day=1)
        expected = (end - start) // step
        i0, i1 = index.searchsorted(start), index.searchsorted(end)
        block = arr[i0:i1]
        valid = ~np.isnan(block)
        frac = valid.sum(axis=0) / expected
        out_frac[row] = frac
        for col in range(arr.shape[1]):
            if frac[col] >= min_valid_fraction and valid[:, col].any():
                k = int(np.nanargmax(block[:, col]))
                out_max[row, col] = block[k, col]
                out_time[row, col] = index[i0 + k]
    year_index = pd.Index(years, name="year")
    times = pd.DataFrame(out_time, index=year_index, columns=values.columns)
    for col in times.columns:
        times[col] = pd.to_datetime(times[col])
    return AnnualMaxima(values=pd.DataFrame(out_max, index=year_index, columns=values.columns),
                        times=times,
                        valid_fraction=pd.DataFrame(out_frac, index=year_index, columns=values.columns))


def strict_totals(daily: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Sum of the days of each calendar month (``MS``) or year (``YS``); NaN unless every day is present."""
    periods = daily.index.to_period("M" if freq == "MS" else "Y")
    expected = pd.Series(periods.days_in_month if freq == "MS" else [366 if p.is_leap_year else 365 for p in periods],
                         index=daily.index).groupby(periods).first()
    total = daily.groupby(periods).sum(min_count=1)
    complete = daily.notna().groupby(periods).sum().eq(expected, axis=0)
    out = total.where(complete)
    out.index = out.index.astype(str)
    out.index.name = "month" if freq == "MS" else "year"
    return out
