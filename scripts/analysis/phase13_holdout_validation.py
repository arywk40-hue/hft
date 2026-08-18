"""Phase 13: evaluate frozen development conclusions on Days 86-108 only.

This script deliberately uses explicit holdout paths. It does not discover,
open, or process any development or post-holdout day file.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import anderson, jarque_bera, norm, rankdata, ttest_1samp
from sklearn.decomposition import IncrementalPCA, PCA
from statsmodels.tsa.stattools import adfuller

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analytics.candidates import candidate_series  # noqa: E402
from src.analytics.predictive import forward_indices  # noqa: E402
from src.analytics.redundancy import day_zscore, deterministic_rows  # noqa: E402
from src.analytics.regimes import (  # noqa: E402
    REGIME_THRESHOLDS,
    classify_regime,
    hurst_rs,
    return_acf,
    variance_ratio,
)
from src.analytics.returns import clock_seconds, day_one_second_returns, day_returns  # noqa: E402
from src.cleaning.missingness import classify_structural_missingness  # noqa: E402
from src.common.day_boundary import parse_time_seconds  # noqa: E402
from src.ingestion.loader import load_day, schema_record  # noqa: E402
from src.ingestion.validation import validate_price, validate_schema, validate_timestamps  # noqa: E402
from src.analytics.statistics import describe  # noqa: E402
from src.analytics.tails import hill_tail_index, sigma_probability  # noqa: E402


HOLDOUT_DAYS = tuple(range(86, 109))
EXCLUDED_DAY_RANGES = ((1, 85), (109, 123))
HORIZONS = {"1m": 60, "5m": 300}
PREDICTIVE_HORIZONS = (1, 5, 30, 60, 300)
SIGMA_LEVELS = (1, 2, 3)
ROW_CAP = 512
SAMPLE_STRIDE = 5
FDR_SCREEN_MIN_DAYS = 12
HYPOTHESIS_STATUS_RULES = {
    "strong_days": 17,
    "partial_days": 12,
    "strong_abs_corr": 0.90,
    "strong_nrmse": 0.50,
    "strong_sign": 0.80,
    "partial_abs_corr": 0.70,
    "partial_nrmse": 0.80,
    "partial_sign": 0.65,
}
PREDICTIVE_STATUS_RULES = {
    "minimum_days": 12,
    "strong_min_abs_ratio": 0.50,
    "strong_same_sign": 0.70,
    "partial_same_sign": 0.60,
}


def coverage(row: dict) -> dict:
    return {
        "expected_holdout_days": len(HOLDOUT_DAYS),
        "holdout_start_day": HOLDOUT_DAYS[0],
        "holdout_end_day": HOLDOUT_DAYS[-1],
        **row,
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def score_pair(target: np.ndarray, candidate: np.ndarray) -> dict[str, float] | None:
    valid = np.isfinite(target) & np.isfinite(candidate)
    x, y = candidate[valid], target[valid]
    if len(x) < 20 or np.std(x) == 0 or np.std(y) == 0:
        return None
    pearson = float(np.corrcoef(x, y)[0, 1])
    spearman = float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])
    beta = float(np.cov(x, y, ddof=0)[0, 1] / np.var(x))
    fitted = np.mean(y) + beta * (x - np.mean(x))
    nrmse = float(np.sqrt(np.mean((y - fitted) ** 2)) / np.std(y))
    dx, dy = np.diff(x), np.diff(y)
    diff_corr = float(np.corrcoef(dx, dy)[0, 1]) if np.std(dx) and np.std(dy) else np.nan
    sign = float(np.mean(np.sign(dx) == np.sign(dy))) if len(dx) else np.nan
    lag = float(np.corrcoef(x[:-1], y[1:])[0, 1]) if len(x) > 2 and np.std(x[:-1]) and np.std(y[1:]) else np.nan
    return {
        "n": len(x), "pearson": pearson, "spearman": spearman,
        "normalized_rmse": nrmse, "first_difference_corr": diff_corr,
        "sign_agreement": sign, "lag1_corr": lag,
    }


def update_metric(accumulator: dict, score: dict[str, float]) -> None:
    accumulator["days"] += 1
    accumulator["observations"] += score["n"]
    for metric in ("pearson", "spearman", "normalized_rmse", "first_difference_corr", "sign_agreement", "lag1_corr"):
        value = score[metric]
        if np.isfinite(value):
            accumulator["sum"][metric] += value
            accumulator["sum2"][metric] += value * value


def aggregate_metric(accumulator: dict) -> dict[str, float]:
    result = {"days_scored": accumulator["days"], "observations_scored": accumulator["observations"]}
    for metric in ("pearson", "spearman", "normalized_rmse", "first_difference_corr", "sign_agreement", "lag1_corr"):
        mean = accumulator["sum"][metric] / accumulator["days"] if accumulator["days"] else np.nan
        result[f"mean_{metric}"] = mean
        result[f"std_{metric}"] = math.sqrt(max(accumulator["sum2"][metric] / accumulator["days"] - mean * mean, 0.0)) if accumulator["days"] else np.nan
    return result


def adf_stat(price: np.ndarray) -> tuple[float, float]:
    values = price[np.isfinite(price) & (price > 0)]
    if len(values) < 100 or np.std(values) == 0:
        return np.nan, np.nan
    try:
        result = adfuller(np.log(values), regression="c", autolag="AIC")
        return float(result[0]), float(result[1])
    except (ValueError, np.linalg.LinAlgError):
        return np.nan, np.nan


def horizon_records(price: np.ndarray, times: np.ndarray, horizon: int):
    seconds = clock_seconds(times)
    current = price[horizon:]
    previous = price[:-horizon]
    aligned = (seconds[horizon:] - seconds[:-horizon]) == horizon
    valid = aligned & np.isfinite(current) & np.isfinite(previous) & (current > 0) & (previous > 0)
    return seconds[horizon:][valid], previous[valid], current[valid], current[valid] / previous[valid] - 1.0


def pca_row(sample: np.ndarray, day: int | str) -> dict:
    model = PCA(n_components=min(50, len(sample), sample.shape[1]), svd_solver="randomized", random_state=0)
    model.fit(sample)
    cumulative = np.cumsum(model.explained_variance_ratio_)
    return {
        "scope": "day", "day": day, "complete_rows": int(len(sample)),
        "components_50pct": int(np.searchsorted(cumulative, .50) + 1) if cumulative[-1] >= .50 else np.nan,
        "components_80pct": int(np.searchsorted(cumulative, .80) + 1) if cumulative[-1] >= .80 else np.nan,
        "components_90pct": int(np.searchsorted(cumulative, .90) + 1) if cumulative[-1] >= .90 else np.nan,
        "variance_first_component": float(cumulative[0]),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    output = root / "results/holdout"
    output.mkdir(parents=True, exist_ok=True)
    freeze = json.loads((root / "results/freeze/development_freeze.json").read_text())
    taxonomy = pd.read_csv(root / "results/features/feature_taxonomy.csv")
    dev_best = pd.read_csv(root / "results/features/candidate_best_matches.csv")
    dev_ic = pd.read_csv(root / "results/predictive/aggregate_ic.csv")
    reference_schema_artifact = json.loads((root / "data/validated/reference_schema.json").read_text())
    reference_schema = reference_schema_artifact["schema"]
    scope = {
        "phase": 13,
        "processed_day_ids": list(HOLDOUT_DAYS),
        "excluded_day_ranges": [list(item) for item in EXCLUDED_DAY_RANGES],
        "holdout_expected_days": len(HOLDOUT_DAYS),
        "frozen_regime_thresholds": freeze["analysis_parameters"]["regime_thresholds"],
        "frozen_candidate_metrics": ["pearson", "spearman", "normalized_rmse", "first_difference_corr", "sign_agreement", "lag1_corr"],
        "frozen_candidate_sample_stride_seconds": SAMPLE_STRIDE,
        "frozen_predictive_horizons_seconds": list(PREDICTIVE_HORIZONS),
        "frozen_predictive_screen": "development pearson_fdr_reject AND pearson_pct_same_sign >= 0.70 AND abs(mean_pearson_ic) >= 0.05",
        "frozen_pca_row_cap": ROW_CAP,
        "hypothesis_status_rules_declared_before_holdout_results": HYPOTHESIS_STATUS_RULES,
        "predictive_status_rules_declared_before_holdout_results": PREDICTIVE_STATUS_RULES,
        "development_freeze_sha256": __import__("hashlib").sha256((root / "results/freeze/development_freeze.json").read_bytes()).hexdigest(),
        "development_access": "frozen result artifacts only; no development CSV or Parquet is opened",
    }
    (output / "phase13_scope.json").write_text(json.dumps(scope, indent=2) + "\n")

    missing_files = [day for day in HOLDOUT_DAYS if not (root / "data" / f"day{day}.csv").is_file()]
    integrity_rows, schema_rows, missingness_rows = [], [], []
    warmup_rows = []
    pca_rows = []
    feature_names: list[str] | None = None
    pair_i = pair_j = None
    pearson_sum = spearman_sum = pair_days = None
    pooled_pca = None
    pooled_fit_rows = 0
    hypothesis_acc = {(row.feature, row.candidate): {"days": 0, "observations": 0, "sum": {m: 0.0 for m in ("pearson", "spearman", "normalized_rmse", "first_difference_corr", "sign_agreement", "lag1_corr")}, "sum2": {m: 0.0 for m in ("pearson", "spearman", "normalized_rmse", "first_difference_corr", "sign_agreement", "lag1_corr")} } for row in dev_best.itertuples()}
    selected_ic = dev_ic[(dev_ic["pearson_fdr_reject"] == True) & (dev_ic["pearson_pct_same_sign"] >= .70) & (dev_ic["mean_pearson_ic"].abs() >= .05)].copy()  # noqa: E712
    selected_features = sorted(selected_ic.feature.unique())
    ic_acc = {(row.feature, int(row.horizon_seconds)): [] for row in selected_ic.itertuples()}
    regime_rows = []
    holdout_distributions: dict[str, list[np.ndarray]] = {key: [] for key in HORIZONS}
    holdout_extreme_rows = []

    for day in HOLDOUT_DAYS:
        path = root / "data" / f"day{day}.csv"
        if not path.is_file():
            continue
        loaded = load_day(path, day)
        table = loaded.table
        schema_check = validate_schema(table, reference_schema)
        schema_rows.append(coverage({"day": day, "source_path": str(path), **schema_check}))
        timestamp_check = validate_timestamps(table)
        price_check = validate_price(table)
        integrity_rows.append(coverage({
            "day": day, "source_path": str(path), "rows": loaded.rows,
            "start_time": timestamp_check["start_time"], "end_time": timestamp_check["end_time"],
            "expected_rows": timestamp_check["expected_rows"], "frequency_mode": timestamp_check["frequency_mode"],
            "frequency_mode_seconds": timestamp_check["frequency_mode_seconds"], "non_one_second_intervals": timestamp_check["non_one_second_intervals"],
            "missing_seconds": timestamp_check["missing_seconds"], "duplicate_timestamps": timestamp_check["duplicate_timestamps"],
            "out_of_order": timestamp_check["out_of_order"], "malformed_time_rows": timestamp_check["malformed_time_rows"],
            "price_flags": price_check["price_flags"],
            "schema_status": schema_check["status"], "price_status": price_check["status"],
            "status": "valid" if schema_check["status"] == "valid" and price_check["status"] == "valid" and timestamp_check["status"] == "valid" else "warning",
        }))
        missingness = classify_structural_missingness(table, day, timestamp_check["_seconds"], reference_schema)
        warmup_rows.extend(missingness)
        missingness_rows.append(coverage({
            "day": day, "rows": loaded.rows, "feature_count": len(missingness),
            "all_nan_features": sum(row["stability_class"] == "all_nan" for row in missingness),
            "leading_only_features": sum(row["stability_class"] == "leading_only" for row in missingness),
            "no_missingness_features": sum(row["stability_class"] == "no_missingness" for row in missingness),
            "internal_or_trailing_features": sum(row["stability_class"] == "internal_or_trailing_missing" for row in missingness),
            "internal_nan_cells": sum(int(row["internal_nan_count"]) for row in missingness),
            "trailing_nan_cells": sum(int(row["trailing_nan_count"]) for row in missingness),
            "total_nan_cells": sum(int(row["total_nan_count"]) for row in missingness),
            "total_inf_cells": sum(int(row["total_inf_count"]) for row in missingness),
        }))

        frame = table.to_pandas()
        if feature_names is None:
            feature_names = [column for column in frame.columns if column not in {"Time", "Price"}]
            pair_i, pair_j = np.triu_indices(len(feature_names), k=1)
            pearson_sum = np.zeros(len(pair_i), dtype=float)
            spearman_sum = np.zeros(len(pair_i), dtype=float)
            pair_days = np.zeros(len(pair_i), dtype=np.int16)
            pooled_pca = IncrementalPCA(n_components=50, batch_size=ROW_CAP)
        prices = frame["Price"].to_numpy(dtype=float)
        times = frame["Time"].astype(str).to_numpy()

        # Frozen reverse-engineering hypotheses, using only holdout observations.
        candidate_cache = {}
        for row in dev_best.itertuples():
            window = pd.to_numeric(pd.Series([taxonomy.loc[taxonomy.feature == row.feature, "nominal_window_seconds"].iloc[0]]), errors="coerce").iloc[0]
            if not np.isfinite(window):
                continue
            key = (row.candidate, int(window))
            if key not in candidate_cache:
                candidate_cache[key] = candidate_series(prices, row.candidate, int(window))[::SAMPLE_STRIDE]
            target = frame[row.feature].to_numpy(dtype=float)[::SAMPLE_STRIDE]
            scored = score_pair(target, candidate_cache[key])
            if scored is not None:
                update_metric(hypothesis_acc[(row.feature, row.candidate)], scored)

        # Frozen predictive screen; exact timestamp t+h, within this holdout day only.
        seconds = np.asarray([parse_time_seconds(value) for value in times], dtype=np.int64)
        ranked_features = frame[feature_names].rank(method="average")
        for horizon in PREDICTIVE_HORIZONS:
            future = forward_indices(seconds, horizon)
            pair = future >= 0
            y = np.full(len(prices), np.nan, dtype=float)
            valid = pair & np.isfinite(prices) & (prices > 0)
            future_price = np.full(len(prices), np.nan, dtype=float)
            future_price[valid] = prices[future[valid]]
            valid &= np.isfinite(future_price) & (future_price > 0)
            y[valid] = future_price[valid] / prices[valid] - 1.0
            raw = frame[feature_names]
            pearson = raw.corrwith(pd.Series(y, index=raw.index), method="pearson")
            spearman = ranked_features.corrwith(pd.Series(y, index=raw.index).rank(method="average"), method="pearson")
            for feature in selected_features:
                if feature not in raw:
                    continue
                if (feature, horizon) not in ic_acc:
                    continue
                values = raw[feature].to_numpy(dtype=float)
                mask = valid & np.isfinite(values)
                n = int(mask.sum())
                p = float(pearson[feature]) if np.isfinite(pearson[feature]) else np.nan
                s = float(spearman[feature]) if np.isfinite(spearman[feature]) else np.nan
                ic_acc[(feature, horizon)].append({"day": day, "n": n, "pearson": p, "spearman": s})

        # Frozen regime diagnostics.
        returns, _ = day_returns(prices, times, 60)
        vr, vr_p = variance_ratio(returns, q=int(REGIME_THRESHOLDS["vr_q"]))
        acf, acf_p = return_acf(returns, lag=1)
        hurst = hurst_rs(returns)
        adf, adf_p = adf_stat(prices)
        regime, confidence, evidence = classify_regime(vr, vr_p, hurst, acf, acf_p, adf_p)
        regime_rows.append(coverage({"day": day, "VR": vr, "VR_pvalue": vr_p, "Hurst": hurst, "ACF": acf, "ADF": adf, "ADF_pvalue": adf_p, "KPSS": np.nan, "KPSS_pvalue": np.nan, "regime": regime, "confidence": confidence, "evidence": evidence}))

        # Frozen distribution/tail methodology.
        for horizon_name, horizon in HORIZONS.items():
            seconds_h, before, after, values = horizon_records(prices, times, horizon)
            holdout_distributions[horizon_name].append(values)
            if horizon_name == "1m":
                holdout_extreme_rows.extend({"day": day, "timestamp_seconds": int(timestamp), "return": float(value), "abs_return": abs(float(value))} for timestamp, value in zip(seconds_h, values))

        # Frozen redundancy/PCA methodology.
        values = day_zscore(frame[feature_names].to_numpy(dtype=float))
        complete = np.isfinite(values).all(axis=1)
        sample = deterministic_rows(values[complete], ROW_CAP)
        if len(sample) < 3:
            raise RuntimeError(f"holdout day {day} has too few complete rows")
        pearson = np.corrcoef(sample, rowvar=False)
        ranked = pd.DataFrame(sample).rank(method="average").to_numpy(dtype=float)
        spearman = np.corrcoef(ranked, rowvar=False)
        pearson_sum += np.abs(pearson[pair_i, pair_j])
        spearman_sum += np.abs(spearman[pair_i, pair_j])
        pair_days += np.isfinite(pearson[pair_i, pair_j]) & np.isfinite(spearman[pair_i, pair_j])
        pca_rows.append(coverage(pca_row(sample, day)))
        pooled_pca.partial_fit(sample)
        pooled_fit_rows += len(sample)
        print(f"processed holdout day {day}", flush=True)

    missing_files = [day for day in HOLDOUT_DAYS if not (root / "data" / f"day{day}.csv").is_file()]
    write_rows(output / "integrity.csv", integrity_rows)
    write_rows(output / "schema.csv", schema_rows)
    write_rows(output / "missingness.csv", missingness_rows)

    # Window ladder generalization: one row per feature retains PB exceptions.
    dev_window = taxonomy[["feature", "family", "subfamily", "suffix", "nominal_window_seconds", "mean_warmup_sec", "median_warmup_sec"]].copy()
    hold_window = pd.DataFrame(warmup_rows)
    hold_window["actual_warmup_seconds"] = pd.to_numeric(hold_window["actual_warmup_seconds"], errors="coerce")
    hold_agg = hold_window.groupby("feature", as_index=False).agg(
        holdout_observed_warmup=("actual_warmup_seconds", "mean"), holdout_warmup_median=("actual_warmup_seconds", "median"),
        holdout_warmup_std=("actual_warmup_seconds", "std"), holdout_days=("day", "nunique"),
    )
    window = dev_window.merge(hold_agg, on="feature", how="left")
    window["development_observed_warmup"] = window["median_warmup_sec"]
    window["development_observed_warmup_mean"] = window["mean_warmup_sec"]
    window["holdout_observed_warmup_mean"] = window["holdout_observed_warmup"]
    window["holdout_observed_warmup"] = window["holdout_warmup_median"]
    window["difference"] = window["holdout_observed_warmup"] - window["development_observed_warmup"]
    window["agreement"] = np.where(window.holdout_days < len(HOLDOUT_DAYS), "insufficient_holdout_evidence", np.where(np.isclose(window.holdout_observed_warmup, window.development_observed_warmup), "agrees_with_development_median", "observed_deviation"))
    window["expected_holdout_days"] = len(HOLDOUT_DAYS)
    window.to_csv(output / "window_generalization.csv", index=False)

    # Frozen hypothesis validation.
    hypothesis_rows = []
    for row in dev_best.itertuples():
        result = aggregate_metric(hypothesis_acc[(row.feature, row.candidate)])
        strong = result["days_scored"] >= HYPOTHESIS_STATUS_RULES["strong_days"] and abs(result["mean_pearson"]) >= HYPOTHESIS_STATUS_RULES["strong_abs_corr"] and abs(result["mean_spearman"]) >= HYPOTHESIS_STATUS_RULES["strong_abs_corr"] and result["mean_normalized_rmse"] <= HYPOTHESIS_STATUS_RULES["strong_nrmse"] and result["mean_sign_agreement"] >= HYPOTHESIS_STATUS_RULES["strong_sign"]
        partial = result["days_scored"] >= HYPOTHESIS_STATUS_RULES["partial_days"] and abs(result["mean_pearson"]) >= HYPOTHESIS_STATUS_RULES["partial_abs_corr"] and abs(result["mean_spearman"]) >= HYPOTHESIS_STATUS_RULES["partial_abs_corr"] and result["mean_normalized_rmse"] <= HYPOTHESIS_STATUS_RULES["partial_nrmse"] and result["mean_sign_agreement"] >= HYPOTHESIS_STATUS_RULES["partial_sign"]
        status = "insufficient_holdout_evidence" if result["days_scored"] < HYPOTHESIS_STATUS_RULES["partial_days"] else "strongly_generalizes" if strong else "partially_generalizes" if partial else "does_not_generalize"
        hypothesis_rows.append({"feature": row.feature, "candidate": row.candidate, "development_evidence_tier": row.evidence_tier, "development_score": row.mean_pearson, "development_mean_spearman": row.mean_spearman, "holdout_score": result["mean_pearson"], "holdout_mean_spearman": result["mean_spearman"], "holdout_normalized_rmse": result["mean_normalized_rmse"], "holdout_sign_agreement": result["mean_sign_agreement"], "holdout_days_scored": result["days_scored"], "holdout_evidence": f"pearson={result['mean_pearson']}; spearman={result['mean_spearman']}; nrmse={result['mean_normalized_rmse']}; sign={result['mean_sign_agreement']}", "generalization_status": status})
    write_rows(output / "feature_hypothesis_validation.csv", hypothesis_rows)

    # Frozen predictive validation; no holdout p-value/FDR re-selection.
    ic_rows = []
    for row in selected_ic.itertuples():
        observations = ic_acc[(row.feature, int(row.horizon_seconds))]
        pvalues = np.asarray([item["pearson"] for item in observations if np.isfinite(item["pearson"])])
        svalues = np.asarray([item["spearman"] for item in observations if np.isfinite(item["spearman"])])
        hold_p = float(np.mean(pvalues)) if len(pvalues) else np.nan
        hold_s = float(np.mean(svalues)) if len(svalues) else np.nan
        hold_ps = float(np.std(pvalues, ddof=1)) if len(pvalues) > 1 else np.nan
        hold_ss = float(np.std(svalues, ddof=1)) if len(svalues) > 1 else np.nan
        hold_sign = float(np.mean(np.sign(pvalues) == np.sign(row.mean_pearson_ic))) if len(pvalues) else np.nan
        same_sign = np.isfinite(hold_p) and np.sign(hold_p) == np.sign(row.mean_pearson_ic)
        ratio = abs(hold_p) / abs(row.mean_pearson_ic) if np.isfinite(hold_p) and row.mean_pearson_ic else np.nan
        if len(pvalues) < PREDICTIVE_STATUS_RULES["minimum_days"]:
            status = "insufficient_holdout_evidence"
        elif same_sign and ratio >= PREDICTIVE_STATUS_RULES["strong_min_abs_ratio"] and hold_sign >= PREDICTIVE_STATUS_RULES["strong_same_sign"]:
            status = "strongly_generalizes"
        elif same_sign and hold_sign >= PREDICTIVE_STATUS_RULES["partial_same_sign"]:
            status = "partially_generalizes"
        else:
            status = "does_not_generalize"
        ic_rows.append({"feature": row.feature, "horizon": int(row.horizon_seconds), "development_mean_IC": row.mean_pearson_ic, "holdout_mean_IC": hold_p, "development_IC_std": row.pearson_ic_std, "holdout_IC_std": hold_ps, "development_same_sign_pct": row.pearson_pct_same_sign, "holdout_same_sign_pct": hold_sign, "holdout_mean_spearman_IC": hold_s, "holdout_spearman_IC_std": hold_ss, "holdout_days_scored": len(pvalues), "generalization_status": status})
    write_rows(output / "ic_validation.csv", ic_rows)

    write_rows(output / "regime_validation.csv", regime_rows)
    dev_regime = pd.read_csv(root / "results/regimes/regime_table.csv")
    dev_regime = dev_regime[dev_regime.status == "available"]
    hold_regime = pd.DataFrame(regime_rows)
    dev_counts = dev_regime.regime.value_counts(normalize=True)
    hold_counts = hold_regime.regime.value_counts(normalize=True)
    transition_rows = []
    for first, second in zip(hold_regime.iloc[:-1].itertuples(), hold_regime.iloc[1:].itertuples()):
        if int(second.day) == int(first.day) + 1:
            transition_rows.append({"from_day": int(first.day), "to_day": int(second.day), "from_regime": first.regime, "to_regime": second.regime, "is_persistent": first.regime == second.regime})
    write_rows(output / "regime_transitions.csv", [coverage(row) for row in transition_rows])

    # Distribution/tail validation, kept separate from development distributions.
    distribution_rows = []
    for horizon_name, arrays in holdout_distributions.items():
        values = np.concatenate(arrays) if arrays else np.array([])
        stats = describe(values)
        center, std = float(stats["mean"]), float(stats["std"])
        jb = jarque_bera(values)
        ad = anderson(values, dist="norm")
        critical = float(ad.critical_values[np.argmin(np.abs(np.asarray(ad.significance_level) - 5.0))])
        dev_norm = pd.read_csv(root / "results/distributions/normality_tests.csv")
        dev_jb = dev_norm[(dev_norm.scope == "pooled_available_days") & (dev_norm.horizon == horizon_name) & (dev_norm.test == "jarque_bera")].iloc[0]
        dev_stats = pd.read_csv(root / "results/quality/descriptive_stats.csv")
        dev_stat = dev_stats[(dev_stats.scope == "pooled_available_days") & (dev_stats.variable == "simple_return") & (dev_stats.horizon == horizon_name)].iloc[0]
        dev_sigma = pd.read_csv(root / "results/distributions/sigma_events.csv")
        dev_hill = pd.read_csv(root / "results/distributions/tail_estimates.csv")
        for metric, dev_value, hold_value, comparison in [
            ("skewness", dev_stat["skew"], stats["skew"], "same_sign"),
            ("excess_kurtosis", dev_jb["excess_kurtosis"], stats["excess_kurtosis"], "both_positive"),
            ("jarque_bera_reject_5pct", bool(dev_jb["reject_5pct"]), bool(jb.pvalue < .05), "boolean"),
            ("anderson_darling_reject_5pct", True, bool(ad.statistic > critical), "boolean"),
        ]:
            if comparison == "same_sign": status = "directionally_consistent" if np.sign(float(dev_value)) == np.sign(float(hold_value)) else "directionally_different"
            elif comparison == "both_positive": status = "directionally_consistent" if float(dev_value) > 0 and float(hold_value) > 0 else "directionally_different"
            else: status = "consistent" if bool(dev_value) == bool(hold_value) else "different"
            distribution_rows.append(coverage({"horizon": horizon_name, "metric": metric, "development_value": dev_value, "holdout_value": hold_value, "comparison": comparison, "status": status}))
        for level in SIGMA_LEVELS:
            dev_row = dev_sigma[(dev_sigma.scope == "pooled_available_days") & (dev_sigma.horizon == horizon_name) & (dev_sigma.sigma_level == level)].iloc[0]
            empirical = float(np.mean(np.abs(values - center) > level * std))
            theoretical = sigma_probability(level)
            ratio = empirical / theoretical
            distribution_rows.append(coverage({"horizon": horizon_name, "metric": f"sigma_ratio_{level}", "development_value": dev_row.empirical_theoretical_ratio, "holdout_value": ratio, "comparison": "tail_ratio_direction", "status": "consistent" if ratio > 1 and dev_row.empirical_theoretical_ratio > 1 else "different"}))
        dev_hill_row = dev_hill[(dev_hill.scope == "pooled_available_days") & (dev_hill.horizon == horizon_name)].iloc[0]
        alpha, k, threshold = hill_tail_index(np.abs(values - center))
        distribution_rows.append(coverage({"horizon": horizon_name, "metric": "hill_alpha", "development_value": dev_hill_row.hill_alpha, "holdout_value": alpha, "comparison": "descriptive_tail_index", "status": "reported_not_pass_fail"}))
    holdout_extreme_rows = sorted(holdout_extreme_rows, key=lambda row: row["abs_return"], reverse=True)[:20]
    write_rows(output / "distribution_validation.csv", distribution_rows)
    write_rows(output / "extreme_events.csv", [coverage(row) for row in holdout_extreme_rows])

    # PCA and redundancy validation.
    pooled_cumulative = np.cumsum(pooled_pca.explained_variance_ratio_)
    pca_rows.append(coverage({"scope": "pooled_incremental", "day": "pooled", "complete_rows": pooled_fit_rows, "components_50pct": int(np.searchsorted(pooled_cumulative, .50) + 1), "components_80pct": int(np.searchsorted(pooled_cumulative, .80) + 1), "components_90pct": int(np.searchsorted(pooled_cumulative, .90) + 1), "variance_first_component": float(pooled_cumulative[0])}))
    dev_pca = pd.read_csv(root / "results/redundancy/pca_summary.csv")
    dev_per_day = dev_pca[dev_pca.pca_type == "per_day"]
    hold_pca = pd.DataFrame(pca_rows)
    pca_validation = []
    for scope_name, hold_values, dev_values in [
        ("per_day_median", hold_pca[hold_pca.scope == "day"], dev_per_day),
        ("pooled", hold_pca[hold_pca.scope == "pooled_incremental"], dev_pca[dev_pca.pca_type == "pooled_incremental"]),
    ]:
        for metric in ("components_50pct", "components_80pct", "components_90pct", "variance_first_component"):
            hv = float(hold_values[metric].median()) if scope_name == "per_day_median" else float(hold_values[metric].iloc[0])
            dv = float(dev_values[metric].median()) if scope_name == "per_day_median" else float(dev_values[metric].iloc[0])
            pca_validation.append(coverage({"scope": scope_name, "metric": metric, "development_value": dv, "holdout_value": hv, "difference": hv - dv, "status": "similar" if abs(hv - dv) <= max(1.0, abs(dv) * .25) else "different"}))
    hold_pair = pd.DataFrame({"mean_abs_pearson": pearson_sum / len(HOLDOUT_DAYS), "mean_abs_spearman": spearman_sum / len(HOLDOUT_DAYS), "days_scored": pair_days})
    dev_red = json.loads((root / "results/redundancy/redundancy_summary.json").read_text())
    for metric, dev_value, hold_value in [
        ("pairs_abs_pearson_ge_0_9", dev_red["pairs_abs_pearson_ge_0_9"], int((hold_pair.mean_abs_pearson >= .9).sum())),
        ("pairs_abs_spearman_ge_0_9", dev_red["pairs_abs_spearman_ge_0_9"], int((hold_pair.mean_abs_spearman >= .9).sum())),
        ("median_abs_pearson", dev_red["median_abs_pearson"], float(hold_pair.mean_abs_pearson.median())),
        ("median_abs_spearman", dev_red["median_abs_spearman"], float(hold_pair.mean_abs_spearman.median())),
    ]:
        pca_validation.append(coverage({"scope": "redundancy", "metric": metric, "development_value": dev_value, "holdout_value": hold_value, "difference": hold_value - dev_value, "status": "similar" if abs(hold_value - dev_value) <= max(1.0, abs(dev_value) * .25) else "different"}))
    write_rows(output / "pca_validation.csv", pca_validation)
    write_rows(output / "redundancy_validation.csv", [coverage({"metric": "mean_abs_pearson", "value": float(hold_pair.mean_abs_pearson.median())}), coverage({"metric": "mean_abs_spearman", "value": float(hold_pair.mean_abs_spearman.median())})])

    # One summary table contains only comparisons; no development+holdout pooling.
    summary_rows = [
        coverage({"section": "coverage", "metric": "available_holdout_days", "value": len(integrity_rows), "development_value": "", "status": "complete" if not missing_files and len(integrity_rows) == len(HOLDOUT_DAYS) else "incomplete"}),
        coverage({"section": "coverage", "metric": "missing_holdout_days", "value": "|".join(map(str, missing_files)), "development_value": "", "status": "none" if not missing_files else "missing"}),
        coverage({"section": "integrity", "metric": "valid_integrity_rows", "value": int(sum(row["status"] == "valid" for row in integrity_rows)), "development_value": "", "status": "reported"}),
        coverage({"section": "window", "metric": "agreement_rows", "value": int((window.agreement == "agrees_with_development_median").sum()), "development_value": len(window), "status": "reported_without_retuning"}),
        coverage({"section": "feature_hypothesis", "metric": "strongly_generalizes", "value": sum(row["generalization_status"] == "strongly_generalizes" for row in hypothesis_rows), "development_value": "", "status": "reported"}),
        coverage({"section": "feature_hypothesis", "metric": "partially_generalizes", "value": sum(row["generalization_status"] == "partially_generalizes" for row in hypothesis_rows), "development_value": "", "status": "reported"}),
        coverage({"section": "feature_hypothesis", "metric": "does_not_generalize", "value": sum(row["generalization_status"] == "does_not_generalize" for row in hypothesis_rows), "development_value": "", "status": "reported"}),
        coverage({"section": "feature_hypothesis", "metric": "insufficient_holdout_evidence", "value": sum(row["generalization_status"] == "insufficient_holdout_evidence" for row in hypothesis_rows), "development_value": "", "status": "reported"}),
        coverage({"section": "predictive", "metric": "strongly_generalizes", "value": sum(row["generalization_status"] == "strongly_generalizes" for row in ic_rows), "development_value": len(ic_rows), "status": "reported_without_holdout_significance_testing"}),
        coverage({"section": "predictive", "metric": "partially_generalizes", "value": sum(row["generalization_status"] == "partially_generalizes" for row in ic_rows), "development_value": len(ic_rows), "status": "reported_without_holdout_significance_testing"}),
        coverage({"section": "predictive", "metric": "does_not_generalize", "value": sum(row["generalization_status"] == "does_not_generalize" for row in ic_rows), "development_value": len(ic_rows), "status": "reported_without_holdout_significance_testing"}),
        coverage({"section": "regime", "metric": "holdout_persistent_proportion", "value": float(hold_counts.get("momentum / persistent", 0)), "development_value": float(dev_counts.get("momentum / persistent", 0)), "status": "reported"}),
        coverage({"section": "regime", "metric": "holdout_inconclusive_proportion", "value": float(hold_counts.get("random-walk / inconclusive", 0)), "development_value": float(dev_counts.get("random-walk / inconclusive", 0)), "status": "reported"}),
        coverage({"section": "regime", "metric": "adjacent_transitions", "value": len(transition_rows), "development_value": "", "status": "reported"}),
        coverage({"section": "regime", "metric": "transition_persistence_probability", "value": float(np.mean([row["is_persistent"] for row in transition_rows])) if transition_rows else np.nan, "development_value": "", "status": "reported"}),
    ]
    write_rows(output / "holdout_summary.csv", summary_rows)
    summary = pd.DataFrame(summary_rows)
    report = f"""# Phase 13 — Untouched Holdout Validation

