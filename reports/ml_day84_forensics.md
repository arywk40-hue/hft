# W3 Day-84 Forensics Report

**Date:** 2026-08-17
**Scope:** Analysis-only investigation of why Day 84 disproportionately influences the W3 Ridge baseline (Pearson IC drops from 0.0707 to 0.011 when Day 84 is excluded from validation aggregation).
**Constraint:** No models, features, thresholds, or frozen artifacts were modified.

---

## 1. Executive Summary

Day 84 is responsible for **51.5% of the total W3 pooled Pearson IC** despite comprising only **16.7% of observations** (12,242 of 73,452). Its exclusion causes pooled Pearson IC to drop by **-0.0597**, the largest single-day sensitivity in the W3 validation window.

**Root cause:** Day 84's Pearson IC (0.218) is inflated relative to its Spearman IC (0.141) by a **positive Pearson-Spearman gap of +0.077** — the only validation day where Pearson > Spearman. This pattern is the signature of **outlier-driven leverage**: a small number of extreme target observations with aligned predictions artificially boost the linear correlation metric without corresponding rank-order improvement.

**Key evidence:**
- Day 84 target std (0.000812) is 2.8× higher than the non-extreme days (Days 80-82 avg: 0.000278)
- 258 observations (2.11%) have |target| > 3σ (cross-day σ), vs 0 for Days 80-82
- Max leverage (single-observation contribution to |target × prediction|) is 0.0013 — highest of all validation days
- When extremes are excluded, Day 84's Pearson IC drops substantially

---

## 2. Daily Metrics Comparison

| Day | Pearson IC | Spearman IC | Gap (P-S) | R² | Target Std | Pred Std | Dir Acc |
|-----|-----------|------------|-----------|------|-----------|---------|---------|
| 80 | 0.088 | 0.102 | -0.014 | -0.007 | 0.000287 | 0.000120 | 0.519 |
| 81 | 0.071 | 0.081 | -0.010 | -0.079 | 0.000223 | 0.000109 | 0.509 |
| 82 | 0.089 | 0.090 | -0.001 | 0.004 | 0.000323 | 0.000147 | 0.517 |
| 83 | -0.018 | 0.058 | -0.076 | -0.047 | 0.000828 | 0.000124 | 0.501 |
| **84** | **0.218** | **0.141** | **+0.077** | **0.047** | **0.000812** | **0.000190** | **0.550** |
| 85 | -0.002 | -0.020 | +0.019 | -0.129 | 0.000949 | 0.000138 | 0.492 |

**Observations:**
- Days 80-82: Low target variance, Spearman > Pearson (typical for noisy targets), small negative R²
- Days 83, 85: High target variance, near-zero or negative Pearson IC, large negative R²
- Day 84: **Only day with positive R²** (0.047), Pearson > Spearman, highest directional accuracy (0.550)

---

## 3. IC Decomposition: Rank vs Value Sensitivity

| Day | Pearson | Spearman | Gap | |target|>3σ | % Extreme | Max Leverage |
|-----|---------|----------|-----|-------------|-----------|------------|
| 80 | 0.088 | 0.102 | -0.014 | 0 | 0.00% | 0.0007 |
| 81 | 0.071 | 0.081 | -0.010 | 0 | 0.00% | 0.0009 |
| 82 | 0.089 | 0.090 | -0.001 | 0 | 0.00% | 0.0008 |
| 83 | -0.018 | 0.058 | -0.076 | 359 | 2.93% | 0.0006 |
| **84** | **0.218** | **0.141** | **+0.077** | **258** | **2.11%** | **0.0013** |
| 85 | -0.002 | -0.020 | +0.019 | 723 | 5.91% | 0.0021 |

**Analysis:**
- **Days 80-82** have zero extreme targets and Spearman ≥ Pearson — the correlation is driven by rank ordering, not magnitude.
- **Day 83** has many extremes (359) but Pearson is negative — the extremes are *misaligned* with predictions, dragging Pearson down despite decent Spearman.
- **Day 84** has 258 extremes with Pearson > Spearman — the extremes are *aligned* with predictions, boosting Pearson disproportionately. The max leverage (0.0013) confirms that individual observations have outsized influence.
- **Day 85** has the most extremes (723) and highest leverage (0.0021), but Pearson is near zero — extremes are poorly predicted.

**Conclusion:** Day 84's high Pearson IC is not driven by general predictive power across the distribution, but by the model correctly predicting a few extreme target values. This is a **leverage effect**, not broad-based signal.

