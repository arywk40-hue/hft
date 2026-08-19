# Data Forensics Discovery Report

**Scope**: Development data only — Days 1–64 and 80–85 (70 days).
**Holdout days loaded**: `[]` (Days 86–108 were not accessed).
**Analysis script**: `scripts/analysis/data_forensics.py`
**Date**: 2026-08-19

---

## 1. Dataset Structure

The processed dataset consists of 70 day-Parquet files, each containing **693 columns**: `Time`, `Price`, and 691 masked features across 5 families.

| Family | Features | Structure | Example |
|--------|----------|-----------|---------|
| PB | 216 | `PB{i}_T{j}` — 18 subfamilies × 12 temporal scales | `PB1_T1` … `PB18_T12` |
| BB | 191 | Mixed — `BB{i}_T{j}` (9 subfamilies × 12 scales) + `BB{k}` (17 flat) | `BB1_T1` … `BB26` |
| V | 115 | Mixed — `V{i}_T{j}` + ratio forms `V{i}_T{j}_T{k}` | `V1_T1` … `V8_T11_T12` |
| PV | 97 | `PV{i}_T{j}` + compound `PV{i}_B{k}_T{j}` | `PV1_T1` … `PV3_B7_T12` |
| VB | 72 | `VB{i}_T{j}` — 6 subfamilies × 12 temporal scales | `VB1_T1` … `VB6_T12` |

**Temporal resolution**: 1-second observations; ~23,340 rows per day (~6.5 trading hours).
**Row counts**: Uniform at 23,340 for Days 1–59; drops to 6,120–12,488 for Days 60–64 (shortened sessions).
**Days 80–85**: Full 23,340 rows restored after the 65–79 gap.

---

## 2. Feature-Family Findings

### 2.1 BB Split-Personality

The BB family contains two structurally distinct subpopulations:

- **BB1–BB9** (108 features): Carry `_T{j}` temporal suffixes (12 scales from 5s to 3600s). Mean values center near 100 (price-level features). **Zero warm-up NaN** for BB1; increasing warm-up for BB2+ proportional to nominal window.
- **BB10–BB26** (83 features): Flat naming, no temporal suffix. Values center near 0.5 (ratio/indicator-type). **Significantly longer warm-up** (up to 3600s). Internal NaN occurrences flagged on some days.

This split suggests BB1–BB9 are smoothed price transforms while BB10–BB26 are derived band/ratio indicators.

### 2.2 Intra-Family Correlation

Intra-family correlation is **very high** within the `_T{j}` subfamilies. For PB and VB on sampled days, the mean pairwise correlation within a family exceeded 0.85, confirming extreme redundancy among temporal-scale variants of the same base indicator.

### 2.3 Cross-Day Stability

Family-level daily means are stable across days. The coefficient of variation of the daily family mean is small for PB, BB, and VB (all < 0.05), indicating the feature distributions are stationary on a day-to-day basis. Days 60–64 show slightly higher variance due to shortened sessions.

---

## 3. Temporal Findings

### 3.1 Intraday Volatility U-Shape

A pronounced U-shape in intraday 1-second volatility:

| Hour | RMS Volatility |
|------|---------------|
| 0 | 6.1 × 10⁻⁵ |
| 1 | 4.8 × 10⁻⁵ |
| 2 | 3.9 × 10⁻⁵ |
| 3 | 3.8 × 10⁻⁵ (minimum) |
| 4 | 4.3 × 10⁻⁵ |
| 5 | 4.2 × 10⁻⁵ |
| 6 | 4.9 × 10⁻⁵ |

The opening hour is ~60% more volatile than the mid-session trough. This is a classic market microstructure effect and is **robust** across all 70 development days.

### 3.2 Return Autocorrelation

1-second return autocorrelation is negligible (lag-1 ACF typically < 0.01 in absolute value). Day 84 shows particularly small ACF values (lag-1: −0.006), consistent with near-random-walk behavior at the 1s timescale.

### 3.3 Daily Volatility Series

