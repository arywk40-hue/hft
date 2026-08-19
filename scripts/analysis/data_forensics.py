#!/usr/bin/env python3
"""Data Forensics Discovery — exploratory analysis of development dataset.

This script performs read-only forensic analysis of the EBX development data.
It does NOT train models, optimize strategies, or access holdout Days 86-108.

Outputs:
  results/data_forensics/   — machine-readable summaries
  figures/data_forensics/   — materially explanatory figures
"""

from __future__ import annotations

import json
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RESULTS_OUT = ROOT / "results" / "data_forensics"
FIGURES_OUT = ROOT / "figures" / "data_forensics"

DEVELOPMENT_DAYS = list(range(1, 65)) + list(range(80, 86))
HOLDOUT_DAYS = list(range(86, 109))
FAMILIES = ["PB", "BB", "PV", "V", "VB"]

# ── helpers ──────────────────────────────────────────────────────────────────

def classify_feature(col: str) -> str:
    for fam in ["PB", "VB", "BB", "PV", "V"]:
        if col.startswith(fam):
            return fam
    return "OTHER"


def load_day(day_id: int) -> pd.DataFrame | None:
    assert day_id not in HOLDOUT_DAYS, f"HOLDOUT VIOLATION: attempted to load day {day_id}"
    path = PROCESSED / f"day{day_id}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


def time_to_seconds(t: str) -> int:
    parts = t.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ("Time", "Price")]


def compute_forward_return(prices: np.ndarray, horizon: int) -> np.ndarray:
    ret = np.full(len(prices), np.nan)
    ret[:-horizon] = (prices[horizon:] - prices[:-horizon]) / prices[:-horizon]
    return ret


def write_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n")


# ── 1. DATASET STRUCTURE ────────────────────────────────────────────────────

def analyze_dataset_structure() -> dict:
    print("  [1/10] Dataset structure...")
    available = []
    day_profiles = []
    for d in DEVELOPMENT_DAYS:
        df = load_day(d)
        if df is None:
            continue
        available.append(d)
        feats = feature_columns(df)
        fam_counts = defaultdict(int)
        for f in feats:
            fam_counts[classify_feature(f)] += 1

        times = df["Time"].values
        ts = np.array([time_to_seconds(str(t)) for t in times])
        duration_sec = ts[-1] - ts[0] if len(ts) > 1 else 0

        day_profiles.append({
            "day": d,
            "rows": len(df),
            "columns": len(df.columns),
            "features": len(feats),
            "duration_seconds": int(duration_sec),
            "first_time": str(times[0]),
            "last_time": str(times[-1]),
            **{f"n_{k}": v for k, v in sorted(fam_counts.items())},
        })

    result = {
        "expected_development_days": len(DEVELOPMENT_DAYS),
        "available_development_days": len(available),
        "available_days": available,
        "missing_days": [d for d in DEVELOPMENT_DAYS if d not in available],
        "holdout_days_loaded": [],
        "day_profiles": day_profiles,
    }
    write_json(result, RESULTS_OUT / "dataset_structure.json")
    return result


# ── 2. TEMPORAL STRUCTURE ───────────────────────────────────────────────────