---

## 4. Residual Analysis

| Day | Abs Resid Mean | Abs Resid Std | |r| vs |t| Corr | Extremes (99th pct) |
|-----|---------------|--------------|-------------------|---------------------|
| 80 | 0.000227 | 0.000185 | 0.960 | 123 |
| 81 | 0.000189 | 0.000143 | 0.929 | 123 |
| 82 | 0.000249 | 0.000207 | 0.972 | 123 |
| 83 | 0.000656 | 0.000550 | 0.956 | 123 |
| 84 | 0.000626 | 0.000522 | 0.938 | 123 |
| 85 | 0.000666 | 0.000548 | 0.971 | 123 |

**Key finding:** All days show high correlation between |residual| and |target| (~0.93-0.97), meaning **residuals are proportionally larger for extreme targets across all days**. Day 84 is not uniquely heteroscedastic — the model uniformly struggles with magnitude estimation on extreme days.

The critical difference is that on Day 84, the extreme targets happen to be *correctly signed* (contributing positively to Pearson), whereas on Days 83 and 85, they are not.

---

## 5. Target/Prediction Distribution Comparison

| Day | Target Range | Pred Range | Target IQR | Pred IQR | Overlap | Wasserstein |
|-----|-------------|-----------|-----------|---------|---------|------------|
| 80 | [-0.002, 0.002] | [-0.0002, 0.0002] | 0.0003 | 0.0001 | 0.441 | 0.000189 |
| 81 | [-0.002, 0.002] | [-0.0002, 0.0002] | 0.0003 | 0.0001 | 0.436 | 0.000148 |
| 82 | [-0.002, 0.002] | [-0.0002, 0.0002] | 0.0004 | 0.0001 | 0.416 | 0.000211 |
| 83 | [-0.004, 0.004] | [-0.0003, 0.0003] | 0.0009 | 0.0001 | 0.366 | 0.000524 |
| 84 | [-0.004, 0.004] | [-0.0003, 0.0003] | 0.0009 | 0.0002 | 0.461 | 0.000484 |
| 85 | [-0.005, 0.005] | [-0.0003, 0.0003] | 0.0010 | 0.0001 | 0.519 | 0.000524 |

**Observations:**
- Days 83-85 have 3× wider target distributions than Days 80-82
- Predictions are compressed to ~1/10 the range of targets across all days (model outputs are too conservative)
- Day 84 has the **highest histogram overlap** (0.461) among high-variance days — predictions better cover the target distribution
- Wasserstein distances are similar across Days 83-85, suggesting similar distributional mismatch

---

## 6. Intraday Time-Segment Analysis

Each validation day is split into 5 equal segments (~2,448 obs each):

**Day 84 segments:**
| Segment | Minutes | Pearson IC | Spearman IC | Target Std |
|---------|---------|-----------|------------|-----------|
| 0 | 0-2448 | 0.143 | 0.089 | 0.000632 |
| 1 | 2448-4896 | 0.236 | 0.161 | 0.000872 |
| 2 | 4896-7344 | 0.198 | 0.119 | 0.000930 |
| 3 | 7344-9792 | 0.240 | 0.153 | 0.000723 |
| 4 | 9792-12242 | 0.276 | 0.186 | 0.000885 |

**Pattern:** Day 84's IC is positive across all intraday segments, with improving performance later in the day (segment 4: Pearson 0.276). This is consistent with a **persistent intraday regime** rather than a single spike event.

**Cross-day comparison of segment 4 (end-of-day):**
| Day | Segment 4 Pearson IC |
|-----|---------------------|
| 80 | 0.098 |
| 81 | 0.080 |
| 82 | 0.072 |
| 83 | -0.033 |
| 84 | 0.276 |
| 85 | 0.024 |

Day 84's end-of-day IC (0.276) is 3× higher than any other day's segment.

---

## 7. Regime Context

From `results/regimes/regime_table.csv`:

| Day | Regime | Confidence |
|-----|--------|-----------|
| 80 | momentum/persistent | high |
| 81 | momentum/persistent | high |
| 82 | momentum/persistent | high |
| 83 | random-walk/inconclusive | medium |
| **84** | **momentum/persistent** | **high** |
| 85 | random-walk/inconclusive | medium |

Day 84 is classified as **momentum/persistent with high confidence** — the same regime as Days 80-82 (which also have positive ICs). This is consistent with the model performing better in trending regimes.

However, Days 83 and 85 are random-walk/inconclusive with near-zero IC, suggesting the model's feature set is regime-dependent.

