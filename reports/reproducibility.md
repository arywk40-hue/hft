# EBX Reproducibility Guide

## 1. Setup

Use Python 3.11 or newer from the repository root:

```bash
python -m pip install -e ".[dev]"
```

The package dependencies are declared in `pyproject.toml`. The raw dataset is
external and is intentionally excluded from Git.

## 2. Configuration and data layout

`config/config.yaml` is the checked-in configuration source for paths, day
ranges, feature ladders, and return/diagnostic horizons. Raw files are expected
as `data/dayN.csv`. Validated manifests and processed Parquet are generated
under `data/validated/` and `data/processed/`.

The development specification contains 85 days, but only 70 were available in
the supplied dataset: Days 1–64 and 80–85. Days 65–79 are explicit missing
days. Holdout Days 86–108 contain 23 available days. Days 109–123 are outside
the project scope.

## 3. Production commands

These commands are safe verification/inventory commands and do not overwrite
frozen analytical results:

```bash
python -m ebx.cli inventory
python -m ebx.cli validate
python -m ebx.cli analyze
python -m ebx.cli holdout
pytest
```

`inventory` reports the configured development universe. `validate` checks the
validated manifest. `analyze` verifies frozen Part 1–4 artifacts. `holdout`
verifies the holdout outputs and freeze hash.

## 4. Historical exact analysis workflow

The executed phase scripts remain in `scripts/` and the reusable logic is
available through both the historical `src.*` modules and the production
`ebx.*` facade. The original phase order was:

```text
phase0_audit.py
phase1_reconnaissance.py
phase2_process.py
phase4_part1.py
phase5_part2.py
phase6_part3.py
phase7_part4a.py
phase8_part4b.py
phase9_part4c.py
phase10_part4d.py
phase11_integrated_review.py
phase12_freeze.py
phase13_freeze_manifest.py
phase13_holdout_validation.py
```

The development scripts must not be rerun against holdout data, and holdout
validation must not be rerun to improve a result. The freeze and holdout
manifest provide the relevant hashes and parameters.

## 5. Results and reports

- Development quality/distribution outputs: `results/quality/`,
  `results/diagnostics/`, and `results/distributions/`
- Feature forensics: `results/features/`, `results/predictive/`, and
  `results/redundancy/`
- Development freeze: `results/freeze/development_freeze.json`
- Holdout validation: `results/holdout/`
- Final report: `reports/final_report.md`
- Traceability: `reports/artifact_index.md`

All rolling, lagged, ACF, and future-return calculations are day-local. NaNs
are preserved and validity is pairwise or column-specific; no silent
imputation is used.
