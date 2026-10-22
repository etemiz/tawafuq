"""Finite Monte Carlo uncertainty; deliberately no Gaussian tail conversion."""
import numpy as np
from scipy.stats import beta


def tail_summary(observed, samples, confidence=0.95):
    samples = np.asarray(samples)
    if samples.ndim != 1 or len(samples) < 2 or not np.isfinite(samples).all():
        raise ValueError("at least two finite scalar replicates required")
    if not np.isfinite(observed) or not 0 < confidence < 1:
        raise ValueError("finite observation and confidence in (0,1) required")
    n = len(samples)
    exceed = int(np.count_nonzero(samples >= observed))
    alpha = 1 - confidence
    low = float(beta.ppf(alpha / 2, exceed, n - exceed + 1)) if exceed else 0.0
    high = float(beta.ppf(1 - alpha / 2, exceed + 1, n - exceed)) if exceed < n else 1.0
    # Separate one-sided upper bound, especially useful at zero exceedances.
    upper = float(beta.ppf(confidence, exceed + 1, n - exceed)) if exceed < n else 1.0
    sd = float(samples.std(ddof=1))
    return dict(observed=float(observed), reps=n, exceedances=exceed,
                null_mean=float(samples.mean()), null_sd=sd,
                null_min=float(samples.min()), null_max=float(samples.max()),
                null_mean_mc_se=sd / np.sqrt(n),
                descriptive_z=(float((observed - samples.mean()) / sd) if sd else None),
                tail_fraction=exceed / n, plus_one_mc=(exceed + 1) / (n + 1),
                confidence=confidence, tail_interval=[low, high],
                tail_upper_one_sided=upper,
                interpretation="Tail under the supplied simulation model; no extreme-tail extrapolation. "
                "Plus-one is an MC reporting convention, not proof of exchangeability.")
