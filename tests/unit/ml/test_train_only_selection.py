import numpy as np
import pandas as pd
import pytest

from src.ebx.ml.schemas import DevelopmentScope
from src.ebx.ml.train_only_selection import fit_training_only_screen, load_training_daily_ic


def _scope():
    return DevelopmentScope(85, tuple(range(1, 65)) + tuple(range(80, 86)), tuple(range(65, 80)), tuple(range(86, 109)))


def _daily(days=(1, 2), value=0.08):
    rows = []
    for day in days:
        rows.append({
            "day": day, "feature": "f1", "horizon_seconds": 300,
            "pair_count": 100, "pearson_ic": value, "spearman_ic": value,
        })
    return pd.DataFrame(rows)


def test_selection_rejects_validation_or_holdout_rows():
    table = pd.concat([_daily(), _daily((80,), 1.0)], ignore_index=True)
    with pytest.raises(ValueError, match="non-training"):
        fit_training_only_screen(table, training_days=(1, 2), target_horizon=300, scope=_scope())


def test_selection_is_deterministic_and_uses_training_statistics_only():
    first, selected_first = fit_training_only_screen(_daily(), training_days=(1, 2), target_horizon=300, scope=_scope())
    second, selected_second = fit_training_only_screen(_daily(), training_days=(1, 2), target_horizon=300, scope=_scope())
    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(selected_first, selected_second)
    assert selected_first["feature"].tolist() == ["f1"]
    assert first.loc[0, "days_scored"] == 2


def test_selection_requires_complete_train_day_coverage():
    with pytest.raises(ValueError, match="incomplete"):
        fit_training_only_screen(_daily((1,)), training_days=(1, 2), target_horizon=300, scope=_scope())


def test_loader_retains_training_rows_and_rejects_holdout_rows(tmp_path):
    source = pd.DataFrame([
        {"day": 1, "feature": "f1", "horizon_seconds": 300, "pair_count": 10, "pearson_ic": 0.1, "spearman_ic": 0.1},
        {"day": 80, "feature": "f1", "horizon_seconds": 300, "pair_count": 10, "pearson_ic": 9.0, "spearman_ic": 9.0},
    ])
    path = tmp_path / "daily_ic.csv"
    source.to_csv(path, index=False)
    result = load_training_daily_ic(path, training_days=(1,), horizons=(300,), scope=_scope())
    assert result["day"].tolist() == [1]
    holdout = pd.concat([source, pd.DataFrame([{
        "day": 86, "feature": "f1", "horizon_seconds": 300, "pair_count": 10,
        "pearson_ic": 0.2, "spearman_ic": 0.2,
    }])], ignore_index=True)
    holdout.to_csv(path, index=False)
    with pytest.raises(ValueError, match="holdout"):
        load_training_daily_ic(path, training_days=(1,), horizons=(300,), scope=_scope())