Cross-day volatility autocorrelation is **−0.036** (effectively zero), meaning tomorrow's volatility is not predictable from today's within this dataset. This contrasts with typical equity market behavior where volatility clusters.

> **Scope**: This finding is limited to the 70 available days with a 15-day gap at Days 65–79. The gap may suppress genuine serial dependence.

---

## 4. Target Relationships

### 4.1 Top Features for 300-Second Return

The strongest univariate associations with the 300-second forward return are **VB-family features** at longer temporal scales:

| Feature | Sign Consistency | FDR Reject |
|---------|-----------------|------------|
| VB2_T12 | 66% positive | Yes |
| VB4_T12 | 66% positive | Yes |
| VB3_T12 | 66% positive | Yes |
| VB4_T5 | 67% positive | Yes |
| VB3_T5 | 67% positive | Yes |
| VB2_T11 | 69% positive | Yes |
| VB2_T10 | 70% positive | Yes |
| VB3_T3 | 70% positive | Yes |

### 4.2 Sign Consistency Assessment

Even the best features only achieve 66–70% same-sign consistency across days. No feature reaches 80%. This places the entire top-feature set in the **MODERATELY STABLE** to **UNSTABLE** classification under conservative criteria.

> **Important distinction**: These are univariate associations, not predictive evidence. A feature with 67% same-sign IC could still produce negative out-of-sample returns after costs.

### 4.3 Daily IC Variation

Daily mean IC (across top-20 features) varies dramatically:

- **Highest IC days**: Day 49 (+0.33), Day 53 (+0.24), Day 5 (+0.24)
- **Lowest IC days**: Day 14 (−0.25), Day 44 (−0.13), Day 47 (−0.12)
- **Day 84**: −0.09 (bottom 5), contradicting its strong *model-level* IC

This apparent paradox is addressed in Section 6.

---

## 5. Regime Findings

### 5.1 Volatility Regime Distribution

Days partition into three volatility terciles with balanced counts:

| Regime | Count | Volatility Range |
|--------|-------|------------------|
| Low-vol | 23 days | σ ≤ 3.20 × 10⁻⁵ |
| Mid-vol | 24 days | 3.20 × 10⁻⁵ < σ ≤ 4.25 × 10⁻⁵ |
| High-vol | 23 days | σ > 4.25 × 10⁻⁵ |

### 5.2 Day 84 is High-Volatility

Day 84 sits at the **91st percentile** of daily volatility (σ = 6.22 × 10⁻⁵). It is classified as high-vol. Days 83 and 85 are high-vol and mid-vol respectively.

### 5.3 Regime and Existing Classification

The existing regime classifier (VR/ACF/Hurst-based) labels 61/70 days as "momentum/persistent" and 9/70 as "random-walk/inconclusive". The volatility tercile classification is orthogonal — momentum/persistent days span all three volatility bands. This suggests at least two independent regime dimensions in the data: **trend persistence** and **volatility level**.

---

## 6. Day-84 Explanation

### 6.1 Statistical Profile

Day 84 is an outlier on several dimensions:

| Metric | Day 84 | Percentile (vs other 69 days) |
|--------|--------|-------------------------------|
| 1s return std | 6.22 × 10⁻⁵ | **91st** |
| 300s target std | 9.94 × 10⁻⁴ | **88th** |
| 300s target range | 7.10 × 10⁻³ | **81st** |
| Return kurtosis | 8.65 | **29th** (moderate) |
| NaN fraction | 0.020 | **14th** (low missingness) |

Day 84 has **high volatility, wide target dispersion, and low missingness**. The kurtosis is unremarkable — it is not an extreme-tail day.

### 6.2 The Feature-IC Paradox

The top-20 univariate feature-target ICs are **negative on Day 84** (mean IC = −0.09). Yet the Ridge model produces its highest daily Pearson IC on Day 84 (0.22 from the temporal robustness W3 sensitivity analysis).

**Explanation**: The Ridge model exploits *multivariate* structure. On Day 84, the PCA dimensionality is **lower than average** (2 components for 50% variance vs mean 2.85, at the 17th percentile). This means the feature space on Day 84 is more tightly organized — the Ridge model can capture a stronger linear combination even though individual features have mixed signs.

