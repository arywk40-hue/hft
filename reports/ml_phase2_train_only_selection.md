# ML Phase 2 — Strict Training-Only Feature Selection

Status: **complete for the available development data**. This is a controlled
comparison against the frozen-screen Ridge baseline; no second model,
hyperparameter search, strategy, or backtest was performed.

## Data boundary and method

- Expected development days: **85**.
- Available development days used: **70** (`1–64` and `80–85`).
- Missing development days: **65–79** (15 days; no data fabricated).
- Training: **Days 1–64**, 64 whole days.
- Validation: **Days 80–85**, 6 whole days.
- Holdout Days 86–108: **not loaded or accessed**.
- Target: `P(t+300) / P(t) - 1`, computed within each day.
- Model: Ridge regression, `alpha=1.0`, fitted intercept, deterministic normal-equation fit.

The candidate universe was the 691-feature universe represented in the audited
day-level IC artifact. The training-only selection input retained only the
64 training-day rows from `results/predictive/per_day_ic.csv`; validation rows
were not retained or passed to selection. The existing selection rule was
refit without changing thresholds:

```text
pearson_fdr_reject
AND pearson_pct_same_sign >= 0.70
AND abs(mean_pearson_ic) >= 0.05
```

Benjamini–Hochberg correction was recalculated across all **3,455** candidate
feature–horizon hypotheses using training-day IC series only. Preprocessing was
fit on training rows only, with no imputation and no clipping, and then applied
unchanged to Days 80–85.

## Selection result

- Candidate features: **691**.
- Candidate feature–horizon hypotheses: **3,455**.
- Selected 300-second features: **198**.
- Frozen 197-feature overlap: **197**.
- Frozen features retained: **100%**.
- Training-only selected features retained in frozen set: **99.49494949%**.

The exact selected list, including the selection statistics and q-values, is
the authoritative artifact at
[`results/ml/train_only_selection/selected_features.csv`](../results/ml/train_only_selection/selected_features.csv).

Selected features:

```text
BB11_T1, BB11_T10, BB11_T11, BB11_T12, BB11_T2, BB11_T3, BB11_T4, BB11_T5, BB11_T6, BB11_T7, BB11_T8, BB11_T9, BB12_T1, BB12_T10, BB12_T11, BB12_T12, BB12_T2, BB12_T3, BB12_T4, BB12_T5, BB12_T6, BB12_T7, BB12_T8, BB12_T9, BB13_T1, BB13_T10, BB13_T11, BB13_T12, BB13_T2, BB13_T3, BB13_T4, BB13_T5, BB13_T6, BB13_T7, BB13_T8, BB13_T9, BB14_T1, BB14_T10, BB14_T11, BB14_T12, BB14_T2, BB14_T3, BB14_T4, BB14_T5, BB14_T6, BB14_T7, BB14_T8, BB14_T9, BB15_T1, BB15_T10, BB15_T11, BB15_T12, BB15_T2, BB15_T3, BB15_T4, BB15_T5, BB15_T6, BB15_T7, BB15_T8, BB15_T9, BB16, BB17, BB18, BB19, BB1_T1, BB1_T10, BB1_T11, BB1_T12, BB1_T2, BB1_T3, BB1_T4, BB1_T5, BB1_T6, BB1_T7, BB1_T8, BB1_T9, BB20, BB21, BB26, BB3_T12, BB4_T1, BB4_T10, BB4_T11, BB4_T12, BB4_T2, BB4_T3, BB4_T4, BB4_T5, BB4_T6, BB4_T7, BB4_T8, BB4_T9, BB5_T1, BB5_T10, BB5_T11, BB5_T12, BB5_T2, BB5_T3, BB5_T4, BB5_T5, BB5_T6, BB5_T7, BB5_T8, BB5_T9, BB6_T1, BB6_T10, BB6_T11, BB6_T12, BB6_T2, BB6_T3, BB6_T4, BB6_T5, BB6_T6, BB6_T7, BB6_T8, BB6_T9, BB7_T1, BB7_T10, BB7_T11, BB7_T12, BB7_T2, BB7_T3, BB7_T4, BB7_T5, BB7_T6, BB7_T7, BB7_T8, BB7_T9, BB8_T1, BB8_T10, BB8_T11, BB8_T12, BB8_T2, BB8_T3, BB8_T4, BB8_T5, BB8_T6, BB8_T7, BB8_T8, BB8_T9, PB10_T1, PB10_T10, PB10_T11, PB10_T12, PB10_T2, PB10_T3, PB10_T4, PB10_T5, PB10_T6, PB10_T7, PB10_T8, PB10_T9, PB11_T1, PB11_T10, PB11_T11, PB11_T12, PB11_T2, PB11_T3, PB11_T4, PB11_T5, PB11_T6, PB11_T7, PB11_T8, PB11_T9, PB12_T12, PB13_T12, PB14_T12, PB1_T12, PB4_T12, PB5_T12, PB6_T10, PB6_T11, PB6_T12, PB6_T9, PB9_T1, PB9_T10, PB9_T11, PB9_T12, PB9_T2, PB9_T3, PB9_T4, PB9_T5, PB9_T6, PB9_T7, PB9_T8, PB9_T9, PV3_B2_T1, PV3_B3_T1, PV3_B3_T2, PV3_B3_T3, PV3_B4_T1, PV3_B4_T2, PV3_B4_T3, PV3_B4_T4, PV3_B5_T1, PV3_B5_T2, PV3_B5_T3, PV3_B6_T1
```