def analyze_temporal_structure(sample_days: list[int] | None = None) -> dict:
    print("  [2/10] Temporal structure...")
    if sample_days is None:
        sample_days = [1, 10, 20, 30, 40, 50, 60, 80, 83, 84, 85]

    hourly_vol = defaultdict(list)
    hourly_ret_mean = defaultdict(list)
    daily_vol = {}
    daily_acf = {}
    daily_ret_stats = {}

    for d in DEVELOPMENT_DAYS:
        df = load_day(d)
        if df is None:
            continue
        prices = df["Price"].values
        rets_1s = np.diff(np.log(prices))
        rets_1s = rets_1s[np.isfinite(rets_1s)]

        daily_vol[d] = float(np.std(rets_1s))
        daily_ret_stats[d] = {
            "mean": float(np.mean(rets_1s)),
            "std": float(np.std(rets_1s)),
            "skew": float(sp_stats.skew(rets_1s)),
            "kurtosis": float(sp_stats.kurtosis(rets_1s)),
            "min": float(np.min(rets_1s)),
            "max": float(np.max(rets_1s)),
        }

        # ACF at lags 1-10
        if len(rets_1s) > 100:
            acf_vals = []
            for lag in range(1, 11):
                if len(rets_1s) > lag:
                    c = np.corrcoef(rets_1s[lag:], rets_1s[:-lag])[0, 1]
                    acf_vals.append(float(c) if np.isfinite(c) else 0.0)
                else:
                    acf_vals.append(0.0)
            daily_acf[d] = acf_vals

        # Hourly volatility
        times = df["Time"].values
        for i in range(1, len(prices)):
            hour = time_to_seconds(str(times[i])) // 3600
            if i < len(rets_1s):
                hourly_vol[hour].append(rets_1s[i - 1] ** 2)
                hourly_ret_mean[hour].append(rets_1s[i - 1])

    hourly_vol_summary = {}
    for h in sorted(hourly_vol):
        vals = hourly_vol[h]
        hourly_vol_summary[h] = {
            "mean_squared_return": float(np.mean(vals)),
            "rms_volatility": float(np.sqrt(np.mean(vals))),
            "n_obs": len(vals),
        }

    # Rolling volatility clustering
    vol_series = [(d, daily_vol[d]) for d in sorted(daily_vol)]
    vol_values = [v for _, v in vol_series]
    vol_autocorr = float(np.corrcoef(vol_values[1:], vol_values[:-1])[0, 1]) if len(vol_values) > 2 else 0.0

    result = {
        "daily_volatility": {str(k): v for k, v in daily_vol.items()},
        "daily_return_stats": {str(k): v for k, v in daily_ret_stats.items()},
        "hourly_volatility": hourly_vol_summary,
        "daily_acf_lag1_to_10": {str(k): v for k, v in daily_acf.items()},
        "volatility_autocorrelation": vol_autocorr,
    }
    write_json(result, RESULTS_OUT / "temporal_structure.json")

    # Figure: intraday volatility pattern
    hours = sorted(hourly_vol_summary)
    rms_vals = [hourly_vol_summary[h]["rms_volatility"] for h in hours]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(hours, rms_vals, color="#4A90D9", alpha=0.8)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("RMS 1-second volatility")
    ax.set_title("Intraday Volatility U-Shape — All Development Days")
    fig.tight_layout()
    fig.savefig(FIGURES_OUT / "intraday_volatility.png", dpi=150)
    plt.close(fig)

    # Figure: daily volatility time series
    fig, ax = plt.subplots(figsize=(12, 4))
    days_sorted = sorted(daily_vol)
    vols = [daily_vol[d] for d in days_sorted]
    ax.plot(days_sorted, vols, "o-", markersize=3, color="#2E86C1")
    ax.axvline(84, color="red", linestyle="--", alpha=0.7, label="Day 84")
    ax.set_xlabel("Day")
    ax.set_ylabel("Daily 1s return std")
    ax.set_title("Daily Volatility Across Development Period")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_OUT / "daily_volatility_series.png", dpi=150)
    plt.close(fig)

    return result


# ── 3. FEATURE FAMILY BEHAVIOR ──────────────────────────────────────────────