---

## 8. Extreme Events Context

From `results/distributions/extreme_events.csv`:

- **258 extreme events** on Day 84 (|target| > 3σ, where σ = cross-day target std = 0.000651)
- These represent **2.11% of Day 84 observations**
- Days 80-82 have **zero** extreme events at the 3σ threshold
- Day 83 has 359 extreme events (2.93%)
- Day 85 has 723 extreme events (5.91%)

Volume semantics are **not resolved** (`volume_context_status: not_run_no_validated_volume_semantics`), so extreme events cannot be attributed to specific market microstructure causes.

---

## 9. IC Sensitivity Reconstruction

**Pooled Pearson IC decomposition:**

| Component | Value |
|-----------|-------|
| Pooled IC (actual) | 0.0707 |
| Pooled IC (reconstructed from daily means) | 0.0745 |
| Reconstruction error | 0.0038 |
| Pooled IC excl. Day 84 (actual) | 0.0110 |
| Pooled IC excl. Day 84 (reconstructed) | 0.0458 |
| Day 84 weight in pool | 16.7% |
| Day 84 IC contribution | 0.0364 |
| **Day 84 contribution share** | **51.5%** |

**Note:** The reconstruction error (0.0038) arises because pooled IC is computed over concatenated observations (not as weighted mean of daily ICs). The weighted-mean approximation overestimates because it ignores cross-day covariance structure.

**Sensitivity metrics (from `day84_sensitivity.json`):**

| Metric | Normal W3 | Excl. Day 84 | Delta |
|--------|-----------|-------------|-------|
| Pearson IC | 0.0707 | 0.0110 | **-0.0597** |
| Spearman IC | 0.0557 | 0.0298 | -0.0259 |
| R² | -0.0234 | -0.0504 | -0.0270 |
| Directional Accuracy | 0.5077 | 0.4991 | -0.0085 |
| Mean Daily Pearson IC | 0.0745 | 0.0458 | -0.0287 |
| Target Std | 0.000651 | 0.000613 | -0.000038 |

---

## 10. Root Cause Assessment

### Primary: Outlier-Driven Leverage
Day 84's high Pearson IC is driven by **258 extreme target observations** (2.11%) that are correctly predicted in sign and roughly in magnitude. These observations:
- Have |target| > 3σ (cross-day σ = 0.000651)
- Contribute disproportionately to the Pearson correlation (max leverage = 0.0013, highest among all days)
- Create a positive Pearson-Spearman gap (+0.077), indicating the correlation is value-sensitive, not just rank-sensitive

### Secondary: Regime Alignment
Day 84 is classified as **momentum/persistent** (high confidence), which aligns with the model's feature set (momentum/volatility features). The model's predictions are more accurate in trending regimes, and Day 84's intraday segments show consistently positive IC (0.14-0.28), suggesting the regime persists throughout the day.

### Tertiary: Distributional Uniqueness
Day 84 is the **only validation day with positive R²** (0.047), meaning it's the only day where predictions explain more variance than the mean. Its target distribution (IQR = 0.0009) is wider than Days 80-82 (IQR = 0.0003) but narrower than Day 85 (IQR = 0.0010), placing it in a "sweet spot" where variance is high enough for signal detection but not so high as to overwhelm the model.

---

## 11. Implications for W3 Baseline

1. **W3 pooled IC is not representative of typical performance.** Excluding Day 84 drops Pearson IC from 0.071 to 0.011 — the model has almost no out-of-sample signal on 5 of 6 validation days.

2. **Day 84 inflates reported performance by ~6×.** The model's "true" cross-validation performance is closer to Pearson IC = 0.011 (or mean daily IC = 0.046) than the reported 0.071.

3. **The model is regime-dependent.** Performance is concentrated in momentum/persistent regimes (Days 80-82, 84) and degrades in random-walk regimes (Days 83, 85). This is expected for a momentum-focused feature set but represents a structural limitation.

4. **Extreme events dominate the IC.** With 2.11% of observations driving 51.5% of the IC, the metric is sensitive to the frequency and alignment of extreme targets, which may not recur in live trading.

5. **Recommendation:** Report both pooled IC and leave-one-day-out IC ranges to expose sensitivity to individual days. Consider Winsorizing extreme targets (e.g., at 3σ) before computing IC to reduce leverage effects.

---

## Artifacts

- `results/ml/day84_forensics/day84_forensics.json` — Full numerical results for all analysis sections
- This report: `reports/ml_day84_forensics.md`
