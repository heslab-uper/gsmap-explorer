"""Hourly rain characteristics: diurnal cycle and rain events.

Wet hour: rain >= ``wet_hour_threshold_mm``. Event: wet hours joined while
the dry spell between them is shorter than ``event_min_dry_gap_hours``
(owner 2026-10-15: 0.1 mm/h, 6 h). A missing hour (NaN) ends an event;
an event with a missing hour or the edge of the series within the gap before
its first or after its last wet hour may be cut, and is marked
``complete = False`` and left out of the summaries.

Times are local end-of-hour labels: an event's ``start`` is the beginning
of its first wet hour (label - 1 h), its ``end`` the end of its last wet hour.

Output in ``<output_folder>/analysis_output/``.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from core.series import HOUR


def diurnal_cycle(hourly: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Per series, month (``all`` and 1..12) and hour of day (end label):
    valid hours, mean rain, wet-hour fraction, mean rain of the wet hours."""
    rows = []
    hours = hourly.index.hour
    months = hourly.index.month
    for col in hourly.columns:
        v = hourly[col].to_numpy()
        valid = ~np.isnan(v)
        wet = valid & (np.nan_to_num(v) >= threshold)
        for month in ["all"] + list(range(1, 13)):
            in_month = np.ones(v.size, bool) if month == "all" else months == month
            if not (in_month & valid).any():
                continue
            for h in range(24):
                sel = in_month & (hours == h) & valid
                n = int(sel.sum())
                n_wet = int((sel & wet).sum())
                rows.append({"series": col, "month": month, "hour_end": h, "n_valid_hours": n,
                             "mean_mm": float(v[sel].mean()) if n else np.nan,
                             "wet_fraction": n_wet / n if n else np.nan,
                             "mean_wet_mm": float(v[sel & wet].mean()) if n_wet else np.nan})
    return pd.DataFrame(rows)


def find_events(index: pd.DatetimeIndex, v: np.ndarray, threshold: float, gap: int) -> list[dict]:
    """Rain events of one series (see the module docstring)."""
    valid = ~np.isnan(v)
    wet = np.nonzero(valid & (np.nan_to_num(v) >= threshold))[0]
    if wet.size == 0:
        return []
    missing = np.cumsum(~valid)  # missing hours up to and including each row
    groups, first = [], wet[0]
    for a, b in zip(wet[:-1], wet[1:]):
        dry = b - a - 1
        has_missing = missing[b] - missing[a] > 0
        if dry >= gap or has_missing:
            groups.append((first, a))
            first = b
    groups.append((first, wet[-1]))

    events = []
    n = v.size
    for i0, i1 in groups:
        before = slice(max(i0 - gap, 0), i0)
        after = slice(i1 + 1, min(i1 + 1 + gap, n))
        complete = (i0 - gap >= 0 and i1 + gap < n and valid[before].all() and valid[after].all())
        block = v[i0:i1 + 1]
        k = int(np.argmax(block))
        events.append({"start": index[i0] - HOUR, "end": index[i1], "duration_hours": int(i1 - i0 + 1),
                       "depth_mm": float(block.sum()), "peak_mm_per_hour": float(block[k]),
                       "peak_time": index[i0 + k], "wet_hours": int((block >= threshold).sum()),
                       "complete": bool(complete)})
    return events


def _summary(ev: pd.DataFrame) -> dict:
    c = ev[ev["complete"]] if len(ev) else ev
    out = {"n_events": int(len(c)), "n_incomplete": int(len(ev) - len(c))}
    for name, col in (("duration_hours", "duration_hours"), ("depth_mm", "depth_mm"),
                      ("peak_mm_per_hour", "peak_mm_per_hour")):
        x = c[col] if len(c) else pd.Series(dtype=float)
        out[f"mean_{name}"] = float(x.mean()) if len(x) else np.nan
        out[f"median_{name}"] = float(x.median()) if len(x) else np.nan
        out[f"max_{name}"] = float(x.max()) if len(x) else np.nan
    return out


def run_hourly_characteristics(hourly: pd.DataFrame, unit: str, s, out_dir: Path) -> None:
    """Diurnal cycle, event list and event summaries of every column; CSV files in ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    thr, gap = s.wet_hour_threshold_mm, s.event_min_dry_gap_hours
    diurnal_cycle(hourly, thr).to_csv(out_dir / "diurnal_cycle.csv", index=False)

    event_rows, summary_rows = [], []
    years = hourly.index.year
    for col in hourly.columns:
        v = hourly[col].to_numpy()
        events = pd.DataFrame(find_events(hourly.index, v, thr, gap))
        if len(events):
            events.insert(0, "series", col)
            events.insert(1, "event", np.arange(1, len(events) + 1))
            event_rows.append(events)
            ev_year = events["start"].dt.year
        valid_hours = pd.Series(~np.isnan(v), index=hourly.index)
        for year in sorted(set(years)):
            in_year = years == year
            hours_in_year = 8784 if pd.Timestamp(year=year, month=12, day=31).dayofyear == 366 else 8760
            ev = events[ev_year == year] if len(events) else events
            summary_rows.append(dict({"series": col, "year": year,
                                      "valid_fraction": float(valid_hours[in_year].sum()) / hours_in_year},
                                     **_summary(ev)))
        summary_rows.append(dict({"series": col, "year": "all",
                                  "valid_fraction": float(valid_hours.mean())}, **_summary(events)))

    cols = ["series", "event", "start", "end", "duration_hours", "depth_mm", "peak_mm_per_hour",
            "peak_time", "wet_hours", "complete"]
    (pd.concat(event_rows, ignore_index=True) if event_rows else pd.DataFrame(columns=cols)).to_csv(
        out_dir / "rain_events.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(out_dir / "rain_event_summary.csv", index=False)
    print(f"✅ Hourly characteristics ({len(hourly.columns)} {unit} series) written to: {out_dir}")
