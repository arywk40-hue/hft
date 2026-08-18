# Predictive ML — Phase 0

## Status

**Complete: model-ready data pipeline only.** No ML model was trained. Parts
1–4, the development freeze, and holdout results were not modified.

## Data boundary

- Expected development days: 85.
- Available development days: 70 — Days 1–64 and 80–85.
- Missing development days: Days 65–79; no data was fabricated.
- Holdout Days 86–108: not loaded by the ML Phase 0 pipeline.
- Days 109–123: outside scope.

All ML outputs preserve this scope in their manifests.

## Frozen feature eligibility

The pasted specification names `results/forensics/ic_table.csv`, but the
audited repository stores the frozen Part 4 predictive artifact at
`results/predictive/aggregate_ic.csv`. No `results/forensics/` predictive
artifact exists. The pipeline consumes the actual frozen artifact directly.

Eligibility is not rediscovered. It uses the frozen rule from the integrated
review and holdout validation:

```text
pearson_fdr_reject
AND pearson_pct_same_sign >= 0.70
AND abs(mean_pearson_ic) >= 0.05
```

The source contains 3,455 feature-horizon rows. The rule selects 543 rows and
197 unique features at the recommended 300-second horizon. Eligible rows by
horizon are:

| Horizon | Eligible rows |
|---:|---:|
| 1s | 0 |
| 5s | 0 |
| 30s | 171 |
| 60s | 175 |
| 300s | 197 |

The frozen screen was computed before this ML split and is consumed as a
research-frozen input; the ML pipeline performs no new feature-selection test.
Because the frozen research screen covers all 70 available development days,
it is not a train-only model-selection fit. A future model-specific selection
stage must fit any new selection statistics on train days only; this phase does
not alter the frozen screen to do so.

## Target profiles and recommendation

Targets use the exact within-day definition:

```text
r(t,h) = P(t+h) / P(t) - 1
```

Exact timestamp matching is required. Missing timestamps and the final `h`
observations of each day produce invalid targets; no fill or interpolation is
performed.

All five candidate horizons were profiled by day and pooled in
`results/ml/targets/target_profile.csv`. The pipeline recommends 300 seconds
because it has the largest frozen eligible feature-horizon count (197), with
the frozen mean absolute IC as the tie-break criterion. This recommendation is
not a model result.

## Split and preprocessing

The split is chronological and whole-day:

- Train: Days 1–64 (64 days).
- Validation: Days 80–85 (6 days).
- Gap: Days 65–79 remain explicit missing days.

Preprocessing is fitted on train rows only. It performs standardization with no
imputation and no clipping. Rows with invalid target values or any invalid
eligible feature are excluded explicitly and counted in the dataset manifest.

## Produced dataset

- Primary horizon: 300 seconds.
- Features: 197.
- Valid target rows before feature validity filtering: 1,575,012.
- Model-ready rows: 819,152.
- Excluded rows: 776,860, reported by reason.
- Partitions: 64 train day files and 6 validation day files.
- Model-ready schema: `day`, `timestamp`, `timestamp_seconds`, `target`, and
  standardized eligible features.

Required artifacts:

```text
results/ml/targets/target_profile.csv
results/ml/targets/target_recommendation.json
results/ml/features/frozen_feature_set.csv
results/ml/splits/split_manifest.json
results/ml/preprocessing/preprocessing_manifest.json
results/ml/datasets/dataset_manifest.json
results/ml/validation/leakage_report.json
results/ml/validation/performance.json
```

## Leakage and reproducibility checks

The leakage report records:

- exact target alignment and day-local target generation;
- no train/validation day overlap;
- preprocessing fit only on train days;
- no holdout days loaded;
- no model training performed.

The real development build processed all 70 available days in 51.24 seconds,
approximately 0.732 seconds per development day, with a 628,568,264-byte ML
cache and reported peak process RSS of 661,291,008 bytes.

The full test suite passed: **49 tests**. The ML-specific suite contributed 9
synthetic unit/integration tests.

Frozen input hashes remained unchanged:

```text
development_freeze.json  916be8b0c6d9bff52570ca1759b84e78eb782ad20140a569a6c1b7df5aa737fe
aggregate_ic.csv         c6b813c4e709f00030b0e2ed4d868fd231dfe89273020c265bd238aad4f37e07
config.yaml              2562097334755551b45d2492cbe3bcff98df26fc0ddfbc30cdb968c675b5f94b
```

## Remaining issues

- The requested `results/forensics/ic_table.csv` path is absent; the actual
  frozen equivalent is `results/predictive/aggregate_ic.csv`.
- The 70-day development scope remains incomplete relative to the specified
  85 days because Days 65–79 are unavailable.
- The frozen Part 4 screen predates and spans the entire 70-day ML development
  universe; it is consumed unchanged. No train-only feature reselection is
  claimed in this phase.
- This phase stops before model training, hyperparameter tuning, GPU work,
  backtesting, and strategy construction.
