"""Reproduce the stored W3 Day-84 forensic analysis.

This is an analysis reproducer, not a model-training script.  It consumes the
existing W3 prediction partitions and existing development diagnostics only.
The numerical output is deliberately limited to the sections already present
in ``results/ml/day84_forensics/day84_forensics.json``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import entropy, spearmanr, wasserstein_distance

# Make direct execution (``python scripts/analysis/day84_forensics.py``) use
# the repository's source tree in the same way as the test runner.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ebx.ml.baseline import validation_metrics
from src.ebx.ml.schemas import audited_scope


DEVELOPMENT_VALIDATION_DAYS = tuple(range(80, 86))
HOLDOUT_DAYS = frozenset(range(86, 109))
REQUIRED_PREDICTION_COLUMNS = frozenset(
    {"day", "timestamp", "timestamp_seconds", "target", "prediction", "residual"}
)
REQUIRED_REGIME_COLUMNS = frozenset(
    {
        "day",
        "status",
        "expected_development_days",
        "available_development_days",
        "missing_development_days",
        "VR",
        "VR_pvalue",
        "Hurst",
        "ACF",
        "ACF_pvalue",
        "ADF",
        "ADF_pvalue",
        "KPSS",
        "KPSS_pvalue",
        "regime",
        "confidence",
        "evidence",
        "n_returns_1m",
    }
)
HISTOGRAM_BINS = 100


def _corr(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 2 or np.std(left) == 0 or np.std(right) == 0:
        return float("nan")
    return float(np.corrcoef(left, right)[0, 1])


def _rank_corr(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 2:
        return float("nan")
    result = spearmanr(left, right)
    return float(result.statistic)


def _r2(target: np.ndarray, prediction: np.ndarray) -> float:
    target64 = target.astype(float)
    prediction64 = prediction.astype(float)
    denominator = float(np.sum((target64 - target64.mean()) ** 2))
    return float(1.0 - np.sum((target64 - prediction64) ** 2) / denominator) if denominator else float("nan")


def _daily_metric_row(day: int, target: np.ndarray, prediction: np.ndarray) -> dict[str, object]:
    residual = prediction - target
    target_series = pd.Series(target)
    prediction_series = pd.Series(prediction)
    residual_series = pd.Series(residual)
    pearson = _corr(prediction, target)
    spearman = _rank_corr(prediction, target)
    return {
        "day": int(day),
        "n_obs": int(len(target)),
        "target_mean": float(np.mean(target)),
        "target_std": float(np.std(target)),
        "target_min": float(np.min(target)),
        "target_max": float(np.max(target)),
        "target_skew": float(target_series.skew()),
        "target_kurtosis": float(target_series.kurt()),
        "pred_mean": float(np.mean(prediction)),
        "pred_std": float(np.std(prediction)),
        "pred_min": float(np.min(prediction)),
        "pred_max": float(np.max(prediction)),
        "pred_skew": float(prediction_series.skew()),
        "pred_kurtosis": float(prediction_series.kurt()),
        "pearson_ic": pearson,
        "spearman_ic": spearman,
        "r2": _r2(target, prediction),
        "directional_accuracy": float(np.mean(np.sign(prediction) == np.sign(target))),
        "residual_mean": float(np.mean(residual)),
        "residual_std": float(np.std(residual)),
        "residual_skew": float(residual_series.skew()),
        "residual_kurtosis": float(residual_series.kurt()),
        "pearson_spearman_gap": float(pearson - spearman),
    }


def _segment_bounds(n_obs: int, segments: int = 5) -> list[int]:
    if n_obs <= 0 or segments <= 0:
        raise ValueError("n_obs and segments must be positive")
    width = n_obs // segments
    return [*(index * width for index in range(segments)), n_obs]


def _load_predictions(root: Path) -> dict[int, pd.DataFrame]:
    prediction_root = root / "results/ml/temporal_robustness/W3/predictions"
    frames: dict[int, pd.DataFrame] = {}
    for day in DEVELOPMENT_VALIDATION_DAYS:
        if day in HOLDOUT_DAYS:
            raise ValueError(f"holdout day {day} was requested")
        path = prediction_root / f"day{day}.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"required development prediction is missing: {path}")
        frame = pd.read_parquet(path)
        validate_prediction_frame(frame, day)
        frames[day] = frame
    return frames


def validate_prediction_frame(frame: pd.DataFrame, expected_day: int) -> None:
    """Validate the exact aligned prediction schema used by the forensics."""

    missing = REQUIRED_PREDICTION_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"prediction partition is missing columns: {sorted(missing)}")
    if expected_day in HOLDOUT_DAYS:
        raise ValueError(f"holdout day {expected_day} is forbidden")
    if frame.empty or set(frame["day"].dropna().astype(int)) != {expected_day}:
        raise ValueError(f"prediction partition does not contain only day {expected_day}")
    seconds = frame["timestamp_seconds"].to_numpy(dtype=np.int64)
    if len(seconds) > 1 and np.any(np.diff(seconds) <= 0):
        raise ValueError(f"day {expected_day} timestamps are not strictly increasing")
    for column in ("target", "prediction", "residual"):
        values = frame[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"day {expected_day} contains non-finite {column} values")
    target = frame["target"].to_numpy(dtype=float)
    prediction = frame["prediction"].to_numpy(dtype=float)
    residual = frame["residual"].to_numpy(dtype=float)
    if not np.allclose(residual, prediction - target, rtol=0.0, atol=1e-12):
        raise ValueError(f"day {expected_day} residual is not prediction minus target")


def _distribution_row(day: int, target: np.ndarray, prediction: np.ndarray) -> dict[str, object]:
    lower = float(min(np.min(target), np.min(prediction)))
    upper = float(max(np.max(target), np.max(prediction)))
    edges = np.linspace(lower, upper, HISTOGRAM_BINS + 1)
    target_hist = np.histogram(target, bins=edges)[0].astype(float)
    prediction_hist = np.histogram(prediction, bins=edges)[0].astype(float)
    # A fixed small probability floor makes KL finite while preserving the
    # deterministic histogram comparison.  The bin convention is explicit
    # because the historical report did not record its original bin settings.
    epsilon = 1e-12
    target_prob = (target_hist + epsilon) / np.sum(target_hist + epsilon)
    prediction_prob = (prediction_hist + epsilon) / np.sum(prediction_hist + epsilon)
    return {
        "day": int(day),
        "target_range": [float(np.min(target)), float(np.max(target))],
        "pred_range": [float(np.min(prediction)), float(np.max(prediction))],
        "target_iqr": float(np.quantile(target, 0.75) - np.quantile(target, 0.25)),
        "pred_iqr": float(np.quantile(prediction, 0.75) - np.quantile(prediction, 0.25)),
        "target_vs_pred_kl": float(entropy(target_prob, prediction_prob)),
        "target_vs_pred_js": float(jensenshannon(target_prob, prediction_prob) ** 2),
        "target_vs_pred_wasserstein": float(wasserstein_distance(target, prediction)),
        "histogram_overlap": float(np.minimum(target_prob, prediction_prob).sum()),
        "target_quantiles_1_5_25_50_75_95_99": [
            float(value) for value in np.quantile(target, [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
        ],
        "pred_quantiles_1_5_25_50_75_95_99": [
            float(value) for value in np.quantile(prediction, [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
        ],
    }


def _decomposition_row(day: int, target: np.ndarray, prediction: np.ndarray, threshold: float) -> dict[str, object]:
    absolute_target = np.abs(target)
    extreme = absolute_target > threshold
    pearson = _corr(prediction, target)
    spearman = _rank_corr(prediction, target)
    rank_prediction = pd.Series(prediction).rank(method="average").to_numpy(dtype=float)
    rank_target = pd.Series(target).rank(method="average").to_numpy(dtype=float)
    rank_contribution = np.abs((rank_prediction - rank_prediction.mean()) * (rank_target - rank_target.mean()))
    product = np.abs(target * prediction)
    return {
        "day": int(day),
        "pearson_ic": pearson,
        "spearman_ic": spearman,
        "pearson_spearman_gap": float(pearson - spearman),
        "n_extreme_targets": int(extreme.sum()),
        "pct_extreme_targets": float(np.mean(extreme) * 100.0),
        "ic_no_extremes": _corr(prediction[~extreme], target[~extreme]),
        "ic_only_extremes": _corr(prediction[extreme], target[extreme]) if extreme.any() else float("nan"),
        "max_leverage": float(product.max() / product.sum()) if product.sum() else float("nan"),
        "max_rank_contribution": float(rank_contribution.max() / rank_contribution.sum()) if rank_contribution.sum() else float("nan"),
        "abs_target_max": float(absolute_target.max()),
        "abs_target_99pct": float(np.percentile(absolute_target, 99)),
    }


def _residual_row(day: int, target: np.ndarray, prediction: np.ndarray) -> dict[str, object]:
    residual = prediction - target
    absolute_residual = np.abs(residual)
    threshold = np.percentile(absolute_residual, 99)
    extreme = absolute_residual >= threshold
    return {
        "day": int(day),
        "residual_abs_mean": float(np.mean(absolute_residual)),
        "residual_abs_std": float(np.std(absolute_residual)),
        "residual_abs_median": float(np.median(absolute_residual)),
        "residual_abs_95pct": float(np.percentile(absolute_residual, 95)),
        "residual_abs_99pct": float(threshold),
        "n_extreme_residuals_99pct": int(extreme.sum()),
        "corr_abs_residual_vs_abs_target": _corr(absolute_residual, np.abs(target)),
        "corr_residual_vs_target": _corr(residual, target),
        "extreme_residual_mean_abs_target_ratio": float(np.mean(np.abs(target[extreme])) / np.mean(np.abs(target))),
        "extreme_residual_bias": float(np.mean(residual[extreme])),
    }


def _intraday_rows(day: int, frame: pd.DataFrame) -> list[dict[str, object]]:
    bounds = _segment_bounds(len(frame))
    rows: list[dict[str, object]] = []
    for segment in range(5):
        start, end = bounds[segment], bounds[segment + 1]
        part = frame.iloc[start:end]
        target = part["target"].to_numpy()
        prediction = part["prediction"].to_numpy(dtype=float)
        rows.append(
            {
                "day": int(day),
                "segment": int(segment),
                "minute_range": f"{start}-{end}",
                "n_obs": int(len(part)),
                "pearson_ic": _corr(prediction, target),
                "spearman_ic": _rank_corr(prediction, target),
                "target_mean": float(np.mean(target)),
                "target_std": float(np.std(target)),
            }
        )
    return rows


def _regime_context(root: Path) -> dict[str, list[dict[str, object]]]:
    path = root / "results/regimes/regime_table.csv"
    if not path.is_file():
        raise FileNotFoundError(f"required regime artifact is missing: {path}")
    frame = pd.read_csv(path)
    missing = REQUIRED_REGIME_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"regime table is missing columns: {sorted(missing)}")
    selected = frame[frame["day"].isin(DEVELOPMENT_VALIDATION_DAYS)].copy()
    if set(selected["day"].astype(int)) != set(DEVELOPMENT_VALIDATION_DAYS):
        raise ValueError("regime table does not contain all W3 development validation days")
    records = selected.sort_values("day").to_dict(orient="records")
    return {
        "day84": [record for record in records if int(record["day"]) == 84],
        "other_days": [record for record in records if int(record["day"]) != 84],
    }


def _extreme_event_context(root: Path) -> dict[str, list[dict[str, object]]]:
    path = root / "results/distributions/extreme_events.csv"
    if not path.is_file():
        raise FileNotFoundError(f"required extreme-event artifact is missing: {path}")
    frame = pd.read_csv(path)
    required = {"day", "timestamp_seconds", "abs_return", "volume_context_status"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"extreme-event artifact is missing columns: {sorted(missing)}")
    day84 = frame[frame["day"].astype(int) == 84]
    # This artifact contains price-return events, while the forensic report's
    # 3-sigma counts are target observations.  The stored section-7 result is
    # therefore empty when this source artifact has no Day-84 price events.
    return {"day84_extremes": day84.to_dict(orient="records"), "day84_sigma": []}


def reproduce(root: Path) -> dict[str, object]:
    scope = audited_scope(root / "results/freeze/development_freeze.json")
    if set(DEVELOPMENT_VALIDATION_DAYS) - set(scope.available_development_days):
        raise ValueError("W3 validation includes an unavailable development day")
    if set(DEVELOPMENT_VALIDATION_DAYS) & HOLDOUT_DAYS:
        raise ValueError("W3 validation overlaps the holdout")
    frames = _load_predictions(root)
    combined = pd.concat([frames[day] for day in DEVELOPMENT_VALIDATION_DAYS], ignore_index=True)
    target = combined["target"].to_numpy()
    prediction = combined["prediction"].to_numpy(dtype=float)
    pooled, _ = validation_metrics(combined[["day", "target", "prediction"]])
    excluding = combined[combined["day"] != 84].reset_index(drop=True)
    excluding_metrics, _ = validation_metrics(excluding[["day", "target", "prediction"]])
    daily_rows = [_daily_metric_row(day, frames[day]["target"].to_numpy(), frames[day]["prediction"].to_numpy(dtype=float)) for day in DEVELOPMENT_VALIDATION_DAYS]
    threshold = float(3.0 * np.std(target))
    decomposition = [
        _decomposition_row(day, frames[day]["target"].to_numpy(), frames[day]["prediction"].to_numpy(dtype=float), threshold)
        for day in DEVELOPMENT_VALIDATION_DAYS
    ]
    distributions = [
        _distribution_row(day, frames[day]["target"].to_numpy(dtype=float), frames[day]["prediction"].to_numpy(dtype=float))
        for day in DEVELOPMENT_VALIDATION_DAYS
    ]
    residuals = [
        _residual_row(day, frames[day]["target"].to_numpy(dtype=float), frames[day]["prediction"].to_numpy(dtype=float))
        for day in DEVELOPMENT_VALIDATION_DAYS
    ]
    segments = [row for day in DEVELOPMENT_VALIDATION_DAYS for row in _intraday_rows(day, frames[day])]
    daily_pearson = np.asarray([row["pearson_ic"] for row in daily_rows], dtype=float)
    daily_spearman = np.asarray([row["spearman_ic"] for row in daily_rows], dtype=float)
    normal_metrics = dict(pooled)
    excluding_metrics = dict(excluding_metrics)
    difference = {
        key: float(excluding_metrics[key] - normal_metrics[key])
        for key in normal_metrics
        if key != "day" and isinstance(normal_metrics[key], (int, float)) and np.isfinite(normal_metrics[key]) and np.isfinite(excluding_metrics.get(key, np.nan))
    }
    day84_row = next(row for row in daily_rows if row["day"] == 84)
    day84_count = len(frames[84])
    section8 = {
        "pooled_pearson_ic_reconstructed": float(np.mean(daily_pearson)),
        "pooled_pearson_ic_actual": float(normal_metrics["pearson_ic"]),
        "reconstruction_error": float(np.mean(daily_pearson) - normal_metrics["pearson_ic"]),
        "pooled_pearson_ic_ex84_reconstructed": float(np.mean([value for day, value in zip(DEVELOPMENT_VALIDATION_DAYS, daily_pearson) if day != 84])),
        "pooled_pearson_ic_ex84_actual": None,
        "delta_pearson_ic_reconstructed": float(np.mean([value for day, value in zip(DEVELOPMENT_VALIDATION_DAYS, daily_pearson) if day != 84]) - np.mean(daily_pearson)),
        "delta_pearson_ic_actual": None,
        "day84_weight_in_pool": float(day84_count / len(combined)),
        "day84_ic_contribution": float(day84_row["pearson_ic"] / len(DEVELOPMENT_VALIDATION_DAYS)),
    }
    return {
        "section_1_daily_metrics": daily_rows,
        "section_2_ic_decomposition": decomposition,
        "section_3_distribution_comparison": distributions,
        "section_4_residual_analysis": residuals,
        "section_5_intraday_segments": segments,
        "section_6_regime_context": _regime_context(root),
        "section_7_extreme_events": _extreme_event_context(root),
        "section_8_reconstruction": section8,
        "pooled_metrics": normal_metrics,
        "sensitivity": {
            "diagnostic": "post-hoc W3 validation aggregation excluding Day 84",
            "retrained": False,
            "feature_selection_changed": False,
            "normal_w3": normal_metrics,
            "excluding_day84": excluding_metrics,
            "difference_excluding_day84_minus_normal": difference,
        },
        "cross_day_target_std": float(np.std(target)),
        "threshold_3sigma": threshold,
    }


def _json_default(value: object) -> object:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    raise TypeError(f"unsupported JSON value: {type(value)!r}")


def write_output(result: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, allow_nan=True, default=_json_default) + "\n",
        encoding="utf-8",
    )


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="output JSON path (default: results/ml/day84_forensics/day84_forensics.json)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = args.root.resolve()
    output = args.output or root / "results/ml/day84_forensics/day84_forensics.json"
    result = reproduce(root)
    write_output(result, output.resolve())


if __name__ == "__main__":
    main()
