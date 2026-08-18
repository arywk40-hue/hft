# Independent Phase 0–2 Statistical and Data-Integrity Audit

Audit scope: existing Phase 0–2 code and generated artifacts. Raw holdout CSVs
Days 86–108 were not opened. Missing Days 65–79 were not fabricated.

## A. Audit findings

### Boundary and ingestion

- Development scope is explicitly constrained to Days 1–85 by
  `scripts/phase2_process.py:54-61`; a new guard rejects any configured range
  outside that interval.
- `data/validated/manifest.csv` contains 85 expected rows: 70 available and
  15 `missing_source` rows for Days 65–79.
- No processed Parquet exists for Days 86–108.
- Filename parsing is strict `dayN.csv`; the loader now rejects a caller/file
  day-ID mismatch (`src/ingestion/loader.py:45-51`).
- Existing real-data schema, timestamp, and price artifacts are valid for all
  70 processed development days.

### Structural missingness and ladders

- The 48,370 structural-missingness rows preserve leading, internal, and
  trailing invalid observations without filling them.
- Actual warm-up is calculated from the day-local first timestamp to each
  feature's first valid timestamp.
- Nominal ladder values are now read from configuration and passed into feature
  parsing; actual deviations remain visible. The existing results contain 594
  feature rows with retained deviations.
- No current real-data feature is all-NaN; the all-NaN branch exists but needs
  stronger direct test coverage.

### Masks, Parquet, and boundaries

- Independent checks covered 70 processed tables, 70 masks, 1,596,012
  timestamp values, and 1,104,440,304 mask values.
- Every processed/mask round-trip is schema- and value-equal.
- Mask values agree with finite/non-null source values; timestamps remain
  aligned.
- All day-local timestamp sequences are one-second ordered sequences. No
  rolling, lagged, or future-return calculation exists in Phase 0–2.

## B. Fixes made

The following HIGH-severity issues were fixed safely without architectural redesign:

1. Timestamp validation no longer creates artificial intervals across malformed
   timestamp rows (`src/ingestion/validation.py:60-76`).
2. Zero-return counts no longer compare prices across invalid rows
   (`src/ingestion/validation.py:125-139`).
3. Phase 2 now uses configured PB and BB/PV/V/VB ladders
   (`scripts/phase2_process.py:47-51, 81-84`).
4. The loader enforces filename/caller day identity and the configured
   development range cannot include holdout days.

## C. Test results

`python3 -m unittest discover -s tests -v`: **15/15 passed**.

Coverage includes missing-day discovery, holdout exclusion by fixture,
timestamp gaps, malformed timestamps, invalid prices, structural missingness,
validity masks, Parquet round-trips, filename/day mismatch, and configuration
guards.

## D. Remaining risks

- **MEDIUM** — The first available day becomes the schema reference
  (`scripts/phase2_process.py:91-100`). A corrupted first day could define a
  bad reference unless an independent canonical schema is supplied.
- **MEDIUM** — Cross-day warm-up aggregation computes global `days_present`
  and global missing days rather than feature-specific missing-day lists
  (`src/cleaning/missingness.py:119-140`). This has no effect on the current
  complete 691-feature schema but could misstate a future partial-schema case.
- **MEDIUM** — Non-numeric feature-cell counts are not emitted separately from
  NaN/invalid validity counts (`src/cleaning/missingness.py:66-109`). They are
  invalidated and surfaced through schema/missingness status, but reporting
  could be more granular.
- **LOW** — Configuration parsing is a deliberately small parser for the
  repository's simple YAML shape, not a general YAML implementation.
- **LOW** — No external dependency lockfile or pytest suite exists; the
  reproducible baseline currently uses Python 3.13, PyArrow 25.0.1, and stdlib
  unittest.

## E. Proceed decision

Phase 2 implementation is trustworthy enough to proceed to Part 1 on the 70
available development days only, provided every Part 1 output states that it
uses 70 of 85 expected development days and keeps Days 65–79 explicitly
missing. This is not 85-day Phase 2 acceptance. Days 86–108 remain untouched.
