# EBX Quantitative Analysis

This repository contains the completed Parts 1–4 statistical analysis of the
EBX high-frequency dataset, untouched holdout validation, and reproducible
research artifacts.

## Verified scope

- Development specification: 85 days
- Available development data: 70 days — Days 1–64 and 80–85
- Missing development days: Days 65–79; never fabricated
- Holdout: Days 86–108, 23/23 processed after the development freeze
- Days 109–123: out of scope
- ML model training, Part 5, and backtesting: not performed

The final generalization verdict is **MOSTLY ROBUST**, with mixed masked-feature
identity evidence and unstable exact tail magnitudes.

## Install

From the repository root:

```bash
python -m pip install -e ".[dev]"
```

The raw dataset is external and must remain outside version control. The
checked-in configuration expects day files at `data/dayN.csv`.

## Production CLI

The default CLI commands verify or inventory artifacts; they do not silently
rerun frozen analysis or overwrite results:

```bash
python -m ebx.cli inventory
python -m ebx.cli validate
python -m ebx.cli analyze
python -m ebx.cli holdout
pytest
```

Historical phase scripts remain under `scripts/` for provenance and exact
analysis reproduction. They are not destructive and should be run only with
the documented scope and freeze safeguards.

## Key artifacts

- [Final research report](reports/final_report.md)
- [Reproducibility guide](reports/reproducibility.md)
- [Artifact index](reports/artifact_index.md)
- [Development freeze](results/freeze/development_freeze.json)
- [Holdout validation report](reports/holdout_validation.md)
- [Holdout freeze manifest](results/holdout/freeze_manifest.json)

## Architecture and implementation

The governing documents are [architecture.md](architecture.md),
[implementation.md](implementation.md), and [quant.md](quant.md). The
production-facing package is under `src/ebx/`; the original `src.*` modules
and phase scripts are retained as compatibility and provenance layers.

## Data safety

Raw CSVs are read-only and ignored by Git. Processed Parquet, generated result
tables, figures, and local validation caches are also ignored or treated as
external generated artifacts. No analytical phase after holdout validation is
authorized by this repository state.
