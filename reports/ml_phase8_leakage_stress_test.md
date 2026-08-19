# ML Phase 8 — Strict Feature/Target Temporal Leakage Stress Test

## Scope and verdict

This was a read-only audit. No model was trained, no production or frozen
result was regenerated, and no holdout data was loaded.

**Final verdict: B. Potential leakage found; investigation required.**

The potential leakage is a provenance limitation, not an observed leak in the
audited in-repository calculations: the repository ingests the 691 PB/VB/BB/
PV/V columns from source CSVs but does not contain the code that originally
constructed those columns. Therefore their timestamp causality cannot be
proven from this repository alone. The available in-repository candidate
formulas, target construction, day-local execution, missingness handling, and
preprocessing passed the synthetic causality checks described below.

## 1. Feature-construction findings

The actual production feature flow is:

1. [`src/ingestion/loader.py`](../src/ingestion/loader.py#L45) reads each CSV
   without sorting, imputation, or cross-day concatenation.
2. [`scripts/analysis/phase2_process.py`](../scripts/analysis/phase2_process.py#L99)
   validates each day and writes the loaded table to processed Parquet without
   recalculating feature columns.
3. [`src/ebx/ml/dataset_builder.py`](../src/ebx/ml/dataset_builder.py#L118)
   reads the selected feature columns unchanged and applies only the target,
   validity mask, and train-only standardization steps.

The only feature-formula implementation in the repository is the forensic
hypothesis helper [`src/analytics/candidates.py`](../src/analytics/candidates.py#L24),
not the source CSV feature producer. Its formulas use trailing pandas rolling
windows with `min_periods=window`, past-only `shift(window)`, and
`ewm(..., adjust=False)`. No future-looking operation was found in that
helper. The diagnostic caller in
[`scripts/analysis/phase8_part4b.py`](../scripts/analysis/phase8_part4b.py#L71)
invokes it separately for each available day.

The feature parser in [`src/common/features.py`](../src/common/features.py)
correctly treats fixed indicator identifiers and varying `_Tj` suffixes as a
family/subfamily taxonomy, but parsing names cannot establish formula
causality.

## 2. PB/VB/BB/PV/V temporal tests

The focused synthetic tests covered all five family labels (`PB`, `VB`, `BB`,
`PV`, `V`) at windows 5 and 30. Future price and volume values from `t+1`
through `t+300` were replaced with extreme values. Every synthetic family
probe returned the same value at `t` before and after the perturbation.

The in-repository candidate implementation was also tested across every
listed price and return candidate and passed the same future-perturbation
property. These family probes are explicitly test fixtures; they are not
claims about the unknown mathematical definitions of the raw feature columns.

The volume candidate names are listed in `VOLUME_CANDIDATES`, but their raw
feature-generation implementation is not present in `candidate_series` or
elsewhere in the repository. This is part of the unresolved provenance risk.

## 3. Target-alignment findings

[`src/ebx/ml/targets.py`](../src/ebx/ml/targets.py#L23) constructs:

```text
r(t,h) = P(t+h) / P(t) - 1
```

using exact within-day timestamp lookup. It rejects non-increasing timestamps,
does not interpolate, and leaves observations without an exact future
timestamp as NaN.

The target-injection test changed only `P(t+300)`. The target changed as
expected, while every tested causal candidate feature at `t` remained
identical. The target is therefore used as a label, not as a feature input.

The deliberately leaked negative-control feature was exactly the future
return. A simple one-feature least-squares model achieved test R² greater than
`0.999999`, demonstrating that the audit harness detects artificial leakage.
That synthetic feature was not written to any model or result artifact.

## 4. Day-boundary findings

Day boundaries are respected in the production call paths:

- Phase 2 processes one discovered day at a time.
- Target construction accepts one ordered day and rejects reset timestamps
  from concatenated days.
- The forensic candidate caller computes candidate series inside its per-day
  loop.
- ML dataset construction loops over individual training and validation days.

The test suite also demonstrates an important API constraint: a generic
rolling helper will cross a boundary if a caller manually concatenates two
days before calling it. The production caller does not do that. This must
remain an explicit usage invariant; the candidate helper itself does not carry
a day key and cannot independently prevent misuse on concatenated arrays.

No lag, rolling, resampling, interpolation, forward fill, or backfill across
Days 65–79 or across day boundaries was introduced by Phase 8.

## 5. Warm-up and missingness findings

The candidate formulas preserve expected warm-up NaNs through
`min_periods=window`. The tests verified that leading warm-up NaNs remain NaN,
later valid values remain finite, and no future value backfills or forward-fills
the warm-up region.

The structural-missingness implementation in
[`src/cleaning/missingness.py`](../src/cleaning/missingness.py#L52) separately
records leading, internal, trailing, and all-NaN patterns, plus actual warm-up
time. The ML complete-case function returns masks without mutating source
data. Structural warm-up is therefore not treated as evidence of corruption.

## 6. Preprocessing and selection findings

[`src/ebx/ml/dataset_builder.py`](../src/ebx/ml/dataset_builder.py#L120)
updates the standardizer only from training-day complete rows, finalizes it
before validation transformation, and records validation days as not used for
fit. [`src/ebx/ml/preprocessing.py`](../src/ebx/ml/preprocessing.py) performs
no imputation and rejects non-finite values rather than filling them.

The training-only selection implementation rejects validation, missing, and
holdout rows and applies FDR only to the supplied training-day IC table. The
existing ML validation tests cover these invariants. No selection or model
artifact was recomputed in Phase 8.

## 7. Positive and negative controls

| Control | Result |
|---|---|
| Deliberately leaked `future_return_leak(t) = r(t,300)` | Detected; test R² > 0.999999 |
| Strictly causal rolling feature | Passed future-perturbation invariance |
| In-repository price/return candidates | All tested candidates passed |
| Synthetic PB/VB/BB/PV/V probes | All five families × two windows passed |

## 8. Existing-artifact integrity

All protected namespaces were hash-checked before and after the audit checks:

- `results/ml/baseline/`
- `results/ml/train_only_selection/`
- `results/ml/temporal_robustness/`
- `results/ml/backtest_baseline/`
- `results/ml/elastic_net/`
- `results/predictive/`
- `results/freeze/`

The 367 frozen development files were unchanged. The existing Elastic Net
namespace was also unchanged. No model, prediction, feature-selection,
backtest, or freeze artifact was regenerated.

## 9. Holdout and development boundary

Phase 8 used synthetic fixtures and source inspection only. It did not load or
inspect Days 86–108 and did not generate holdout predictions.

The existing ML manifests continue to record:

```text
holdout_days_loaded: []
```

Days 65–79 remain explicit unavailable development gaps. No synthetic data was
inserted for those days.

## 10. Tests

Added focused tests at
[`tests/unit/ml/test_leakage_stress.py`](../tests/unit/ml/test_leakage_stress.py).
They cover:

- all in-repository candidate formulas;
- PB/VB/BB/PV/V synthetic family probes;
- multiple rolling windows;
- target injection;
- day-boundary handling;
- structural warm-up behavior;
- train-only preprocessing and no mutation;
- negative leakage control;
- positive causal control.

Results:

- Focused leakage tests: **35 passed**
- Full suite: **106 passed, 2 existing SciPy warnings**
- `git diff --check`: **passed**

## Remaining investigation required

To move from verdict B to verdict A, the original feature-construction
implementation or an authoritative causal specification for the raw PB/VB/
BB/PV/V columns is required. The current repository can verify that its own
downstream ingestion and modeling path does not add temporal leakage, but it
cannot certify that the externally generated feature values at timestamp `t`
were computed without observations after `t`.

No experiments are invalidated by an observed confirmed leak in this audit;
the limitation is that raw-feature causality remains unproven. No model
improvement, tuning, or holdout validation was performed.
