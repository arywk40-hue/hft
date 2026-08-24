"""Leakage-safe day summaries and deterministic PAM clustering for Phase 10."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PAMResult:
    labels: np.ndarray
    medoid_indices: np.ndarray


def day_features(day: int, frame: pd.DataFrame) -> dict[str, float | int]:
    """Compute reproducible price-only day features; no cross-day information."""
    price = frame["Price"].astype(float).to_numpy()
    if len(price) < 10 or np.any(~np.isfinite(price)) or np.any(price <= 0):
        raise ValueError("day requires at least ten finite positive prices")
    ret = np.diff(np.log(price))
    x = np.arange(len(price), dtype=float)
    slope, intercept = np.polyfit(x, np.log(price), 1)
    fitted = slope * x + intercept
    ss_tot = float(np.sum((np.log(price) - np.mean(np.log(price))) ** 2))
    r2 = 1.0 - float(np.sum((np.log(price) - fitted) ** 2)) / ss_tot if ss_tot else 0.0
    peak = np.maximum.accumulate(price)
    return {"day": day, "open_to_close_return": float(price[-1] / price[0] - 1),
            "realized_vol_1s": float(np.std(ret)), "realized_vol_5s": float(np.std(ret[4::5])),
            "intraday_range": float((price.max() - price.min()) / price[0]),
            "trend_slope": float(slope), "trend_r2": float(r2),
            "max_drawdown": float(np.min(price / peak - 1)), "return_skew": float(pd.Series(ret).skew()),
            "return_kurtosis": float(pd.Series(ret).kurt()),
            "three_sigma_frequency": float(np.mean(np.abs(ret) > 3 * np.std(ret))) if np.std(ret) else 0.0,
            "lag1_autocorrelation": float(pd.Series(ret).autocorr(lag=1) or 0.0)}


def standardize_development(table: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, dict[str, dict[str, float]]]:
    values = table[columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    mean, std = values.mean(), values.std(ddof=0).replace(0.0, 1.0)
    return ((values - mean) / std).to_numpy(float), {c: {"mean": float(mean[c]), "std": float(std[c])} for c in columns}


def deterministic_pam(x: np.ndarray, n_clusters: int = 5) -> PAMResult:
    """Small deterministic PAM: lexicographic initial medoids and exhaustive swaps."""
    if not 1 <= n_clusters <= len(x): raise ValueError("invalid cluster count")
    dist = np.sqrt(((x[:, None, :] - x[None, :, :]) ** 2).sum(axis=2))
    medoids = np.linspace(0, len(x) - 1, n_clusters, dtype=int)
    def objective(m: np.ndarray) -> float: return float(dist[:, m].min(axis=1).sum())
    improved = True
    while improved:
        improved = False; base = objective(medoids)
        for old in range(n_clusters):
            for candidate in range(len(x)):
                if candidate in medoids: continue
                proposed = medoids.copy(); proposed[old] = candidate; proposed.sort()
                value = objective(proposed)
                if value < base - 1e-12:
                    medoids, base, improved = proposed, value, True
    labels = dist[:, medoids].argmin(axis=1)
    return PAMResult(labels=labels, medoid_indices=medoids)


def representative_indices(labels: np.ndarray, medoids: np.ndarray, total: int = 14) -> np.ndarray:
    chosen = set(map(int, medoids)); n = len(labels)
    for cluster in range(len(medoids)):
        members = np.flatnonzero(labels == cluster)
        quota = max(1, round(total * len(members) / n))
        for index in members:
            if len([i for i in chosen if labels[i] == cluster]) >= quota: break
            chosen.add(int(index))
    return np.asarray(sorted(chosen), dtype=int)
