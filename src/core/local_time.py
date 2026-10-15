"""UTC to local time of the output: the one place that holds the offsets."""

import pandas as pd

# GSMaP time is UTC and marks the START of each hourly period. Offset = time
# zone (WIB +7, WITA +8, WIT +9) + 1 h, so the label marks the END of the
# period (rain that has already fallen). Intended (owner 2026-10-15).
LOCAL_OFFSET_HOURS = {"WIB": 8, "WITA": 9, "WIT": 10}


def local_offset_hours(wilayah_waktu) -> int:
    """Hours added to the UTC start-of-hour stamps; 0 (UTC start labels) for any other value."""
    return LOCAL_OFFSET_HOURS.get(wilayah_waktu, 0)


def to_local_end_labels(times_utc, wilayah_waktu) -> pd.DatetimeIndex:
    """UTC start-of-hour stamps -> local end-of-hour labels."""
    return pd.DatetimeIndex(times_utc) + pd.Timedelta(hours=local_offset_hours(wilayah_waktu))
