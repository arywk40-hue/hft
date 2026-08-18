"""Phase 3: fit and evaluate the first frozen-screen Ridge baseline."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ebx.ml.baseline import RidgeBaseline, validate_baseline_scope, validation_metrics  # noqa: E402
from src.ebx.ml.cache import sha256_file, write_json, write_partition  # noqa: E402
from src.ebx.ml.schemas import audited_scope  # noqa: E402
from src.ebx.ml.splits import write_split_manifest  # noqa: E402


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    scope = audited_scope(root / "results/freeze/development_freeze.json")
    ml_root = root / "results/ml"
    baseline_root = ml_root / "baseline"
    split = json.loads((ml_root / "splits/split_manifest.json").read_text())
    dataset_manifest = json.loads((ml_root / "datasets/dataset_manifest.json").read_text())
    features = tuple(dataset_manifest["feature_names"])
    target_horizon = int(dataset_manifest["target_horizon"])
    training_days = [int(day) for day in split["training_days"]]
    validation_days = [int(day) for day in split["validation_days"]]
    validate_baseline_scope(scope, training_days, validation_days, features, target_horizon)
    if dataset_manifest["feature_count"] != 197 or target_horizon != 300:
        raise ValueError("model-ready dataset does not match Phase 3 frozen configuration")

    train_paths = [ml_root / "datasets" / "train" / f"day{day}.parquet" for day in training_days]
    validation_paths = [ml_root / "datasets" / "validation" / f"day{day}.parquet" for day in validation_days]
    if not all(path.exists() for path in train_paths + validation_paths):
        raise FileNotFoundError("a required model-ready development partition is missing")
    if any(86 <= day <= 108 for day in training_days + validation_days):
        raise AssertionError("holdout day entered baseline split")

    model = RidgeBaseline(features, alpha=1.0, fit_intercept=True)
    model.fit_partition_paths([str(path) for path in train_paths])
    model_path = baseline_root / "ridge_model.pkl"
    model.save(model_path)

    prediction_frames: list[pd.DataFrame] = []
    partition_rows = []
    columns = ["day", "timestamp", "timestamp_seconds", "target", *features]
    for day, path in zip(validation_days, validation_paths):
        frame = pd.read_parquet(path, columns=columns)
        if set(frame["day"].astype(int).unique()) != {day}:
            raise ValueError(f"validation partition day mismatch: {path}")
        prediction = model.predict(frame)
        output = frame[["day", "timestamp", "timestamp_seconds", "target"]].copy()
        output["prediction"] = prediction
        output["residual"] = output["prediction"] - output["target"]
        prediction_path = baseline_root / "predictions" / f"day{day}.parquet"
        write_partition(output, prediction_path)
        prediction_frames.append(output)
        partition_rows.append({"day": day, "path": str(prediction_path), "rows": int(len(output))})

    predictions = pd.concat(prediction_frames, ignore_index=True)
    pooled_metrics, daily_metrics = validation_metrics(predictions)
    write_json(pooled_metrics, baseline_root / "validation_metrics.json")
    baseline_root.mkdir(parents=True, exist_ok=True)
    daily_metrics.to_csv(baseline_root / "daily_metrics.csv", index=False)

    input_paths = {
        "development_freeze.json": root / "results/freeze/development_freeze.json",
        "aggregate_ic.csv": root / "results/predictive/aggregate_ic.csv",
        "config.yaml": root / "config/config.yaml",
        "frozen_feature_set.csv": ml_root / "features/frozen_feature_set.csv",
        "split_manifest.json": ml_root / "splits/split_manifest.json",
        "preprocessing_manifest.json": ml_root / "preprocessing/preprocessing_manifest.json",
        "dataset_manifest.json": ml_root / "datasets/dataset_manifest.json",
    }
    model_config = {
        "model": "ridge",
        "alpha": 1.0,
        "fit_intercept": True,
        "solver": "deterministic normal equations from day-wise sufficient statistics",
        "target_horizon_seconds": target_horizon,
        "feature_count": len(features),
        "feature_set": "existing frozen Part 4 screen, consumed unchanged",
        "frozen_screen_baseline_note": "Frozen-screen baseline: the feature set was predetermined by the existing Part-4 frozen artifact and consumed unchanged. A later experiment will perform model-specific feature selection using training days only.",
        "training_days": training_days,
        "validation_days": validation_days,
        "missing_days": list(scope.missing_development_days),
        "holdout_days_excluded": list(scope.holdout_days),
        "preprocessing": "existing train-only standardization; no imputation or clipping",
    }
    write_json(model_config, baseline_root / "model_config.json")

    run_manifest = {
        "phase": "ML Phase 3 — First Baseline Model",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "expected_development_days": scope.expected_development_days,
        "available_development_days": len(scope.available_development_days),
        "missing_development_days": list(scope.missing_development_days),
        "training_days": training_days,
        "validation_days": validation_days,
        "training_rows": int(model.n_train_samples_),
        "validation_rows": int(len(predictions)),
        "feature_count": len(features),
        "target_horizon_seconds": target_horizon,
        "model_artifact": str(model_path),
        "prediction_partitions": partition_rows,
        "model_training_performed": True,
        "holdout_days_loaded": [],
        "frozen_screen_baseline": True,
        "input_sha256": {name: sha256_file(path) for name, path in input_paths.items()},
    }
    write_json(run_manifest, baseline_root / "run_manifest.json")
    write_json({
        "deterministic_fit": True,
        "random_seed": None,
        "fit_order": [str(path) for path in train_paths],
        "prediction_order": [str(path) for path in validation_paths],
        "model_artifact_sha256": sha256_file(model_path),
        "input_sha256": run_manifest["input_sha256"],
        "no_holdout_access": True,
    }, baseline_root / "reproducibility.json")
    print(json.dumps({
        "phase": run_manifest["phase"],
        "training_rows": run_manifest["training_rows"],
        "validation_rows": run_manifest["validation_rows"],
        "feature_count": len(features),
        "target_horizon_seconds": target_horizon,
        "pearson_ic": pooled_metrics["pearson_ic"],
        "spearman_ic": pooled_metrics["spearman_ic"],
        "r2": pooled_metrics["r2"],
        "mae": pooled_metrics["mae"],
        "rmse": pooled_metrics["rmse"],
        "holdout_days_loaded": [],
    }, indent=2))


if __name__ == "__main__":
    main()
