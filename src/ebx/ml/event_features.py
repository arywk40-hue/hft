"""Causal Phase 10 event features and matched negative sampling."""
from __future__ import annotations

import numpy as np
import pandas as pd

LAGS = (5, 30, 60, 300)


def causal_features(frame: pd.DataFrame, *, day: int, feature_columns: list[str]) -> pd.DataFrame:
    """Return features that use rows at or before each timestamp only."""
    result = pd.DataFrame({"day": day, "timestamp_seconds": frame["timestamp_seconds"].to_numpy(int)})
    price = frame["Price"].astype(float)
    log_price = np.log(price)
    result["return_5s"] = log_price.diff(5)
    result["return_30s"] = log_price.diff(30)
    result["return_60s"] = log_price.diff(60)
    result["return_300s"] = log_price.diff(300)
    result["volatility_60s"] = log_price.diff().rolling(60, min_periods=30).std()
    result["volatility_300s"] = log_price.diff().rolling(300, min_periods=60).std()
    result["time_of_session"] = result["timestamp_seconds"] / max(1, int(result["timestamp_seconds"].max()))
    for column in feature_columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        result[f"value_{column}"] = values
        for lag in LAGS:
            result[f"delta_{column}_{lag}s"] = values.diff(lag)
        mean = values.rolling(300, min_periods=60).mean()
        std = values.rolling(300, min_periods=60).std().replace(0, np.nan)
        result[f"zscore_{column}"] = (values - mean) / std
    return result.replace([np.inf, -np.inf], np.nan)


def event_dataset(features: pd.DataFrame, oracle: pd.DataFrame, *, seed: int = 20260824) -> pd.DataFrame:
    """Build positives plus time/volatility-matched and nearby hard negatives."""
    rng = np.random.default_rng(seed); rows=[]
    for event in oracle.itertuples(index=False):
        day = int(event.day); ts = int(event.entry_timestamp_seconds)
        subset = features[features.day == day]
        positive = subset[subset.timestamp_seconds == ts]
        if positive.empty: continue
        direction = 1 if event.direction == "LONG" else -1
        rows.append(positive.assign(label=direction, sample_type="oracle"))
        # hard negative immediately outside a 60-second event exclusion region
        for candidate_ts in (ts - 90, ts + 90):
            candidate = subset[subset.timestamp_seconds == candidate_ts]
            if not candidate.empty and not ((oracle.day == day) & (np.abs(oracle.entry_timestamp_seconds - candidate_ts) <= 60)).any():
                rows.append(candidate.assign(label=0, sample_type="hard_negative"))
        # same-day, similar 5-minute time-of-day bucket, away from oracle entries
        bucket = ts // 300
        controls = subset[(subset.timestamp_seconds // 300 == bucket) & ~subset.timestamp_seconds.isin(range(ts - 60, ts + 61))]
        if not controls.empty:
            rows.append(controls.iloc[[int(rng.integers(len(controls))) ]].assign(label=0, sample_type="matched_control"))
    if not rows: return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).dropna().reset_index(drop=True)
