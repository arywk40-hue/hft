"""Run the fixed LightGBM W3 benchmark and write isolated Phase 9 outputs."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ebx.ml.lightgbm_benchmark import run  # noqa: E402


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    result = run(root)
    metrics = result["validation_metrics"]
    print({
        "phase": "ML Phase 9 — Controlled LightGBM W3 Benchmark",
        "training_rows": result["training_rows"],
        "validation_rows": result["validation_rows"],
        "feature_count": result["model_config"]["feature_count"],
        "pearson_ic": metrics["pearson_ic"],
        "spearman_ic": metrics["spearman_ic"],
        "directional_accuracy": metrics["directional_accuracy"],
        "r2": metrics["r2"],
        "mae": metrics["mae"],
        "rmse": metrics["rmse"],
        "net_pnl": result["economic_summary"]["net_pnl"],
        "classification": result["classification"],
        "holdout_days_loaded": [],
    })


if __name__ == "__main__":
    main()