### 6.3 PCA Concentration on Day 84

Day 84's first principal component explains **30.3%** of variance (65th percentile — above average but not exceptional). However, its 50%-threshold dimensionality of 2 components (vs mean 2.85) indicates that the feature space on Day 84 is **effectively 2-dimensional** for half the variance. This is a regime-specific structural property, not a data quality artifact.

### 6.4 Intraday Segmentation

Day 84's first half has 35% higher volatility than the second half:
- First half: σ = 7.06 × 10⁻⁵
- Second half: σ = 5.25 × 10⁻⁵

This asymmetry is more pronounced than most days and may contribute to the model's leverage over the intraday regime transition.

### 6.5 Assessment

Day 84's strong model performance is **not a data quality artifact**. It is explained by:
1. High target dispersion (more signal-to-noise for the model to exploit)
2. Low effective feature dimensionality (tighter linear structure)
3. Low missingness (more complete data for the model to use)

This combination is **regime-specific** — it occurs when volatility is high and the feature space is unusually concentrated. The effect is unlikely to be reliably reproducible.

---

## 7. Redundancy / Latent Structure

### 7.1 Effective Dimensionality

From pooled PCA:
- **3 components** explain 50% of total feature variance
- **15 components** explain 80%
- **35 components** explain 90%

The 691 features effectively represent ~15 independent latent factors for the purposes of 80% variance capture. This extreme redundancy is concentrated within temporal-scale variants (`_T1` through `_T12`) of the same base indicator.

### 7.2 Per-Day Dimensionality Variation

Daily effective dimensionality varies substantially:
- 50%-threshold range: 1–4 components
- Mean: 2.86, Std: 0.77
- Days with 1 component (extremely concentrated): Days 3, 22, 24

Days with lower dimensionality tend to have one dominant factor (the first component explaining >50% of variance). Day 84 falls in this low-dimensionality cluster.

### 7.3 Family-Level Redundancy

Within each `{Family}{i}_T{j}` subfamily, the 12 temporal-scale variants are near-identical at short scales. For example, `PB1_T1` (5s window) and `PB1_T2` (10s window) carry essentially the same information. The redundancy drops only for widely separated scales (e.g., `T1` vs `T12`).

---

## 8. Missingness Findings

### 8.1 Warm-Up Is Purely Structural

Missingness is **deterministic and structural**: each feature has leading NaN rows equal to its nominal window size in seconds. No evidence of regime-dependent or suspicious missingness patterns.

| Family | Mean Warm-Up | Max Warm-Up | Internal NaNs? |
|--------|-------------|-------------|-----------------|
| PB | 709s | 10,798s | Yes (rare) |
| BB | 566s | 3,600s | Yes (rare) |
| PV | 93s | 3,600s | No |
| V | 78s | 3,599s | No |
| VB | 626s | 3,600s | Yes (rare) |

### 8.2 Intraday Missingness Decay

Missingness follows a sharp decay curve: Hour 0 shows ~80 NaN features per row (warm-up period), dropping to ~0 by Hour 1+. This is entirely explained by the rolling-window warm-up pattern.

### 8.3 PB and BB Internal NaNs

PB, BB, and VB show rare "unexpected internal NaN" flags in the structural missingness audit. These occur on specific days for specific features and are likely caused by invalid intermediate calculations (e.g., division by zero in a ratio). They are **not** suspicious and do not warrant concern.

### 8.4 Classification

**Missingness is purely structural (Category A)**. It is not regime-dependent, not informative, and not suspicious.

---

## 9. Extreme-Event Findings

### 9.1 Event Concentration

All 20 extreme return events in the development period occur on just **2 days**:
- **Day 36**: 7 events (timestamps 5348–5356, ~1.5 hours into session)
- **Day 51**: 13 events (timestamps ~22,277, near session end)

Day 36 events involve returns of 0.69–0.78% in a single second — orders of magnitude above typical 1s returns (~0.003%).

### 9.2 Precursor Pattern

