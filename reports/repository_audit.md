# Repository Organization and Traceability Audit

## Audit scope

This audit finalized documentation and repository navigation only. No raw CSV,
processed Parquet, result table, figure, freeze file, configuration value,
statistical method, ML implementation, or backtest implementation was changed.
No new data was accessed or processed. Holdout Days 86–108 were not accessed
during this synchronization pass.

The governing sources are:

1. `docs/quant.md` — challenge requirements and deliverables.
2. `docs/architecture.md` — data flow, statistical methodology, and leakage rules.
3. `docs/implementation.md` — phase order, acceptance gates, and execution history.
4. `README.md` — reviewer-facing navigation and operating instructions.

## Final directory tree

Generated data and analytical tables are present locally but remain ignored by
Git. The tree below shows the reviewable repository structure and the generated
artifact directories.

```text
hft/
├── README.md
├── docs/
│   ├── quant.md
│   ├── architecture.md
│   └── implementation.md
├── pyproject.toml
├── .gitignore
├── config/
│   └── config.yaml
├── data/
│   ├── README.md
│   ├── raw/                         # external, read-only, not committed
│   ├── validated/                   # local manifest and flags
│   └── processed/                   # local per-day Parquet and masks
├── ebx/
│   └── __init__.py                  # source-checkout import shim
├── src/
│   ├── ebx/                         # production-facing package facade
│   │   ├── io/
│   │   ├── validation/
│   │   ├── features/
│   │   ├── diagnostics/
│   │   ├── distribution/
│   │   ├── regimes/
│   │   ├── forensics/
│   │   ├── common/
│   │   └── ml/                       # frozen development ML/backtest primitives
│   ├── ingestion/                   # audited compatibility implementation
│   ├── cleaning/                    # audited compatibility implementation
│   ├── analytics/                   # audited compatibility implementation
│   └── common/                      # audited compatibility implementation
├── scripts/
│   ├── analysis/                    # phase runners (Parts 1–4, holdout)
│   ├── ml/                          # ML phase runners (Phase 0–4 / Part 5 baseline)
│   ├── plot_part4.py                # Part 4 visualization suite
│   └── run_pipeline.py              # safe production verifier
├── tests/                           # phase, unit, integration tests
├── notebooks/                       # presentation-only extension point
├── results/                         # local generated results; see README
├── figures/                         # local generated figures; see README
└── reports/
    ├── final_report.md
    ├── report.md                    # implementation-spec pointer
    ├── holdout_validation.md
    ├── reproducibility.md
    ├── artifact_index.md
    ├── phase2_audit.md
    ├── feature_semantics_audit.md
    ├── ml_phase0.md through ml_phase5_audit.md
    ├── development_freeze.md
    └── repository_audit.md
```

## Quant.md requirement mapping

