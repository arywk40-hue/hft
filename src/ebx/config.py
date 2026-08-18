"""Configuration loading and repository-scope policy."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def load_yaml_subset(path: Path) -> dict[str, Any]:
    """Load the project's intentionally simple YAML-like configuration."""

    settings: dict[str, Any] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        try:
            settings[key] = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            settings[key] = value.strip("\"'")
    return settings


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    settings: dict[str, Any]

    @classmethod
    def from_root(cls, root: Path) -> "ProjectConfig":
        root = root.resolve()
        path = root / "config" / "config.yaml"
        if not path.is_file():
            raise FileNotFoundError(path)
        return cls(root=root, settings=load_yaml_subset(path))

    @property
    def data_dir(self) -> Path:
        return self._path("raw_data_dir", "data")

    @property
    def development_days(self) -> tuple[int, ...]:
        value = self.settings.get("development_days", [1, 85])
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("development_days must be [start, end]")
        return tuple(range(int(value[0]), int(value[1]) + 1))

    @property
    def holdout_days(self) -> tuple[int, ...]:
        value = self.settings.get("holdout_days", [86, 108])
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("holdout_days must be [start, end]")
        return tuple(range(int(value[0]), int(value[1]) + 1))

    def _path(self, key: str, default: str) -> Path:
        value = Path(str(self.settings.get(key, default)))
        return value if value.is_absolute() else self.root / value