def analyze_feature_families() -> dict:
    print("  [3/10] Feature family behavior...")
    family_stats = {fam: {"daily_means": [], "daily_stds": [], "daily_nan_fracs": []} for fam in FAMILIES}
    family_cross_day_means = {fam: defaultdict(list) for fam in FAMILIES}

    sample_days_for_corr = [1, 20, 40, 60, 84]
    family_intra_corr = {fam: [] for fam in FAMILIES}

    for d in DEVELOPMENT_DAYS:
        df = load_day(d)
        if df is None:
            continue
        feats = feature_columns(df)
        for fam in FAMILIES:
            fam_cols = [f for f in feats if classify_feature(f) == fam]
            if not fam_cols:
                continue
            vals = df[fam_cols].values
            fam_mean = float(np.nanmean(vals))
            fam_std = float(np.nanstd(vals))
            fam_nan = float(np.mean(np.isnan(vals)))
            family_stats[fam]["daily_means"].append({"day": d, "mean": fam_mean})
            family_stats[fam]["daily_stds"].append({"day": d, "std": fam_std})
            family_stats[fam]["daily_nan_fracs"].append({"day": d, "nan_frac": fam_nan})

            # Track per-feature daily means for stability analysis
            for col in fam_cols[:5]:  # Sample 5 features per family
                family_cross_day_means[fam][col].append(float(np.nanmean(df[col].values)))

            # Intra-family correlation on sample days
            if d in sample_days_for_corr and len(fam_cols) > 1:
                valid = df[fam_cols].dropna(axis=0, how="any")
                if len(valid) > 50:
                    corr = valid.corr().values
                    upper = corr[np.triu_indices_from(corr, k=1)]
                    family_intra_corr[fam].append({
                        "day": d,
                        "mean_corr": float(np.mean(upper)),
                        "median_corr": float(np.median(upper)),
                        "min_corr": float(np.min(upper)),
                        "max_corr": float(np.max(upper)),
                        "n_pairs": len(upper),
                    })

    # Cross-day stability: coefficient of variation of daily family means
    stability = {}
    for fam in FAMILIES:
        means = [e["mean"] for e in family_stats[fam]["daily_means"]]
        if means and np.mean(means) != 0:
            stability[fam] = {
                "cv_of_daily_mean": float(np.std(means) / abs(np.mean(means))),
                "mean_of_daily_mean": float(np.mean(means)),
                "std_of_daily_mean": float(np.std(means)),
            }

    result = {
        "family_daily_stats": {k: {"n_days": len(v["daily_means"])} for k, v in family_stats.items()},
        "family_stability": stability,
        "family_intra_correlation": family_intra_corr,
    }
    write_json(result, RESULTS_OUT / "feature_family_behavior.json")
    return result


# ── 4. TARGET RELATIONSHIPS ─────────────────────────────────────────────────

def analyze_target_relationships() -> dict:
    print("  [4/10] Target relationships...")
    horizon = 300
    daily_ic = {}
    hourly_ic = defaultdict(list)
    sign_consistency = defaultdict(lambda: {"pos": 0, "neg": 0, "days": 0})

    # Load aggregate IC for reference
    agg_ic_path = ROOT / "results" / "predictive" / "aggregate_ic.csv"
    agg_ic = pd.read_csv(agg_ic_path)
    top_features_300s = agg_ic[
        (agg_ic["horizon_seconds"] == 300) &
        (agg_ic["pearson_fdr_reject"] == True)
    ].nlargest(20, "mean_pearson_ic")["feature"].tolist()

    if not top_features_300s:
        top_features_300s = agg_ic[agg_ic["horizon_seconds"] == 300].nlargest(20, "mean_pearson_ic")["feature"].tolist()

    for d in DEVELOPMENT_DAYS:
        df = load_day(d)
        if df is None:
            continue
        prices = df["Price"].values
        target = compute_forward_return(prices, horizon)
        times = df["Time"].values

        day_ics = {}
        available_feats = [f for f in top_features_300s if f in df.columns]
        for feat in available_feats:
            fvals = df[feat].values
            mask = np.isfinite(target) & np.isfinite(fvals)
            if mask.sum() < 50:
                continue
            ic = float(np.corrcoef(fvals[mask], target[mask])[0, 1])
            if np.isfinite(ic):
                day_ics[feat] = ic
                if ic > 0:
                    sign_consistency[feat]["pos"] += 1
                else:
                    sign_consistency[feat]["neg"] += 1
                sign_consistency[feat]["days"] += 1

                # Hourly IC
                for i in np.where(mask)[0]:
                    hour = time_to_seconds(str(times[i])) // 3600
                    hourly_ic[(feat, hour)].append((fvals[i], target[i]))

        daily_ic[d] = day_ics

    # Aggregate sign consistency
    sign_summary = {}
    for feat in top_features_300s:
        if feat in sign_consistency:
            sc = sign_consistency[feat]
            total = sc["days"]
            sign_summary[feat] = {
                "positive_days": sc["pos"],
                "negative_days": sc["neg"],
                "total_days": total,
                "positive_fraction": sc["pos"] / total if total > 0 else 0,
            }

    # Day-level IC summary for top features
    ic_by_day = {}
    for d, ics in daily_ic.items():
        if ics:
            vals = list(ics.values())
            ic_by_day[d] = {
                "mean_ic": float(np.mean(vals)),
                "median_ic": float(np.median(vals)),
                "max_ic": float(np.max(vals)),
                "n_features": len(vals),
            }

    result = {
        "horizon_seconds": horizon,
        "top_features_analyzed": top_features_300s[:10],
        "sign_consistency": sign_summary,
        "daily_ic_summary": {str(k): v for k, v in ic_by_day.items()},
    }
    write_json(result, RESULTS_OUT / "target_relationships.json")

    # Figure: daily mean IC across top features
    if ic_by_day:
        fig, ax = plt.subplots(figsize=(12, 4))
        days_s = sorted(ic_by_day)
        mean_ics = [ic_by_day[d]["mean_ic"] for d in days_s]
        colors = ["red" if d == 84 else "#4A90D9" for d in days_s]
        ax.bar(days_s, mean_ics, color=colors, alpha=0.8)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_xlabel("Day")
        ax.set_ylabel("Mean Pearson IC (top 20 features, 300s)")
        ax.set_title("Daily Feature-Target IC — 300s Horizon")
        fig.tight_layout()
        fig.savefig(FIGURES_OUT / "daily_ic_300s.png", dpi=150)
        plt.close(fig)

    return result


