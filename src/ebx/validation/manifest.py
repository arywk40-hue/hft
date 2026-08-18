"""Manifest scope helpers."""

from __future__ import annotations

import csv
from pathlib import Path


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


__all__ = ["read_manifest"]
