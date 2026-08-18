"""ML Phase 2: training-only feature selection and controlled Ridge comparison."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ebx.ml.baseline import RidgeBaseline, validation_metrics  # noqa: E402
from src.ebx.ml.cache import sha256_file, write_json, write_partition  # noqa: E402
from src.ebx.ml.schemas import TARGET_HORIZONS_SECONDS, audited_scope  # noqa: E402
from src.ebx.ml.train_only_selection import (  # noqa: E402
    build_training_only_partitions,
    fit_training_only_screen,
    load_training_daily_ic,
)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    scope = audited_scope(root / "results/freeze/development_freeze.json")
    ml_root = root / "results/ml"
    output = ml_root / "train_only_selection"
    output.mkdir(parents=True, exist_ok=True)
    split = json.loads((ml_root / "splits/split_manifest.json").read_text())
    training_days = tuple(int(day) for day in split["training_days"])
    validation_days = tuple(int(day) for day in split["validation_days"])
    if training_days != tuple(range(1, 65)) or validation_days != tuple(range(80, 86)):
        raise ValueError("Phase 2 requires the existing Days 1-64 / 80-85 split")
    if set(scope.missing_development_days) != set(range(65, 80)):
        raise ValueError("missing development-day boundary changed")

    daily_ic = load_training_daily_ic(
        root / "results/predictive/per_day_ic.csv",
        training_days=training_days,
        horizons=TARGET_HORIZONS_SECONDS,
        scope=scope,
    )
    aggregate, selected = fit_training_only_screen(
        daily_ic,
        training_days=training_days,
        target_horizon=300,
        scope=scope,
    )
    if selected.empty:
        raise ValueError("training-only selection produced no eligible 300-second features")
    features = tuple(selected["feature"].astype(str))
    daily_ic.to_csv(output / "selection_daily_ic.csv", index=False)
    aggregate.to_csv(output / "selection_aggregate_ic.csv", index=False)
    selected.to_csv(output / "selected_features.csv", index=False)

    scaler, partition_reports = build_training_only_partitions(
        processed_dir=root / "data/processed",
        output_root=output,
        training_days=training_days,
        validation_days=validation_days,
        features=features,
        target_horizon=300,
        scope=scope,
    )
    write_json({
        **scope.as_dict(),
        "preprocessing_version": "train-only-standardization-v1",
        "fit_days": list(training_days),
        "validation_days_not_used_for_fit": list(validation_days),
        "target_horizon_seconds": 300,
        "feature_count": len(features),
        **scaler.manifest(),
    }, output / "preprocessing_manifest.json")

    model = RidgeBaseline(features, alpha=1.0, fit_intercept=True)
    train_paths = [output / "datasets/train" / f"day{day}.parquet" for day in training_days]
    validation_paths = [output / "datasets/validation" / f"day{day}.parquet" for day in validation_days]
    model.fit_partition_paths(train_paths)
    model_path = output / "ridge_model.pkl"
    model.save(model_path)

    prediction_frames: list[pd.DataFrame] = []
    prediction_partitions = []
    for day, path in zip(validation_days, validation_paths):
        frame = pd.read_parquet(path)
        if set(frame["day"].astype(int).unique()) != {day}:
            raise ValueError(f"validation partition day mismatch: {path}")
        prediction = model.predict(frame)
        result = frame[["day", "timestamp", "timestamp_seconds", "target"]].copy()
        result["prediction"] = prediction
        result["residual"] = result["prediction"] - result["target"]
        destination = output / "predictions" / f"day{day}.parquet"
        write_partition(result, destination)
        prediction_frames.append(result)
        prediction_partitions.append({"day": day, "path": str(destination), "rows": int(len(result))})

    predictions = pd.concat(prediction_frames, ignore_index=True)
    pooled, daily = validation_metrics(predictions)
    write_json(pooled, output / "validation_metrics.json")
    daily.to_csv(output / "daily_metrics.csv", index=False)

    frozen_manifest = json.loads((ml_root / "datasets/dataset_manifest.json").read_text())
    frozen_features = set(frozen_manifest["feature_names"])
    selected_features = set(features)
    overlap = sorted(frozen_features & selected_features)
    comparison = {
        "experiment_a": {
            "name": "frozen 197-feature screen Ridge baseline",
            "feature_count": len(frozen_features),
            "metrics": json.loads((ml_root / "baseline/validation_metrics.json").read_text()),
        },
        "experiment_b": {
            "name": "training-only feature selection Ridge",
            "feature_count": len(features),
            "metrics": pooled,
        },
        "feature_overlap_count": len(overlap),
        "feature_overlap_fraction_of_frozen": len(overlap) / len(frozen_features),
        "feature_overlap_fraction_of_training_only": len(overlap) / len(selected_features),
        "overlap_features": overlap,
    }
    write_json(comparison, output / "comparison.json")

    input_paths = {
        "development_freeze.json": root / "results/freeze/development_freeze.json",
        "split_manifest.json": ml_root / "splits/split_manifest.json",
        "frozen_dataset_manifest.json": ml_root / "datasets/dataset_manifest.json",
        "frozen_feature_set.csv": ml_root / "features/frozen_feature_set.csv",
        "baseline_metrics.json": ml_root / "baseline/validation_metrics.json",
        "per_day_ic.csv": root / "results/predictive/per_day_ic.csv",
        "config.yaml": root / "config/config.yaml",
    }
    source_paths = [root / "data/processed" / f"day{day}.parquet" for day in (*training_days, *validation_days)]
    run_manifest = {
        "phase": "ML Phase 2 — Strict Training-Only Feature Selection",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "expected_development_days": scope.expected_development_days,
        "available_development_days": len(scope.available_development_days),
        "missing_development_days": list(scope.missing_development_days),
        "training_days": list(training_days),
        "validation_days": list(validation_days),
        "holdout_days_loaded": [],
        "source_days_loaded": [*training_days, *validation_days],
        "candidate_feature_count": int(daily_ic["feature"].nunique()),
        "candidate_hypothesis_count": int(len(aggregate)),
        "selected_feature_count": len(features),
        "selected_feature_names": list(features),
        "target_horizon_seconds": 300,
        "model": "ridge",
        "alpha": 1.0,
        "fit_intercept": True,
        "training_rows": int(model.n_train_samples_),
        "validation_rows": int(len(predictions)),
        "selection_days_only": list(training_days),
        "selection_rule": "pearson_fdr_reject AND pearson_pct_same_sign >= 0.70 AND abs(mean_pearson_ic) >= 0.05",
        "fdr_scope": "all candidate feature-horizon hypotheses, refit on training-day ICs",
        "validation_not_used_for_selection": True,
        "holdout_accessed": False,
        "input_sha256": {name: sha256_file(path) for name, path in input_paths.items()},
        "source_day_sha256": {f"day{day}.parquet": sha256_file(path) for day, path in zip((*training_days, *validation_days), source_paths)},
        "partition_reports": partition_reports,
        "prediction_partitions": prediction_partitions,
    }
    write_json(run_manifest, output / "run_manifest.json")
    write_json({
        "deterministic_selection": True,
        "deterministic_fit": True,
        "random_seed": None,
        "selection_days": list(training_days),
        "fit_days": list(training_days),
        "prediction_days": list(validation_days),
        "holdout_days_loaded": [],
        "model_artifact_sha256": sha256_file(model_path),
    }, output / "reproducibility.json")
    write_json({
        "model": model.summary(),
        "preprocessing": scaler.manifest(),
        "selected_feature_count": len(features),
        "selected_feature_names": list(features),
    }, output / "model_config.json")
    print(json.dumps({
        "phase": run_manifest["phase"],
        "candidate_feature_count": run_manifest["candidate_feature_count"],
        "candidate_hypothesis_count": run_manifest["candidate_hypothesis_count"],
        "selected_feature_count": run_manifest["selected_feature_count"],
        "training_rows": run_manifest["training_rows"],
        "validation_rows": run_manifest["validation_rows"],
        "pearson_ic": pooled["pearson_ic"],
        "spearman_ic": pooled["spearman_ic"],
        "r2": pooled["r2"],
        "mae": pooled["mae"],
        "rmse": pooled["rmse"],
        "holdout_days_loaded": [],
    }, indent=2))


if __name__ == "__main__":
    main()