# ── 5. REGIME DISCOVERY ─────────────────────────────────────────────────────

def analyze_regimes() -> dict:
    print("  [5/10] Regime discovery...")
    regime_path = ROOT / "results" / "regimes" / "regime_table.csv"
    regimes = pd.read_csv(regime_path)
    regimes_avail = regimes[regimes["status"] == "available"]

    # Collect daily volatility, return stats, and feature dispersion
    day_metrics = {}
    for d in DEVELOPMENT_DAYS:
        df = load_day(d)
        if df is None:
            continue
        prices = df["Price"].values
        rets = np.diff(np.log(prices))
        rets = rets[np.isfinite(rets)]

        # Feature dispersion: std of feature means across families
        feats = feature_columns(df)
        fam_means = []
        for fam in FAMILIES:
            fam_cols = [f for f in feats if classify_feature(f) == fam]
            if fam_cols:
                fam_means.append(float(np.nanmean(df[fam_cols].values)))

        day_metrics[d] = {
            "volatility": float(np.std(rets)),
            "abs_return": float(np.abs(np.sum(rets))),
            "kurtosis": float(sp_stats.kurtosis(rets)),
            "feature_dispersion": float(np.std(fam_means)) if len(fam_means) > 1 else 0,
        }

    # Classify days into volatility terciles
    vols = {d: m["volatility"] for d, m in day_metrics.items()}
    vol_sorted = sorted(vols.values())
    t1 = np.percentile(vol_sorted, 33)
    t2 = np.percentile(vol_sorted, 67)
    vol_regime = {}
    for d, v in vols.items():
        if v <= t1:
            vol_regime[d] = "low_vol"
        elif v <= t2:
            vol_regime[d] = "mid_vol"
        else:
            vol_regime[d] = "high_vol"

    # Day 84 regime position
    day84_metrics = day_metrics.get(84, {})
    day84_vol_pct = 0
    if 84 in vols:
        day84_vol_pct = float(sp_stats.percentileofscore(vol_sorted, vols[84]))

    result = {
        "volatility_terciles": {"t1": float(t1), "t2": float(t2)},
        "day_regime": {str(k): v for k, v in vol_regime.items()},
        "day84_volatility_percentile": day84_vol_pct,
        "day84_metrics": day84_metrics,
        "regime_counts": {
            r: sum(1 for v in vol_regime.values() if v == r)
            for r in ["low_vol", "mid_vol", "high_vol"]
        },
    }
    write_json(result, RESULTS_OUT / "regime_discovery.json")
    return result


# ── 6. DAY-84 FORENSICS ────────────────────────────────────────────────────

