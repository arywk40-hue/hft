# Final quant.md Compliance and Submission Audit

## Executive verdict

The analytical work is substantially complete for the available development scope. Parts 1–4 are submission-ready as a clearly labeled 70-of-85-day analysis, with Days 65–79 explicitly represented as missing. Part 5 is implemented and independently audited as a fixed baseline. Its literal trade-log compatibility aliases are now present in the staged artifact; the original 941 rows and all original fields/values remain unchanged.

Before this packaging pass, the repository was not submission-ready as a fresh
Git checkout because generated results and figures were ignored and Phase 9
files were untracked. The final staged index now contains the explicit
submission allowlist below. A commit is still required before a remote clone
can contain it.

This audit did not train models, regenerate results, modify frozen analytical artifacts, or load raw Days 86–108 data. It updated packaging metadata, documentation, and the Part 5 trade-log header compatibility layer only. The required full test suite did read pre-existing files under `results/holdout/` through its Phase 13/integration artifact-verification tests; it performed no new holdout analysis or data processing.

## Scope and evidence

The governing documents read were:

- docs/quant.md
- docs/architecture.md
- docs/implementation.md
- README.md
- reports/final_report.md
- reports/repository_audit.md
- reports/development_freeze.md

The audit inspected actual source modules, scripts, tests, available development result files, figures, manifests, and documentation. Raw holdout-day data was not loaded, inspected, hashed, profiled, or used. Existing holdout result artifacts were read only as part of the repository's pre-existing test verification.

## Part-by-part compliance

Status meanings: DONE means evidenced for the available scope. PARTIAL means a requirement or coverage limitation remains. UNCERTAIN means provenance cannot establish the claim. MISSING means no adequate artifact was found.

| Requirement | Evidence | Status | Remaining issue |
|---|---|---|---|
| Part 1 scope, ingestion, schema, timestamps, duplicates, prices | results/phase0/dataset_inventory.csv; src/ebx/io/; src/ebx/validation/; results/quality/; results/missingness/ | PARTIAL | Validated for 70 available days; Days 65–79 are unavailable. |
| Part 1 cleaning policy | results/quality/cleaning_policy.txt; src/cleaning/missingness.py | DONE | Structural NaNs preserved; unexpected missingness flagged. |
| Part 1 descriptive statistics and ACF | results/quality/descriptive_stats.csv; results/diagnostics/acf_returns.csv | DONE | Available-day scope only. |
| Part 1 intraday seasonality | figures/part1/volatility_seasonality.png; results/diagnostics/volume_seasonality.csv | PARTIAL | Volatility is present; validated raw volume is unavailable. |
| Part 2 normality tests | results/distributions/normality_tests.csv; src/ebx/distribution/; phase5_part2.py | DONE | Available-day scope only. |
| Part 2 sigma events, tails, and rare events | results/distributions/sigma_events.csv; tail_estimates.csv; extreme_events.csv | DONE with caveat | Volume coincidence cannot be tested without validated raw volume. |
| Part 2 plots and risk discussion | figures/part2/; reports/final_report.md §4 | DONE | Volume limitation is correctly documented. |
| Part 3 independent tests | src/ebx/regimes/methods.py; results/regimes/regime_table.csv | DONE for available days | Fifteen rows are missing-source rows. |
| Part 3 counts and transitions out of 85 | results/regimes/regime_summary.csv; transition_matrix.csv | PARTIAL | 61 persistent and 9 inconclusive are counts for 70 classified days, not 85 observed days. |
| Part 4A taxonomy and naming hypothesis | src/common/features.py; results/features/feature_taxonomy.csv | DONE | Naming taxonomy is not formula provenance. |
| Part 4B candidate reverse engineering | src/analytics/candidates.py; results/features/candidate_scores.csv; candidate_best_matches.csv | DONE as hypotheses | Original masked-feature generator is unavailable. |
| Part 4C predictive relevance and FDR | src/ebx/forensics/predictive.py; results/predictive/aggregate_ic.csv | DONE for available days | Statistical relevance is not causal identity. |
| Part 4D redundancy and PCA | src/ebx/forensics/redundancy.py; results/redundancy/; figures/part4/ | DONE for available days | No additional data was used in this audit. |
| Part 4 dossier and figures | reports/feature_semantics_audit.md; final_report.md §§6–8; figures/part4/ | DONE with provenance limitation | Feature identities remain hypotheses. |
| Part 5 signal, sizing, costs, and execution | src/ebx/ml/backtest.py; scripts/ml/phase_ml4_backtest.py; reports/ml_phase4_backtest.md | DONE | 5 bps entry plus 5 bps exit is an explicit assumption, not measured microstructure. |
| Part 5 look-ahead and day-local execution | tests/unit/ml/test_leakage_stress.py; reports/ml_phase5_audit.md; trade timestamps | DONE for audited downstream path | Raw PB/VB/BB/PV/V producer causality remains uncertified. |
| Part 5 in/out-of-sample and tuning | results/ml/temporal_robustness/; split manifests | PARTIAL | Chronological validation exists; the fixed baseline intentionally did not tune parameters. |
| Part 5 metrics and trade log | results/ml/backtest_baseline/; reports/ml_phase4_backtest.md | DONE | The canonical 941-row trade log preserves the original fields and includes the requested `timestamp`, `side`, `entry_price`, `exit_price`, `quantity`, `pnl`, and `pnl_pct` aliases. |
| Part 5 fresh-checkout deliverables | results/ml/backtest_baseline/; figures/ml_phase4/ | DONE in staged index | The canonical trade log, metrics, manifests, and figures are now explicitly staged. |

