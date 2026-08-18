# EBX Quantitative Analysis

## 1. Executive Summary

The supplied dataset specifies 85 development days, but only 70 were available:
Days 1–64 and 80–85. Days 65–79 are explicit missing days and were never
fabricated. Days 86–108 were held untouched until the final validation and all
23 holdout days were processed. Days 109–123 remain out of scope.

Parts 1–4 found heavy-tailed, non-normal returns; persistent/inconclusive
intraday regimes under the frozen methodology; substantial nominal-vs-actual
window deviations; strong redundancy; and a low-dimensional feature panel.
The frozen predictive screen contained 543 feature-horizon rows, of which 535
strongly generalized, 7 partially generalized, and 1 did not generalize.

The overall out-of-sample verdict is **MOSTLY ROBUST**. This applies to the
general statistical structure, not to every masked-feature identity hypothesis
or exact tail magnitude.

## 2. Dataset and Methodology

Each day is processed independently at one-second frequency. The schema contains
`Time`, `Price`, and 691 masked features across PB, BB, PV, V, and VB families.
Two nominal ladders are preserved as hypotheses: PB uses 15–10800 seconds and
BB/PV/V/VB use 5–3600 seconds.

Structural NaNs are preserved. Unexpected internal/trailing missingness is
flagged, not imputed. Returns, rolling calculations, ACF, regime tests, and
forward-return alignment are day-local. Development and holdout results remain
strictly separate.

## 3. Data Hygiene

The 70 available development days were converted to lossless per-day Parquet
with validity masks. The 23 holdout days each had 23,340 rows, 693 columns, and
valid schema, timestamps, and prices. Holdout integrity found zero timestamp
gaps, duplicates, out-of-order rows, malformed timestamps, or invalid prices.

Development taxonomy identified 594/691 feature-level nominal-vs-actual window
deviations. The holdout comparison preserved these exceptions and found median
warm-up agreement for all 691 features.

## 4. Distribution and Tails

Development pooled 1-minute and 5-minute returns rejected normality under both
Jarque–Bera and Anderson–Darling. Excess kurtosis was 16.2943 at 1m and
11.4267 at 5m. The >3σ empirical/theoretical ratios were 6.2054 and 5.9569.

The holdout conclusions about non-normality and positive excess kurtosis
generalized. Holdout excess kurtosis increased to 129.7917 at 1m and 151.5252
at 5m. >3σ ratios remained elevated at 5.6448 and 4.9152. However, >1σ and
>2σ ratios were lower than development, and Hill alpha fell from 3.9907 to
2.3619 at 1m and from 5.5339 to 1.9479 at 5m. Thus tail direction/general
heaviness generalized, while exact tail magnitude was unstable.

## 5. Regime Classification

The frozen method uses variance ratio q=5, rescaled-range Hurst, lag-1 return
ACF, and ADF on log price, with predeclared thresholds. Development classified
61/70 days as momentum/persistent and 9/70 as random-walk/inconclusive; no day
was classified mean-reverting.

Holdout classified 19/23 days as momentum/persistent and 4/23 as
random-walk/inconclusive. Holdout had 22 adjacent transitions and a persistence
probability of 0.7273. The modest distribution shift did not make the frozen
method uninterpretable.

## 6. Feature Forensics

The taxonomy covers all 691 features. Candidate formulas were evaluated using
multiple metrics: Pearson, Spearman, affine-normalized RMSE, first-difference
correlation, sign agreement, and lagged correlation. Volume candidates remained
explicitly unavailable because no validated raw-volume semantic source was
present.

The 407 frozen best-match hypotheses produced 153 strong, 150 partial, 93
non-generalizing, and 11 insufficient holdout outcomes. A candidate match is a
feature identity hypothesis, not a confirmed identity. Correlation with a
candidate formula alone is not sufficient evidence.

## 7. Predictive Relevance

The development screen used exact `feature(t) → return(t+h)` alignment at 1s,
5s, 30s, 60s, and 300s, with Benjamini–Hochberg FDR alpha 0.05. It retained
543 frozen feature-horizon rows using the declared development screen.

On holdout, 535 strongly generalized, 7 partially generalized, and 1 failed.
The failed relationship was `PB14_T12` at 300 seconds. This is frozen
statistical predictive relevance, not ML model performance, causal evidence, or
a trading result. No holdout significance re-selection was performed.

## 8. PCA and Redundancy

Development pooled PCA reached 50%, 80%, and 90% variance at 3, 15, and 35
components. Holdout reached those levels at 3, 14, and 34 components. Median
per-day counts remained 3, 11, and 22.

Development median absolute Pearson/Spearman redundancy was 0.1319/0.1582;
holdout was 0.1227/0.1414. The pooled first-component variance changed from
0.2468 to 0.2021. The broad low-dimensional and redundant structure therefore
generalized, with some magnitude variation.

## 9. Out-of-Sample Validation

All 23/23 holdout days passed integrity validation. Window medians, PCA/
redundancy structure, regime proportions, normality rejection, and most frozen
predictive relationships generalized. Feature-hypothesis identity evidence was
mixed, and exact tail magnitudes were not stable.

The final verdict is **MOSTLY ROBUST**.

## 10. Limitations

- Development coverage is 70 days, not the specified 85; Days 65–79 remain missing.
- The dataset is masked and feature semantics are inferred hypotheses, not confirmed identities.
- Exact tail-index estimates are unstable across development and holdout.
- Some feature hypotheses did not generalize or lacked sufficient holdout evidence.
- No trained ML model was built.
- No trading strategy, Part 5, or backtest was performed.
- Statistical persistence is not proof of economic value, causal effect, or deployability.

## Reproducibility

See [reports/reproducibility.md](reproducibility.md) and the
[artifact index](artifact_index.md). The development freeze and holdout
manifest must remain unchanged for these conclusions to retain their recorded
scope.
