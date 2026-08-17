# EBX Quant Analysis

This repository follows the phase-gated implementation plan in
[`implementation.md`](implementation.md) and the architecture in
[`architecture.md`](architecture.md).

Current phase: **PHASE 0 — Repository Audit and Environment Setup**.

The raw dataset is currently located directly under `data/` (not
`data/raw/`) and is treated as read-only. Development work is restricted to
Days 1–85; the available development files and missing days are recorded in
`results/phase0/`.

Run the Phase 0 audit with:

```text
python3 scripts/phase0_audit.py
```

The audit performs metadata-only discovery of day files; it does not parse or
modify raw CSV contents.

Phase 2 can be run with:

```text
python3 scripts/phase2_process.py
```

It processes only configured development days, records missing expected days,
preserves structural missingness, and writes per-day Parquet plus validity
masks. It does not process the holdout range.
