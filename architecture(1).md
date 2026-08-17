# EBX Quant Challenge — Architecture Decision Document

## Parts 1–4
**Data Hygiene, Distribution & Tails, Regime Classification, Feature Forensics**

This document is the stable architecture/specification. Implementation tasks should live in `implementation.md`.

---

# A. Architecture Diagram

```text
                          ┌─────────────────────────┐
                          │   config/config.yaml    │
                          │  single source of truth │
                          └────────────┬────────────┘
                                       │
┌──────────────────┐       ┌───────────▼────────────┐       ┌──────────────────┐
│ data/raw/         │──────▶│ src/ingestion/         │──────▶│ data/validated/  │
│ day1..day85.csv   │       │ schema + integrity     │       │ manifest + flags │
└──────────────────┘       └───────────┬────────────┘       └────────┬─────────┘
                                       │                              │
                                ┌──────▼──────────────┐               │
                                │ src/cleaning/       │               │
                                │ structural NaNs     │               │
                                └──────────┬───────────┘               │
                                           │                           │
                              ┌────────────▼─────────────┐             │
                              │ data/processed/          │             │
                              │ dayN.parquet             │             │
                              │ dayN_validity_mask       │             │
                              └────────────┬─────────────┘             │
                                           │                           │
             ┌─────────────────────────────┼───────────────────────────┐
             ▼                             ▼                           ▼
      src/diagnostics/              src/distribution/          src/regimes/
          Part 1                       Part 2                    Part 3
             │                             │                           │
             └─────────────────────────────┼───────────────────────────┘
                                           ▼
                                  src/forensics/ Part 4
                                           │
                                           ▼
                                  results/*.csv
                                           │
                                           ▼
                                   figures/*.png
                                           │
                                           ▼
                                  reports/report.md
```

Each analysis layer reads only from `data/processed/` and writes its own outputs independently. Part 4 does not depend on Part 3 having completed.

---

# B. Data-Flow Principles

```text
raw CSV
  → schema validation
  → timestamp validation
  → price validation
  → structural-missingness classification
  → processed Parquet + validity mask
  → Parts 1–4
```

Nothing upstream of `data/processed/` is overwritten.

Raw CSVs are touched only during ingestion.

---

# C. Repository Structure

```text
ebx-analysis/
├── architecture.md
├── implementation.md
├── README.md
│
├── config/
│   └── config.yaml
│
├── data/
│   ├── raw/                  # untouched, read-only
│   ├── validated/            # manifest + quality flags
│   └── processed/            # per-day Parquet + validity masks
│
├── src/
│   ├── ingestion/            # loaders, schema, manifest
│   ├── cleaning/             # structural missingness, masks
│   ├── diagnostics/          # Part 1
│   ├── distribution/         # Part 2
│   ├── regimes/              # Part 3
│   ├── forensics/            # Part 4
│   └── common/               # returns, day boundaries, FDR, I/O
│
├── notebooks/                # thin orchestration/presentation only
│   ├── 01_data_hygiene.ipynb
│   ├── 02_distribution_tails.ipynb
│   ├── 03_regime_classification.ipynb
│   └── 04_feature_forensics.ipynb
│
├── scripts/
├── tests/
├── results/
├── figures/
└── reports/
```

`src/common/day_boundary.py` is critical. Every rolling, lagged, ACF, or future-return operation must respect day boundaries.

---

# D. Statistical Methodology

## Part 1 — Data Hygiene

Returns should be computed as both:

```text
simple return = P_t / P_(t-1) - 1
log return    = ln(P_t) - ln(P_(t-1))
```

Use relevant horizons such as 1 second, 1 minute and 5 minutes.

Compute descriptive statistics for both price levels and returns:

- count
- mean
- median
- standard deviation
- skewness
- kurtosis
- quantiles
- min/max

Statistics should be reported per-day and pooled where meaningful.

Any lagged statistic, including ACF, must be computed **within each day only** and never across day boundaries.

Intraday seasonality should be assessed through volatility and, once a volume interpretation is validated, volume-like behavior.

---

## Part 2 — Distribution & Tails

Use:

- Jarque–Bera
- one independent second normality test such as Shapiro-Wilk or Anderson-Darling

Large-sample test results must not be interpreted from p-values alone. Report practical effect measures such as excess kurtosis and QQ plots.

Compare empirical frequencies of:

```text
|r| > 1σ
|r| > 2σ
|r| > 3σ
```

against Gaussian expectations.

Quantify:

```text
theoretical probability
empirical probability
empirical/theoretical ratio
```

Assess tails using tools such as:

- QQ plots
- empirical quantiles
- Hill estimation where assumptions are appropriate

Catalogue extreme return events and inspect relevant volume-related features around them.

---

## Part 3 — Regime Classification

Each of Days 1–85 should receive a regime assessment using at least two independent approaches from:

- Variance Ratio
- Hurst exponent
- return autocorrelation
- ADF
- KPSS

Candidate regimes:

```text
mean-reverting
momentum / persistent
random-walk / inconclusive
```

Never classify a day from a single test.

Produce an 85-row table containing the relevant test statistics, p-values, regime and confidence.

Also measure:

- regime counts
- proportions
- adjacent-day transition matrix
- persistence probability
- average regime duration
- clustering

All regime tests must be computed within individual days.

---

# E. NaN / Cleaning Policy

## Structural NaNs are evidence

Preserve raw NaNs.

Do not forward-fill or interpolate structural warm-up NaNs because those NaNs provide evidence for the rolling-window hypothesis.

For every feature determine:

```text
first_valid_index
first_valid_timestamp
leading_nan_count
internal_nan_count
trailing_nan_count
```

A leading block of NaNs before the first valid value is potentially structural.

Any NaN appearing after the first valid value is unexpected and must initially be **flagged, not imputed**.

Do not drop an entire day merely because long-window features are still warming up.

Each downstream analysis should use the validity mask for the specific columns it requires.

Example:

```text
Price-only analysis:
    use all valid Price observations

PB18_T12 analysis:
    use only observations where PB18_T12 is valid
```

The different effective sample sizes are legitimate and must be documented.

---

# F. Feature-Forensics Methodology

## Step 1 — Taxonomy

Parse each masked feature into:

```text
family
subfamily
suffix
nominal window
actual warm-up
```

Attach:

- variance
- missingness
- scale
- contemporaneous correlations

Do not assume the family name proves the feature's semantics.

---

## Step 2 — Candidate Library

Construct interpretable candidate formulas.

### Price-oriented candidates

- rolling mean
- rolling median
- rolling standard deviation
- rolling variance
- rolling min/max
- price-minus-rolling-mean
- normalized deviation
- rolling z-score
- momentum
- cumulative return
- EMA
- distance from rolling high/low

### Return-oriented candidates

- rolling return mean
- realized variance
- realized volatility
- absolute-return mean
- downside volatility
- upside volatility

### Volume-oriented candidates

- rolling volume mean
- rolling volume standard deviation
- volume z-score
- volume change
- price-volume covariance
- imbalance proxies

Candidates should use the feature's inferred/nominal window where appropriate.

---

## Step 3 — Hypothesis Scoring

For every masked feature/candidate pair, evaluate multiple diagnostics:

- Pearson correlation
- Spearman correlation
- normalized RMSE after affine rescaling
- first-difference correlation
- sign agreement
- lagged correlation where relevant

Do not infer feature identity from one high correlation.

Use evidence tiers:

```text
strong evidence
moderate evidence
weak evidence
no convincing match
```

---

## Step 4 — Window Reconstruction

Validate `_Tn` behavior across all available development days and across families.

Known hypotheses:

### PB

```text
T1  ≈ 15s
T2  ≈ 30s
T3  ≈ 90s
T4  ≈ 180s
T5  ≈ 270s
T6  ≈ 360s
T7  ≈ 900s
T8  ≈ 1800s
T9  ≈ 2700s
T10 ≈ 4500s
T11 ≈ 5400s
T12 ≈ 10800s
```

### BB / PV / V / VB

```text
T1  ≈ 5s
T2  ≈ 10s
T3  ≈ 30s
T4  ≈ 60s
T5  ≈ 90s
T6  ≈ 120s
T7  ≈ 300s
T8  ≈ 600s
T9  ≈ 900s
T10 ≈ 1500s
T11 ≈ 1800s
T12 ≈ 3600s
```

These are hypotheses, not enforced truths.

Individual PB subfeatures can have much shorter actual warm-up than their nominal `_Tn` bucket.

---

## Step 5 — Predictive Relevance

Evaluate masked features against future returns:

```text
feature(t) → return(t+h)
```

Candidate horizons:

```text
1s
5s
30s
60s
300s
```