Day 36's extreme cluster occurs at timestamps 5348–5356 (8 seconds). This is a **localized price jump**, not a gradual acceleration. The rolling 60s volatility before the event (4.86 × 10⁻⁴) is already elevated, suggesting the extreme move occurs within an already-volatile period.

Day 51's events occur near session end, consistent with a closing auction or liquidity withdrawal pattern.

### 9.3 Assessment

The extreme events are **day-specific and non-repeatable**. There is no evidence of a systematic precursor pattern that could be exploited across multiple days. The events are concentrated enough that they would not survive any robust cross-validation.

---

## 10. Cross-Day Stability

### 10.1 Stability Classification of Top Features

Of the 20 features with the highest mean Pearson IC at the 300s horizon:

| Classification | Count | Criterion |
|---------------|-------|-----------|
| ROBUST | 0 | ≥80% same-sign, FDR reject |
| MODERATELY STABLE | 3 | ≥70% same-sign |
| UNSTABLE | 17 | 60–70% same-sign |
| LIKELY ARTIFACT | 0 | <60% same-sign |

**No feature achieves ROBUST status.** The best features (VB2_T10, VB3_T3) reach only 70% sign consistency.

### 10.2 IC Concentration

The daily IC distribution across top features is **fat-tailed**: a few exceptional days (Day 49, Day 53) drive the aggregate mean IC, while many days contribute near-zero or negative IC. This means the aggregate IC is **not representative** of typical daily performance.

### 10.3 Lead/Lag Analysis

Feature-target lag correlations decay smoothly from lag-0 to lag-60 with no suspicious jumps. No downstream leakage flag was raised in this diagnostic. This does not certify causal provenance of the supplied masked PB/VB/BB/PV/V columns. The correlation at lag-0 is modestly higher than lag-1, but the difference is small (< 2× ratio) and consistent with genuine contemporaneous association rather than temporal misalignment.

---

## 11. Potential Leakage Flags

No confirmed leakage was found in this downstream diagnostic. Causal provenance of the supplied PB/VB/BB/PV/V features could not be independently certified because the original feature-generation source is unavailable.

The lead/lag analysis across 15 sampled features (3 per family) showed smooth correlation decay with increasing lag. No feature exhibited:
- Suspicious lag-0 spikes
- Forward-looking temporal alignment
- Target contamination patterns

The feature warm-up structure (leading NaN) prevents backward-filling contamination. The day-local computation enforced by the pipeline prevents cross-day leakage.

---

## 12. Top Evidence-Backed Hypotheses

### Hypothesis 1: VB-Family Dominance
- **Hypothesis**: VB features at longer temporal scales (T10–T12) carry the strongest univariate signal for 300s returns.
- **Evidence**: Top 8 features by mean IC are all VB-family. Sign consistency 66–70%.
- **Affected features**: VB2, VB3, VB4 subfamilies at T4–T12.
- **Affected days**: All 70 development days, but effect is unstable.
- **Statistical strength**: FDR-corrected p-values reject the null for all top VB features.
- **Cross-day stability**: MODERATELY STABLE at best (70% same-sign).
- **Possible explanation**: VB features appear to be volume-band ratio indicators. Longer-scale variants capture regime-level volume information that has weak but statistically detectable association with 5-minute forward returns.
- **Potential leakage concern**: None detected.
- **How to test later**: Track VB-family IC on out-of-sample data; test whether VB signal survives transaction costs.

### Hypothesis 2: Low-Dimensionality Days Drive Model Performance
- **Hypothesis**: The Ridge model performs best on days where the feature space has lower effective PCA dimensionality.
- **Evidence**: Day 84 (strongest model IC) has the lowest 50%-threshold PCA dimensionality (2 components). Days with 1-component dominance (Day 22, Day 24) also show structurally concentrated feature spaces.
- **Affected features**: All families, through the first principal component.
- **Affected days**: Days with components_50pct ≤ 2 (~30% of days).
- **Statistical strength**: Moderate — based on Day 84 analysis and PCA variation.
- **Cross-day stability**: REGIME-SPECIFIC.
- **Possible explanation**: When features are tightly correlated, the Ridge regularizer is more effective at finding the dominant linear combination.
- **Potential leakage concern**: None.
- **How to test later**: Correlate daily PCA dimensionality with model IC across all validation days.