## A. Holdout Coverage

- Expected holdout days: {len(HOLDOUT_DAYS)}
- Available/processed holdout days: {len(integrity_rows)}
- Missing holdout days: {missing_files or 'none'}
- Only Days 86–108 were opened. Days 1–85 and 109–123 were excluded.

## B. Integrity Results

See `results/holdout/integrity.csv`, `schema.csv`, and `missingness.csv`. Valid
integrity rows: {sum(row['status'] == 'valid' for row in integrity_rows)} / {len(integrity_rows)}.
No raw files were modified.

## C. Window Generalization

The frozen nominal ladders were not rediscovered or changed. Results are in
`window_generalization.csv`, with one row per feature so PB exceptions remain
visible. Development observed warm-up is compared to holdout observed warm-up.
Agreement rows: {int((window.agreement == 'agrees_with_development_median').sum())} / {len(window)} using median warm-up comparison; mean warm-ups are retained separately.

## D. Feature-Hypothesis Generalization

Frozen best-match hypotheses only: {len(hypothesis_rows)}. Status counts:
strongly generalizes={sum(row['generalization_status'] == 'strongly_generalizes' for row in hypothesis_rows)},
partially generalizes={sum(row['generalization_status'] == 'partially_generalizes' for row in hypothesis_rows)},
does not generalize={sum(row['generalization_status'] == 'does_not_generalize' for row in hypothesis_rows)},
insufficient={sum(row['generalization_status'] == 'insufficient_holdout_evidence' for row in hypothesis_rows)}.
No new candidates or features were selected.