## Final model comparison

| Model | Pearson IC | Directional accuracy | Net P&L |
|---|---:|---:|---:|
| Ridge | 0.07071228928810865 | 0.5076512552415182 | -0.2247185557472797 |
| Elastic Net | 0.03365231726756271 | 0.5082094429014867 | -0.2431015522444560 |
| LightGBM | 0.043318708746485406 | 0.5213608887436694 | -0.2445651284399513 |

Evidence: Ridge in results/ml/temporal_robustness/W3/ and results/ml/backtest_baseline/; Elastic Net in results/ml/elastic_net/; LightGBM in results/ml/lightgbm/ and reports/ml_phase9_lightgbm.md.

Ridge remains strongest by Pearson IC and net P&L among tested models. Elastic Net and LightGBM do not improve the conclusion. All tested strategies remain negative after costs. These results do not establish profitability, alpha, production readiness, or holdout generalization.

## Day-84 consistency

| Claim | Authoritative evidence | Finding |
|---|---|---|
| W3 including Day 84 | results/ml/temporal_robustness/day84_sensitivity.json | Pearson IC 0.07071228928810865 |
| W3 excluding Day 84 | same artifact | Pearson IC 0.011037267308543089 |
| Regime | results/regimes/regime_table.csv; results/ml/day84_forensics/day84_forensics.json | random-walk / inconclusive, low confidence |
| Intraday relationship | day84_forensics.json section_5_intraday_segments; reports/ml_day84_forensics.md | Mixed and non-monotonic; segment 3 Pearson IC -0.12328349152607022 |
| 258 observations | day84_forensics.json and reports/ml_day84_forensics.md §8 | 300-second ML target threshold events, not Part 2 raw price-return events |
| Part 2 catalogue | results/distributions/extreme_events.csv | 20 raw one-minute events and no Day-84 row |

The forensic JSON and Day-84 report agree to displayed precision on the intraday values. The earlier discrepancy was documentation/artifact-selection drift, not a current analytical disagreement. No result should be removed. The 258 target events and 20 Part 2 events must remain separate.

One traceability limitation remains: day84_forensics.json leaves one excluded-pooled-IC reconstruction field null, while the separate temporal-robustness sensitivity artifact stores the authoritative excluded-day value.

## Leakage and provenance

The defensible conclusion is:

> No confirmed leakage was found in the audited downstream ML/target/preprocessing pipeline, but causal provenance of the supplied PB/VB/BB/PV/V features could not be independently certified because the original feature-generation source is unavailable.

This is supported by reports/ml_phase8_leakage_stress_test.md and reports/ml_phase8b_feature_provenance.md.