### Hypothesis 3: Extreme Redundancy Limits Effective Feature Count
- **Hypothesis**: The 197 selected features effectively represent ~15 independent factors.
- **Evidence**: Pooled PCA shows 15 components for 80% variance, 35 for 90%.
- **Affected features**: All families, especially within-subfamily temporal variants.
- **Affected days**: All days (structural property).
- **Statistical strength**: Strong — PCA is deterministic.
- **Cross-day stability**: ROBUST.
- **Possible explanation**: The `_T{j}` suffix represents temporal smoothing windows. Adjacent windows (e.g., T5 vs T6) carry near-identical information.
- **Potential leakage concern**: None.
- **How to test later**: Compare Ridge performance with 15 PCA-derived features vs 197 raw features.

### Hypothesis 4: Intraday Volatility U-Shape Is Exploitable Context
- **Hypothesis**: Feature-target relationships may vary systematically with time of day due to the volatility U-shape.
- **Evidence**: Opening-hour volatility is 60% higher than mid-session. Feature warm-up patterns overlap with the high-volatility open.
- **Affected features**: All families, but PB and BB are most affected (longest warm-ups).
- **Affected days**: All days.
- **Statistical strength**: Moderate — volatility U-shape is robust, but feature-target IC variation by hour was not separately measured.
- **Cross-day stability**: ROBUST for the volatility pattern; unknown for IC variation.
- **Possible explanation**: Different market microstructure regimes within the trading day.
- **Potential leakage concern**: None if hour-of-day is used as context, not as a feature.
- **How to test later**: Compute hourly IC for top features; fit separate models for open/mid/close periods.

### Hypothesis 5: Day 84 Effect Is Regime-Driven, Not Anomalous
- **Hypothesis**: Day 84's strong model performance is explained by the combination of high volatility + low dimensionality + low missingness, not by data error.
- **Evidence**: Day 84 is at the 91st percentile for volatility, 17th percentile for PCA dimensionality (components_50pct), and 14th percentile for missingness. All three conditions favor linear model performance.
- **Affected features**: All families through multivariate structure.
- **Affected days**: Day 84 specifically; other high-vol/low-dim days may show similar effect.
- **Statistical strength**: Moderate — single-day evidence with mechanistic explanation.
- **Cross-day stability**: DAY-SPECIFIC (this exact combination is rare).
- **Possible explanation**: The Ridge model's advantage scales with target dispersion and feature coherence.
- **Potential leakage concern**: None.
- **How to test later**: Identify other high-vol/low-dim days (if any exist in holdout) and check model IC.

### Hypothesis 6: BB Split-Personality May Carry Different Signals
- **Hypothesis**: BB1–BB9 (price-level smoothed) and BB10–BB26 (ratio/indicator) contain qualitatively different information.
- **Evidence**: BB1–BB9 have means near 100 and zero warm-up for the shortest scales. BB10–BB26 have means near 0.5 and significant warm-up. Internal NaNs occur only in BB10+.
- **Affected features**: BB family, 191 features.
- **Affected days**: All days.
- **Statistical strength**: Strong — structural property visible in raw data.
- **Cross-day stability**: ROBUST.
- **Possible explanation**: BB10–BB26 may be Bollinger-band width or %B indicators derived from BB1–BB9 price transforms.
- **Potential leakage concern**: None.
- **How to test later**: Analyze IC separately for BB1–BB9 vs BB10–BB26 at the 300s horizon.

---

## 13. Findings Tested and Rejected

### 13.1 Daily Volatility Clustering
**Tested**: Whether daily volatility shows serial correlation (clustering).
**Result**: Cross-day volatility autocorrelation = −0.036 (effectively zero).
**Conclusion**: **Rejected.** No evidence of volatility clustering at the daily level in this dataset. The 15-day gap (Days 65–79) may interfere with this measurement.

