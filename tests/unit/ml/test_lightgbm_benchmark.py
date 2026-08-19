import numpy as np
import pandas as pd
import pytest

from src.ebx.ml.lightgbm_benchmark import (
    LightGBMConfig,
    MISSING_DAYS,
    HOLDOUT_DAYS,
    TARGET_HORIZON_SECONDS,
    TRAIN_DAYS,
    VALIDATION_DAYS,
    build_predictions,
    validate_split,
)
from src.ebx.ml.baseline import validation_metrics


def test_configuration_is_fixed_and_deterministic():
    config = LightGBMConfig()
    assert config.parameters()["seed"] == 20260819
    assert config.parameters()["num_threads"] == 1
    assert config.parameters()["deterministic"] is True
    assert config.num_boost_round == 200
    assert config.bagging_fraction == 1.0


def test_split_rejects_holdout_and_missing_days():
    from src.ebx.ml.schemas import DevelopmentScope

    scope = DevelopmentScope(85, tuple(range(1, 65)) + tuple(range(80, 86)), tuple(range(65, 80)), tuple(range(86, 109)))
    with pytest.raises(ValueError, match="holdout"):
        validate_split(scope, validation_days=[86])
    with pytest.raises(ValueError, match="unavailable"):
        validate_split(scope, validation_days=[65])


def test_phase_boundary_and_target_are_fixed():
    assert TRAIN_DAYS == tuple(range(1, 65))
    assert VALIDATION_DAYS == tuple(range(80, 86))
    assert MISSING_DAYS == tuple(range(65, 80))
    assert HOLDOUT_DAYS == frozenset(range(86, 109))
    assert TARGET_HORIZON_SECONDS == 300


def test_prediction_alignment_preserves_validation_day_order():
    class Model:
        def predict(self, values):
            return np.zeros(len(values), dtype=float)

    frames = []
    for day in VALIDATION_DAYS:
        frames.append(pd.DataFrame({
            "day": [day, day],
            "timestamp": ["00:00:00", "00:00:01"],
            "timestamp_seconds": [0, 1],
            "target": [0.1, -0.1],
            "x": [1.0, 2.0],
        }))
    combined, by_day = build_predictions(Model(), frames, ("x",))
    assert tuple(combined.day.drop_duplicates()) == VALIDATION_DAYS
    assert tuple(by_day) == VALIDATION_DAYS
    assert combined.prediction.tolist() == [0.0] * 12


def test_lightgbm_fit_is_reproducible_when_dependency_is_available():
    lgb = pytest.importorskip("lightgbm")
    from src.ebx.ml.lightgbm_benchmark import fit_model

    frames = [pd.DataFrame({"day": [1, 1, 2, 2], "x": [0.0, 1.0, 0.0, 1.0], "target": [0.0, 1.0, 0.0, 1.0]})]
    config = LightGBMConfig(num_boost_round=5, min_child_samples=1)
    first = fit_model(frames, ("x",), config).predict(np.asarray([[0.25], [0.75]], dtype=np.float32))
    second = fit_model(frames, ("x",), config).predict(np.asarray([[0.25], [0.75]], dtype=np.float32))
    assert np.array_equal(first, second)


def test_validation_metric_calculation_uses_aligned_rows():
    predictions = pd.DataFrame({
        "day": [80, 80, 81, 81],
        "target": [1.0, -1.0, 1.0, -1.0],
        "prediction": [1.0, -1.0, -1.0, 1.0],
    })
    pooled, daily = validation_metrics(predictions)
    assert len(daily) == 2
    assert pooled["validation_observations"] == 4
    assert pooled["directional_accuracy"] == 0.5
    assert daily.loc[daily["day"] == 80, "directional_accuracy"].iloc[0] == 1.0
