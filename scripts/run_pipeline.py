#!/usr/bin/env python3
"""Run the safe production verification workflow in scope order.

This orchestrator verifies existing artifacts. It intentionally does not rerun
frozen statistical analysis or holdout validation.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ebx.cli import main  # noqa: E402


def run() -> int:
    for command in ("inventory", "validate", "analyze", "holdout"):
        status = main(["--root", str(ROOT), command])
        if status:
            return status
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