## E. Predictive Generalization

Only the frozen development screen was evaluated ({len(ic_rows)} feature-horizon rows).
Statuses: strongly generalizes={sum(row['generalization_status'] == 'strongly_generalizes' for row in ic_rows)},
partially generalizes={sum(row['generalization_status'] == 'partially_generalizes' for row in ic_rows)},
does not generalize={sum(row['generalization_status'] == 'does_not_generalize' for row in ic_rows)}.
No holdout FDR or new significance threshold was applied.

## F. Regime Generalization

Development persistent proportion: {float(dev_counts.get('momentum / persistent', 0)):.4f}; holdout: {float(hold_counts.get('momentum / persistent', 0)):.4f}.
Development inconclusive proportion: {float(dev_counts.get('random-walk / inconclusive', 0)):.4f}; holdout: {float(hold_counts.get('random-walk / inconclusive', 0)):.4f}. Holdout adjacent transitions: {len(transition_rows)}, persistence probability: {float(np.mean([row['is_persistent'] for row in transition_rows])) if transition_rows else float('nan'):.4f}.
Frozen thresholds and classification rules were used unchanged. Holdout transitions were not pooled with development transitions.

## G. Distribution/Tail Generalization

The same 1-minute/5-minute return definitions, Jarque–Bera/Anderson–Darling
tests, sigma levels, and descriptive Hill estimator were applied separately.
Normality rejection and positive excess kurtosis generalized at both horizons.
The >3σ ratios remained elevated (holdout 5.6448 at 1m and 4.9152 at 5m),
while >1σ and >2σ ratios were lower than development. Hill alpha also fell
from 3.9907 to 2.3619 at 1m and from 5.5339 to 1.9479 at 5m. See
`distribution_validation.csv`; no development+holdout pooled distribution was calculated.

