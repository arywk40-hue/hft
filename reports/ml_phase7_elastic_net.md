# ML Phase 7 — Elastic Net Model Comparison Against Ridge

## Executive summary

This is one isolated Elastic Net comparison against the existing Ridge
experiments. The model, feature-selection artifacts, target, preprocessing,
chronological windows, and Part 5 execution convention were fixed before the
real-data evaluation. No hyperparameter search or validation-based selection
was performed.

The primary result uses the existing training-only selected feature artifact
and is evaluated on Days 80–85. Elastic Net has lower primary Pearson IC than
the corresponding training-only Ridge comparison (0.033652 vs 0.070712),
negative pooled R², and negative cost-adjusted backtest P&L in every temporal
window. This does not support an economic edge.

The direct estimator comparison is against the existing training-only Ridge
artifacts because this Phase 7 controls the model change while retaining the
validated training-only feature-selection protocol. The frozen-screen 197-
feature Ridge remains a prior context artifact; it was not modified or
recomputed here.

## Data and boundary

| Item | Value |
|---|---:|
| Expected development days | 85 |
| Available development days | 70 |
| Missing development days | 65–79 (15 days) |
| Primary training days | 1–64 |
| Primary validation days | 80–85 |
| Holdout days loaded | `[]` |
| Holdout accessed | `false` |

Days 65–79 remain an explicit gap. Days 86–108 were not loaded, inspected,
or used by the implementation or validation run.

Temporal robustness windows used the existing development-only definitions:

| Window | Training | Validation | Selected features | Train rows | Validation rows |
|---|---|---|---:|---:|---:|
| W1 | 1–44 | 45–54 | 195 | 538,648 | 122,420 |
| W2 | 1–54 | 55–64 | 194 | 661,068 | 84,632 |
| W3 / primary | 1–64 | 80–85 | 198 | 745,700 | 73,452 |

The W1/W2 validation row counts are lower than ten times the nominal day
count because the existing model-ready partitions retain their actual valid
rows. No rows were imputed or silently fabricated by this experiment.

## Feature-selection and preprocessing protocol

The experiment consumed the existing training-only selected feature artifacts
unchanged:

- primary/W3: [`results/ml/train_only_selection/selected_features.csv`](../results/ml/train_only_selection/selected_features.csv)
- W1: [`results/ml/temporal_robustness/W1/selected_features.csv`](../results/ml/temporal_robustness/W1/selected_features.csv)
- W2: [`results/ml/temporal_robustness/W2/selected_features.csv`](../results/ml/temporal_robustness/W2/selected_features.csv)

The feature counts are therefore 198, 195, and 194 respectively. No feature
screen was recomputed and no feature names were added, removed, or tuned after
observing validation results. The existing train-only preprocessing was
consumed through the existing model-ready partitions; Elastic Net fitting
used only the training partitions, and validation partitions were transformed
only for prediction/evaluation.

The primary 198-feature artifact is not the frozen 197-feature screen. It is
the already-completed training-only selection experiment. This is intentional
and is recorded to keep the estimator comparison methodologically controlled.

## Model specification

The only new model is Elastic Net with deterministic cyclic coordinate descent:

```text
alpha       = 1e-6
l1_ratio    = 0.5
max_iter    = 10000
tol         = 1e-4
fit_intercept = true
selection   = cyclic
random_state = null
target      = 300-second future return
```

The initial fixed iteration cap of 5,000 was found to be insufficient for
convergence on the correlated real feature matrix. It was raised once to
10,000 as a convergence/correctness remediation, not as validation tuning.
All four real-data fits converged before that cap:

| Window | Iterations | Converged | Nonzero coefficients |
|---|---:|---|---:|
| W1 | 5,615 | true | 27 |
| W2 | 5,402 | true | 27 |
| W3 / primary | 5,091 | true | 23 |

The sufficient-statistics coordinate-descent implementation was checked on a
synthetic fixture against scikit-learn Elastic Net; coefficients, intercept,
and predictions matched to floating-point precision.

## Predictive validation results

### Pooled metrics

