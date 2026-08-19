# EBX Research Artifact Index

Every principal conclusion in `reports/final_report.md` is traceable to a
generated artifact.

| Conclusion | Source artifact |
|---|---|
| Development coverage and missing Days 65–79 | `results/phase0/dataset_inventory.csv`, `data/validated/manifest.csv` |
| Development freeze and thresholds | `results/freeze/development_freeze.json` |
| Freeze checksum used for holdout | `results/holdout/freeze_manifest.json` |
| Schema, timestamps, and prices | `results/quality/schema_validation.csv`, `results/quality/day_integrity.csv`, `results/quality/price_validation.csv` |
| Structural missingness and warm-up | `results/missingness/structural_missingness.csv`, `results/missingness/cross_day_warmup.csv` |
| Part 1 descriptive statistics and ACF | `results/quality/descriptive_stats.csv`, `results/diagnostics/acf_returns.csv`, `results/diagnostics/volatility_seasonality.csv` |
| Distribution and tails | `results/distributions/normality_tests.csv`, `results/distributions/sigma_events.csv`, `results/distributions/tail_estimates.csv`, `results/distributions/extreme_events.csv` |
| Development regimes | `results/regimes/regime_table.csv`, `results/regimes/transition_matrix.csv`, `results/regimes/regime_durations.csv` |
| Feature taxonomy | `results/features/feature_taxonomy.csv`, `results/features/family_summary.csv` |
| Frozen formula hypotheses | `results/features/candidate_best_matches.csv`, `results/features/candidate_scores.csv` |
| Development predictive screen | `results/predictive/aggregate_ic.csv`, `results/predictive/per_day_ic.csv` |
| Development PCA/redundancy | `results/redundancy/pca_summary.csv`, `results/redundancy/redundancy_summary.json` |
| ML Phase 0 model-ready pipeline | `results/ml/targets/`, `results/ml/datasets/`, `results/ml/validation/` |
| Ridge baseline and controlled ML experiments | `results/ml/baseline/`, `results/ml/train_only_selection/`, `results/ml/temporal_robustness/`, `results/ml/day84_forensics/` |
| Part 5 baseline development backtest | `results/ml/backtest_baseline/`, `figures/ml_phase4/`, `reports/ml_phase4_backtest.md` |
| Integrated development interpretation | `reports/phase11_integrated_review.md` |
| Holdout integrity | `results/holdout/integrity.csv`, `results/holdout/schema.csv`, `results/holdout/missingness.csv` |
| Window generalization | `results/holdout/window_generalization.csv` |
| Feature-hypothesis generalization | `results/holdout/feature_hypothesis_validation.csv` |
| Predictive generalization | `results/holdout/ic_validation.csv` |
| Regime generalization | `results/holdout/regime_validation.csv`, `results/holdout/regime_transitions.csv` |
| Distribution/tail generalization | `results/holdout/distribution_validation.csv`, `results/holdout/extreme_events.csv` |
| PCA/redundancy generalization | `results/holdout/pca_validation.csv`, `results/holdout/redundancy_validation.csv` |
| Final holdout verdict | `reports/holdout_validation.md`, `results/holdout/holdout_summary.csv` |

No table combines development and holdout observations for an out-of-sample
claim.
