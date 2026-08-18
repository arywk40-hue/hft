"""Train-only, no-imputation feature standardization."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class TrainOnlyStandardizer:
    feature_names: tuple[str, ...]
    count: int = 0
    _mean: np.ndarray | None = None
    _m2: np.ndarray | None = None
    mean: np.ndarray | None = None
    scale: np.ndarray | None = None

    def update(self, values: pd.DataFrame | np.ndarray) -> None:
        array = values.to_numpy(dtype=float) if isinstance(values, pd.DataFrame) else np.asarray(values, dtype=float)
        if array.ndim != 2 or array.shape[1] != len(self.feature_names):
            raise ValueError("standardizer input has the wrong feature shape")
        if len(array) == 0:
            return
        if not np.isfinite(array).all():
            raise ValueError("standardizer cannot fit non-finite values; imputation is not permitted")
        batch_count = len(array)
        batch_mean = array.mean(axis=0)
        batch_m2 = ((array - batch_mean) ** 2).sum(axis=0)
        if self.count == 0:
            self._mean = batch_mean
            self._m2 = batch_m2
            self.count = batch_count
            return
        assert self._mean is not None and self._m2 is not None
        delta = batch_mean - self._mean
        total = self.count + batch_count
        self._m2 = self._m2 + batch_m2 + delta * delta * self.count * batch_count / total
        self._mean = self._mean + delta * batch_count / total
        self.count = total

    def finalize(self) -> "TrainOnlyStandardizer":
        if self.count == 0 or self._mean is None or self._m2 is None:
            raise ValueError("cannot finalize an unfitted standardizer")
        variance = self._m2 / self.count
        self.mean = self._mean.copy()
        self.scale = np.sqrt(variance)
        self.scale[self.scale == 0] = 1.0
        return self

    @property
    def fitted(self) -> bool:
        return self.mean is not None and self.scale is not None

    def transform(self, values: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            raise ValueError("standardizer has not been fitted")
        if tuple(values.columns) != self.feature_names:
            raise ValueError("transform columns do not match fitted feature names")
        array = values.to_numpy(dtype=float)
        if not np.isfinite(array).all():
            raise ValueError("validation contains non-finite values; rows must be validity-filtered first")
        assert self.mean is not None and self.scale is not None
        transformed = (array - self.mean) / self.scale
        return pd.DataFrame(transformed.astype(np.float32), index=values.index, columns=values.columns)

    def manifest(self) -> dict[str, object]:
        if not self.fitted:
            raise ValueError("standardizer has not been fitted")
        assert self.mean is not None and self.scale is not None
        return {
            "preprocessing_type": "train_only_standardization",
            "imputation": "none",
            "clip": "none",
            "feature_names": list(self.feature_names),
            "fit_row_count": self.count,
            "mean": {name: float(value) for name, value in zip(self.feature_names, self.mean)},
            "scale": {name: float(value) for name, value in zip(self.feature_names, self.scale)},
        }


def complete_case_mask(frame: pd.DataFrame, feature_names: tuple[str, ...], target: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return target-valid, feature-valid, and complete masks without mutation."""

    target_values = target.to_numpy(dtype=float)
    target_valid = np.isfinite(target_values)
    features = frame.loc[:, list(feature_names)].to_numpy(dtype=float)
    feature_valid = np.isfinite(features).all(axis=1)
    return target_valid, feature_valid, target_valid & feature_valid
