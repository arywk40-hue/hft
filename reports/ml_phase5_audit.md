# ML Phase 5 Backtest Audit / Reproducibility Check

## Executive verdict

The Part 5 baseline backtest is mathematically correct, temporally consistent, free of look-ahead in the execution path that was audited, and reproducible for all stable outputs. The development result is negative after costs, and that negative result is internally consistent with the trade log and daily P&L.

The only non-stable artifact on rerun was `run_manifest.json`, because it records `created_utc`. All research-bearing outputs were byte-identical across the rerun.

## Scope

Audited artifacts:

- [`src/ebx/ml/backtest.py`](../src/ebx/ml/backtest.py)
- [`scripts/ml/phase_ml4_backtest.py`](../scripts/ml/phase_ml4_backtest.py)
- [`tests/unit/ml/test_backtest.py`](../tests/unit/ml/test_backtest.py)
- [`reports/ml_phase4_backtest.md`](./ml_phase4_backtest.md)
- `results/ml/backtest_baseline/`
- relevant Part 5 language in [`docs/quant.md`](../docs/quant.md)

No holdout day in `86–108` was loaded or inspected during the audit rerun.

## Cost accounting verification

The implementation uses a fixed proportional execution-cost model:

- entry cost: `5 bps`
- exit cost: `5 bps`
- fee: `0 bps`

For a unit-notional trade, total transaction cost is:

`0.0005 + 0.0005 = 0.001`

The trade log contains `941` completed trades, so the pooled cost is:

`941 × 0.001 = 0.941`

That matches the reported pooled transaction cost exactly.

Per-trade cost is also internally consistent in the log: every executed trade has `entry_cost = 0.0005`, `exit_cost = 0.0005`, and `transaction_cost = 0.001`.

## Gross P&L verification

I recomputed gross P&L directly from the trade log using:

`gross_return = direction × (exit_price / entry_price - 1)`

`gross_pnl = gross_return × notional`

The recomputed sums match the reported values up to floating-point roundoff only:

| Window | Trades | Recomputed gross P&L | Reported gross P&L | Difference |
|---|---:|---:|---:|---:|
| W1 | 410 | 0.008677674911853039 | 0.008677674911853672 | ~6.3e-16 |
| W2 | 285 | 0.014409137940399460 | 0.014409137940399441 | ~1.9e-17 |
| W3 | 246 | 0.021281444252719980 | 0.021281444252720383 | ~4.0e-16 |
| Pooled | 941 | 0.044368257104972470 | 0.044368257104973496 | ~1.0e-15 |

No gross P&L discrepancy was found.

## Net P&L verification

The identity

`net P&L = gross P&L - transaction costs`

holds exactly at the reported precision for W1, W2, W3, and pooled.

Examples:

- W1: `0.008677674911853672 - 0.41000000000000014 = -0.40132232508814647`
- W2: `0.014409137940399441 - 0.28500000000000003 = -0.2705908620596006`
- W3: `0.021281444252720383 - 0.2460000000000001 = -0.2247185557472797`
- Pooled: `0.044368257104973496 - 0.9410000000000004 = -0.8966317428950269`

## Timestamp / holding-period verification

Every executed trade in `results/ml/backtest_baseline/trade_log.csv` satisfies:

- `exit_timestamp_seconds - entry_timestamp_seconds = 300`
- entry and exit are within the same day
- no cross-day carry was used

The implementation uses an exact same-day exit convention:

- entry: first raw price observation at or after the signal timestamp
- exit: the exact raw timestamp at `entry + 300 seconds`
- if that exact exit is absent, the trade is skipped

This matches the report and the code path.

## Look-ahead verification

The audited execution path uses only:

- timestamped predictions from the validated temporal artifacts
- same-day raw price observations for entry and exit accounting

It does not use:

- target values
- future prices
- future feature values
- future-day regime information
- validation aggregates

for signal generation or trade execution.

The signal rule is purely sign-based and deterministic.

## Position / overlap verification

The intended protocol is one position at a time.

The audit recomputation found:

- maximum simultaneous position count: `1`
- no pyramiding
- no duplicate overlapping trades
- no unintended cross-day position state

Signals arriving before the exact exit timestamp are ignored, which is consistent with the documented rule.

## Day-boundary verification

The development windows are:

- W1: `45–54`
- W2: `55–64`
- W3: `80–85`

Days `65–79` are explicitly represented as missing development days and were not fabricated.
Days `86–108` were not loaded or inspected.

No trade crossed a day boundary.

## Day-84 sensitivity verification

The Day-84 diagnostic is a post-hoc aggregation only.

| W3 aggregation | Trades | Gross P&L | Costs | Net P&L |
|---|---:|---:|---:|---:|
| Including Day 84 | 246 | 0.021281444252720383 | 0.2460000000000001 | -0.2247185557472797 |
| Excluding Day 84 | 205 | 0.007387805990262564 | 0.20500000000000007 | -0.1976121940097375 |

The difference comes only from removing Day 84’s realized trades and P&L from the aggregation. There was no retraining, no strategy change, and no feature-selection change.

## Sharpe calculation audit

