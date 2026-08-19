# EBX Quantitative Analysis

This repository answers the EBX Quant Data Challenge through Parts 1–5,
the audited Ridge, Elastic Net, and LightGBM development comparisons, and one
pre-specified Part 5 baseline backtest. Days 86–108 remain reserved holdout
data and are not part of this development package.

## Reviewer summary

- Development specification: **85 days**.
- Development data available: **70 days** — Days 1–64 and 80–85.
- Missing development data: **Days 65–79** — explicitly represented and never fabricated.
- Holdout: **Days 86–108** are reserved and were not accessed for this final
  development package.
- Days 109–123: out of scope.
- Parts 1–4 and their development conclusions are frozen.
- ML development includes the Phase 0 pipeline, Ridge baseline,
  training-only selection, temporal robustness, Day-84 forensics, Elastic Net,
  and one fixed LightGBM W3 comparison.
- Part 5 contains one fixed-rule development backtest. Its net result is
  negative after the documented costs; no economic viability or production
  strategy claim is made.
- Ridge remains the strongest tested model by Pearson IC and net P&L. Elastic
  Net and LightGBM do not improve it. No optimization, final production model,
  or additional strategy is included.
- The supplied PB/VB/BB/PV/V feature-generation source is unavailable, so
  downstream leakage checks do not certify upstream feature causality.

The complete written synthesis is [reports/final_report.md](reports/final_report.md).
The final packaging and traceability audit is
[reports/final_submission_audit.md](reports/final_submission_audit.md).
The earlier organization record is retained as historical evidence in
[reports/repository_audit.md](reports/repository_audit.md).

## Governing documents and flow

[`docs/quant.md`](docs/quant.md) defines the challenge and deliverables.
[`docs/architecture.md`](docs/architecture.md) defines the data flow and
statistical safeguards. [`docs/implementation.md`](docs/implementation.md)
records the phase gates and execution order. The implementation produces
scoped artifacts:

```text
docs/quant.md requirements
        ↓
src/ebx/ + historical src.* implementations + scripts/
        ↓
results/ and figures/ (generated, locally preserved, indexed)
        ↓
reports/ (reviewable conclusions and traceability)
```

## Part-to-artifact traceability

