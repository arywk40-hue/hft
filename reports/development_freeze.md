# EBX Development Freeze

## Scope

This note freezes the completed development research state. The specification
contains 85 development days; 70 are available (Days 1–64 and 80–85), while
Days 65–79 remain explicit missing gaps. No result is an 85-day development
claim.

## Completed work

- Parts 1–4: data hygiene, distributions and tails, regimes, and feature
  forensics, including the completed Part 4 figure set.
- ML Phase 0: model-ready, day-local, train-only-preprocessed data pipeline.
- Ridge baseline: frozen 197-feature screen, 300-second target, train Days
  1–64 and validate Days 80–85.
- Training-only feature selection: 691 candidates, 198 selected 300-second
  features, with all 197 frozen features retained.
- Temporal robustness: W1, W2, and W3 blocked chronological experiments.
- Day-84 forensic analysis: post-hoc diagnostic only; Day 84 remains in W3.
- Part 5: one fixed-rule baseline strategy and development backtest.
- Part 5 audit: cost, P&L, timestamp, overlap, day-boundary, look-ahead, and
  reproducibility checks completed.

## Key development metrics

| Window | Trades | Gross P&L | Costs | Net P&L | Sharpe |
|---|---:|---:|---:|---:|---:|
| W1 | 410 | 0.008677675 | 0.410000 | -0.401322325 | -186.162764 |
| W2 | 285 | 0.014409138 | 0.285000 | -0.270590862 | -32.994427 |
| W3 | 246 | 0.021281444 | 0.246000 | -0.224718556 | -106.280913 |
| Pooled development | 941 | 0.044368257 | 0.941000 | -0.896631743 | -52.575858 |

The strategy uses prediction sign, fixed unit notional, one position at a time,
and a 300-second same-day holding period. The documented cost assumption is 5
bps on entry plus 5 bps on exit, with zero fee. It is a parameterized baseline
assumption, not an empirically measured market-microstructure estimate.

Day-84 sensitivity is post-hoc only: W3 net P&L is -0.224718556 including Day
84 and -0.197612194 excluding it. The primary result includes Day 84.

## Limitations and freeze rules

- Predictive association is not economic utility. The positive gross P&L did
  not survive the documented transaction-cost assumption.
- The development baseline does not demonstrate economic viability after the
  documented transaction-cost assumption.
- No production-readiness, profitability, alpha, or holdout-generalization
  claim is made from the development backtest.
- No further model, feature selection, optimization, strategy, or backtest is
  part of this freeze.

Days 86–108 were not used for development, tuning, or evaluation.
