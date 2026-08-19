"""ML Phase 7: isolated Elastic Net comparison against existing Ridge runs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analytics.coverage import load_price_day  # noqa: E402
from src.ebx.ml.backtest import (  # noqa: E402
    StrategyConfig,
    TransactionCostModel,
    daily_pnl_from_trades,
    equity_curve_from_daily,
    simulate_day,
    summarize_trades,
)
from src.ebx.ml.baseline import validation_metrics  # noqa: E402
from src.ebx.ml.cache import sha256_file, write_json, write_partition  # noqa: E402
from src.ebx.ml.elastic_net import ElasticNetBaseline  # noqa: E402
from src.ebx.ml.schemas import audited_scope  # noqa: E402
from src.ebx.ml.temporal_robustness import TEMPORAL_WINDOWS, validate_temporal_windows  # noqa: E402


ALPHA = 1e-6
L1_RATIO = 0.5
MAX_ITER = 10000
TOL = 1e-4
SELECTION = "cyclic"
RANDOM_STATE = None

EXPERIMENTS: dict[str, dict[str, object]] = {
    "primary": {
        "source_root": "results/ml/train_only_selection",
        "ridge_root": "results/ml/train_only_selection",
        "training_days": tuple(range(1, 65)),
        "validation_days": tuple(range(80, 86)),
    },
    "W1": {
        "source_root": "results/ml/temporal_robustness/W1",
        "ridge_root": "results/ml/temporal_robustness/W1",
        "training_days": TEMPORAL_WINDOWS["W1"]["training_days"],
        "validation_days": TEMPORAL_WINDOWS["W1"]["validation_days"],
    },
    "W2": {
        "source_root": "results/ml/temporal_robustness/W2",
        "ridge_root": "results/ml/temporal_robustness/W2",
        "training_days": TEMPORAL_WINDOWS["W2"]["training_days"],
        "validation_days": TEMPORAL_WINDOWS["W2"]["validation_days"],
    },
    "W3": {
        "source_root": "results/ml/temporal_robustness/W3",
        "ridge_root": "results/ml/temporal_robustness/W3",
        "training_days": TEMPORAL_WINDOWS["W3"]["training_days"],
        "validation_days": TEMPORAL_WINDOWS["W3"]["validation_days"],
    },
}

PREDICTIVE_METRICS = (
    "pearson_ic",
    "spearman_ic",
    "mean_daily_pearson_ic",
    "median_daily_pearson_ic",
    "std_daily_pearson_ic",
    "directional_accuracy",
    "prediction_mean",
    "prediction_std",
    "target_mean",
    "target_std",
    "r2",
    "mae",
    "rmse",
)


def _paths(root: Path, relative_root: str, split: str, days: tuple[int, ...]) -> list[Path]:
    base = root / relative_root / "datasets" / split
    paths = [base / f"day{day}.parquet" for day in days]
    if not all(path.exists() for path in paths):
        missing = [str(path) for path in paths if not path.exists()]
        raise FileNotFoundError(f"missing model-ready development partitions: {missing}")
    return paths


def _validate_source_manifest(root: Path, relative_root: str, train: tuple[int, ...], validation: tuple[int, ...]) -> dict[str, object]:
    manifest_path = root / relative_root / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("holdout_days_loaded") != [] or manifest.get("holdout_accessed") not in {False, None}:
        raise RuntimeError(f"source manifest does not prove holdout isolation: {manifest_path}")
    if tuple(manifest.get("selection_days_only", train)) != tuple(train):
        raise RuntimeError(f"selection days do not match requested training days: {manifest_path}")
    if set(train) & set(range(86, 109)) or set(validation) & set(range(86, 109)):
        raise AssertionError("holdout day entered Elastic Net experiment")
    return manifest


def _feature_names(root: Path, relative_root: str) -> tuple[str, ...]:
    table = pd.read_csv(root / relative_root / "selected_features.csv")
    if "feature" not in table.columns or table["feature"].isna().any():
        raise ValueError(f"selected feature artifact is invalid: {relative_root}")
    features = tuple(table["feature"].astype(str))
    if len(features) != len(set(features)):
        raise ValueError(f"selected feature artifact contains duplicate features: {relative_root}")
    return features


def _fit_window(root: Path, output: Path, name: str, specification: dict[str, object]) -> tuple[dict[str, object], pd.DataFrame, dict[str, str]]:
    source_root = str(specification["source_root"])
    ridge_root = str(specification["ridge_root"])
    train = tuple(int(day) for day in specification["training_days"])  # type: ignore[index]
    validation = tuple(int(day) for day in specification["validation_days"])  # type: ignore[index]
    _validate_source_manifest(root, source_root, train, validation)
    features = _feature_names(root, source_root)
    train_paths = _paths(root, source_root, "train", train)
    validation_paths = _paths(root, source_root, "validation", validation)

    window_root = output / name
    window_root.mkdir(parents=True, exist_ok=True)
    model = ElasticNetBaseline(
        features,
        alpha=ALPHA,
        l1_ratio=L1_RATIO,
        max_iter=MAX_ITER,
        tol=TOL,
        fit_intercept=True,
        selection=SELECTION,
        random_state=RANDOM_STATE,
    ).fit_partition_paths(train_paths)
    model_path = window_root / "elastic_net_model.pkl"
    model.save(model_path)

    prediction_frames: list[pd.DataFrame] = []
    prediction_files: list[Path] = []
    for day, path in zip(validation, validation_paths):
        frame = pd.read_parquet(path)
        if set(frame["day"].astype(int).unique()) != {day}:
            raise ValueError(f"{name} validation partition day mismatch: {path}")
        prediction = model.predict(frame)
        result = frame[["day", "timestamp", "timestamp_seconds", "target"]].copy()
        result["prediction"] = prediction
        result["residual"] = result["prediction"] - result["target"]
        destination = window_root / "predictions" / f"day{day}.parquet"
        write_partition(result, destination)
        prediction_frames.append(result)
        prediction_files.append(destination)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    pooled, daily = validation_metrics(predictions)
    write_json(pooled, window_root / "validation_metrics.json")
    daily.to_csv(window_root / "daily_metrics.csv", index=False)
    model_config = {
        "model": "elastic_net",
        "alpha": ALPHA,
        "l1_ratio": L1_RATIO,
        "max_iter": MAX_ITER,
        "tol": TOL,
        "solver": "coordinate_descent",
        "selection": SELECTION,
        "random_state": RANDOM_STATE,
        "fit_intercept": True,
        "target_horizon_seconds": 300,
        "feature_selection_source": str(root / source_root / "selected_features.csv"),
        "feature_selection_protocol": "existing training-only selection artifact consumed unchanged",
        "feature_count": len(features),
        "training_days": list(train),
        "validation_days": list(validation),
        "missing_days": list(range(65, 80)),
        "holdout_days_excluded": list(range(86, 109)),
        "model_summary": model.summary(),
    }
    write_json(model_config, window_root / "model_config.json")

    input_paths = {
        "development_freeze.json": root / "results/freeze/development_freeze.json",
        "config.yaml": root / "config/config.yaml",
        "selection_manifest.json": root / source_root / "run_manifest.json",
        "selected_features.csv": root / source_root / "selected_features.csv",
        "preprocessing_manifest.json": root / source_root / "preprocessing_manifest.json",
        "ridge_metrics.json": root / ridge_root / "validation_metrics.json",
    }
    manifest = {
        "phase": "ML Phase 7 — Elastic Net Model Comparison Against Ridge",
        "window": name,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "expected_development_days": 85,
        "available_development_days": 70,
        "missing_development_days": list(range(65, 80)),
        "training_days": list(train),
        "validation_days": list(validation),
        "source_days_loaded": list(train + validation),
        "selection_days_only": list(train),
        "preprocessing_fit_days": list(train),
        "target_horizon_seconds": 300,
        "feature_count": len(features),
        "feature_selection_source": str(root / source_root / "selected_features.csv"),
        "ridge_comparison_source": str(root / ridge_root),
        "model": model_config,
        "training_rows": int(model.n_train_samples_),
        "validation_rows": int(len(predictions)),
        "prediction_partitions": [str(path) for path in prediction_files],
        "holdout_days_loaded": [],
        "holdout_accessed": False,
        "frozen_artifacts_modified": False,
        "input_sha256": {key: sha256_file(path) for key, path in input_paths.items()},
    }
    write_json(manifest, window_root / "run_manifest.json")
    write_json({
        "deterministic_selection": True,
        "deterministic_fit": True,
        "random_state": RANDOM_STATE,
        "fit_days": list(train),
        "prediction_days": list(validation),
        "holdout_days_loaded": [],
        "model_artifact_sha256": sha256_file(model_path),
        "prediction_sha256": {path.name: sha256_file(path) for path in prediction_files},
    }, window_root / "reproducibility.json")
    return pooled, daily, {key: sha256_file(path) for key, path in input_paths.items()}


def _comparison_rows(name: str, ridge: dict[str, object], elastic: dict[str, object], metrics: tuple[str, ...]) -> list[dict[str, object]]:
    rows = []
    for metric in metrics:
        ridge_value = float(ridge[metric])
        elastic_value = float(elastic[metric])
        rows.append({"experiment": name, "metric": metric, "ridge": ridge_value, "elastic_net": elastic_value, "difference_elastic_minus_ridge": elastic_value - ridge_value})
    return rows


def _run_backtest(root: Path, output: Path, elastic_predictions: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    strategy = StrategyConfig()
    strategy.validate()
    costs = TransactionCostModel()
    all_trades: list[pd.DataFrame] = []
    all_daily: list[pd.DataFrame] = []
    window_summaries: list[dict[str, object]] = []
    for name in ("W1", "W2", "W3"):
        validation = tuple(EXPERIMENTS[name]["validation_days"])  # type: ignore[index]
        by_day: list[pd.DataFrame] = []
        session_seconds: dict[int, int] = {}
        for day in validation:
            prediction = elastic_predictions[name]
            prediction = prediction[prediction["day"].astype(int) == day].reset_index(drop=True)
            price = load_price_day(root, day)
            session_seconds[day] = len(price) - 1
            by_day.append(simulate_day(prediction, price, window=name, day=day, strategy=strategy, costs=costs))
        trades = pd.concat(by_day, ignore_index=True) if by_day else pd.DataFrame()
        daily = daily_pnl_from_trades(trades, days=validation, window=name, session_seconds=session_seconds)
        summary = summarize_trades(trades, daily, window=name, strategy=strategy)
        summary["validation_rows"] = int(len(elastic_predictions[name]))
        window_summaries.append(summary)
        all_trades.append(trades)
        all_daily.append(daily)

    trades = pd.concat(all_trades, ignore_index=True)
    daily = pd.concat(all_daily, ignore_index=True)
    equity = equity_curve_from_daily(daily, starting_capital=strategy.starting_capital)
    backtest_root = output / "backtest"
    backtest_root.mkdir(parents=True, exist_ok=True)
    trades.to_csv(backtest_root / "trade_log.csv", index=False)
    daily.to_csv(backtest_root / "daily_pnl.csv", index=False)
    equity.to_csv(backtest_root / "equity_curve.csv", index=False)
    pd.DataFrame(window_summaries).to_csv(backtest_root / "window_metrics.csv", index=False)
    pd.DataFrame([{
        "window": row["window"],
        "trades": row["trades"],
        "gross_pnl": row["gross_pnl"],
        "transaction_costs": row["transaction_costs"],
        "net_pnl": row["net_pnl"],
        "turnover": row["turnover"],
        "entry_cost_bps": costs.entry_cost_bps,
        "exit_cost_bps": costs.exit_cost_bps,
        "fee_bps": costs.fee_bps,
    } for row in window_summaries]).to_csv(backtest_root / "cost_breakdown.csv", index=False)

    ridge_windows = pd.read_csv(root / "results/ml/backtest_baseline/window_metrics.csv")
    economic_rows: list[dict[str, object]] = []
    for row in window_summaries:
        ridge = ridge_windows[ridge_windows["window"] == row["window"]].iloc[0].to_dict()
        for metric in ("gross_pnl", "transaction_costs", "net_pnl", "sharpe", "maximum_drawdown", "turnover", "trades"):
            economic_rows.append({"window": row["window"], "metric": metric, "ridge": float(ridge[metric]), "elastic_net": float(row[metric]), "difference_elastic_minus_ridge": float(row[metric]) - float(ridge[metric])})
    pd.DataFrame(economic_rows).to_csv(output / "economic_comparison.csv", index=False)
    w3 = trades[(trades["window"] == "W3") & (trades["day"] != 84)]
    w3_daily = daily[(daily["window"] == "W3") & (daily["day"] != 84)].reset_index(drop=True)
    sensitivity = summarize_trades(w3, w3_daily, window="W3_excluding_day84", strategy=strategy)
    sensitivity["diagnostic"] = "post-hoc W3 aggregation excluding Day 84"
    sensitivity["retrained"] = False
    write_json({"normal_w3": window_summaries[2], "excluding_day84": sensitivity}, backtest_root / "day84_sensitivity.json")
    pooled = summarize_trades(trades, daily, window="pooled_development", strategy=strategy)
    pooled["validation_rows"] = int(sum(len(elastic_predictions[name]) for name in ("W1", "W2", "W3")))
    return trades, daily, {"by_window": window_summaries, "pooled": pooled, "day84_sensitivity": sensitivity}


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    scope = audited_scope(root / "results/freeze/development_freeze.json")
    validate_temporal_windows(TEMPORAL_WINDOWS, scope)
    output = root / "results/ml/elastic_net"
    output.mkdir(parents=True, exist_ok=True)

    pooled_by_name: dict[str, dict[str, object]] = {}
    daily_by_name: dict[str, pd.DataFrame] = {}
    input_hashes: dict[str, str] = {}
    for name, specification in EXPERIMENTS.items():
        pooled, daily, hashes = _fit_window(root, output, name, specification)
        pooled_by_name[name] = pooled
        daily_by_name[name] = daily
        input_hashes.update({f"{name}/{key}": value for key, value in hashes.items()})

    comparison_rows: list[dict[str, object]] = []
    daily_comparison_rows: list[dict[str, object]] = []
    for name, specification in EXPERIMENTS.items():
        ridge_root = root / str(specification["ridge_root"])
        ridge_metrics = json.loads((ridge_root / "validation_metrics.json").read_text())
        comparison_rows.extend(_comparison_rows(name, ridge_metrics, pooled_by_name[name], PREDICTIVE_METRICS))
        ridge_daily = pd.read_csv(ridge_root / "daily_metrics.csv")
        elastic_daily = daily_by_name[name]
        for _, ridge_row in ridge_daily.iterrows():
            day = int(ridge_row["day"])
            elastic_row = elastic_daily[elastic_daily["day"].astype(int) == day].iloc[0]
            daily_comparison_rows.append({
                "experiment": name,
                "day": day,
                "ridge_pearson_ic": float(ridge_row["pearson_ic"]),
                "elastic_net_pearson_ic": float(elastic_row["pearson_ic"]),
                "difference_pearson_ic": float(elastic_row["pearson_ic"] - ridge_row["pearson_ic"]),
                "ridge_r2": float(ridge_row["r2"]),
                "elastic_net_r2": float(elastic_row["r2"]),
                "ridge_directional_accuracy": float(ridge_row["directional_accuracy"]),
                "elastic_net_directional_accuracy": float(elastic_row["directional_accuracy"]),
            })

    pd.DataFrame(comparison_rows).to_csv(output / "predictive_comparison.csv", index=False)
    pd.DataFrame(daily_comparison_rows).to_csv(output / "daily_comparison.csv", index=False)
    trades, daily, backtest_summary = _run_backtest(root, output, {name: pd.concat([pd.read_parquet(output / name / "predictions" / f"day{day}.parquet") for day in tuple(specification["validation_days"])], ignore_index=True) for name, specification in EXPERIMENTS.items() if name != "primary"})
    write_json(backtest_summary, output / "backtest_summary.json")

    top_manifest = {
        "phase": "ML Phase 7 — Elastic Net Model Comparison Against Ridge",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "expected_development_days": 85,
        "available_development_days": 70,
        "missing_development_days": list(range(65, 80)),
        "experiments": {name: {key: list(value) if isinstance(value, tuple) else value for key, value in specification.items()} for name, specification in EXPERIMENTS.items()},
        "elastic_net_configuration": {
            "alpha": ALPHA,
            "l1_ratio": L1_RATIO,
            "max_iter": MAX_ITER,
            "tol": TOL,
            "solver": "coordinate_descent",
            "selection": SELECTION,
            "random_state": RANDOM_STATE,
            "fit_intercept": True,
        },
        "feature_selection_protocol": "existing train-only selection artifacts consumed unchanged",
        "target_horizon_seconds": 300,
        "backtest_protocol": "existing Part 5 baseline strategy and accounting reused unchanged",
        "source_days_loaded": sorted({day for specification in EXPERIMENTS.values() for day in tuple(specification["training_days"]) + tuple(specification["validation_days"])}),
        "holdout_days_loaded": [],
        "holdout_accessed": False,
        "frozen_artifacts_modified": False,
        "input_sha256": input_hashes,
        "primary_elastic_net_metrics": pooled_by_name["primary"],
        "temporal_elastic_net_metrics": {name: pooled_by_name[name] for name in ("W1", "W2", "W3")},
        "backtest_trade_count": int(len(trades)),
        "backtest_daily_rows": int(len(daily)),
    }
    write_json(top_manifest, output / "run_manifest.json")
    stable_files = [
        output / "primary/elastic_net_model.pkl",
        output / "primary/validation_metrics.json",
        output / "primary/daily_metrics.csv",
        output / "predictive_comparison.csv",
        output / "daily_comparison.csv",
        output / "backtest/trade_log.csv",
        output / "backtest/daily_pnl.csv",
        output / "backtest/window_metrics.csv",
        output / "backtest_summary.json",
    ]
    write_json({
        "deterministic": True,
        "stable_output_sha256": {str(path.relative_to(output)): sha256_file(path) for path in stable_files},
        "holdout_days_loaded": [],
        "random_state": RANDOM_STATE,
    }, output / "reproducibility.json")
    print(json.dumps({
        "phase": top_manifest["phase"],
        "primary": {key: pooled_by_name["primary"][key] for key in ("pearson_ic", "spearman_ic", "r2", "mae", "rmse")},
        "temporal_pearson_ic": {name: pooled_by_name[name]["pearson_ic"] for name in ("W1", "W2", "W3")},
        "backtest_net_pnl": {row["window"]: row["net_pnl"] for row in backtest_summary["by_window"]},
        "holdout_days_loaded": [],
    }, indent=2))


if __name__ == "__main__":
    main()