| Requirement | Source modules / scripts | Results | Figures | Report section |
|---|---|---|---|---|
| Part 1 — Data Hygiene & Descriptive Statistics | `src/ebx/io/`, `src/ebx/validation/`, `src/ebx/common/`, `src/ebx/diagnostics/`; `scripts/analysis/phase2_process.py`, `scripts/analysis/phase4_part1.py` | `results/quality/`, `results/diagnostics/`, `results/missingness/` | `figures/part1/` | [Final report §3](reports/final_report.md#3-data-hygiene) |
| Part 2 — Distribution & Tails | `src/ebx/distribution/`; `scripts/analysis/phase5_part2.py` | `results/distributions/` | `figures/part2/` | [Final report §4](reports/final_report.md#4-distribution-and-tails) |
| Part 3 — Regime Classification | `src/ebx/regimes/`; `scripts/analysis/phase6_part3.py` | `results/regimes/` | No dedicated Part 3 figure currently exists | [Final report §5](reports/final_report.md#5-regime-classification) |
| Part 4 — Feature Forensics | `src/ebx/features/`, `src/ebx/forensics/`; `scripts/analysis/phase7_part4a.py`, `scripts/analysis/phase8_part4b.py`, `scripts/analysis/phase9_part4c.py`, `scripts/analysis/phase10_part4d.py` | `results/features/`, `results/predictive/`, `results/redundancy/` | `figures/part4/` | [Final report §§6–8](reports/final_report.md#6-feature-forensics) |
| ML Phases 0–9 — Model-ready pipeline and controlled model comparisons | `src/ebx/ml/`; `scripts/ml/phase_ml0.py` through `phase_ml9_lightgbm.py` | `results/ml/` | — | [ML reports](reports/ml_phase0.md), [LightGBM report](reports/ml_phase9_lightgbm.md) |
| Part 5 — Baseline development backtest | `src/ebx/ml/backtest.py`; `scripts/ml/phase_ml4_backtest.py` | `results/ml/backtest_baseline/` | `figures/ml_phase4/` | [Backtest report](reports/ml_phase4_backtest.md), [audit](reports/ml_phase5_audit.md) |
| Holdout — Days 86–108 | `src/ebx/validation/`, `src/ebx/cli.py`; `scripts/analysis/phase13_holdout_validation.py` | `results/holdout/` | Holdout figures not generated | [Holdout report](reports/holdout_validation.md), [Final report §10](reports/final_report.md#10-out-of-sample-validation) |

The generated directories are intentionally not committed as bulk data. Their
contents, scope, and review status are catalogued in [results/README.md](results/README.md)
and [figures/README.md](figures/README.md); frozen hashes are recorded in the
repository audit and holdout manifest.

## Install and run

From the repository root:

```bash
python -m pip install -e ".[dev]"
python -m ebx.cli inventory
python -m ebx.cli validate
python -m ebx.cli analyze
python scripts/run_pipeline.py
pytest
```

The CLI is a non-mutating verifier by default. It does not silently rerun
analysis or overwrite frozen outputs. Historical phase scripts remain under
`scripts/` for provenance; run them only with their declared scope and freeze
safeguards.
The existing holdout validation is frozen and must not be rerun for tuning or
new analysis.

## ML Phase 0 and first baseline

The model-ready pipeline and first Ridge baseline are implemented. The
reproducible entry point is
`python scripts/ml/phase_ml0.py` to consume only the 70 available development
Parquet days, profile 1s/5s/30s/60s/300s targets, consume the frozen Part 4
predictive screen, assign a chronological train/validation split, fit
train-only standardization, and write day-wise model-ready Parquet partitions.
These ML and Part 5 outputs are frozen; do not rerun them to tune or improve a
result.

Run `python scripts/ml/phase_ml1_baseline.py` for the fixed-alpha Ridge
baseline. The controlled training-only selection and temporal-robustness
experiments are in `phase_ml2_train_only_selection.py` and
`phase_ml3_temporal_robustness.py`. See the ML reports for their validation
results. The single Part 5 development backtest is isolated under
`results/ml/backtest_baseline/` and documented in
[reports/ml_phase4_backtest.md](reports/ml_phase4_backtest.md). No tree model,
neural network, hyperparameter search, final production model, or second
strategy is included.

Outputs are under `results/ml/`: target profiles and recommendation, frozen
feature set, split manifest, preprocessing manifest, dataset manifest, leakage
report, performance metrics, and train/validation partitions. The selected
primary target recommendation is 300 seconds based on the frozen screen; this
is a pipeline recommendation, not a trading or model result. Days 86–108 are
not read by this pipeline.

## Repository layout

```text
hft/
├── README.md
├── docs/                   # quant.md, architecture.md, implementation.md
├── config/                 # configuration source of truth
├── src/ebx/                # production-facing package
├── src/{analytics,cleaning,common,ingestion}/  # audited compatibility layer
├── scripts/
│   ├── analysis/           # phase runners (Parts 1–4; holdout reserved)
│   ├── ml/                 # ML phase runners (Phase 0–9 / Part 5 baseline)
│   ├── plot_part4.py       # Part 4 visualization suite
│   └── run_pipeline.py     # safe production verifier
├── tests/                  # phase, unit, and integration tests
├── notebooks/              # reserved for presentation notebooks; none required
├── data/                   # external raw and generated local data
├── results/                # generated result inventory and local artifacts
├── figures/                # generated figure inventory and local figures
└── reports/                # final report, audit, reproducibility, and evidence
```

## Data and research boundaries

Raw CSVs are read-only and excluded from version control. Processed Parquet,
generated tables, and figures remain local generated artifacts. Structural NaNs
are preserved, no silent imputation is used, and rolling/lagged operations are
day-local. Days 65–79 remain missing; no new data was introduced for this
finalization pass. The development ML and Part 5 baseline artifacts are frozen.
No further model, strategy, optimization, or backtest is authorized by the
frozen repository state. Holdout Days 86–108 are reserved and must not be used
for new work.

See [reports/reproducibility.md](reports/reproducibility.md) for provenance and
[reports/artifact_index.md](reports/artifact_index.md) for detailed artifact
mapping.
