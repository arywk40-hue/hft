"""Deterministic Elastic Net baseline for isolated ML Phase 7 experiments."""

from __future__ import annotations

from dataclasses import dataclass
import pickle
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class ElasticNetBaseline:
    """Elastic Net fitted from existing model-ready day partitions.

    The estimator is intentionally configured once for Phase 7.  Partitions
    are read only from the caller-supplied training paths; validation paths are
    never passed to ``fit_partition_paths``.
    """

    feature_names: tuple[str, ...]
    alpha: float = 1e-6
    l1_ratio: float = 0.5
    max_iter: int = 10000
    tol: float = 1e-4
    fit_intercept: bool = True
    selection: str = "cyclic"
    random_state: int | None = None
    coef_: np.ndarray | None = None
    intercept_: float = 0.0
    n_train_samples_: int = 0
    n_iter_: int = 0
    converged_: bool = False

    def validate(self) -> None:
        if not self.feature_names:
            raise ValueError("Elastic Net requires at least one feature")
        if self.alpha <= 0:
            raise ValueError("Elastic Net alpha must be positive")
        if not 0 <= self.l1_ratio <= 1:
            raise ValueError("Elastic Net l1_ratio must be between 0 and 1")
        if self.max_iter <= 0:
            raise ValueError("Elastic Net max_iter must be positive")
        if self.tol <= 0:
            raise ValueError("Elastic Net tolerance must be positive")
        if self.selection != "cyclic":
            raise ValueError("this deterministic Elastic Net implementation requires cyclic selection")

    def fit_partition_paths(self, paths: list[str | Path]) -> "ElasticNetBaseline":
        self.validate()
        if not paths:
            raise ValueError("at least one training partition is required")
        feature_count = len(self.feature_names)
        sum_x = np.zeros(feature_count, dtype=np.float64)
        sum_y = 0.0
        gram_raw = np.zeros((feature_count, feature_count), dtype=np.float64)
        rhs_raw = np.zeros(feature_count, dtype=np.float64)
        count = 0
        columns = [*self.feature_names, "target"]
        for path in paths:
            frame = pd.read_parquet(path, columns=columns)
            values = frame.loc[:, list(self.feature_names)].to_numpy(dtype=np.float64)
            target = frame["target"].to_numpy(dtype=np.float64)
            if len(frame) == 0 or not np.isfinite(values).all() or not np.isfinite(target).all():
                raise ValueError(f"invalid training partition: {path}")
            sum_x += values.sum(axis=0)
            sum_y += float(target.sum())
            gram_raw += values.T @ values
            rhs_raw += values.T @ target
            count += len(frame)
        mean_x = sum_x / count
        mean_y = sum_y / count
        gram = gram_raw - np.outer(sum_x, sum_x) / count
        rhs = rhs_raw - sum_x * sum_y / count
        gram = (gram + gram.T) / 2.0
        diagonal = np.diag(gram) / count
        if np.any(diagonal < -1e-10):
            raise ValueError("centered training Gram matrix is invalid")

        coefficients = np.zeros(feature_count, dtype=np.float64)
        l1_penalty = self.alpha * self.l1_ratio
        l2_penalty = self.alpha * (1.0 - self.l1_ratio)
        normalized_gram = gram / count
        normalized_rhs = rhs / count
        denominator = np.maximum(diagonal, 0.0) + l2_penalty
        converged = False
        for iteration in range(1, self.max_iter + 1):
            maximum_change = 0.0
            for index in range(feature_count):
                partial = normalized_rhs[index] - float(normalized_gram[index] @ coefficients) + normalized_gram[index, index] * coefficients[index]
                if partial > l1_penalty:
                    updated = (partial - l1_penalty) / denominator[index]
                elif partial < -l1_penalty:
                    updated = (partial + l1_penalty) / denominator[index]
                else:
                    updated = 0.0
                maximum_change = max(maximum_change, abs(updated - coefficients[index]))
                coefficients[index] = updated
            scale = max(1e-12, float(np.max(np.abs(coefficients))))
            if maximum_change <= self.tol * scale:
                converged = True
                break

        self.coef_ = coefficients
        self.intercept_ = float(mean_y - mean_x @ coefficients) if self.fit_intercept else 0.0
        self.n_train_samples_ = count
        self.n_iter_ = iteration
        self.converged_ = converged
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        if self.coef_ is None:
            raise ValueError("Elastic Net baseline has not been fitted")
        missing = set(self.feature_names) - set(frame.columns)
        if missing:
            raise ValueError(f"prediction frame is missing features: {sorted(missing)}")
        values = frame.loc[:, list(self.feature_names)].to_numpy(dtype=np.float64)
        if not np.isfinite(values).all():
            raise ValueError("prediction features contain non-finite values")
        return np.asarray(values @ self.coef_ + self.intercept_, dtype=float)

    def summary(self) -> dict[str, object]:
        if self.coef_ is None:
            raise ValueError("Elastic Net baseline has not been fitted")
        return {
            "model": "elastic_net",
            "alpha": float(self.alpha),
            "l1_ratio": float(self.l1_ratio),
            "max_iter": int(self.max_iter),
            "tol": float(self.tol),
            "fit_intercept": bool(self.fit_intercept),
            "selection": self.selection,
            "random_state": self.random_state,
            "feature_count": len(self.feature_names),
            "feature_names": list(self.feature_names),
            "n_train_samples": int(self.n_train_samples_),
            "intercept": float(self.intercept_),
            "coefficient_l1_norm": float(np.linalg.norm(self.coef_, ord=1)),
            "coefficient_l2_norm": float(np.linalg.norm(self.coef_)),
            "nonzero_coefficient_count": int(np.count_nonzero(self.coef_)),
            "n_iter": int(self.n_iter_),
            "converged": bool(self.converged_),
        }

    def save(self, path: str | Path) -> None:
        if self.coef_ is None:
            raise ValueError("cannot save an unfitted Elastic Net baseline")
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            pickle.dump(self, handle, protocol=5)

    @classmethod
    def load(cls, path: str | Path) -> "ElasticNetBaseline":
        with Path(path).open("rb") as handle:
            model = pickle.load(handle)
        if not isinstance(model, cls):
            raise TypeError("model artifact is not an ElasticNetBaseline")
        return model