The previously identified over-broad wording was corrected in this packaging pass:

- reports/data_forensics_discovery.md now scopes the finding to the audited downstream pipeline and states the feature-provenance limitation;
- reports/quant_md_compliance_audit.md now uses the same provenance-limited wording.

The phase-8b wording is the final defensible formulation.

## Required deliverables and fresh checkout

| Deliverable | Local | Fresh Git checkout | Finding |
|---|---:|---:|---|
| Governing docs, README, config | Yes | Yes | Accessible. |
| Existing source, scripts, tests | Yes | Yes | Accessible. |
| Phase 9 source, test, report | Yes | Yes in staged index | Commit is still required for a remote clone. |
| final_report.md | Yes | Yes | Includes the final Elastic Net/LightGBM comparison and limitations. |
| Part 5 script and report | Yes | Yes | Present. |
| Results tables and manifests | Yes | Yes in staged index | Canonical allowlisted files are staged; Parquet partitions remain excluded. |
| Trade log | Yes | Yes in staged index | Part 5 and LightGBM trade logs are staged; the Part 5 log includes the literal compatibility aliases. |
| Figures | Yes | Yes in staged index | Required Part 1, Part 2, Part 4, and Part 5 figures are staged. |
| LightGBM namespace | Yes, 20 files | Yes in staged index for required outputs | Predictions Parquet is excluded; model/config/metrics/reproducibility outputs are staged. |

## Final packaging table

| Deliverable | Exists | Tracked in staged index | Required | Action |
|---|---:|---:|---:|---|
| Parts 1–4 source and scripts | Yes | Yes | Yes | Keep |
| Part 1–4 canonical tables | Yes | Yes | Yes | Keep |
| Part 1, 2, and 4 figures | Yes | Yes | Yes | Keep |
| Part 5 backtest script/report | Yes | Yes | Yes | Keep |
| Part 5 trade log and performance outputs | Yes | Yes | Yes for Level 2 | Keep |
| Part 5 literal trade-log aliases | Yes | Yes | Yes | Keep; aliases are packaging-only and row-by-row verified |
| Ridge/Elastic Net evidence | Yes | Yes | Model-comparison evidence | Keep selected metrics/configs/manifests |
| LightGBM source, test, report, config, model, metrics, and manifests | Yes | Yes | Final comparison evidence | Keep |
| Raw CSVs and processed Parquet partitions | Local inputs | No | No; not submission deliverables | Leave ignored |
| Duplicate selection daily exports and Elastic Net primary duplicate | Yes locally | No | No | Leave ignored; do not delete |

Packaging metadata is in `.gitignore` and `.gitattributes`. `.gitignore`
allowlists only the selected final evidence files; raw CSVs, Parquet
partitions, model caches, duplicate exports, and temporary files remain
excluded. `.gitattributes` preserves generated CSV bytes and prevents CRLF
record terminators from being misreported as trailing whitespace by Git.

## KEEP / ARCHIVE / DELETE-CANDIDATE

### KEEP

Keep governing documents, configuration, source modules, all phase scripts, tests, canonical reports, freeze/reproducibility manifests, Part 1–5 result namespaces, figures, trade logs, and the Phase 9 LightGBM files. These are required evidence or reproducibility inputs.

### ARCHIVE

Useful historical material may be archived in a later approved pass:

- phase reports ml_phase0 through ml_phase5_audit;
- phase2_audit.md, feature_semantics_audit.md, and interim leakage/compliance audits;
- data_forensics_discovery.md and older integrated summaries;
- reports/report.md, until all links are confirmed.

These should not be deleted because they preserve decisions, caveats, and research history.

### DELETE-CANDIDATE

No safe delete-candidate was identified. Stale wording is not a deletion reason; those reports should be corrected or labeled historical in a separate approved documentation pass. No temporary/debug file was found in the tracked working tree.

## Pre-packaging documentation findings and disposition