| Window | Pearson IC | Spearman IC | Mean daily Pearson IC | Median daily Pearson IC | Daily Pearson SD | Directional accuracy | R² | MAE | RMSE | Prediction mean | Prediction SD | Target mean | Target SD | Rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| W1 | -0.0221621274 | -0.0100365308 | 0.0211146548 | -0.0177771695 | 0.1090000037 | 0.4927789577 | -0.0273071902 | 0.0004554827 | 0.0007846549 | -0.0000106591 | 0.0000970980 | 0.0000493905 | 0.0007741593 | 122,420 |
| W2 | 0.0004949406 | -0.0483169882 | -0.0302139549 | -0.0190925536 | 0.1500414595 | 0.4718428018 | -0.0138397044 | 0.0004404260 | 0.0006392111 | 0.0000102835 | 0.0000730836 | -0.0000065201 | 0.0006348370 | 84,632 |
| W3 / primary | 0.0336523173 | 0.0167399275 | 0.0037559573 | 0.0005424608 | 0.0475279440 | 0.5082094429 | -0.0164686767 | 0.0004302557 | 0.0006564259 | 0.0000021035 | 0.0000724318 | 0.0000721680 | 0.0006510910 | 73,452 |

### Daily metrics — W3 / primary validation Days 80–85

| Day | Pearson IC | Spearman IC | R² | MAE | RMSE | Directional accuracy | Rows |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 80 | -0.015720 | 0.006012 | -0.034339 | 0.000228 | 0.000292 | 0.562980 | 12,242 |
| 81 | -0.064043 | -0.055253 | -0.083234 | 0.000189 | 0.000232 | 0.461117 | 12,242 |
| 82 | 0.081406 | 0.058705 | 0.004323 | 0.000249 | 0.000323 | 0.552442 | 12,242 |
| 83 | 0.002855 | 0.030163 | -0.011043 | 0.000644 | 0.000832 | 0.504248 | 12,242 |
| 84 | -0.001771 | -0.099732 | -0.018716 | 0.000633 | 0.000819 | 0.480559 | 12,242 |
| 85 | 0.019808 | 0.070975 | -0.085521 | 0.000638 | 0.000989 | 0.487910 | 12,242 |

The complete unrounded daily files are preserved at:

- [`results/ml/elastic_net/primary/daily_metrics.csv`](../results/ml/elastic_net/primary/daily_metrics.csv)
- [`results/ml/elastic_net/W1/daily_metrics.csv`](../results/ml/elastic_net/W1/daily_metrics.csv)
- [`results/ml/elastic_net/W2/daily_metrics.csv`](../results/ml/elastic_net/W2/daily_metrics.csv)
- [`results/ml/elastic_net/W3/daily_metrics.csv`](../results/ml/elastic_net/W3/daily_metrics.csv)

### Temporal daily Pearson IC

| Window | Daily Pearson ICs in chronological order |
|---|---|
| W1 (45–54) | -0.046930, 0.132641, 0.281622, -0.094673, -0.011919, -0.035148, 0.013501, 0.022229, -0.023636, -0.026542 |
| W2 (55–64) | 0.159575, -0.075319, 0.037134, 0.053456, -0.156852, 0.104395, -0.308258, 0.124290, -0.147301, -0.093260 |
| W3 (80–85) | -0.015720, -0.064043, 0.081406, 0.002855, -0.001771, 0.019808 |

## Ridge comparison

The comparison files preserve every metric and delta:

- [`results/ml/elastic_net/predictive_comparison.csv`](../results/ml/elastic_net/predictive_comparison.csv)
- [`results/ml/elastic_net/daily_comparison.csv`](../results/ml/elastic_net/daily_comparison.csv)

For the primary/W3 comparison, Ridge versus Elastic Net was:

| Metric | Ridge | Elastic Net | Elastic Net − Ridge |
|---|---:|---:|---:|
| Pearson IC | 0.0707122893 | 0.0336523173 | -0.0370599720 |
| Spearman IC | 0.0557371133 | 0.0167399275 | -0.0389971858 |
| Mean daily Pearson IC | 0.0745360339 | 0.0037559573 | -0.0707800766 |
| Median daily Pearson IC | 0.0795849359 | 0.0005424608 | -0.0790424750 |
| Directional accuracy | 0.5076512552 | 0.5082094429 | 0.0005581877 |
| R² | -0.0234135533 | -0.0164686767 | 0.0069448766 |
| MAE | 0.0004355501 | 0.0004302557 | -0.0000052943 |
| RMSE | 0.0006586646 | 0.0006564259 | -0.0000022387 |

The small MAE/RMSE improvement and near-chance directional accuracy do not
offset the lower correlation metrics. Elastic Net was not selected because of
these results; it was the single pre-specified comparison.

## Economic comparison using the existing Part 5 convention

