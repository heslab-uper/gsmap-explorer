"""Design rainfall: annual maxima, distribution fits, goodness of fit, return levels, intensity (IDF).

Follows the choices of heslab-design-rainfall (owner 2026-10-08):

- daily = fixed-day total from ``day_start_hour`` to the same hour next day
  (local time), dated by its start or end day; durations in hours = sliding
  sums of the hourly series, labelled at their last hour;
- annual maxima per ``year_start_month`` when the year holds at least
  ``min_valid_fraction`` valid values; at least ``min_years`` years to fit;
- selected distribution: among the fits that pass both Chi-square and
  Smirnov-Kolmogorov, the one with the smallest Delta max; none when no fit
  passes both (every fit is still tabulated);
- intensity: ``mononobe`` from the design daily total; ``idf`` = R_T(d) / d of
  the sliding durations; every formula is fitted per return period and the one
  with the smallest mean absolute deviation is selected.

Output in ``<path_out>/analysis_output/``.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from core import frequency as fq
from core.series import compute_annual_maxima, compute_daily_totals, compute_window_sums

DAILY = "daily"


def _n_classes(setting, n: int) -> int:
    """Chi-square classes: the configured integer, or Sturges 1 + 3.322 log10 n rounded to the nearest integer."""
    if setting == "sturges":
        return int(math.floor(1 + 3.322 * math.log10(n) + 0.5))
    return setting


def duration_sets(hourly: pd.DataFrame, s) -> list[tuple[str, pd.DataFrame]]:
    """(label, series) of the daily total and of every sliding duration used by idf."""
    sets = [(DAILY, compute_daily_totals(hourly, day_start_hour=s.day_start_hour, date_label=s.daily_date_label))]
    if "idf" in s.intensity_methods:
        sets += [(f"{h}h", compute_window_sums(hourly, h)) for h in s.idf_durations_hours]
    return sets


def analyse_sample(series: str, duration: str, x: np.ndarray, s) -> tuple[list, list, dict | None, str]:
    """Fits, return levels, the selected fit (with ``levels_by_T``) and a note for one sample."""
    fits, levels, best = [], [], None
    if x.size < s.min_years:
        return fits, levels, None, f"{x.size} complete years, fewer than min_years = {s.min_years}"
    n_classes = _n_classes(s.chi_square_classes, x.size)
    for name in s.distributions:
        row = {"series": series, "duration": duration, "distribution": name, "n": int(x.size),
               "chi_square_classes": n_classes}
        try:
            fitted = fq.fit_distribution(x, name)
            chi = fq.test_chi_square(x, fitted, n_classes=n_classes,
                                     parameters_subtracted=s.chi_square_parameters_subtracted, alpha=s.alpha)
            sk = fq.test_smirnov_kolmogorov(x, fitted, plotting_position=s.plotting_position, alpha=s.alpha)
            values = fq.compute_return_levels(fitted, s.return_periods)
        except ValueError as exc:
            row["error"] = str(exc)
            fits.append(row)
            continue
        row.update(parameters=json.dumps(fitted.parameters), chi_square=chi.statistic,
                   chi_square_critical=chi.critical, chi_square_dof=chi.dof, chi_square_passed=chi.passed,
                   delta_max=sk.delta_max, delta_critical=sk.critical, smirnov_kolmogorov_passed=sk.passed,
                   selected=False)
        fits.append(row)
        for t, v in zip(s.return_periods, values):
            levels.append({"series": series, "duration": duration, "distribution": name, "return_period": t,
                           "value_mm": float(v), "frequency_factor": float(fitted.frequency_factor(1 - 1 / t))})
        if chi.passed and sk.passed and (best is None or sk.delta_max < best[0]["delta_max"]):
            best = (row, values)
    if best is None:
        return fits, levels, None, "no fit passes both Chi-square and Smirnov-Kolmogorov"
    best[0]["selected"] = True
    selected = dict(best[0], levels_by_T=dict(zip(s.return_periods, (float(v) for v in best[1]))))
    return fits, levels, selected, ""


def _fit_formulas(t: np.ndarray, i: np.ndarray, s):
    ok = ~np.isnan(i) & (i > 0)
    if np.unique(t[ok]).size < 3:
        return [], None
    fits = [fq.fit_idf(t[ok], i[ok], formula=f) for f in s.idf_formulas]
    return fits, min(fits, key=lambda f: f.mean_deviation)


def intensity_tables(design: dict, s) -> tuple[list, list]:
    """Intensity rows and IDF parameter rows from the design depths {(series, duration): {T: mm}}."""
    rows, params = [], []
    series_names = sorted({k[0] for k in design}, key=str)
    for method in s.intensity_methods:
        for name in series_names:
            for t_ret in s.return_periods:
                if method == "mononobe":
                    t = np.asarray(s.output_durations_minutes, dtype=np.float64)
                    r24 = design.get((name, DAILY), {}).get(t_ret, math.nan)
                    i = fq.compute_mononobe_intensity([r24], t / 60)[0]
                    note = "" if not math.isnan(r24) else "no design daily total"
                else:
                    d = np.asarray(s.idf_durations_hours, dtype=np.float64)
                    depth = np.array([design.get((name, f"{int(h)}h"), {}).get(t_ret, math.nan) for h in d])
                    ok = ~np.isnan(depth)
                    t, i = d[ok] * 60, depth[ok] / d[ok]
                    note = "" if ok.all() else "left out (no design value): " + ", ".join(f"{int(h)}h" for h in d[~ok])
                fits, best = _fit_formulas(t, i, s)
                base = {"method": method, "series": name, "return_period": t_ret}
                if not fits:
                    params.append(dict(base, formula="", a=math.nan, b=math.nan, mean_deviation=math.nan,
                                       rmse=math.nan, selected=False, n_durations=int(np.sum(~np.isnan(i))),
                                       note=(note + "; " if note else "") + "fewer than 3 durations: no fit"))
                for f in fits:
                    params.append(dict(base, formula=f.formula, a=f.a, b=f.b, mean_deviation=f.mean_deviation,
                                       rmse=f.rmse, selected=f is best, n_durations=int(t.size), note=note))
                out_t = np.asarray(s.output_durations_minutes, dtype=np.float64)
                if method == "mononobe":
                    ref = i
                else:
                    # Only within the fitted durations: a formula fitted to hours is not extrapolated to minutes.
                    out_t = np.union1d(out_t, t)
                    out_t = out_t[(out_t >= t.min()) & (out_t <= t.max())] if t.size else out_t[:0]
                    ref = np.full(out_t.size, np.nan)
                    hit = np.isin(out_t, t)
                    ref[hit] = i[np.searchsorted(t, out_t[hit])]
                for k, tm in enumerate(out_t):
                    row = dict(base, duration_minutes=float(tm), duration_hours=float(tm) / 60,
                               intensity_reference=float(ref[k]))
                    for f in fits:
                        row[f"intensity_{f.formula}"] = float(f.intensity(tm))
                    row["intensity_selected"] = float(best.intensity(tm)) if best else math.nan
                    row["formula_selected"] = best.formula if best else ""
                    rows.append(row)
    return rows, params


def run_frequency_analysis(hourly: pd.DataFrame, unit: str, s, out_dir: Path) -> None:
    """Annual maxima, fits, return levels and intensity of every column of ``hourly``; CSV files in ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    am_rows, fit_rows, level_rows, design_rows = [], [], [], []
    design = {}
    for label, values in duration_sets(hourly, s):
        am = compute_annual_maxima(values, year_start_month=s.year_start_month,
                                   min_valid_fraction=s.min_valid_fraction)
        chosen = 0
        for col in values.columns:
            v, tm, frac = am.values[col], am.times[col], am.valid_fraction[col]
            for year in am.values.index:
                am_rows.append({"series": col, "duration": label, "year": int(year), "value_mm": v[year],
                                "time": tm[year], "valid_fraction": frac[year]})
            ok = v.notna().to_numpy()
            fits, levels, selected, note = analyse_sample(col, label, v.to_numpy()[ok], s)
            fit_rows += fits
            level_rows += levels
            if selected:
                chosen += 1
                design[(col, label)] = selected["levels_by_T"]
            for t in s.return_periods:
                design_rows.append({"series": col, "duration": label, "return_period": t,
                                    "value_mm": selected["levels_by_T"][t] if selected else math.nan,
                                    "distribution": selected["distribution"] if selected else "",
                                    "n_years": int(ok.sum()), "note": note})
        print(f"  {label}: {len(values.columns)} {unit} series, {chosen} with a selected distribution")

    int_rows, idf_rows = intensity_tables(design, s)
    pd.DataFrame(am_rows).to_csv(out_dir / "annual_maxima.csv", index=False)
    pd.DataFrame(fit_rows).to_csv(out_dir / "distribution_fits.csv", index=False)
    pd.DataFrame(level_rows).to_csv(out_dir / "return_levels_all.csv", index=False)
    pd.DataFrame(design_rows).to_csv(out_dir / "design_rainfall.csv", index=False)
    pd.DataFrame(int_rows).to_csv(out_dir / "intensity.csv", index=False)
    pd.DataFrame(idf_rows).to_csv(out_dir / "idf_parameters.csv", index=False)
    print(f"✅ Frequency analysis written to: {out_dir}")