| File | Finding | Severity |
|---|---|---|
| README.md | Earlier copy omitted Elastic Net and LightGBM and used stale model-scope wording. | Resolved in staged index |
| reports/final_report.md | Earlier copy omitted the final Elastic Net/LightGBM comparison and holdout reservation. | Resolved in staged index |
| reports/repository_audit.md | Historical report retains earlier test count and phase mapping. | Keep as historical evidence; not the final audit |
| reports/development_freeze.md | Correct for the earlier freeze; later model comparisons are documented separately. | Keep; historical scope is intentional |
| results/README.md and scripts/README.md | Earlier inventories omitted Elastic Net and LightGBM. | Resolved in staged index |
| reports/quant_md_compliance_audit.md | Earlier copy used stale test/leakage/score wording. | Resolved in staged index; historical score caveat retained |
| reports/data_forensics_discovery.md | Earlier copy contained unqualified no-leakage statements. | Resolved in staged index |
| reports/ml_phase9_lightgbm.md | Matches stored LightGBM configuration, metrics, comparisons, sensitivity, and boundary. | NONE |
| reports/ml_day84_forensics.md and relevant final-report sections | Required Day-84 distinctions are present. | NONE |

## Conservative rubric estimate

The rubric supplies weights but no point-level scoring scheme, and the listed section weights sum to 90 before bonus. The following is a transparent, non-official estimate:

| Section | Score |
|---|---:|
| Part 1 | 8 / 10 |
| Part 2 | 13 / 15 |
| Part 3 | 17 / 20 |
| Part 4 | 17 / 20 |
| Part 5 | 21 / 25 |
| Base | 76 / 90 |
| Bonus | 12 / 15 |
| Total | 88 / 105 |

Basis: strong available-day implementation, explicit missing-day treatment, incomplete raw-volume evidence, feature-provenance uncertainty, and a fixed rather than tuned Part 5 strategy. This estimate should not be presented as an official grade. The prior 103.05/115 score is not a reliable literal score because it treats a 90-point base as 100 and contains stale counts/claims.

## Remaining issues

### HIGH

No remaining analytical or packaging HIGH issue was found in the staged index. A commit is still required before a remote clone can contain the staged package.

### MEDIUM

1. Part 5 does not literally tune parameters on a subset, by design.
2. Raw-volume seasonality and volume coincidence are unavailable.
3. Development coverage is 70/85, not 85/85.
4. No dedicated Part 3 figure exists, although quant.md does not explicitly require one.

### LOW

1. Historical reports retain older counts and narratives.
2. One Day-84 reconstruction field is null despite a separate authoritative sensitivity artifact.

## Recommended cleanup plan — not executed

1. Commit the staged package when explicitly authorized; no commit or push was performed in this audit.
2. Preserve the 70/85 boundary, Days 65–79 gap, Day-84 primary result, and post-hoc sensitivity.
3. Do not retrain, tune, add another model, alter frozen methodology, fill missing days, or access Days 86–108.

## Explicit answers

A. Parts 1–4: Yes, as a labeled 70-of-85-day submission; not as an 85-day result.

B. Part 5: Analytically and packaging-ready as a fixed baseline; the requested literal aliases are present and the original trade-log values are preserved.

C. Model comparison: Complete enough for Ridge, Elastic Net, and one fixed LightGBM W3 benchmark. No holdout generalization claim.

D. Leakage wording: The Phase 8B wording is defensible and is now used in the final documentation; historical reports that retain older language are identified as historical evidence.

E. Day-84 documentation: Current authoritative artifacts are consistent; retain all results and distinguish the two event catalogues.

F. Required deliverables: Present locally and in the staged Git index for the scoped final package; a commit is still needed for a remote/fresh clone.

G. Reproducibility: Research-bearing outputs are reproducible locally and the required scoped artifacts are present in the staged index; a commit is still needed for a remote/fresh clone.

H. Stopping point: Yes. Further model search would be scope expansion without evidence.

I. Must fix before submission: commit the staged package when authorized. No analytical fix remains; the trade-log aliases and documentation synchronization are complete.

J. Should not continue: no more models, tuning, strategy search, missing-day fabrication, frozen-method changes, or holdout access.

## Final recommendation

**STOP analytical development. CONTINUE only with controlled packaging and traceability cleanup.**

This phase is complete after the required verification checks. Raw Days 86–108 remained untouched; the full suite's existing holdout-artifact checks are disclosed above.
