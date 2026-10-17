"""Rain of the grid cells read for one run: hourly, daily, monthly, yearly totals and the period mean.

One column per cell, in the order of ``koordinat.csv`` (rows of ``lat`` as
read, then ``lon``). Hourly labels are local and mark the end of the hour;
hours missing from the files are NaN rows (``core.series``). Daily, monthly
and yearly totals follow the series mode exactly: fixed days of
``day_start_hour``, months and years only when every day is present and
inside the period (``core.series.strict_totals``).
"""

from dataclasses import dataclass
from functools import cached_property

import numpy as np
import pandas as pd

from core.local_time import rain_day_labels, to_local_end_labels
from core.series import compute_daily_totals, strict_totals


@dataclass
class RainGrid:
    hourly: pd.DataFrame
    lon: np.ndarray
    lat: np.ndarray
    day_start_hour: int
    date_label: str
    year_start_month: int = 1

    @classmethod
    def from_read(cls, values, times_utc, lon, lat, settings) -> "RainGrid":
        """From ``core.reader.read_netcdf``: values (time, lat, lon), UTC start-of-hour stamps."""
        labels = to_local_end_labels(times_utc, settings.time_zone)
        hourly = pd.DataFrame(np.asarray(values).reshape(len(labels), -1), index=labels)
        first, last = rain_day_labels(settings.start_date, settings.end_date, settings.day_start_hour,
                                      settings.daily_date_label)
        full = pd.date_range(first, last, freq="h", name="time")
        hourly = hourly[(hourly.index >= first) & (hourly.index <= last)].reindex(full)
        return cls(hourly=hourly, lon=np.asarray(lon), lat=np.asarray(lat),
                   day_start_hour=settings.day_start_hour, date_label=settings.daily_date_label,
                   year_start_month=settings.year_start_month)

    @cached_property
    def daily(self) -> pd.DataFrame:
        return compute_daily_totals(self.hourly, day_start_hour=self.day_start_hour, date_label=self.date_label)

    @cached_property
    def monthly(self) -> pd.DataFrame:
        """Index ``YYYY-MM``; NaN where a day is missing or the month is not wholly in the period."""
        return strict_totals(self.daily, "MS")

    @cached_property
    def yearly(self) -> pd.DataFrame:
        """Index ``YYYY`` (year from ``year_start_month``); NaN where a day is missing or the year is not
        wholly in the period."""
        return strict_totals(self.daily, "YS", self.year_start_month)

    def field(self, row: pd.Series) -> np.ndarray:
        """One row of a table as a (lat, lon) array."""
        return row.to_numpy(dtype=np.float64).reshape(len(self.lat), len(self.lon))

    def period_mean(self) -> tuple[np.ndarray, str, str]:
        """Background of the grid-point map: (field, kind, description).

        Mean of the complete years (mm/year, kind ``yearly``) when at least one
        year is whole in the period; otherwise the mean daily rain of the
        period (mm/day, kind ``daily``). Never scaled from part of a year.
        """
        complete = self.yearly.dropna(how="all")
        if not complete.empty:
            years = list(complete.index)
            span = years[0] if len(years) == 1 else f"{years[0]}-{years[-1]}"
            return self.field(complete.mean(axis=0, skipna=False)), "yearly", \
                f"rerata hujan tahunan {span} ({len(years)} tahun lengkap)"
        d = self.daily
        return self.field(d.mean(axis=0, skipna=True)), "daily", \
            f"rerata hujan harian {d.index[0]:%d %b %Y} - {d.index[-1]:%d %b %Y}"