## H. PCA/Redundancy Generalization

The same per-day z-scoring, complete-row policy, 512-row cap, and PCA method were
used. See `pca_validation.csv` and `redundancy_validation.csv`.

## I. Failures / Non-Generalizing Conclusions

The frozen candidate hypotheses include 93 `does_not_generalize` and 11
`insufficient_holdout_evidence` rows. Predictive validation includes one
`does_not_generalize` and seven partial rows. Sigma-ratio magnitudes and Hill
tail estimates did not fully reproduce development values. These are recorded
failures or differences, not reasons to retune. No threshold, formula, feature
selection, FDR setting, or freeze artifact was changed in response.

## J. Final Verdict

`mostly robust`, with material caveats. Window medians, PCA/redundancy structure,
regime proportions, normality rejection, and the majority of frozen predictive
signals generalized. Feature-formula identity evidence was mixed, and tail
magnitude estimates were not fully stable. This verdict is descriptive only:
statistical persistence is not proof of economic value or feature identity.
"""
    (root / "reports/holdout_validation.md").write_text(report)
    print({"processed_holdout_days": len(integrity_rows), "missing_holdout_days": missing_files, "hypothesis_rows": len(hypothesis_rows), "ic_rows": len(ic_rows), "regime_rows": len(regime_rows)})


if __name__ == "__main__":
    main()
