"""UTC to local time of the output, and rain days to hours: the one place that holds the offsets."""

from datetime import date, datetime

import pandas as pd

TIME_ZONE_HOURS = {"WIB": 7, "WITA": 8, "WIT": 9, "UTC": 0}
"""Offset of each time zone from UTC (config key ``time_zone``)."""

GSMAP_LABEL_SHIFT_HOURS = 1
"""GSMaP time is UTC and marks the START of each hourly period; +1 h moves the
label to the END of the period (rain that has already fallen). A fixed property
of the data, added to every time zone: WIB = UTC + 8 h (owner 2026-10-15,
2026-10-17)."""


def local_offset_hours(time_zone: str) -> int:
    """Hours added to the UTC start-of-hour stamps: zone offset + 1 h."""
    if time_zone not in TIME_ZONE_HOURS:
        raise ValueError(f"time zone {time_zone!r}: use one of {list(TIME_ZONE_HOURS)}")
    return TIME_ZONE_HOURS[time_zone] + GSMAP_LABEL_SHIFT_HOURS


def to_local_end_labels(times_utc, time_zone: str) -> pd.DatetimeIndex:
    """UTC start-of-hour stamps -> local end-of-hour labels."""
    return pd.DatetimeIndex(times_utc) + pd.Timedelta(hours=local_offset_hours(time_zone))


def rain_day_labels(start: date, end: date, day_start_hour: int, date_label: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """First and last local end-of-hour label of the rain days ``start`` .. ``end``.

    Day D holds the hours labelled day_start_hour + 1 h on D .. day_start_hour
    on D + 1 when ``date_label`` is ``"start"`` (07-07: 08:00 D .. 07:00 D+1);
    with ``"end"`` the day is dated by the date its window ends.
    """
    h = pd.Timedelta(hours=day_start_hour)
    back = pd.Timedelta(days=1) if date_label == "end" else pd.Timedelta(0)
    first_day, last_day = pd.Timestamp(start) - back, pd.Timestamp(end) - back
    return first_day + h + pd.Timedelta(hours=1), last_day + pd.Timedelta(days=1) + h


def rain_day_utc_window(start: date, end: date, day_start_hour: int, date_label: str,
                        time_zone: str) -> tuple[datetime, datetime]:
    """UTC start-of-hour stamps of the first and last hour of the rain days ``start`` .. ``end``."""
    first, last = rain_day_labels(start, end, day_start_hour, date_label)
    off = pd.Timedelta(hours=local_offset_hours(time_zone))
    return (first - off).to_pydatetime(), (last - off).to_pydatetime()