For W1/W2/W3 only, the same existing strategy/backtest implementation was
run on Elastic Net predictions:

- prediction sign determines long/short direction;
- one unit notional, one position at a time;
- 300-second same-day holding period;
- exact same-day exit timestamp required;
- 5 bps entry cost and 5 bps exit cost, with zero fee;
- no strategy or parameter search.

| Window | Trades | Gross P&L | Costs | Net P&L | Sharpe | Max drawdown | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|
| W1 | 410 | 0.0092045846 | 0.4100000000 | -0.4007954154 | -502.7628167 | -0.3752325064 | 820 |
| W2 | 285 | -0.0004260234 | 0.2850000000 | -0.2854260234 | -36.9845923 | -0.2569215291 | 570 |
| W3 | 246 | 0.0028984478 | 0.2460000000 | -0.2431015522 | -266.6959359 | -0.2112449285 | 492 |

The Ridge comparison is preserved in
[`results/ml/elastic_net/economic_comparison.csv`](../results/ml/elastic_net/economic_comparison.csv).
Costs and trade counts match the Ridge run because the execution convention
is fixed; Elastic Net’s net P&L is negative in all three windows.

The W3 Day-84 sensitivity is post-hoc aggregation only; there was no retraining
or strategy change:

| W3 aggregation | Trades | Gross P&L | Costs | Net P&L |
|---|---:|---:|---:|---:|
| Primary, including Day 84 | 246 | 0.0028984478 | 0.2460000000 | -0.2431015522 |
| Sensitivity, excluding Day 84 | 205 | 0.0066263064 | 0.2050000000 | -0.1983736936 |

## Artifacts

All new outputs are isolated under [`results/ml/elastic_net/`](../results/ml/elastic_net/):

- per-window model pickle, model configuration, validation metrics, daily metrics;
- per-day prediction Parquet files;
- per-window run manifests and reproducibility metadata;
- predictive and daily Ridge comparisons;
- Elastic Net backtest trade log, daily P&L, equity curve, window metrics,
  cost breakdown, and Day-84 sensitivity;
- top-level run manifest, backtest summary, and reproducibility hashes.

New implementation and tests:

- [`src/ebx/ml/elastic_net.py`](../src/ebx/ml/elastic_net.py)
- [`scripts/ml/phase_ml5_elastic_net.py`](../scripts/ml/phase_ml5_elastic_net.py)
- [`tests/unit/ml/test_elastic_net.py`](../tests/unit/ml/test_elastic_net.py)

## Reproducibility and integrity

The run manifest records `holdout_days_loaded: []`, `holdout_accessed: false`,
the 15 missing development days, input SHA-256 hashes, train/validation day
lists, and row counts. Model and prediction outputs are deterministic because
the feature order, cyclic coordinate order, preprocessing artifacts, and
random state (`null`) are fixed.

The 367-file frozen-artifact hash set covering development freeze, Part 4
artifacts, Ridge/selection/temporal artifacts, Day-84 forensics, and the
existing Part 5 baseline was unchanged by this phase. No existing Ridge,
feature-selection, temporal, forensic, or backtest artifact was overwritten.

## Testing

The focused Elastic Net tests cover deterministic fitting and reload,
configuration validation, non-finite training rejection, missing-feature
rejection, fixed phase scope, supplied-training row counts, and prediction
alignment. The solver was additionally checked against scikit-learn on a
synthetic fixture to floating-point precision.

Final verification: `pytest -q` passed **71 tests** with 2 pre-existing SciPy
precision-loss warnings in the training-only-selection tests. `git diff
--check` passed.

## Limitations and interpretation

The feature set is a pre-existing training-only selection artifact, not a new
feature-selection calculation in this phase. It was not selected using the
validation period here, but it was created in an earlier experiment and is
consumed unchanged. The direct Ridge comparison uses the matching training-only
Ridge artifacts rather than the separate frozen-screen Ridge artifact.

The cost model is the existing parameterized 5 bps-per-side assumption, not an
empirical bid/ask or fee estimate. The pooled temporal backtest combines
separate development windows and is descriptive rather than one continuous
portfolio history. Negative R² and negative net P&L should not be interpreted
as evidence of holdout behavior or production performance.

**Interpretation: B — Elastic Net does not provide a stronger predictive or
economic baseline than the controlled Ridge comparison.**

No strategy development, hyperparameter search, backtest optimization, or
holdout validation was performed after this comparison.