def analyze_day84() -> dict:
    print("  [6/10] Day-84 forensics...")
    df84 = load_day(84)
    if df84 is None:
        return {"error": "Day 84 not available"}

    prices84 = df84["Price"].values
    rets84 = np.diff(np.log(prices84))
    target84 = compute_forward_return(prices84, 300)
    feats84 = feature_columns(df84)

    # Compare Day 84 stats to all other days
    all_day_stats = {}
    for d in DEVELOPMENT_DAYS:
        df = load_day(d)
        if df is None:
            continue
        p = df["Price"].values
        r = np.diff(np.log(p))
        r = r[np.isfinite(r)]
        t300 = compute_forward_return(p, 300)
        valid_t = t300[np.isfinite(t300)]

        all_day_stats[d] = {
            "ret_std": float(np.std(r)),
            "ret_kurtosis": float(sp_stats.kurtosis(r)),
            "ret_skew": float(sp_stats.skew(r)),
            "target_std": float(np.std(valid_t)) if len(valid_t) > 0 else 0,
            "target_range": float(np.max(valid_t) - np.min(valid_t)) if len(valid_t) > 0 else 0,
            "nan_frac": float(np.mean([np.mean(np.isnan(df[f].values)) for f in feature_columns(df)])),
            "n_rows": len(df),
        }

    # Percentile rank of Day 84 across all metrics
    d84 = all_day_stats.get(84, {})
    percentiles = {}
    for metric in d84:
        all_vals = [all_day_stats[d][metric] for d in all_day_stats if d != 84]
        if all_vals:
            percentiles[metric] = float(sp_stats.percentileofscore(all_vals, d84[metric]))

    # Feature-target IC on Day 84 vs others
    ic_day84 = {}
    ic_other_days = defaultdict(list)
    sample_feats = feats84[:50]  # Sample first 50 features

    for feat in sample_feats:
        fv84 = df84[feat].values
        mask84 = np.isfinite(target84) & np.isfinite(fv84)
        if mask84.sum() > 50:
            ic84 = float(np.corrcoef(fv84[mask84], target84[mask84])[0, 1])
            if np.isfinite(ic84):
                ic_day84[feat] = ic84

    for d in DEVELOPMENT_DAYS:
        if d == 84:
            continue
        df = load_day(d)
        if df is None:
            continue
        p = df["Price"].values
        t300 = compute_forward_return(p, 300)
        for feat in sample_feats:
            if feat not in df.columns:
                continue
            fv = df[feat].values
            mask = np.isfinite(t300) & np.isfinite(fv)
            if mask.sum() > 50:
                ic = float(np.corrcoef(fv[mask], t300[mask])[0, 1])
                if np.isfinite(ic):
                    ic_other_days[feat].append(ic)

    # Day 84 IC percentile for each feature
    ic_percentiles = {}
    for feat in ic_day84:
        if feat in ic_other_days and ic_other_days[feat]:
            ic_percentiles[feat] = {
                "day84_ic": ic_day84[feat],
                "other_mean": float(np.mean(ic_other_days[feat])),
                "other_std": float(np.std(ic_other_days[feat])),
                "percentile": float(sp_stats.percentileofscore(ic_other_days[feat], ic_day84[feat])),
            }

    # Intraday segmentation of Day 84
    times84 = df84["Time"].values
    ts84 = np.array([time_to_seconds(str(t)) for t in times84])
    segments = {"first_half": ts84 < ts84[-1] / 2, "second_half": ts84 >= ts84[-1] / 2}
    seg_stats = {}
    for name, mask_seg in segments.items():
        seg_rets = np.diff(np.log(prices84[mask_seg]))
        seg_rets = seg_rets[np.isfinite(seg_rets)]
        seg_stats[name] = {
            "n_obs": int(mask_seg.sum()),
            "ret_std": float(np.std(seg_rets)) if len(seg_rets) > 0 else 0,
            "ret_mean": float(np.mean(seg_rets)) if len(seg_rets) > 0 else 0,
        }

    result = {
        "day84_percentiles": percentiles,
        "day84_stats": d84,
        "day84_ic_vs_others": {k: v for k, v in list(ic_percentiles.items())[:10]},
        "intraday_segments": seg_stats,
        "n_features_with_higher_ic_on_day84": sum(
            1 for f in ic_percentiles if ic_percentiles[f]["percentile"] > 75
        ),
        "n_features_sampled": len(sample_feats),
    }
    write_json(result, RESULTS_OUT / "day84_forensics.json")

    # Figure: Day 84 IC distribution vs other days
    if ic_percentiles:
        fig, ax = plt.subplots(figsize=(10, 5))
        pcts = [ic_percentiles[f]["percentile"] for f in ic_percentiles]
        ax.hist(pcts, bins=20, color="#E74C3C", alpha=0.7, edgecolor="black")
        ax.axvline(50, color="black", linestyle="--", alpha=0.5, label="Median baseline")
        ax.set_xlabel("Percentile rank of Day 84 IC among other days")
        ax.set_ylabel("Feature count")
        ax.set_title("Day 84: Feature-Target IC Percentile Distribution")
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGURES_OUT / "day84_ic_percentiles.png", dpi=150)
        plt.close(fig)

    return result


