"""Future-only labels for Phase 10; never use these values as input features."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class OracleConfig:
    max_trades: int = 5
    min_holding_seconds: int = 30
    max_holding_seconds: int = 300
    entry_cost_bps: float = 1.0
    exit_cost_bps: float = 1.0

def extract_oracle_trades(day: int, prices: pd.DataFrame, config: OracleConfig = OracleConfig(), entry_stride_seconds: int = 30) -> pd.DataFrame:
    """Dynamic-programming maximum net P&L labels over non-overlapping intervals."""
    p = prices["Price"].to_numpy(float); t = np.arange(len(p)) if "timestamp_seconds" not in prices else prices["timestamp_seconds"].to_numpy(int)
    candidates=[]; cost=(config.entry_cost_bps+config.exit_cost_bps)/10000
    # Candidate entries are deliberately sampled at a declared 30-second cadence;
    # this bounds label construction without changing the causal feature timeline.
    holding_grid = tuple(range(config.min_holding_seconds, config.max_holding_seconds + 1, 30))
    for i in range(0, len(p), entry_stride_seconds):
        for hold in holding_grid:
            j = int(np.searchsorted(t, t[i] + hold, side="left"))
            if j >= len(p) or int(t[j] - t[i]) != hold: continue
            raw=p[j]/p[i]-1
            for direction, gross in ((1, raw), (-1, -raw)):
                net=gross-cost
                if net > 0: candidates.append((j,i,direction,gross,net,hold))
    candidates.sort()
    # weighted interval scheduling with cardinality cap
    dp=np.zeros((len(candidates)+1, config.max_trades+1)); take=np.zeros_like(dp,dtype=bool)
    ends=np.asarray([c[0] for c in candidates], dtype=int)
    for q,(end,start,*_) in enumerate(candidates,1):
        prev=int(np.searchsorted(ends, start, side="right"))
        for k in range(1,config.max_trades+1):
            a=dp[q-1,k]; b=dp[prev,k-1]+candidates[q-1][4]
            if b>a: dp[q,k]=b; take[q,k]=True
            else: dp[q,k]=a
    out=[]; q,k=len(candidates),config.max_trades
    while q and k:
        if take[q,k]:
            end,start,direction,gross,net,hold=candidates[q-1]; out.append({"day":day,"entry_timestamp_seconds":int(t[start]),"exit_timestamp_seconds":int(t[end]),"direction":"LONG" if direction>0 else "SHORT","holding_seconds":hold,"gross_return":gross,"transaction_cost":cost,"net_return":net}); q=int(np.searchsorted(ends[:q-1],start,side="right")); k-=1
        else: q-=1
    return pd.DataFrame(sorted(out,key=lambda r:r["entry_timestamp_seconds"]))
