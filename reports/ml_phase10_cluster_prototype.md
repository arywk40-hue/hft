# Phase 10 — Cluster-Conditioned Prototype Strategy

## Execution status: partial real-data execution; implementation in progress

This organiser-requested extension is isolated from frozen Phases 0–9. It is
not a validated strategy and makes no claim of profitability or alpha.

The supplied Ridge sign rule trades on nearly every nonzero continuous
prediction, so its weak directional information can be overwhelmed by
turnover. Phase 10 therefore specifies confidence-gated entries only when
predicted gross edge exceeds the fixed 2 bps round-trip cost plus a frozen
safety buffer.

## Data boundary

The permitted ordered inventory is Days 1–64 and 80–85 (70 days). The first
42 are development and the remaining 28 are final test. Days 65–79 are
missing, and Days 86–108 are locked and explicitly rejected by the runner.
No test-day statistic may select a configuration.

## Implemented foundations

`day_clustering.py` computes day-local price summaries, standardizes only the
development table, and runs deterministic PAM with five observed medoids.
`oracle_trades.py` uses future prices solely to create labels via cardinality-
capped weighted interval scheduling: no more than five non-overlapping,
same-day trades; 30–300 second holds; and 1 bp per-side costs. `prototype_strategy.py`
provides bounded confidence/volatility sizing and a cost-aware entry gate.
`latency.py` measures batch-size-one calls after 1,000 warm-ups and 10,000
timed iterations using `perf_counter_ns`.

## Initial real-data result

The frozen 28-day test was run once the configuration had been written and
hashed. The prototype produced gross P&L of 0.01842, transaction costs of
0.31960, and net P&L of **-0.30117** across 1,718 trades. Its 36.38% hit rate,
large turnover (3,195.98), and negative median trade return (-0.000144) do not
support an economic claim. Measured preprocessing-plus-model batch-size-one
latency was p50 733,167 ns, p95 1,417,136 ns, and p99 3,059,153 ns on the
recorded local environment. These are measured artifacts, not projections.

## Remaining work before submission

The runner now creates the split, day table, clusters, representatives, oracle
labels, event dataset, calibrated linear opportunity model, frozen
configuration hash, latency artifact, strategy trade log, daily P&L and cost
sensitivity table. It still lacks the specified Ridge/random/flat/passive
comparators, model-only and complete feature-update latency measurements, full
cluster/regime diagnostics, and the complete requested figure suite. The local
matplotlib runtime also aborted during figure rendering because its font cache
was not writable; this needs environment remediation before chart QA. These
gaps mean this is not ready for pull-request submission.

## Verification

Focused Phase 10 tests passed (4 passed). The repository unit suite passed
(78 passed, 1 skipped because the optional LightGBM dependency is unavailable).
The integration subset had 3 passing tests and one unrelated failure:
results/holdout/freeze_manifest.json is absent, so its frozen-artifact test
cannot read the expected historical manifest. This extension did not create or
alter holdout artifacts, and no replacement was fabricated.
