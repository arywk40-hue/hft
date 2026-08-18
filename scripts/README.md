# Phase scripts

Scripts preserve the phase execution history and are grouped by the phase
numbers in `implementation.md`:

- `phase0_audit.py` through `phase2_process.py`: discovery and ingestion
- `phase4_part1.py` through `phase7_part4a.py`: Parts 1–4A
- `phase8_part4b.py` through `phase10_part4d.py`: Part 4B–4D
- `phase11_integrated_review.py` through `phase13_holdout_validation.py`:
  integration, freeze, and holdout validation
- `run_pipeline.py`: non-mutating production artifact verifier

The production-facing import surface is `src/ebx/`. Historical `src.*`
modules remain because the `src/ebx/` package delegates to them; they are
audited compatibility and provenance code, not obsolete duplicates.