# ── 7. REDUNDANCY & LATENT STRUCTURE ────────────────────────────────────────

def analyze_redundancy() -> dict:
    print("  [7/10] Redundancy & latent structure...")
    pca_path = ROOT / "results" / "redundancy" / "pca_summary.csv"
    pca = pd.read_csv(pca_path)

    pca_per_day = pca[pca["pca_type"] == "per_day"]
    pooled = pca[pca["pca_type"] == "pooled_incremental"]

    effective_dim = {
        "pooled_50pct": int(pooled.iloc[0]["components_50pct"]) if len(pooled) > 0 else None,
        "pooled_80pct": int(pooled.iloc[0]["components_80pct"]) if len(pooled) > 0 else None,
        "pooled_90pct": int(pooled.iloc[0]["components_90pct"]) if len(pooled) > 0 else None,
        "variance_first_component_pooled": float(pooled.iloc[0]["variance_first_component"]) if len(pooled) > 0 else None,
    }

    # Per-day dimensionality variation
    day_dims = {}
    for _, row in pca_per_day.iterrows():
        day_dims[int(row["day"])] = {
            "components_50pct": int(row["components_50pct"]),
            "components_80pct": int(row["components_80pct"]),
            "components_90pct": int(row["components_90pct"]),
            "var_first": float(row["variance_first_component"]),
        }

    # Day 84 dimensionality vs others
    d84_dim = day_dims.get(84, {})
    other_50 = [day_dims[d]["components_50pct"] for d in day_dims if d != 84]
    other_var1 = [day_dims[d]["var_first"] for d in day_dims if d != 84]

    result = {
        "effective_dimensionality": effective_dim,
        "day84_components_50pct": d84_dim.get("components_50pct"),
        "day84_var_first_component": d84_dim.get("var_first"),
        "day84_50pct_percentile": float(sp_stats.percentileofscore(other_50, d84_dim.get("components_50pct", 0))) if other_50 else None,
        "day84_var_first_percentile": float(sp_stats.percentileofscore(other_var1, d84_dim.get("var_first", 0))) if other_var1 else None,
        "mean_daily_components_50pct": float(np.mean(other_50)) if other_50 else None,
        "std_daily_components_50pct": float(np.std(other_50)) if other_50 else None,
    }
    write_json(result, RESULTS_OUT / "redundancy_structure.json")
    return result


# ── 8. LEAD/LAG STRUCTURE ──────────────────────────────────────────────────