## Validation results

Rows: **745,700 training**, **73,452 validation** (12,242 per validation day).
Target mean and standard deviation are reported from the validation labels;
they are not used for feature selection or preprocessing.

| Metric | Experiment A: frozen 197 | Experiment B: training-only |
|---|---:|---:|
| Pearson IC | 0.0714158715285 | 0.0707122892894 |
| Spearman IC | 0.0607256189657 | 0.0557371132606 |
| Mean daily Pearson IC | 0.0732273967717 | 0.0745360338656 |
| Median daily Pearson IC | 0.0675873862843 | 0.0795849358993 |
| Daily Pearson IC std. dev. | 0.0915778672660 | 0.0839820791346 |
| Directional accuracy | 0.5087812448946 | 0.5076512552415 |
| R² | -0.0231861466418 | -0.0234135533098 |
| MAE | 0.0004353338139 | 0.0004355500826 |
| RMSE | 0.0006585913852 | 0.0006586645683 |
| Prediction mean | 0.0000044251002 | 0.0000053533013 |
| Prediction std. dev. | 0.0001325330190 | 0.0001331084620 |
| Target mean | 0.0000721679714 | 0.0000721679714 |
| Target std. dev. | 0.0006510909761 | 0.0006510909761 |

Experiment B has slightly lower pooled Pearson and Spearman IC, slightly worse
R²/MAE/RMSE, and near-chance directional accuracy. It was not tuned against
validation performance. The small change is consistent with the fact that the
training-only screen adds one feature while removing none of the frozen 197;
it does not establish economic utility.

### Daily validation IC

| Day | Observations | Pearson IC | Spearman IC | Directional accuracy | R² |
|---:|---:|---:|---:|---:|---:|
| 80 | 12,242 | 0.087898 | 0.101525 | 0.539699 | -0.007301 |
| 81 | 12,242 | 0.071272 | 0.081032 | 0.477781 | -0.079109 |
| 82 | 12,242 | 0.088887 | 0.089728 | 0.536677 | 0.003453 |
| 83 | 12,242 | -0.017523 | 0.057962 | 0.518624 | -0.046581 |
| 84 | 12,242 | 0.218135 | 0.141325 | 0.550319 | 0.047290 |
| 85 | 12,242 | -0.001452 | -0.019991 | 0.422807 | -0.128934 |

## Outputs and integrity

All Experiment B artifacts are isolated under
`results/ml/train_only_selection/`, including the selected-feature table,
selection daily/aggregate tables, train-only preprocessing manifest, Ridge
artifact, predictions, daily/pooled metrics, comparison, run manifest, and
reproducibility manifest.

The existing baseline namespace `results/ml/baseline/` was not written. Hashes
of the existing frozen feature set, aggregate IC artifact, development freeze,
split manifest, and baseline metrics were unchanged after the run. The source
day manifest lists only Days 1–64 and 80–85; no Days 65–79 or 86–108 partition
was opened.

## Limitations

- The source day-level IC artifact was generated for the development universe;
  this experiment retained only its Days 1–64 rows and refit aggregation,
  t-tests, FDR, and eligibility from those rows. A future implementation could
  recompute those daily IC rows directly from training partitions as a separate
  audit, but no validation statistic entered this experiment.
- Validation contains six available days and is not the untouched holdout.
- The frozen feature artifact was not changed, and no claim is made about an
  85-day complete development result.
- No ML model beyond this controlled Ridge comparison, no strategy, and no
  backtest was implemented.
