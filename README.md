# EBX Quantitative Analysis

This repository answers the EBX Quant Data Challenge through Parts 1–4:
data hygiene, distribution and tail analysis, regime classification, and
masked-feature forensics. It also contains the frozen development conclusions
and the separate Days 86–108 holdout validation.

## Reviewer summary

- Development specification: **85 days**.
- Development data available: **70 days** — Days 1–64 and 80–85.
- Missing development data: **Days 65–79** — explicitly represented and never fabricated.
- Holdout: **Days 86–108**, 23/23 days validated after the development freeze.
- Days 109–123: out of scope.
- Final generalization verdict: **MOSTLY ROBUST**.
- ML modeling, Part 5, backtesting, and new analysis: intentionally not included.

The complete written synthesis is [reports/final_report.md](reports/final_report.md).
The repository-level traceability audit is [reports/repository_audit.md](reports/repository_audit.md).

## Governing documents and flow

`quant.md` defines the challenge and deliverables. `architecture.md` defines
the data flow and statistical safeguards. `implementation.md` records the
phase gates and execution order. The implementation produces scoped artifacts:

```text
quant.md requirements
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
| Part 1 — Data Hygiene & Descriptive Statistics | `src/ebx/io/`, `src/ebx/validation/`, `src/ebx/common/`, `src/ebx/diagnostics/`; `scripts/phase2_process.py`, `scripts/phase4_part1.py` | `results/quality/`, `results/diagnostics/`, `results/missingness/` | `figures/part1/` | [Final report §3](reports/final_report.md#3-data-hygiene) |
| Part 2 — Distribution & Tails | `src/ebx/distribution/`; `scripts/phase5_part2.py` | `results/distributions/` | `figures/part2/` | [Final report §4](reports/final_report.md#4-distribution-and-tails) |
| Part 3 — Regime Classification | `src/ebx/regimes/`; `scripts/phase6_part3.py` | `results/regimes/` | No dedicated Part 3 figure currently exists | [Final report §5](reports/final_report.md#5-regime-classification) |
| Part 4 — Feature Forensics | `src/ebx/features/`, `src/ebx/forensics/`; `scripts/phase7_part4a.py`, `scripts/phase8_part4b.py`, `scripts/phase9_part4c.py`, `scripts/phase10_part4d.py` | `results/features/`, `results/predictive/`, `results/redundancy/` | No dedicated Part 4 figure set currently exists | [Final report §§6–8](reports/final_report.md#6-feature-forensics) |
| Holdout — Days 86–108 | `src/ebx/validation/`, `src/ebx/cli.py`; `scripts/phase13_holdout_validation.py` | `results/holdout/` | Holdout figures not generated | [Holdout report](reports/holdout_validation.md), [Final report §9](reports/final_report.md#9-out-of-sample-validation) |

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
python -m ebx.cli holdout
python scripts/run_pipeline.py
pytest
```

The CLI is a non-mutating verifier by default. It does not silently rerun
analysis or overwrite frozen outputs. Historical phase scripts remain under
`scripts/` for provenance; run them only with their declared scope and freeze
safeguards.

## ML Phase 0 and first baseline

The model-ready pipeline and first Ridge baseline are implemented. Run
`python scripts/phase_ml0.py` to consume only the 70 available development
Parquet days, profile 1s/5s/30s/60s/300s targets, consume the frozen Part 4
predictive screen, assign a chronological train/validation split, fit
train-only standardization, and write day-wise model-ready Parquet partitions.

Run `python scripts/phase_ml1_baseline.py` for the fixed-alpha Ridge baseline.
See [reports/ml_phase3_baseline.md](reports/ml_phase3_baseline.md) for its
validation results. No tree model, neural network, strategy, or backtest has
been implemented.

Outputs are under `results/ml/`: target profiles and recommendation, frozen
feature set, split manifest, preprocessing manifest, dataset manifest, leakage
report, performance metrics, and train/validation partitions. The selected
primary target recommendation is 300 seconds based on the frozen screen; this
is a pipeline recommendation, not a trading or model result. Days 86–108 are
not read by this pipeline.

## Repository layout

```text
hft/
├── README.md, quant.md, architecture.md, implementation.md
├── config/                 # configuration source of truth
├── src/ebx/                # production-facing package
├── src/{analytics,cleaning,common,ingestion}/  # audited compatibility layer
├── scripts/                # phase runners and safe verifier
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
organization pass. No ML model, trading strategy, Part 5 backtest, or further
statistical analysis is authorized by the frozen repository state.

See [reports/reproducibility.md](reports/reproducibility.md) for provenance and
[reports/artifact_index.md](reports/artifact_index.md) for detailed artifact
mapping.