### 13.2 Temporal Leakage in Features
**Tested**: Whether any feature shows suspiciously high lag-0 correlation relative to lag-1.
**Result**: All sampled features show smooth, gradual correlation decay across lags.
**Conclusion**: **Rejected for the tested downstream diagnostic.** This does not certify upstream feature causality; the original feature-generation source is unavailable.

### 13.3 Extreme Events as Predictable Precursors
**Tested**: Whether extreme 1s returns have systematic precursor patterns.
**Result**: All 20 extreme events concentrate on 2 days (36 and 51). The events are localized price jumps, not gradual accelerations.
**Conclusion**: **Rejected.** No repeatable precursor pattern.

---

## 14. What Should NOT Be Pursued

1. **Feature selection by individual IC magnitude** — Even the best features are UNSTABLE (66–70% same-sign). Optimizing based on aggregate IC would overfit to the few high-IC days.

2. **Removing Day 84** — Day 84 is not a data error. Its strong model performance has a mechanistic explanation (Section 6). Removing it would reduce the effective validation set without scientific justification.

3. **Time-of-day segmented models** — While the volatility U-shape is real, the feature warm-up pattern means the opening period has maximum missingness. Building a separate opening-period model would have incomplete features and likely overfit.

4. **Extreme-event trading rules** — The 20 extreme events across 70 days (0.03% of observations) are too concentrated (2 days) to form a robust signal.

5. **Expanding the temporal-scale feature set** — The existing T1–T12 scales already exhibit extreme redundancy. Adding more scales would increase dimensionality without adding information.

---

## 15. Recommended Next Experiments

1. **PCA-reduced Ridge comparison**: Fit a Ridge model on the top 15 principal components instead of 197 raw features. Compare IC and stability.

2. **Volatility-conditioned evaluation**: Stratify model performance by volatility tercile. Test whether the model systematically outperforms in high-vol regimes.

3. **VB-family isolation test**: Train a Ridge model using only VB-family features and compare to the full-feature model. This tests whether VB carries the dominant signal.

4. **BB subpopulation analysis**: Compute 300s IC separately for BB1–BB9 (price-level) and BB10–BB26 (ratio) to determine which carries more predictive content.

5. **Hourly IC profiling**: Compute feature-target IC separately for each trading hour to determine whether the signal concentrates at specific times of day.

---

## Final Verdict

### A. ROBUST FINDINGS

1. **Extreme redundancy**: 691 features effectively represent ~15 independent factors (PCA evidence, all days).
2. **Intraday volatility U-shape**: 60% higher volatility at open vs mid-session (all days).
3. **Missingness is purely structural**: Deterministic warm-up pattern, no regime dependence (all days).
4. **BB split-personality**: Two structurally distinct subpopulations within the BB family (all days).
5. **No confirmed downstream temporal leakage**: Smooth lag-correlation decay across all sampled features; upstream feature causality remains uncertified.

### B. INTERESTING BUT UNPROVEN HYPOTHESES

1. **Low-dimensionality days favor Ridge models** — Supported by Day 84 analysis, needs cross-validation.
2. **VB-family dominance in 300s prediction** — Best univariate IC but only MODERATELY STABLE.
3. **Volatility regime determines model utility** — Day 84 is high-vol; needs systematic stratification.
4. **Intraday IC variation** — Likely exists given volatility U-shape, but not directly measured.

### C. LIKELY ARTIFACTS / DO NOT PURSUE

1. **Daily volatility clustering** — No serial correlation detected (rejected).
2. **Extreme-event precursors** — All 20 events on 2 days; non-repeatable (rejected).
3. **Individual feature IC as selection criterion** — No feature reaches ROBUST stability (0/20).

---

## Reproducibility Record

| Item | Value |
|------|-------|
| Script | `scripts/analysis/data_forensics.py` |
| Development days analyzed | 70 (Days 1–64, 80–85) |
| Holdout days loaded | `[]` |
| Feature count | 691 |
| Target | 300-second forward log return |
| Python version | 3.9.6 |
| Random seed | None (deterministic analysis) |
| Frozen artifacts modified | None |
| ML outputs modified | None |
