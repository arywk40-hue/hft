# Phase scripts

Scripts preserve the phase execution history and are grouped by the phase
numbers in [`docs/implementation.md`](../docs/implementation.md):

## `analysis/` — Statistical analysis phases

- `phase0_audit.py` through `phase2_process.py`: discovery and ingestion
- `phase4_part1.py` through `phase7_part4a.py`: Parts 1–4A
- `phase8_part4b.py` through `phase10_part4d.py`: Part 4B–4D
- `phase11_integrated_review.py` through `phase13_holdout_validation.py`:
  integration, freeze, and holdout validation

## `ml/` — ML pipeline phases

- `phase_ml0.py`: model-ready data preparation (no training)
- `phase_ml1_baseline.py`: fixed-alpha Ridge baseline
- `phase_ml2_train_only_selection.py`: training-only feature selection
- `phase_ml3_temporal_robustness.py`: temporal robustness experiment
- `phase_ml4_backtest.py`: one fixed-rule Part 5 development baseline backtest

The ML and Part 5 outputs are frozen development artifacts. The backtest is not
a production strategy, and no additional model, optimization, or holdout run is
part of the frozen state.

## Root scripts

- `run_pipeline.py`: non-mutating production artifact verifier
- `plot_part4.py`: Part 4 feature forensics visualization suite

The production-facing import surface is `src/ebx/`. Historical `src.*`
modules remain because the `src/ebx/` package delegates to them; they are
audited compatibility and provenance code, not obsolete duplicates.