| `quant.md` requirement | Implementation | Results / figures | Report location | Status |
|---|---|---|---|---|
| Part 1: ingestion and sanity checks | `src/ebx/io/`, `src/ebx/validation/`, `src/ebx/common/`, `scripts/analysis/phase2_process.py` | `results/quality/`, `results/diagnostics/`, `results/missingness/`, `figures/part1/` | `reports/final_report.md` §3 | Implemented for 70 available development days |
| Part 1: descriptive statistics, ACF, seasonality | `src/ebx/diagnostics/`, `src/ebx/common/returns.py`, `scripts/analysis/phase4_part1.py` | `results/quality/descriptive_stats.csv`, `results/diagnostics/`, `figures/part1/` | §3 | Implemented; volume semantics remain unavailable |
| Part 2: normality testing | `src/ebx/distribution/`, `scripts/analysis/phase5_part2.py` | `results/distributions/normality_tests.csv`, `figures/part2/` | §4 | Implemented |
| Part 2: sigma events, tails, extreme-event catalogue | `src/ebx/distribution/`, `scripts/analysis/phase5_part2.py` | `results/distributions/sigma_events.csv`, `tail_estimates.csv`, `extreme_events.csv` | §4 | Implemented |
| Part 3: per-day regimes and independent tests | `src/ebx/regimes/`, `scripts/analysis/phase6_part3.py` | `results/regimes/regime_table.csv`, summaries, transitions, durations | §5 | 85-row scoped table exists; 15 rows explicitly mark missing source |
| Part 4A: taxonomy and window hypotheses | `src/ebx/features/`, `scripts/analysis/phase7_part4a.py` | `results/features/feature_taxonomy.csv`, `results/missingness/` | §6 | Implemented |
| Part 4B: candidate scoring and reverse engineering | `src/ebx/forensics/candidates.py`, `scripts/analysis/phase8_part4b.py` | `results/features/candidate_scores.csv`, `candidate_best_matches.csv` | §6 | Implemented; identities remain hypotheses |
| Part 4C: forward-return predictive relevance and FDR | `src/ebx/forensics/predictive.py`, `scripts/analysis/phase9_part4c.py` | `results/predictive/`, `figures/part4/` | §7 | Implemented |
| Part 4D: redundancy and PCA | `src/ebx/forensics/redundancy.py`, `scripts/analysis/phase10_part4d.py` | `results/redundancy/`, `figures/part4/` | §8 | Implemented |
| ML Phase 0: model-ready pipeline | `src/ebx/ml/` and `scripts/ml/phase_ml0.py` | `results/ml/targets/`, `datasets/`, `validation/` | `reports/ml_phase0.md` | Complete for 70 available development days |
| ML Ridge baseline, training-only selection, temporal robustness, and Day-84 forensics | `src/ebx/ml/`; `scripts/ml/phase_ml1_baseline.py` through `phase_ml3_temporal_robustness.py` | `results/ml/baseline/`, `train_only_selection/`, `temporal_robustness/`, `day84_forensics/` | ML phase reports | Complete; development-only |
| Holdout validation on Days 86–108 | `src/ebx/validation/`, `src/ebx/cli.py`, `scripts/analysis/phase13_holdout_validation.py` | `results/holdout/` | `reports/holdout_validation.md`, final §10 | Complete and separate from development |
| Written report | phase reports and `reports/final_report.md` | — | `reports/final_report.md` | Present as Markdown; rendered page count/PDF not supplied |
| Part 5 trade log and baseline backtest | `src/ebx/ml/backtest.py`, `scripts/ml/phase_ml4_backtest.py` | `results/ml/backtest_baseline/`, `figures/ml_phase4/` | `reports/ml_phase4_backtest.md`, `reports/ml_phase5_audit.md` | Complete; negative after documented costs |

## Organization decisions

### Files renamed or moved

The following structural reorganization was performed:

- `quant.md`, `architecture.md`, `implementation.md` moved to `docs/`.
- Analysis phase scripts (`phase0_audit.py` through `phase13_holdout_validation.py`)
  moved to `scripts/analysis/`.
- ML phase scripts (`phase_ml0.py` through `phase_ml3_temporal_robustness.py`)
  moved to `scripts/ml/`.
- `sys.path` resolution updated in all moved scripts.
- Test imports updated to match new script locations.
- All cross-references in README and documentation updated.

The production package under `src/ebx/` delegates to historical `src.*` modules;
those modules were not moved because doing so would break imports and weaken
provenance. The compatibility layer is documented in `scripts/README.md`,
`src/` package layout, and the main README.

### Obsolete files removed

None. Existing phase scripts, tests, and reports are useful historical evidence
and were retained. No duplicate implementation was removed because the apparent
duplication is an intentional production facade over the audited implementation.

### Documentation added or improved

- `README.md` now contains one-minute scope, coverage, pipeline instructions,
  Part 1–4, ML, Part 5, and holdout traceability, plus explicit freeze limits.
- `reports/report.md` points the implementation-spec report path to the
  canonical `reports/final_report.md`.
- `results/README.md`, `figures/README.md`, `data/README.md`,
  `scripts/README.md`, and `notebooks/README.md` explain local/generated
  boundaries and provenance.
- This report records the final tree, gaps, and verification evidence.

## Frozen-artifact verification

The following SHA-256 values were recorded before this documentation pass and
must remain unchanged. Development and Part 5 namespaces were rehashed after
the edits; holdout hashes below are historical records and were not reread in
this pass.