Use per-day Information Coefficient:

- Pearson IC
- Spearman IC
- mean IC
- IC standard deviation
- percentage of days with same-sign IC

Never let future information enter the feature.

A feature with modest but stable daily IC is more interesting than a large pooled correlation driven by a small number of days.

---

## Step 6 — Multiple Testing

Feature forensics involves hundreds of hypotheses.

Use Benjamini-Hochberg FDR where appropriate.

Freeze the FDR alpha before interpreting the final results.

Do not tune significance thresholds after seeing how many features survive.

---

## Step 7 — Redundancy / PCA

Use:

- Pearson correlation matrix
- Spearman correlation matrix
- clustering where useful
- PCA

Feature normalization should account for day-to-day scale differences, for example via per-day z-scoring.

Account explicitly for NaNs and different feature-validity windows.

Report the number of components explaining:

```text
50%
80%
90%
```

of variance.

Compare pooled and per-day PCA behavior where appropriate.

---

# G. Leakage-Control Strategy

## Look-ahead

Future returns are generated separately and only joined during evaluation.

The feature at time `t` must never use data from `t+1` onward.

## Day leakage

No rolling, lagging, ACF, or future-return operation may cross a day boundary.

## Threshold leakage

Thresholds are declared in configuration before final interpretation and are not tuned per day to obtain desirable outcomes.

## Survivorship bias

Every day considered must remain in the manifest.

If a day is excluded because of data integrity failure, record the exact reason.

Never silently remove a difficult day.

## Holdout leakage

Days 86–108 are never used while choosing feature formulas, thresholds, regimes, hypotheses, or development conclusions.

---

# H. Computational Strategy

Raw CSVs are large.

Use:

- per-day processing
- Parquet conversion
- vectorized NumPy/pandas operations
- cached intermediate results
- incremental result writing
- float32 where appropriate for memory-heavy analyses

Do not build a giant 85-day DataFrame unless a specific analysis truly requires it.

Part 4 can use stratified pooled samples where full resolution is unnecessary.

---

# I. Core Output Schemas

At minimum:

```text
data/validated/manifest.csv
    day
    rows
    time_range
    gaps
    duplicates
    price_flags
    status
```

```text
results/quality/descriptive_stats.csv
    day
    variable
    horizon
    mean
    median
    std
    skew
    kurtosis
```

```text
results/distributions/normality_tests.csv
    scope
    horizon
    test
    statistic
    p_value
```

```text
results/distributions/sigma_events.csv
    day
    sigma_level
    theoretical_probability
    empirical_probability
    ratio
```

```text
results/regimes/regime_table.csv
    day
    VR
    VR_p
    Hurst
    ACF
    ADF
    ADF_p
    KPSS
    KPSS_p
    regime
    confidence
```

```text
results/forensics/structural_missingness.csv
    feature
    family
    suffix
    nominal_window
    actual_warmup
    missing_fraction
    unexpected_missing
```

```text
results/forensics/feature_hypotheses.csv
    feature
    candidate
    pearson
    spearman
    normalized_rmse
    diff_corr
    evidence_tier
```

```text
results/forensics/ic_table.csv
    feature
    horizon
    mean_IC
    IC_std
    pct_same_sign
    FDR_significant
```

```text
results/forensics/pca_summary.csv
    component
    explained_variance
    cumulative_variance
```

---

# J. Execution Order

The stable architectural order is:

1. ingest and validate development days
2. classify structural missingness
3. convert to processed Parquet
4. generate validity masks
5. perform Part 1
6. perform Part 2
7. perform Part 3
8. perform Part 4 feature taxonomy
9. perform Part 4 reverse engineering
10. perform predictive relevance
11. perform redundancy/PCA
12. integrate findings
13. freeze development conclusions
14. test conclusions on Days 86–108

The holdout is a final validation layer, not a development dataset.

---

# K. Highest-Risk Statistical Decisions

These must receive explicit validation:

1. whether nominal `_Tn` values correspond to actual windows across all families
2. whether Day 1 is representative
3. how structural versus unexpected NaNs are distinguished
4. which regime tests are sufficiently independent
5. how conflicting regime tests are classified
6. how feature identity evidence is graded
7. how multiple testing is controlled
8. whether PCA structure is stable across days
9. whether apparent predictive feature relationships generalize out of sample

No high-confidence claim should be made without evidence supporting it.
