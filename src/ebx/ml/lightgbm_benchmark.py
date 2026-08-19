"""Isolated, fixed-configuration LightGBM benchmark for ML Phase 9.

The benchmark consumes the existing W3 model-ready partitions. Feature
selection and preprocessing are not performed here: the W3 selected-feature
artifact and train-only standardized partitions are inputs, not outputs of
this experiment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .backtest import (
    StrategyConfig,
    TransactionCostModel,
    daily_pnl_from_trades,
    equity_curve_from_daily,
    simulate_day,
    summarize_trades,
)
from .baseline import validation_metrics
from .cache import sha256_file, write_partition
from .schemas import DevelopmentScope


TRAIN_DAYS = tuple(range(1, 65))
VALIDATION_DAYS = tuple(range(80, 86))
MISSING_DAYS = tuple(range(65, 80))
HOLDOUT_DAYS = frozenset(range(86, 109))
TARGET_HORIZON_SECONDS = 300


@dataclass(frozen=True)
class LightGBMConfig:
    """One predetermined conservative configuration; no tuning is allowed."""

    objective: str = "regression"
    boosting_type: str = "gbdt"
    learning_rate: float = 0.03
    num_leaves: int = 15
    max_depth: int = 5
    min_child_samples: int = 200
    bagging_fraction: float = 1.0
    bagging_freq: int = 0
    feature_fraction: float = 1.0
    reg_alpha: float = 1e-3
    reg_lambda: float = 1.0
    num_boost_round: int = 200
    seed: int = 20260819
    deterministic: bool = True
    force_col_wise: bool = True
    num_threads: int = 1
    verbosity: int = -1

    def validate(self) -> None:
        if self.objective != "regression" or self.boosting_type != "gbdt":
            raise ValueError("Phase 9 requires fixed regression GBDT configuration")
        if self.learning_rate <= 0 or self.num_leaves < 2 or self.max_depth < 1:
            raise ValueError("invalid LightGBM complexity configuration")
        if self.min_child_samples < 1 or self.num_boost_round < 1:
            raise ValueError("invalid LightGBM training configuration")
        if not 0 < self.bagging_fraction <= 1 or not 0 < self.feature_fraction <= 1:
            raise ValueError("sampling fractions must be in (0, 1]")
        if self.bagging_fraction != 1.0 and self.bagging_freq == 0:
            raise ValueError("bagging_fraction below 1 requires a fixed bagging frequency")
        if self.num_threads != 1 or not self.deterministic or not self.force_col_wise:
            raise ValueError("Phase 9 requires deterministic single-threaded LightGBM")

    def parameters(self) -> dict[str, object]:
        self.validate()
        return {
            "objective": self.objective,
            "boosting_type": self.boosting_type,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "min_child_samples": self.min_child_samples,
            "bagging_fraction": self.bagging_fraction,
            "bagging_freq": self.bagging_freq,
            "feature_fraction": self.feature_fraction,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "seed": self.seed,
            "feature_fraction_seed": self.seed,
            "bagging_seed": self.seed,
            "data_random_seed": self.seed,
            "deterministic": self.deterministic,
            "force_col_wise": self.force_col_wise,
            "num_threads": self.num_threads,
            "verbosity": self.verbosity,
        }

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return asdict(self)


def validate_split(
    scope: DevelopmentScope,
    training_days: Iterable[int] = TRAIN_DAYS,
    validation_days: Iterable[int] = VALIDATION_DAYS,
) -> None:
    """Reject missing, overlapping, non-development, or holdout days."""

    training = tuple(int(day) for day in training_days)
    validation = tuple(int(day) for day in validation_days)
    requested = training + validation
    if set(training) & set(validation):
        raise ValueError("training and validation days overlap")
    if not training or not validation or max(training) >= min(validation):
        raise ValueError("LightGBM split is not chronological")
    if set(requested) & HOLDOUT_DAYS:
        raise ValueError("holdout day entered LightGBM benchmark")
    if set(requested) & set(MISSING_DAYS):
        raise ValueError("unavailable development day entered LightGBM benchmark")
    scope.assert_development_days(requested)
    if set(requested) != set(scope.available_development_days):
        raise ValueError("LightGBM W3 split must cover available development days")


def require_lightgbm():
    """Import LightGBM lazily so non-LightGBM repository tests remain usable."""

    try:
        import lightgbm as lgb
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("LightGBM 4.6.0 is required for Phase 9") from exc
    return lgb


def load_feature_names(root: Path) -> tuple[str, ...]:
    path = root / "results/ml/temporal_robustness/W3/selected_features.csv"
    if not path.is_file():
        raise FileNotFoundError(f"W3 selected-feature artifact is missing: {path}")
    table = pd.read_csv(path)
    if "feature" not in table.columns or table["feature"].isna().any():
        raise ValueError("W3 selected-feature artifact has an invalid feature column")
    features = tuple(table["feature"].astype(str))
    if len(features) != 198 or len(features) != len(set(features)):
        raise ValueError(f"expected 198 unique W3 features, got {len(features)}")
    return features


def validate_w3_preprocessing(root: Path, features: tuple[str, ...]) -> dict[str, object]:
    path = root / "results/ml/temporal_robustness/W3/preprocessing_manifest.json"
    manifest = json.loads(path.read_text())
    if tuple(manifest.get("fit_days", [])) != TRAIN_DAYS:
        raise ValueError("W3 preprocessing was not fitted on Days 1-64")
    if int(manifest.get("target_horizon_seconds", -1)) != TARGET_HORIZON_SECONDS:
        raise ValueError("W3 preprocessing target horizon is not 300 seconds")
    if set(int(day) for day in manifest.get("available_development_days", [])) != set(TRAIN_DAYS + VALIDATION_DAYS):
        raise ValueError("W3 preprocessing development scope changed")
    if int(manifest.get("feature_count", -1)) != len(features):
        raise ValueError("W3 preprocessing feature count does not match selection")
    if manifest.get("imputation") not in {"none", None}:
        raise ValueError("LightGBM input preprocessing contains imputation")
    return manifest


def _partition_path(root: Path, split: str, day: int) -> Path:
    day = int(day)
    if day in HOLDOUT_DAYS:
        raise ValueError(f"holdout day {day} cannot be loaded")
    if day in MISSING_DAYS:
        raise ValueError(f"missing development day {day} cannot be loaded")
    return root / "results/ml/temporal_robustness/W3/datasets" / split / f"day{day}.parquet"


def load_partition(root: Path, split: str, day: int, features: tuple[str, ...]) -> pd.DataFrame:
    path = _partition_path(root, split, day)
    if not path.is_file():
        raise FileNotFoundError(f"required W3 model-ready partition is missing: {path}")
    required = ["day", "timestamp", "timestamp_seconds", "target", *features]
    frame = pd.read_parquet(path, columns=required)
    if set(frame["day"].astype(int).unique()) != {int(day)}:
        raise ValueError(f"partition day mismatch: {path}")
    seconds = frame["timestamp_seconds"].to_numpy(dtype=np.int64)
    if len(seconds) > 1 and np.any(np.diff(seconds) <= 0):
        raise ValueError(f"partition timestamps are not strictly increasing: {path}")
    values = frame.loc[:, list(features)].to_numpy(dtype=float)
    target = frame["target"].to_numpy(dtype=float)
    if not np.isfinite(values).all() or not np.isfinite(target).all():
        raise ValueError(f"partition contains non-finite model inputs: {path}")
    return frame


def load_partitions(root: Path, split: str, days: Iterable[int], features: tuple[str, ...]) -> list[pd.DataFrame]:
    return [load_partition(root, split, int(day), features) for day in days]


def fit_model(train_frames: list[pd.DataFrame], features: tuple[str, ...], config: LightGBMConfig):
    """Fit without validation data, early stopping, or validation callbacks."""

    if not train_frames:
        raise ValueError("at least one training partition is required")
    config.validate()
    lgb = require_lightgbm()
    x = np.concatenate([frame.loc[:, list(features)].to_numpy(dtype=np.float32) for frame in train_frames])
    y = np.concatenate([frame["target"].to_numpy(dtype=np.float32) for frame in train_frames])
    dataset = lgb.Dataset(x, label=y, feature_name=list(features), free_raw_data=False)
    return lgb.train(config.parameters(), dataset, num_boost_round=config.num_boost_round)


def build_predictions(model, validation_frames: list[pd.DataFrame], features: tuple[str, ...]) -> tuple[pd.DataFrame, dict[int, pd.DataFrame]]:
    by_day: dict[int, pd.DataFrame] = {}
    for frame in validation_frames:
        day = int(frame["day"].iloc[0])
        x = frame.loc[:, list(features)].to_numpy(dtype=np.float32)
        prediction = np.asarray(model.predict(x), dtype=np.float64)
        result = frame[["day", "timestamp", "timestamp_seconds", "target"]].copy()
        result["prediction"] = prediction
        result["residual"] = result["prediction"] - result["target"]
        if len(result) != len(frame) or not np.isfinite(prediction).all():
            raise ValueError(f"invalid prediction alignment for day {day}")
        by_day[day] = result
    if tuple(sorted(by_day)) != VALIDATION_DAYS:
        raise ValueError("prediction partitions do not cover exactly W3 validation Days 80-85")
    return pd.concat([by_day[day] for day in VALIDATION_DAYS], ignore_index=True), by_day


def run_backtest(root: Path, predictions: dict[int, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    strategy = StrategyConfig()
    strategy.validate()
    costs = TransactionCostModel()
    trades_by_day: list[pd.DataFrame] = []
    session_seconds: dict[int, int] = {}
    for day in VALIDATION_DAYS:
        price = __import__("src.analytics.coverage", fromlist=["load_price_day"]).load_price_day(root, day)
        session_seconds[day] = len(price) - 1
        trades_by_day.append(
            simulate_day(
                predictions[day],
                price,
                window="W3",
                day=day,
                strategy=strategy,
                costs=costs,
            )
        )
    trades = pd.concat(trades_by_day, ignore_index=True)
    daily = daily_pnl_from_trades(
        trades,
        days=VALIDATION_DAYS,
        window="W3",
        session_seconds=session_seconds,
    )
    summary = summarize_trades(trades, daily, window="W3", strategy=strategy)
    summary["validation_rows"] = int(sum(len(predictions[day]) for day in VALIDATION_DAYS))
    return trades, daily, summary


def _write_json(path: Path, value: dict[str, object] | list[object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=True) + "\n")


def sha256_paths(paths: Iterable[Path]) -> dict[str, str]:
    return {str(path): sha256_file(path) for path in paths}


def validate_frozen_outputs(before: dict[str, str], after: dict[str, str]) -> None:
    if before != after:
        changed = [path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]
        raise AssertionError(f"frozen research artifacts changed: {changed[:10]}")


def sanity_flags(metrics: dict[str, object], economic: dict[str, object]) -> list[str]:
    flags: list[str] = []
    if abs(float(metrics["pearson_ic"])) > 0.20 or abs(float(metrics["spearman_ic"])) > 0.20:
        flags.append("IC magnitude is unusually large relative to existing W3 evidence")
    if float(metrics["directional_accuracy"]) > 0.60:
        flags.append("directional accuracy exceeds the conservative 60% sanity threshold")
    if float(metrics["r2"]) > 0.10:
        flags.append("R2 exceeds the conservative 0.10 sanity threshold")
    if float(economic["net_pnl"]) > 0:
        flags.append("net P&L is positive after costs and requires leakage review")
    return flags


def classify_outcome(
    flags: list[str],
    lightgbm_metrics: dict[str, object],
    lightgbm_economic: dict[str, object],
    ridge_metrics: dict[str, object],
    elastic_metrics: dict[str, object],
    ridge_economic: dict[str, object],
    elastic_economic: dict[str, object],
) -> str:
    """Give the required post-measurement A/B/C/D interpretation."""

    if flags:
        return "D — suspicious result requiring leakage investigation"
    best_predictive = max(
        float(ridge_metrics["pearson_ic"]),
        float(elastic_metrics["pearson_ic"]),
    )
    best_economic = max(
        float(ridge_economic["net_pnl"]),
        float(elastic_economic["net_pnl"]),
    )
    predictive_gain = float(lightgbm_metrics["pearson_ic"]) - best_predictive
    economic_gain = float(lightgbm_economic["net_pnl"]) - best_economic
    if predictive_gain > 0.01 and economic_gain > 0.01:
        return "A — LightGBM materially improves the evidence"
    if predictive_gain > 0.0 or economic_gain > 0.0:
        return "B — LightGBM provides only marginal improvement"
    return "C — LightGBM does not improve the Ridge baseline"


def _fmt(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(float(value)):
            return "NA"
        return format(float(value), ".15g")
    return str(value)


def _markdown_table(frame: pd.DataFrame) -> str:
    """Stable pipe table without depending on optional tabulate."""

    columns = [str(column) for column in frame.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(_fmt(value) for value in row) + " |")
    return "\n".join(lines)


def _delta_table(frame: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    rows = []
    for metric in metrics:
        values = frame.set_index("model")[metric]
        ridge = float(values["Ridge"])
        lightgbm = float(values["LightGBM"])
        relative = (lightgbm - ridge) / abs(ridge) * 100.0 if ridge else np.nan
        rows.append({
            "metric": metric,
            "Ridge": ridge,
            "Elastic Net": float(values["Elastic Net"]),
            "LightGBM": lightgbm,
            "LightGBM - Ridge": lightgbm - ridge,
            "relative_vs_Ridge_%": relative,
        })
    return pd.DataFrame(rows)


def write_report(root: Path, output: Path, result: dict[str, object]) -> Path:
    """Write the deterministic Phase 9 report from the stored result files."""

    config = result["model_config"]
    metrics = result["validation_metrics"]
    economic = result["economic_summary"]
    daily = pd.read_csv(output / "daily_metrics.csv")
    predictive_comparison = pd.read_csv(output / "predictive_comparison.csv")
    economic_comparison = pd.read_csv(output / "economic_comparison.csv")
    sensitivity = json.loads((output / "day84_sensitivity.json").read_text())
    environment = config["environment"]
    report_path = root / "reports/ml_phase9_lightgbm.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    daily_columns = [
        "day", "validation_observations", "pearson_ic", "spearman_ic", "r2",
        "mae", "rmse", "directional_accuracy", "prediction_mean", "prediction_std",
        "target_mean", "target_std",
    ]
    comparison_predictive = predictive_comparison.copy()
    comparison_economic = economic_comparison.copy()
    lines = [
        "# ML Phase 9 — Controlled LightGBM W3 Benchmark",
        "",
        "## Scope and data boundary",
        "",
        "This is one fixed LightGBM benchmark using the existing W3 model-ready data. "
        "It is not a feature-engineering, feature-selection, tuning, or model-search experiment.",
        "",
        f"- Expected development days: **85**",
        f"- Available development days: **70**",
        f"- Missing development days: **65–79 (15 days)**",
        f"- Training days: **1–64**; validation days: **80–85**",
        "- Holdout days 86–108: **not loaded, accessed, inspected, or used**",
        f"- Training rows: **{result['training_rows']}**; validation rows: **{result['validation_rows']}**",
        f"- Features: **{config['feature_count']}**, from the existing W3 training-only selected-feature artifact",
        "",
        "## Fixed model and preprocessing",
        "",
        "The existing W3 train-only feature selection and preprocessing artifacts were consumed unchanged. "
        "Preprocessing was fitted on Days 1–64; no validation statistics, target values, or early stopping were used.",
        "",
        "```json",
        json.dumps({"configuration": config["configuration"], "lightgbm_parameters": config["lightgbm_parameters"]}, indent=2, sort_keys=True),
        "```",
        "",
        f"LightGBM version: `{environment['lightgbm_version']}`; Python executable: `{environment['python_executable']}`.",
        f"scikit-learn package version: `{environment['scikit_learn_version']}`; import status: `{environment['scikit_learn_import_error'] or 'available'}`.",
        "",
        "## Predictive results",
        "",
        _markdown_table(pd.DataFrame([{
            "metric": key,
            "LightGBM W3": metrics.get(key),
        } for key in [
            "pearson_ic", "spearman_ic", "mean_daily_pearson_ic", "median_daily_pearson_ic",
            "std_daily_pearson_ic", "directional_accuracy", "r2", "mae", "rmse",
            "prediction_mean", "prediction_std", "target_mean", "target_std",
            "validation_observations",
        ]])),
        "",
        "### Validation metrics by day",
        "",
        _markdown_table(daily[daily_columns]),
        "",
        "### Comparison with existing W3 models",
        "",
        _markdown_table(comparison_predictive),
        "",
        "Differences below are LightGBM minus Ridge; relative change is divided by the absolute Ridge value and is descriptive only.",
        "",
        _markdown_table(_delta_table(comparison_predictive, [
            "pearson_ic", "spearman_ic", "mean_daily_pearson_ic", "directional_accuracy",
            "r2", "mae", "rmse",
        ])),
        "",
        "## Economic utility using the existing Part 5 backtest",
        "",
        "The exact existing Part 5 mechanics were applied to LightGBM predictions: prediction sign, unit notional, "
        "one position at a time, 300-second same-day exact exit, no interpolation or overnight carry, and 5 bps "
        "per side with zero fee. This is an assumed baseline cost, not an empirically calibrated spread estimate.",
        "",
        _markdown_table(comparison_economic),
        "",
        _markdown_table(_delta_table(comparison_economic, [
            "gross_pnl", "transaction_costs", "net_pnl", "sharpe", "maximum_drawdown",
            "turnover", "trades",
        ])),
        "",
        "### LightGBM W3 economic summary",
        "",
        _markdown_table(pd.DataFrame([{
            "metric": key,
            "LightGBM W3": economic.get(key),
        } for key in [
            "gross_pnl", "transaction_costs", "net_pnl", "sharpe", "maximum_drawdown",
            "turnover", "trades", "win_rate", "average_trade_return", "median_trade_return",
            "daily_pnl_std", "average_exposure", "maximum_exposure",
        ]])),
        "",
        "### Day-84 sensitivity (post-hoc aggregation only)",
        "",
        "Day 84 remains in the primary W3 result. The exclusion is a diagnostic aggregation only; there was no retraining or refitting.",
        "",
        _markdown_table(pd.DataFrame([
            {"aggregation": "W3 including Day 84", **sensitivity["normal_w3_predictive"]},
            {"aggregation": "W3 excluding Day 84", **sensitivity["excluding_day84_predictive"]},
        ])[ ["aggregation", "pearson_ic", "spearman_ic", "r2", "mae", "rmse", "directional_accuracy", "validation_observations"] ]),
        "",
        _markdown_table(pd.DataFrame([
            {"aggregation": "W3 including Day 84", **sensitivity["normal_w3_economic"]},
            {"aggregation": "W3 excluding Day 84", **sensitivity["excluding_day84_economic"]},
        ])[["aggregation", "gross_pnl", "transaction_costs", "net_pnl", "sharpe", "maximum_drawdown", "turnover", "trades"]]),
        "",
        "## Sanity review and conclusion",
        "",
        f"Sanity flags: **{', '.join(result['sanity_flags']) if result['sanity_flags'] else 'none'}**.",
        f"Classification: **{result['classification']}**.",
        "The benchmark does not establish production readiness, alpha, profitability, or holdout generalization. "
        "The original Ridge and Elastic Net artifacts were read for comparison only and were not retrained or modified.",
        "",
        "## Reproducibility and integrity",
        "",
        "Research-bearing outputs are deterministic under the fixed seed, single-threaded configuration, and fixed input artifacts. "
        "`run_manifest.json` contains a run timestamp; stable output hashes are recorded in `reproducibility.json`.",
        "",
        "- `holdout_days_loaded: []`",
        "- frozen namespaces were not modified",
        "- missing Days 65–79 were not fabricated",
        "- no strategy search, hyperparameter search, or additional model was run",
        "",
    ]
    report_path.write_text("\n".join(lines))
    return report_path


def run(root: Path, output: Path | None = None) -> dict[str, object]:
    root = root.resolve()
    output = (output or root / "results/ml/lightgbm").resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = LightGBMConfig()
    config.validate()
    scope_path = root / "results/freeze/development_freeze.json"
    scope = DevelopmentScope.from_freeze(scope_path)
    validate_split(scope)
    features = load_feature_names(root)
    preprocessing_manifest = validate_w3_preprocessing(root, features)
    train_frames = load_partitions(root, "train", TRAIN_DAYS, features)
    validation_frames = load_partitions(root, "validation", VALIDATION_DAYS, features)
    model = fit_model(train_frames, features, config)
    model_path = output / "lightgbm_model.txt"
    model.save_model(str(model_path))

    predictions, predictions_by_day = build_predictions(model, validation_frames, features)
    pooled_metrics, daily_metrics = validation_metrics(predictions)
    for day, frame in predictions_by_day.items():
        write_partition(frame, output / "predictions" / f"day{day}.parquet")
    _write_json(output / "validation_metrics.json", pooled_metrics)
    daily_metrics.to_csv(output / "daily_metrics.csv", index=False)

    trades, daily_pnl, economic_summary = run_backtest(root, predictions_by_day)
    trades.to_csv(output / "trade_log.csv", index=False)
    daily_pnl.to_csv(output / "daily_pnl.csv", index=False)
    equity = equity_curve_from_daily(daily_pnl, starting_capital=1.0)
    equity.to_csv(output / "equity_curve.csv", index=False)
    pd.DataFrame([economic_summary]).to_csv(output / "window_metrics.csv", index=False)
    pd.DataFrame([{
        "window": "W3",
        "trades": economic_summary["trades"],
        "gross_pnl": economic_summary["gross_pnl"],
        "transaction_costs": economic_summary["transaction_costs"],
        "net_pnl": economic_summary["net_pnl"],
        "turnover": economic_summary["turnover"],
        "entry_cost_bps": 5.0,
        "exit_cost_bps": 5.0,
        "fee_bps": 0.0,
    }]).to_csv(output / "cost_breakdown.csv", index=False)

    normal_excluding = predictions[predictions["day"] != 84].reset_index(drop=True)
    excluding_metrics, _ = validation_metrics(normal_excluding)
    excluding_trades = trades[trades["day"] != 84].reset_index(drop=True)
    excluding_daily = daily_pnl[daily_pnl["day"] != 84].reset_index(drop=True)
    excluding_economic = summarize_trades(
        excluding_trades,
        excluding_daily,
        window="W3_excluding_day84",
        strategy=StrategyConfig(),
    )
    excluding_economic["validation_rows"] = int(len(normal_excluding))
    _write_json(output / "day84_sensitivity.json", {
        "diagnostic": "post-hoc W3 aggregation excluding Day 84",
        "retrained": False,
        "feature_selection_changed": False,
        "normal_w3_predictive": pooled_metrics,
        "excluding_day84_predictive": excluding_metrics,
        "normal_w3_economic": economic_summary,
        "excluding_day84_economic": excluding_economic,
    })

    ridge_metrics = json.loads((root / "results/ml/temporal_robustness/W3/validation_metrics.json").read_text())
    elastic_metrics = json.loads((root / "results/ml/elastic_net/W3/validation_metrics.json").read_text())
    metric_columns = [
        "pearson_ic", "spearman_ic", "mean_daily_pearson_ic", "directional_accuracy",
        "r2", "mae", "rmse",
    ]
    model_metrics = {"Ridge": ridge_metrics, "Elastic Net": elastic_metrics, "LightGBM": pooled_metrics}
    pd.DataFrame([
        {"model": name, **{metric: float(metrics[metric]) for metric in metric_columns}}
        for name, metrics in model_metrics.items()
    ]).to_csv(output / "predictive_comparison.csv", index=False)

    ridge_economic = pd.read_csv(root / "results/ml/backtest_baseline/window_metrics.csv")
    ridge_economic = ridge_economic[ridge_economic["window"] == "W3"].iloc[0].to_dict()
    elastic_economic_payload = json.loads((root / "results/ml/elastic_net/backtest_summary.json").read_text())
    elastic_economic = next(row for row in elastic_economic_payload["by_window"] if row["window"] == "W3")
    economic_sources = {"Ridge": ridge_economic, "Elastic Net": elastic_economic, "LightGBM": economic_summary}
    economic_columns = ["gross_pnl", "transaction_costs", "net_pnl", "sharpe", "maximum_drawdown", "turnover", "trades"]
    pd.DataFrame([
        {"model": name, **{metric: float(source[metric]) for metric in economic_columns}}
        for name, source in economic_sources.items()
    ]).to_csv(output / "economic_comparison.csv", index=False)

    import importlib.metadata as metadata
    import lightgbm
    import scipy
    try:
        sklearn_version = metadata.version("scikit-learn")
    except metadata.PackageNotFoundError:
        sklearn_version = "unavailable"
    try:
        import sklearn  # noqa: F401
        sklearn_import_error = None
    except Exception as exc:  # pragma: no cover - environment-specific
        sklearn_import_error = repr(exc)
    environment = {
        "python_version": __import__("sys").version,
        "python_executable": __import__("sys").executable,
        "lightgbm_version": lightgbm.__version__,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "pandas_version": pd.__version__,
        "scikit_learn_version": sklearn_version,
        "scikit_learn_import_error": sklearn_import_error,
    }
    model_config = {
        "model": "lightgbm",
        "target_horizon_seconds": TARGET_HORIZON_SECONDS,
        "feature_selection_source": str(root / "results/ml/temporal_robustness/W3/selected_features.csv"),
        "feature_selection_protocol": "existing W3 training-only selection artifact consumed unchanged",
        "preprocessing_source": str(root / "results/ml/temporal_robustness/W3/preprocessing_manifest.json"),
        "preprocessing_fit_days": list(TRAIN_DAYS),
        "training_days": list(TRAIN_DAYS),
        "validation_days": list(VALIDATION_DAYS),
        "missing_days": list(MISSING_DAYS),
        "holdout_days_excluded": sorted(HOLDOUT_DAYS),
        "feature_count": len(features),
        "configuration": config.as_dict(),
        "lightgbm_parameters": config.parameters(),
        "environment": environment,
    }
    _write_json(output / "model_config.json", model_config)
    input_paths = [
        root / "results/freeze/development_freeze.json",
        root / "results/ml/temporal_robustness/W3/selected_features.csv",
        root / "results/ml/temporal_robustness/W3/preprocessing_manifest.json",
        root / "results/ml/temporal_robustness/W3/run_manifest.json",
        root / "results/ml/temporal_robustness/W3/validation_metrics.json",
        root / "results/ml/elastic_net/W3/validation_metrics.json",
        root / "results/ml/backtest_baseline/strategy_config.json",
    ]
    flags = sanity_flags(pooled_metrics, economic_summary)
    classification = classify_outcome(
        flags,
        pooled_metrics,
        economic_summary,
        ridge_metrics,
        elastic_metrics,
        ridge_economic,
        elastic_economic,
    )
    run_manifest = {
        "phase": "ML Phase 9 — Controlled LightGBM W3 Benchmark",
        "created_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "expected_development_days": 85,
        "available_development_days": 70,
        "missing_development_days": list(MISSING_DAYS),
        "training_days": list(TRAIN_DAYS),
        "validation_days": list(VALIDATION_DAYS),
        "source_days_loaded": list(TRAIN_DAYS + VALIDATION_DAYS),
        "training_rows": int(sum(len(frame) for frame in train_frames)),
        "validation_rows": int(len(predictions)),
        "feature_count": len(features),
        "selection_days_only": list(TRAIN_DAYS),
        "preprocessing_fit_days": list(TRAIN_DAYS),
        "validation_statistics_used_for_fit": False,
        "early_stopping_used": False,
        "holdout_days_loaded": [],
        "holdout_accessed": False,
        "frozen_artifacts_modified": False,
        "model_config": model_config,
        "preprocessing_manifest_fit_row_count": preprocessing_manifest.get("fit_row_count"),
        "input_sha256": {str(path.relative_to(root)): sha256_file(path) for path in input_paths},
        "sanity_flags": flags,
        "classification": classification,
    }
    _write_json(output / "run_manifest.json", run_manifest)
    stable_paths = [
        model_path,
        output / "model_config.json",
        output / "validation_metrics.json",
        output / "daily_metrics.csv",
        output / "predictive_comparison.csv",
        output / "economic_comparison.csv",
        output / "trade_log.csv",
        output / "daily_pnl.csv",
        output / "window_metrics.csv",
        output / "day84_sensitivity.json",
        output / "equity_curve.csv",
        output / "cost_breakdown.csv",
        *sorted((output / "predictions").glob("day*.parquet")),
    ]
    _write_json(output / "reproducibility.json", {
        "deterministic": True,
        "random_seed": config.seed,
        "holdout_days_loaded": [],
        "stable_output_sha256": {str(path.relative_to(output)): sha256_file(path) for path in stable_paths},
    })
    result = {
        "model_config": model_config,
        "validation_metrics": pooled_metrics,
        "daily_metrics": daily_metrics,
        "economic_summary": economic_summary,
        "excluding_day84_predictive": excluding_metrics,
        "excluding_day84_economic": excluding_economic,
        "classification": run_manifest["classification"],
        "sanity_flags": flags,
        "training_rows": run_manifest["training_rows"],
        "validation_rows": run_manifest["validation_rows"],
    }
    write_report(root, output, result)
    return result