The reported Sharpe values are computed from daily net P&L using:

- mean daily net P&L
- sample standard deviation of daily net P&L
- annualization factor `sqrt(252)`

That is mathematically coherent and matches the implementation.

The unusually large negative magnitudes are a consequence of the fact that daily net P&L is consistently negative after fixed costs. This makes the Sharpe statistically valid but economically unattractive and potentially easy to misread if the daily convention is not stated explicitly.

## Turnover audit

Turnover is defined as:

`2 × sum(notional over trades)`

With unit notional, each completed trade contributes `2.0` of turnover.

Therefore:

- `410 × 2 = 820`
- `285 × 2 = 570`
- `246 × 2 = 492`
- pooled `941 × 2 = 1882`

That matches the reported results exactly.

## Cost-assumption audit

The 5 bps per-side cost model is not empirically estimated from the data because the repository does not provide validated bid/ask, fee, or slippage fields for Part 5 execution. It is an explicit parameterized baseline assumption.

That assumption is supported as a reasonable challenge-compliant placeholder, but it should be described as an assumption rather than a measured market microstructure estimate.

## Part 5 rubric mapping

| Requirement | Implemented? | Evidence / path | Remaining gap |
|---|---|---|---|
| Clear long / flat / short signal | Yes | `src/ebx/ml/backtest.py`, `signal_rule` | None |
| Fixed position sizing | Yes | fixed unit notional in `StrategyConfig` | None |
| Transaction costs | Yes | `TransactionCostModel`, `strategy_config.json` | Assumption is not empirically calibrated |
| No look-ahead | Yes | `simulate_day` uses same-day predictions and prices only | None found |
| In-sample / out-of-sample split | Yes | temporal windows in `results/ml/temporal_robustness/` and Part 5 report | None |
| Sharpe / Sortino / max drawdown / hit rate / turnover | Yes | `summary_metrics.json`, `window_metrics.csv` | None |
| Trade log | Yes | `results/ml/backtest_baseline/trade_log.csv` | Schema is richer than the minimum rubric |
| Backtesting script | Yes | `scripts/ml/phase_ml4_backtest.py` | None |
| Performance report | Yes | `reports/ml_phase4_backtest.md` | None |
| Required comparisons | Yes | primary, random-null, passive-long, zero-trade | Comparators are descriptive, not selection criteria |

## Reproducibility result

I reran the Part 5 script once during the audit.

Stable outputs were byte-identical before and after the rerun:

- `trade_log.csv`
- `daily_pnl.csv`
- `window_metrics.csv`
- `baseline_metrics.csv`
- `summary_metrics.json`
- `equity_curve.csv`
- `cost_breakdown.csv`
- `strategy_config.json`
- `W1_manifest.json`
- `W2_manifest.json`
- `W3_manifest.json`
- `day84_sensitivity.json`
- `reproducibility.json`

Only `run_manifest.json` changed, because it stores a fresh `created_utc` timestamp on each execution.

## Frozen-artifact hash comparison

Verified unchanged frozen artifacts:

- `results/freeze/development_freeze.json`
- `results/predictive/aggregate_ic.csv`
- `results/ml/features/frozen_feature_set.csv`
- `results/ml/train_only_selection/selected_features.csv`
- `results/ml/temporal_robustness/run_manifest.json`
- `results/ml/day84_forensics/day84_forensics.json`
- `results/ml/temporal_robustness/day84_sensitivity.json`

Representative hashes:

- development freeze: `916be8b0c6d9bff52570ca1759b84e78eb782ad20140a569a6c1b7df5aa737fe`
- aggregate IC: `c6b813c4e709f00030b0e2ed4d868fd231dfe89273020c265bd238aad4f37e07`
- frozen feature set: `d9aec0b7292ba595dd06a5c90eefe4ec6bd1563023428f9a414041fe4594e4fa`
- train-only selection features: `84a6c1ef307b4f00673efa5e75a017f9221b904fc9d35080f4fdd4b6d883c86d`
- temporal robustness manifest: `dd84ad1ea8e1f23018ac3b852e494f26f5982057c32040f15377e6e889c84325`
- day-84 forensic result: `395d731a28e6c721a5b96aab4059568796232eb83cab96a0ab2e61999870d3b3`

The Part 5 rerun did not modify those files.

## Holdout-access confirmation

`holdout_days_loaded: []` is present in the backtest run manifest and the temporal validation manifests used by Part 5.

Days `86–108` were not loaded, inspected, or used in the audit rerun.

## Methodological issues

1. The 5 bps per-side execution cost is an explicit assumption, not an empirically measured cost from repository data.
2. The pooled development result concatenates multiple temporal windows that reuse some calendar days across experiments, so it is descriptive rather than a single continuous portfolio.
3. The Sharpe values are mathematically correct under the daily-net-P&L convention, but the magnitude is extreme because fixed costs dominate the signal.

## Final assessment

The existing Part 5 development baseline is suitable for inclusion in the final research report as a negative-cost-adjusted baseline, provided the caveats above are stated clearly.

It should not be framed as profitability evidence, alpha evidence, production readiness, or holdout generalization.

