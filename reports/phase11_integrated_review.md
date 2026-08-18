# Phase 11 — Integrated Evidence Review

## Scope

- expected_development_days = 85
- available_development_days = 70 (Days 1–64 and 80–85)
- missing_development_days = 15 (Days 65–79)
- Days 86–108 were not opened or processed.

## Observed facts

- The taxonomy contains 691 masked features; 594 retain nominal-vs-actual warm-up deviations.
- The regime table contains 61 persistent and 9 random-walk/inconclusive available-day classifications; 9 rows retain conflicts.
- Pairwise redundancy includes 9455 pairs with mean absolute Pearson correlation at least 0.90.
- The pooled PCA reaches 50%, 80%, and 90% variance at 3, 15, and 35 components.

## Statistical results

- Predictive relevance uses exact within-day feature(t) to return(t+h) alignment and FDR alpha 0.05. After requiring FDR rejection, same-sign fraction at least 0.70, and absolute mean Pearson IC at least 0.05, 543 feature-horizon rows remain; these are statistical/practical screening results, not a strategy.
- Candidate reverse engineering produced 407 best-match hypotheses. The median dominant candidate fraction across the 70 available days is 1.0000; 268 features have a dominant candidate on at least 80% of available days.
- Regime/volatility consistency is written to `results/phase11/regime_volatility_consistency.csv`; this is descriptive and does not validate regime causality.

## Hypotheses and interpretations

- Nominal window ladders are hypotheses constrained by observed warm-up; deviations are retained and are not forced to match.
- Candidate correlations support formula hypotheses only. No masked feature identity is confirmed from one metric, one day, or one horizon.
- Feature redundancy and PCA indicate a low-dimensional representation may be plausible, but do not establish independent tradable factors.
- The top 20 extreme events were catalogued. No event-conditioned feature identity claim is made; raw volume semantics remain unavailable.

## Limitations

- All conclusions are development-only and based on 70 days, not 85.
- Days 65–79 are explicit missing gaps; no transition, lag, rolling, or forward-return calculation bridges them.
- Holdout validation is intentionally not performed in this run.