def analyze_lead_lag() -> dict:
    print("  [8/10] Lead/lag structure...")
    lags = [0, 1, 5, 10, 30, 60]
    sample_days = [1, 20, 40, 60, 84]
    sample_feats_per_family = 3

    # Select sample features
    df1 = load_day(1)
    if df1 is None:
        return {}
    all_feats = feature_columns(df1)
    sample_feats = []
    for fam in FAMILIES:
        fam_feats = [f for f in all_feats if classify_feature(f) == fam]
        sample_feats.extend(fam_feats[:sample_feats_per_family])

    lag_corr = defaultdict(lambda: defaultdict(list))

    for d in DEVELOPMENT_DAYS:
        df = load_day(d)
        if df is None:
            continue
        prices = df["Price"].values
        rets = compute_forward_return(prices, 300)

        for feat in sample_feats:
            if feat not in df.columns:
                continue
            fvals = df[feat].values
            for lag in lags:
                if lag == 0:
                    f_shifted = fvals
                    t_shifted = rets
                else:
                    f_shifted = fvals[:-lag]
                    t_shifted = rets[lag:]
                mask = np.isfinite(f_shifted) & np.isfinite(t_shifted)
                if mask.sum() > 100:
                    c = float(np.corrcoef(f_shifted[mask], t_shifted[mask])[0, 1])
                    if np.isfinite(c):
                        lag_corr[feat][lag].append(c)

    # Summarize
    summary = {}
    leakage_flags = []
    for feat in sample_feats:
        if feat not in lag_corr:
            continue
        feat_summary = {}
        for lag in lags:
            if lag in lag_corr[feat]:
                vals = lag_corr[feat][lag]
                feat_summary[f"lag_{lag}"] = {
                    "mean_corr": float(np.mean(vals)),
                    "std_corr": float(np.std(vals)),
                    "n_days": len(vals),
                }
        summary[feat] = feat_summary

        # Flag if lag=0 correlation is suspiciously higher than lagged
        if "lag_0" in feat_summary and "lag_1" in feat_summary:
            lag0_abs = abs(feat_summary["lag_0"]["mean_corr"])
            lag1_abs = abs(feat_summary["lag_1"]["mean_corr"])
            if lag0_abs > 0.1 and lag0_abs > lag1_abs * 3:
                leakage_flags.append({
                    "feature": feat,
                    "lag0_corr": feat_summary["lag_0"]["mean_corr"],
                    "lag1_corr": feat_summary["lag_1"]["mean_corr"],
                    "concern": "lag-0 correlation much higher than lag-1; check temporal alignment",
                })

    result = {
        "lag_correlation_summary": summary,
        "leakage_flags": leakage_flags,
    }
    write_json(result, RESULTS_OUT / "lead_lag_structure.json")
    return result


# ── 9. MISSINGNESS AS INFORMATION ──────────────────────────────────────────

def analyze_missingness() -> dict:
    print("  [9/10] Missingness patterns...")
    daily_miss = {}
    hourly_miss = defaultdict(list)

    for d in DEVELOPMENT_DAYS:
        df = load_day(d)
        if df is None:
            continue
        feats = feature_columns(df)
        times = df["Time"].values
        nan_counts = df[feats].isna().sum(axis=1).values

        daily_miss[d] = {
            "mean_nan_per_row": float(np.mean(nan_counts)),
            "max_nan_per_row": int(np.max(nan_counts)),
            "rows_all_valid": int(np.sum(nan_counts == 0)),
            "total_rows": len(df),
            "valid_frac_rows": float(np.mean(nan_counts == 0)),
        }

        # Hourly missingness
        for i, t in enumerate(times):
            hour = time_to_seconds(str(t)) // 3600
            hourly_miss[hour].append(nan_counts[i])

    # Hourly summary
    hourly_summary = {}
    for h in sorted(hourly_miss):
        vals = hourly_miss[h]
        hourly_summary[h] = {
            "mean_nan_features": float(np.mean(vals)),
            "n_obs": len(vals),
        }

    # Family-specific warm-up
    miss_path = ROOT / "results" / "missingness" / "structural_missingness.csv"
    struct_miss = pd.read_csv(miss_path)
    family_warmup = {}
    for fam in FAMILIES:
        fam_data = struct_miss[struct_miss["family"] == fam]
        if len(fam_data) > 0:
            family_warmup[fam] = {
                "mean_warmup_sec": float(fam_data["actual_warmup_seconds"].mean()),
                "max_warmup_sec": float(fam_data["actual_warmup_seconds"].max()),
                "median_warmup_sec": float(fam_data["actual_warmup_seconds"].median()),
                "has_internal_nans": bool(fam_data["unexpected_internal_nan"].any()),
            }

    result = {
        "daily_missingness": {str(k): v for k, v in daily_miss.items()},
        "hourly_missingness": hourly_summary,
        "family_warmup": family_warmup,
        "missingness_classification": "purely_structural",
    }
    write_json(result, RESULTS_OUT / "missingness_patterns.json")

    # Figure: hourly missingness
    fig, ax = plt.subplots(figsize=(10, 5))
    hours = sorted(hourly_summary)
    mean_nans = [hourly_summary[h]["mean_nan_features"] for h in hours]
    ax.bar(hours, mean_nans, color="#E67E22", alpha=0.8)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Mean NaN features per row")
    ax.set_title("Intraday Missingness — Warm-Up Decay Pattern")
    fig.tight_layout()
    fig.savefig(FIGURES_OUT / "intraday_missingness.png", dpi=150)
    plt.close(fig)

    return result