| Artifact | SHA-256 |
|---|---|
| `results/freeze/development_freeze.json` | `916be8b0c6d9bff52570ca1759b84e78eb782ad20140a569a6c1b7df5aa737fe` |
| `results/predictive/aggregate_ic.csv` | `c6b813c4e709f00030b0e2ed4d868fd231dfe89273020c265bd238aad4f37e07` |
| `results/ml/features/frozen_feature_set.csv` | `d9aec0b7292ba595dd06a5c90eefe4ec6bd1563023428f9a414041fe4594e4fa` |
| `results/ml/baseline/validation_metrics.json` | `e371ca8d4bb9fde1c53fc8e1b030d5d9033947db4aa520c5f4ae5fb3c0a5b5aa` |
| `results/ml/train_only_selection/comparison.json` | `94fa5907fc70c403d65bc9a9df7852ea93e75783ce77866a3cfb793ac5616` |
| `results/ml/temporal_robustness/aggregate_robustness.json` | `b535668ec297cff67a752c0bbd9080c485305d963ae8142599cfb17d108599a6` |
| `results/ml/day84_forensics/day84_forensics.json` | `395d731a28e6c721a5b96aab4059568796232eb83cab96a0ab2e61999870d3b3` |
| `results/ml/backtest_baseline/summary_metrics.json` | `bcf6d9a99bc742215b119439b41ef084699f2c88e3cf1017f77e08ac144d33af` |
| `results/ml/backtest_baseline/trade_log.csv` | `5f22f90eae85f179093beea7c07b8773200d23636b871168b08add1ee87773b9` |
| `results/holdout/freeze_manifest.json` | `08897b19622ccedb13c973a6f14eb8cbc26e07dbeb153ce9d502b521bce712ff` |
| `results/holdout/phase13_scope.json` | `96500b8e3aa9bab9158ee15bf09400e72d84bd98c7d3a36dbbca7086e567c682` |
| `results/phase11/integrated_facts.json` | `bef651e27a4aded25ea1cb3f9693a4f068ec9a511750dbf8fcc0d3c2484b2a0c` |
| `config/config.yaml` | `2562097334755551b45d2492cbe3bcff98df26fc0ddfbc30cdb968c675b5f94b` |

The post-synchronization verification produced the same values for every
development artifact listed above, including all files under the baseline,
training-only selection, temporal-robustness, Day-84 forensic, and Part 5
backtest namespaces. Holdout artifacts were not accessed during this pass.
The frozen development and Part 5 artifacts therefore remain byte-identical.

## Tests and smoke checks

The following checks were run at the end of this audit:

```text
pytest
python -m ebx.cli inventory
python -m ebx.cli validate
python -m ebx.cli analyze
git diff --check
```

Observed results:

- `pytest -q`: **66 passed, 2 warnings**.
- `python3 -m ebx.cli inventory`: passed; 70 available, 15 missing, raw files opened `false`.
- `python3 -m ebx.cli validate`: passed; manifest matches the 70 audited development days.
- `python3 -m ebx.cli analyze`: passed; all frozen artifacts present, analysis rerun `false`.
- Holdout status was read from existing manifests only; no holdout command or
  holdout data was accessed during this documentation pass. Existing manifests
  continue to record `holdout_days_loaded: []` for the development ML and Part 5
  artifacts.
- `git diff --check`: passed with no whitespace errors.

## Remaining gaps

1. Days 65–79 remain unavailable. Therefore no claim based on a complete
   85-day development dataset is valid; the 85-row regime table explicitly
   marks those 15 rows as `missing_source`.
2. No dedicated Part 3 or holdout figure set exists. The corresponding tables
   and written conclusions are present; the Part 4 figure set is complete.
3. `implementation.md` requests `reports/report.md`; the canonical report is
   `reports/final_report.md`, with `reports/report.md` retained as a pointer.
4. The report is Markdown and its rendered page count has not been formally
   checked; no PDF is claimed.
5. The available development data remains 70 of 85 days; Days 65–79 are
   explicit gaps. No complete 85-day development claim is made.
6. Part 5 uses an explicit 5 bps-per-side cost assumption rather than measured
   bid/ask or fee data. Its development baseline is not evidence of economic
   viability or production readiness.
