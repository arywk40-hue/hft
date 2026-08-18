"""Day-boundary-safe future-return target generation and profiling."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from src.common.day_boundary import parse_time_seconds


def _timestamp_seconds(values: Iterable[object]) -> np.ndarray:
    parsed = [parse_time_seconds(value) for value in values]
    if any(value is None for value in parsed):
        raise ValueError("invalid timestamp in target input")
    seconds = np.asarray(parsed, dtype=np.int64)
    if len(seconds) > 1 and np.any(np.diff(seconds) <= 0):
        raise ValueError("target input must have strictly increasing timestamps")
    return seconds


def build_future_return_target(
    day_data: pd.DataFrame,
    horizon: int,
    *,
    time_column: str = "Time",
    price_column: str = "Price",
) -> pd.Series:
    """Return ``P(t+h) / P(t) - 1`` using exact timestamps within one day.

    The function accepts one day only. Missing timestamps and the final ``h``
    observations naturally receive NaN targets; no interpolation or forward
    fill is performed.
    """

    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if time_column not in day_data or price_column not in day_data:
        raise KeyError(f"missing {time_column!r} or {price_column!r}")
    seconds = _timestamp_seconds(day_data[time_column].tolist())
    prices = pd.to_numeric(day_data[price_column], errors="coerce").to_numpy(dtype=float)
    by_second = {int(second): index for index, second in enumerate(seconds)}
    result = np.full(len(day_data), np.nan, dtype=float)
    for index, second in enumerate(seconds):
        future_index = by_second.get(int(second + horizon))
        if future_index is None:
            continue
        current = prices[index]
        future = prices[future_index]
        if np.isfinite(current) and current > 0 and np.isfinite(future) and future > 0:
            result[index] = future / current - 1.0
    return pd.Series(result, index=day_data.index, name=f"future_return_{horizon}s")


def _profile(values: np.ndarray) -> dict[str, float | int]:
    valid = values[np.isfinite(values)]
    if len(valid) == 0:
        return {
            "valid_observations": 0,
            "missing_target_observations": int(len(values)),
            "mean": np.nan,
            "std": np.nan,
            "skewness": np.nan,
            "kurtosis": np.nan,
            "q01": np.nan,
            "q05": np.nan,
            "q25": np.nan,
            "q50": np.nan,
            "q75": np.nan,
            "q95": np.nan,
            "q99": np.nan,
            "positive_fraction": np.nan,
            "negative_fraction": np.nan,
            "zero_fraction": np.nan,
        }
    return {
        "valid_observations": int(len(valid)),
        "missing_target_observations": int(len(values) - len(valid)),
        "mean": float(np.mean(valid)),
        "std": float(np.std(valid, ddof=1)) if len(valid) > 1 else np.nan,
        "skewness": float(pd.Series(valid).skew()) if len(valid) > 2 else np.nan,
        "kurtosis": float(pd.Series(valid).kurt()) if len(valid) > 3 else np.nan,
        "q01": float(np.quantile(valid, 0.01)),
        "q05": float(np.quantile(valid, 0.05)),
        "q25": float(np.quantile(valid, 0.25)),
        "q50": float(np.quantile(valid, 0.50)),
        "q75": float(np.quantile(valid, 0.75)),
        "q95": float(np.quantile(valid, 0.95)),
        "q99": float(np.quantile(valid, 0.99)),
        "positive_fraction": float(np.mean(valid > 0)),
        "negative_fraction": float(np.mean(valid < 0)),
        "zero_fraction": float(np.mean(valid == 0)),
    }


def profile_target(values: pd.Series | np.ndarray, *, scope: str, day: int | None, horizon: int) -> dict[str, object]:
    """Create one day or pooled target-profile row."""

    array = np.asarray(values, dtype=float)
    return {"scope": scope, "day": day, "horizon_seconds": int(horizon), **_profile(array)}
