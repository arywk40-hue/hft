"""Synthetic temporal-causality and leakage stress tests.

The raw PB/VB/BB/PV/V feature formulas are not implemented in this
repository.  These tests therefore cover the in-repository candidate formula
implementation and explicitly labelled synthetic family probes; they do not
claim to reconstruct the source CSV producer's formulas.
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.candidates import PRICE_CANDIDATES, RETURN_CANDIDATES, candidate_series
from src.ebx.ml.preprocessing import TrainOnlyStandardizer, complete_case_mask
from src.ebx.ml.targets import build_future_return_target


def _prices(size: int = 700) -> np.ndarray:
    index = np.arange(size, dtype=float)
    return 100.0 + 0.01 * index + 0.5 * np.sin(index / 13.0)


def _frame(prices: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({
        "Time": [f"{i // 3600:02d}:{(i % 3600) // 60:02d}:{i % 60:02d}" for i in range(len(prices))],
        "Price": prices,
    })


@pytest.mark.parametrize("name", (*PRICE_CANDIDATES, *RETURN_CANDIDATES))
def test_in_repository_candidate_at_t_is_invariant_to_future_perturbation(name):
    base = _prices()
    changed = base.copy()
    timestamp = 400
    changed[timestamp + 1:timestamp + 301] = 1_000_000.0

    before = candidate_series(base, name, 30)
    after = candidate_series(changed, name, 30)

    assert np.isfinite(before[timestamp])
    assert np.isfinite(after[timestamp])
    assert after[timestamp] == before[timestamp]


def _synthetic_family_probe(family: str, price: np.ndarray, volume: np.ndarray, window: int) -> np.ndarray:
    """A causal test probe, not a claim about the raw feature formula."""

    p = pd.Series(price)
    v = pd.Series(volume)
    if family == "PB":
        return p.rolling(window, min_periods=window).mean().to_numpy()
    if family == "BB":
        return ((p - p.rolling(window, min_periods=window).mean()) /
                p.rolling(window, min_periods=window).std()).to_numpy()
    if family == "V":
        return v.rolling(window, min_periods=window).mean().to_numpy()
    if family == "VB":
        return (v / v.shift(window) - 1.0).to_numpy()
    if family == "PV":
        return (p * v).rolling(window, min_periods=window).mean().to_numpy()
    raise ValueError(family)


@pytest.mark.parametrize("family", ("PB", "VB", "BB", "PV", "V"))
@pytest.mark.parametrize("window", (5, 30))
def test_synthetic_family_probes_are_future_invariant(family, window):
    price = _prices()
    volume = 1_000.0 + 3.0 * np.arange(len(price)) + 10.0 * np.cos(np.arange(len(price)) / 9.0)
    changed_price = price.copy()
    changed_volume = volume.copy()
    timestamp = 400
    changed_price[timestamp + 1:timestamp + 301] = 1_000_000.0
    changed_volume[timestamp + 1:timestamp + 301] = 1_000_000.0

    before = _synthetic_family_probe(family, price, volume, window)
    after = _synthetic_family_probe(family, changed_price, changed_volume, window)
    assert np.isfinite(before[timestamp])
    assert np.isfinite(after[timestamp])
    assert after[timestamp] == before[timestamp]


def test_target_injection_changes_only_the_target_not_causal_candidates():
    base = _prices()
    changed = base.copy()
    timestamp = 250
    horizon = 300
    changed[timestamp + horizon] *= 2.0
    frame_a = _frame(base)
    frame_b = _frame(changed)
    target_a = build_future_return_target(frame_a, horizon)
    target_b = build_future_return_target(frame_b, horizon)
    assert target_a.iloc[timestamp] != target_b.iloc[timestamp]

    for name in (*PRICE_CANDIDATES, *RETURN_CANDIDATES):
        feature_a = candidate_series(base, name, 30)
        feature_b = candidate_series(changed, name, 30)
        assert feature_a[timestamp] == feature_b[timestamp], name


def test_day_local_feature_and_target_calculation_does_not_cross_boundaries():
    day_one = _prices(100)
    day_two = _prices(100) + 10_000.0
    extreme_day_one = np.full_like(day_one, 1_000_000.0)
    local = candidate_series(day_two, "rolling_mean", 5)
    with_extreme_previous_day = candidate_series(
        np.concatenate([extreme_day_one, day_two]), "rolling_mean", 5
    )[100:]
    assert np.isnan(local[:4]).all()
    assert not np.array_equal(local, with_extreme_previous_day, equal_nan=True)

    reset_times = pd.concat([_frame(day_one), _frame(day_two)], ignore_index=True)
    with pytest.raises(ValueError, match="strictly increasing"):
        build_future_return_target(reset_times, 5)


def test_structural_warmup_is_not_backfilled_or_forward_filled():
    result = candidate_series(_prices(100), "rolling_mean", 5)
    assert np.isnan(result[:4]).all()
    assert np.isfinite(result[4:]).all()
    assert not np.isfinite(result[:4]).any()


def test_train_only_preprocessing_ignores_validation_values_and_does_not_impute():
    features = ("x", "y")
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [10.0, 20.0, 30.0]})
    validation = pd.DataFrame({"x": [1000.0, 2000.0], "y": [10000.0, 20000.0]})
    standardizer = TrainOnlyStandardizer(features)
    standardizer.update(train)
    standardizer.finalize()
    train_mean = standardizer.mean.copy()
    train_scale = standardizer.scale.copy()
    transformed = standardizer.transform(validation)
    assert np.array_equal(standardizer.mean, train_mean)
    assert np.array_equal(standardizer.scale, train_scale)
    assert np.isfinite(transformed.to_numpy()).all()

    raw = pd.DataFrame({"x": [1.0, np.nan], "y": [2.0, 3.0]})
    target = pd.Series([0.1, 0.2])
    before = raw.copy(deep=True)
    _, _, complete = complete_case_mask(raw, features, target)
    assert complete.tolist() == [True, False]
    pd.testing.assert_frame_equal(raw, before)


def test_negative_control_detects_deliberately_leaked_future_return():
    rng = np.random.default_rng(20260819)
    prices = 100.0 + rng.uniform(0.0, 20.0, size=700)
    target = build_future_return_target(_frame(prices), 10).to_numpy()
    valid = np.isfinite(target)
    leaked = target[valid]
    split = 350
    x_train = np.column_stack([np.ones(split), leaked[:split]])
    coefficients = np.linalg.lstsq(x_train, leaked[:split], rcond=None)[0]
    predicted = np.column_stack([np.ones(len(leaked) - split), leaked[split:]]) @ coefficients
    residual = leaked[split:] - predicted
    total = leaked[split:] - leaked[split:].mean()
    r2 = 1.0 - float(residual @ residual) / float(total @ total)
    assert r2 > 0.999999


def test_positive_control_is_strictly_causal():
    base = _prices()
    changed = base.copy()
    timestamp = 300
    changed[timestamp + 1:] = 999_999.0
    causal = candidate_series(base, "rolling_mean", 30)
    altered = candidate_series(changed, "rolling_mean", 30)
    assert causal[timestamp] == altered[timestamp]