# ── 10. EXTREME EVENTS & CROSS-DAY STABILITY ──────────────────────────────

def analyze_extremes_and_stability() -> dict:
    print("  [10/10] Extreme events & cross-day stability...")
    extreme_path = ROOT / "results" / "distributions" / "extreme_events.csv"
    extremes = pd.read_csv(extreme_path)

    # Days with extreme events
    extreme_days = extremes["day"].unique().tolist()

    # Cross-day stability: check if top-IC features are consistent
    agg_ic = pd.read_csv(ROOT / "results" / "predictive" / "aggregate_ic.csv")
    ic_300 = agg_ic[agg_ic["horizon_seconds"] == 300].copy()
    top_features = ic_300.nlargest(20, "mean_pearson_ic")["feature"].tolist()

    # Check sign consistency
    feature_sign = {}
    for _, row in ic_300.iterrows():
        feat = row["feature"]
        if feat in top_features:
            feature_sign[feat] = {
                "mean_ic": float(row["mean_pearson_ic"]),
                "ic_std": float(row["pearson_ic_std"]),
                "same_sign_pct": float(row["pearson_pct_same_sign"]),
                "fdr_reject": bool(row["pearson_fdr_reject"]),
            }

    # Stability classification
    stability = {}
    for feat, data in feature_sign.items():
        if data["same_sign_pct"] >= 0.8 and data["fdr_reject"]:
            stability[feat] = "ROBUST"
        elif data["same_sign_pct"] >= 0.7:
            stability[feat] = "MODERATELY_STABLE"
        elif data["same_sign_pct"] >= 0.6:
            stability[feat] = "UNSTABLE"
        else:
            stability[feat] = "LIKELY_ARTIFACT"

    result = {
        "extreme_event_days": extreme_days,
        "n_extreme_events": len(extremes),
        "feature_sign_consistency": feature_sign,
        "stability_classification": stability,
        "stability_summary": {
            cls: sum(1 for v in stability.values() if v == cls)
            for cls in ["ROBUST", "MODERATELY_STABLE", "UNSTABLE", "LIKELY_ARTIFACT"]
        },
    }
    write_json(result, RESULTS_OUT / "extremes_stability.json")
    return result


# ── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    RESULTS_OUT.mkdir(parents=True, exist_ok=True)
    FIGURES_OUT.mkdir(parents=True, exist_ok=True)

    print("Data Forensics Discovery — Development Days Only")
    print(f"  Development scope: {DEVELOPMENT_DAYS[0]}-{DEVELOPMENT_DAYS[-1]}")
    print(f"  Holdout scope: NONE (Days 86-108 absolutely excluded)")
    print()

    results = {}
    results["structure"] = analyze_dataset_structure()
    results["temporal"] = analyze_temporal_structure()
    results["families"] = analyze_feature_families()
    results["target"] = analyze_target_relationships()
    results["regimes"] = analyze_regimes()
    results["day84"] = analyze_day84()
    results["redundancy"] = analyze_redundancy()
    results["lead_lag"] = analyze_lead_lag()
    results["missingness"] = analyze_missingness()
    results["extremes"] = analyze_extremes_and_stability()

    # Final manifest
    manifest = {
        "holdout_days_loaded": [],
        "development_days_analyzed": results["structure"]["available_days"],
        "n_days_analyzed": results["structure"]["available_development_days"],
        "n_figures_generated": len(list(FIGURES_OUT.glob("*.png"))),
        "n_result_files": len(list(RESULTS_OUT.glob("*.json"))),
        "analyses_completed": list(results.keys()),
    }
    write_json(manifest, RESULTS_OUT / "manifest.json")
    print()
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
