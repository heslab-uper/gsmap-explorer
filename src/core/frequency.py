"""Frequency analysis of annual maxima: sample statistics, distributions, goodness of fit, intensity.

Ported from heslab-stats 0.3.0 (commit f0773d6, 2026-10-12), modules
``frequency.sample``, ``frequency.distributions`` (method of moments only),
``frequency.goodness_of_fit`` and ``frequency.intensity``, so that this
release runs without the heslab packages. Results are identical to that
source for the distributions kept here.

Distributions (method of moments, SNI 2415:2016 practice):
``normal``, ``lognormal`` (normal on log10 x), ``gumbel``,
``log_pearson3`` (Pearson III on log10 x).
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats

DISTRIBUTIONS = ("normal", "lognormal", "gumbel", "log_pearson3")

PLOTTING_POSITIONS = ("weibull", "gringorten", "cunnane", "hazen", "california")

IDF_FORMULAS = ("talbot", "sherman", "ishiguro")
"""``talbot`` I = a / (t + b); ``sherman`` I = a / t**n; ``ishiguro`` I = a / (sqrt(t) + b); t in minutes."""

N_PARAMETERS = {"normal": 2, "lognormal": 2, "gumbel": 2, "log_pearson3": 3}

_FAMILIES = {
    # name: (scipy family, fitted on log10 x)
    "normal": (stats.norm, False),
    "lognormal": (stats.norm, True),
    "gumbel": (stats.gumbel_r, False),
    "log_pearson3": (stats.pearson3, True),
}


# --- sample ---------------------------------------------------------------------------


def check_sample(values, *, minimum: int, positive: bool = False) -> np.ndarray:
    """``values`` as a 1-D float64 array; raises ValueError if not 1-D, not finite,
    shorter than ``minimum``, constant, or (``positive``) holding a value <= 0."""
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError(f"sample must be 1-D, got shape {x.shape}")
    if not np.isfinite(x).all():
        raise ValueError("sample holds NaN or infinity; build the sample from complete years only")
    if x.size < minimum:
        raise ValueError(f"sample needs at least {minimum} values, got {x.size}")
    if np.ptp(x) == 0:
        raise ValueError("sample is constant")
    if positive and (x <= 0).any():
        raise ValueError(f"sample must be > 0 for a log transform, smallest value is {x.min()}")
    return x


@dataclass(frozen=True)
class SampleStatistics:
    """Bias-corrected moments of a sample (std with n - 1; Cs, Ck as in SNI 2415:2016)."""

    n: int
    mean: float
    std: float
    cv: float
    cs: float
    ck: float


def compute_sample_statistics(values) -> SampleStatistics:
    """Mean, standard deviation (n - 1), Cv, skewness Cs and kurtosis Ck of a sample.

    ``cs = n * S3 / ((n-1)(n-2) std**3)``, ``ck = n**2 * S4 / ((n-1)(n-2)(n-3) std**4)``,
    Sk = sum of k-th powers of deviations from the mean. At least 4 values.
    """
    x = check_sample(values, minimum=4)
    n = x.size
    mean = float(x.mean())
    d = x - mean
    std = float(np.sqrt((d ** 2).sum() / (n - 1)))
    cs = n * (d ** 3).sum() / ((n - 1) * (n - 2) * std ** 3)
    ck = n ** 2 * (d ** 4).sum() / ((n - 1) * (n - 2) * (n - 3) * std ** 4)
    cv = std / mean if mean != 0 else float("nan")
    return SampleStatistics(n=n, mean=mean, std=std, cv=float(cv), cs=float(cs), ck=float(ck))


def compute_plotting_positions(n: int, *, method: str) -> np.ndarray:
    """Exceedance probability of ranks 1..n of a sample sorted in descending order.

    ``weibull`` m / (n + 1); ``gringorten`` (m - 0.44) / (n + 0.12);
    ``cunnane`` (m - 0.4) / (n + 0.2); ``hazen`` (m - 0.5) / n; ``california`` m / n.
    """
    if not isinstance(n, (int, np.integer)) or isinstance(n, bool) or n < 1:
        raise ValueError(f"n must be an integer >= 1, got {n!r}")
    m = np.arange(1, n + 1, dtype=np.float64)
    if method == "weibull":
        return m / (n + 1)
    if method == "gringorten":
        return (m - 0.44) / (n + 0.12)
    if method == "cunnane":
        return (m - 0.4) / (n + 0.2)
    if method == "hazen":
        return (m - 0.5) / n
    if method == "california":
        return m / n
    raise ValueError(f"unknown plotting position {method!r}; use one of {PLOTTING_POSITIONS}")


# --- distributions ------------------------------------------------------------------------


@dataclass(frozen=True)
class FittedDistribution:
    """A distribution fitted by moments; ``parameters`` in the fitted space (log10 x when ``log10``).

    ``loc``, ``scale`` and, for ``log_pearson3``, ``shape`` (the ``skew`` of
    ``scipy.stats.pearson3``).
    """

    distribution: str
    n: int
    parameters: dict
    log10: bool
    sample_mean: float
    sample_std: float

    @property
    def n_parameters(self) -> int:
        return N_PARAMETERS[self.distribution]

    def _frozen(self):
        family = _FAMILIES[self.distribution][0]
        par = self.parameters
        if "shape" in par:
            return family(par["shape"], loc=par["loc"], scale=par["scale"])
        return family(loc=par["loc"], scale=par["scale"])

    def quantile(self, non_exceedance) -> np.ndarray:
        """Value with the given non-exceedance probability (0 < p < 1), sample units."""
        p = np.asarray(non_exceedance, dtype=np.float64)
        if ((p <= 0) | (p >= 1)).any() or np.isnan(p).any():
            raise ValueError("non-exceedance probability must be strictly between 0 and 1")
        y = self._frozen().ppf(p)
        return 10 ** y if self.log10 else y

    def cdf(self, values) -> np.ndarray:
        """Non-exceedance probability of each value (sample units)."""
        x = np.asarray(values, dtype=np.float64)
        if self.log10:
            with np.errstate(invalid="ignore", divide="ignore"):
                y = np.where(x > 0, np.log10(np.where(x > 0, x, 1.0)), -np.inf)
        else:
            y = x
        return self._frozen().cdf(y)

    def frequency_factor(self, non_exceedance) -> np.ndarray:
        """K = (y_T - mean) / std in the fitted space (the K of the frequency tables)."""
        q = self.quantile(non_exceedance)
        y = np.log10(q) if self.log10 else q
        return (y - self.sample_mean) / self.sample_std


def fit_distribution(values, distribution: str) -> FittedDistribution:
    """Fit one distribution by the method of moments.

    Parameters
    ----------
    values : array-like
        Annual maxima (mm), at least 4 finite values, not constant; > 0 for
        ``lognormal`` and ``log_pearson3``.
    distribution : str
        One of ``DISTRIBUTIONS``.
    """
    if distribution not in _FAMILIES:
        raise ValueError(f"unknown distribution {distribution!r}; use one of {DISTRIBUTIONS}")
    log10 = _FAMILIES[distribution][1]
    x = check_sample(values, minimum=4, positive=log10)
    y = np.log10(x) if log10 else x
    st = compute_sample_statistics(y)
    if distribution in ("normal", "lognormal"):
        par = {"loc": st.mean, "scale": st.std}
    elif distribution == "gumbel":
        scale = st.std * math.sqrt(6) / math.pi
        par = {"loc": st.mean - np.euler_gamma * scale, "scale": scale}
    else:
        par = {"shape": st.cs, "loc": st.mean, "scale": st.std}
    return FittedDistribution(distribution=distribution, n=int(x.size), parameters=par, log10=log10,
                              sample_mean=st.mean, sample_std=st.std)


def compute_return_levels(fitted: FittedDistribution, return_periods) -> np.ndarray:
    """Value of each return period T (years), non-exceedance p = 1 - 1/T."""
    t = np.asarray(return_periods, dtype=np.float64)
    if np.isnan(t).any() or (t <= 1).any():
        raise ValueError("return periods must be > 1 year")
    return fitted.quantile(1 - 1 / t)


# --- goodness of fit -----------------------------------------------------------------------


@dataclass(frozen=True)
class ChiSquareResult:
    """Chi-square test with classes of equal probability under the fitted distribution."""

    statistic: float
    critical: float
    dof: int
    passed: bool
    """``statistic < critical``: the distribution is accepted."""


def test_chi_square(values, fitted: FittedDistribution, *, n_classes: int,
                    parameters_subtracted: int, alpha: float) -> ChiSquareResult:
    """Chi-square with ``n_classes`` classes of equal probability.

    Class bounds = fitted quantiles at k / n_classes (a value on a bound counts
    in the upper class); X2 = sum((O - E)**2 / E), E = n / n_classes; degrees
    of freedom = n_classes - 1 - parameters_subtracted; critical value from
    ``scipy.stats.chi2``.
    """
    x = check_sample(values, minimum=4)
    if x.size != fitted.n:
        raise ValueError(f"sample has {x.size} values, the distribution was fitted to {fitted.n}")
    if not isinstance(n_classes, (int, np.integer)) or n_classes < 3:
        raise ValueError(f"n_classes must be an integer >= 3, got {n_classes!r}")
    dof = int(n_classes) - 1 - int(parameters_subtracted)
    if dof < 1:
        raise ValueError(f"degrees of freedom {n_classes} - 1 - {parameters_subtracted} = {dof} < 1; use more classes")
    bounds = fitted.quantile(np.arange(1, n_classes) / n_classes)
    observed = np.bincount(np.searchsorted(bounds, x, side="right"), minlength=n_classes)
    expected = x.size / n_classes
    statistic = float(((observed - expected) ** 2 / expected).sum())
    critical = float(stats.chi2.ppf(1 - alpha, dof))
    return ChiSquareResult(statistic=statistic, critical=critical, dof=dof, passed=statistic < critical)


@dataclass(frozen=True)
class SmirnovKolmogorovResult:
    delta_max: float
    critical: float
    passed: bool
    """``delta_max < critical``: the distribution is accepted."""


def test_smirnov_kolmogorov(values, fitted: FittedDistribution, *, plotting_position: str,
                            alpha: float) -> SmirnovKolmogorovResult:
    """Smirnov-Kolmogorov as in the Indonesian texts.

    Delta_max = max |P_e(x_m) - P_t(x_m)| over the sample sorted in descending
    order, P_e from ``plotting_position``, P_t = 1 - F(x_m). Critical value: the
    (1 - alpha) quantile of the exact two-sided statistic (``scipy.stats.kstwo``;
    n = 10, alpha = 0.05: 0.409).
    """
    x = check_sample(values, minimum=4)
    if x.size != fitted.n:
        raise ValueError(f"sample has {x.size} values, the distribution was fitted to {fitted.n}")
    xs = np.sort(x)[::-1]
    empirical = compute_plotting_positions(xs.size, method=plotting_position)
    theoretical = 1 - fitted.cdf(xs)
    delta = float(np.abs(empirical - theoretical).max())
    critical = float(stats.kstwo.ppf(1 - alpha, xs.size))
    return SmirnovKolmogorovResult(delta_max=delta, critical=critical, passed=delta < critical)


# --- intensity -----------------------------------------------------------------------------


def compute_mononobe_intensity(r24, durations_hours) -> np.ndarray:
    """Mononobe intensity ``I = R24 / 24 * (24 / t) ** (2/3)`` (mm/h); shape r24.shape + (len(t),)."""
    r = np.asarray(r24, dtype=np.float64)
    t = np.asarray(durations_hours, dtype=np.float64)
    if t.ndim != 1 or t.size == 0 or not (t > 0).all():
        raise ValueError("durations_hours must be a non-empty 1-D array of values > 0")
    return r[..., None] / 24 * (24 / t) ** (2 / 3)


@dataclass(frozen=True)
class IdfFit:
    """An IDF formula fitted to the intensities of one return period."""

    formula: str
    a: float
    b: float
    """``b`` of Talbot/Ishiguro; the exponent n of Sherman."""
    rmse: float
    mean_deviation: float
    """sum(|I fitted - I given|) / N, mm/h; the smallest selects the formula."""

    def intensity(self, durations_minutes) -> np.ndarray:
        t = np.asarray(durations_minutes, dtype=np.float64)
        if self.formula == "talbot":
            return self.a / (t + self.b)
        if self.formula == "sherman":
            return self.a / t ** self.b
        return self.a / (np.sqrt(t) + self.b)


def fit_idf(durations_minutes, intensities, *, formula: str) -> IdfFit:
    """Least-squares fit of an IDF formula (Sosrodarsono & Takeda).

    Talbot and Ishiguro by linearised least squares with u = t or sqrt(t):
    ``a = ([I u][I^2] - [I^2 u][I]) / (N [I^2] - [I]^2)``,
    ``b = ([I][I u] - N [I^2 u]) / (N [I^2] - [I]^2)``;
    Sherman by least squares of log I = log a - n log t. t in minutes, I in mm/h,
    at least 3 distinct durations, all values > 0.
    """
    t = np.asarray(durations_minutes, dtype=np.float64)
    i = np.asarray(intensities, dtype=np.float64)
    if t.ndim != 1 or t.shape != i.shape or np.unique(t).size < 3:
        raise ValueError("durations and intensities must be 1-D of the same length with at least 3 distinct durations")
    if not (np.isfinite(t).all() and np.isfinite(i).all() and (t > 0).all() and (i > 0).all()):
        raise ValueError("durations and intensities must be finite and > 0")
    if formula in ("talbot", "ishiguro"):
        u = t if formula == "talbot" else np.sqrt(t)
        n = t.size
        den = n * (i ** 2).sum() - i.sum() ** 2
        a = ((i * u).sum() * (i ** 2).sum() - (i ** 2 * u).sum() * i.sum()) / den
        b = (i.sum() * (i * u).sum() - n * (i ** 2 * u).sum()) / den
    elif formula == "sherman":
        slope, intercept = np.polyfit(np.log10(t), np.log10(i), 1)
        a, b = 10 ** intercept, -slope
    else:
        raise ValueError(f"unknown IDF formula {formula!r}; use one of {IDF_FORMULAS}")
    diff = IdfFit(formula, float(a), float(b), 0.0, 0.0).intensity(t) - i
    return IdfFit(formula=formula, a=float(a), b=float(b), rmse=float(np.sqrt((diff ** 2).mean())),
                  mean_deviation=float(np.abs(diff).mean()))
