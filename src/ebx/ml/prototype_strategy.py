"""Causal confidence gate and bounded volatility-adjusted sizing."""
from __future__ import annotations
import numpy as np
import pandas as pd

def position_size(confidence: float, volatility: float, *, threshold: float, target_volatility: float, epsilon: float = 1e-8) -> float:
    if not (0 <= confidence <= 1) or volatility < 0: raise ValueError("invalid confidence or volatility")
    if confidence < threshold: return 0.0
    strength=(confidence-threshold)/max(1-threshold,epsilon)
    return float(min(1.0, strength*target_volatility/max(volatility,epsilon)))

def should_enter(predicted_gross_edge: float, confidence: float, *, threshold: float, safety_buffer: float, round_trip_cost: float = .0002) -> bool:
    return bool(np.isfinite(predicted_gross_edge) and predicted_gross_edge > round_trip_cost+safety_buffer and confidence >= threshold)


def simulate_confidence_strategy(features: pd.DataFrame, probabilities: np.ndarray, prices: pd.DataFrame, *, threshold: float, safety_buffer: float, target_volatility: float, max_hold: int = 300) -> pd.DataFrame:
    """One-position causal simulation; exits use only current price/P&L and time."""
    price_by_time = dict(zip(prices.timestamp_seconds.astype(int), prices.Price.astype(float)))
    rows=[]; next_allowed=-1
    for item, prob in zip(features.itertuples(index=False), probabilities):
        ts=int(item.timestamp_seconds)
        if ts < next_allowed or ts not in price_by_time: continue
        direction=int(np.argmax(prob))-1; confidence=float(np.max(prob))
        if direction == 0: continue
        edge=float(abs(getattr(item,"return_300s",0.0) or 0.0))
        vol=float(getattr(item,"volatility_60s",0.0) or 0.0)
        if not should_enter(edge,confidence,threshold=threshold,safety_buffer=safety_buffer): continue
        size=position_size(confidence,vol,threshold=threshold,target_volatility=target_volatility)
        exit_ts=ts+max_hold
        if exit_ts not in price_by_time: continue
        gross=direction*(price_by_time[exit_ts]/price_by_time[ts]-1); cost=.0002*size
        rows.append({"day":int(item.day),"entry_timestamp_seconds":ts,"exit_timestamp_seconds":exit_ts,"direction":direction,"position_size":size,"gross_return":gross*size,"transaction_cost":cost,"net_return":gross*size-cost})
        next_allowed=exit_ts
    return pd.DataFrame(rows)
