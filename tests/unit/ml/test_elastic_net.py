import numpy as np
import pandas as pd
import pytest

import scripts.ml.phase_ml5_elastic_net as phase7
from src.ebx.ml.elastic_net import ElasticNetBaseline


def _partition(path, day=1):
    pd.DataFrame({
        "day": [day] * 5,
        "timestamp": [f"00:00:0{i}" for i in range(5)],
        "timestamp_seconds": list(range(5)),
        "target": [0.0, 0.1, 0.2, 0.3, 0.4],
        "f1": [0.0, 1.0, 2.0, 3.0, 4.0],
        "f2": [1.0, 1.0, 1.0, 1.0, 1.0],
    }).to_parquet(path, index=False)


def test_elastic_net_fit_prediction_and_reload_are_deterministic(tmp_path):
    path = tmp_path / "train.parquet"
    _partition(path)
    config = dict(alpha=1e-6, l1_ratio=0.5, max_iter=5000, tol=1e-4)
    first = ElasticNetBaseline(("f1", "f2"), **config).fit_partition_paths([path])
    second = ElasticNetBaseline(("f1", "f2"), **config).fit_partition_paths([path])
    frame = pd.read_parquet(path)
    np.testing.assert_array_equal(first.coef_, second.coef_)
    np.testing.assert_array_equal(first.predict(frame), second.predict(frame))
    artifact = tmp_path / "elastic_net.pkl"
    first.save(artifact)
    loaded = ElasticNetBaseline.load(artifact)
    np.testing.assert_array_equal(first.predict(frame), loaded.predict(frame))


def test_elastic_net_rejects_invalid_configuration_and_nonfinite_data(tmp_path):
    with pytest.raises(ValueError, match="l1_ratio"):
        ElasticNetBaseline(("f1",), l1_ratio=1.5).validate()
    with pytest.raises(ValueError, match="alpha"):
        ElasticNetBaseline(("f1",), alpha=0).validate()
    path = tmp_path / "invalid.parquet"
    _partition(path)
    frame = pd.read_parquet(path)
    frame.loc[0, "f1"] = np.nan
    frame.to_parquet(path, index=False)
    with pytest.raises(ValueError, match="invalid training partition"):
        ElasticNetBaseline(("f1", "f2")).fit_partition_paths([path])


def test_elastic_net_prediction_requires_all_selected_features(tmp_path):
    path = tmp_path / "train.parquet"
    _partition(path)
    model = ElasticNetBaseline(("f1", "f2")).fit_partition_paths([path])
    with pytest.raises(ValueError, match="missing features"):
        model.predict(pd.DataFrame({"f1": [1.0]}))


def test_phase7_configuration_and_scope_are_fixed():
    assert phase7.ALPHA == 1e-6
    assert phase7.L1_RATIO == 0.5
    assert phase7.MAX_ITER == 10000
    assert phase7.TOL == 1e-4
    assert phase7.SELECTION == "cyclic"
    for specification in phase7.EXPERIMENTS.values():
        training = set(specification["training_days"])
        validation = set(specification["validation_days"])
        assert not training & validation
        assert not (training | validation) & set(range(65, 80))
        assert not (training | validation) & set(range(86, 109))


def test_fit_row_count_and_prediction_alignment_use_supplied_training_only(tmp_path):
    first = tmp_path / "day1.parquet"
    second = tmp_path / "day2.parquet"
    _partition(first, day=1)
    _partition(second, day=2)
    model = ElasticNetBaseline(("f1", "f2"), max_iter=1000).fit_partition_paths([first])
    frame = pd.read_parquet(first)
    assert model.n_train_samples_ == len(frame)
    expected = frame[["f1", "f2"]].to_numpy() @ model.coef_ + model.intercept_
    np.testing.assert_array_equal(model.predict(frame), expected)
