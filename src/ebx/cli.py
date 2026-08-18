"""Safe production CLI for inventory and artifact verification.

The default commands verify the frozen production artifacts. They do not
silently rerun analysis or overwrite frozen results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Iterable

from .config import ProjectConfig
from .io.discovery import discover_days


LOGGER = logging.getLogger("ebx")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root(value: str | None) -> Path:
    return Path(value or ".").resolve()


def inventory(config: ProjectConfig) -> int:
    result = discover_days(config.data_dir, config.development_days)
    payload = {
        "development_expected_days": len(config.development_days),
        "development_available_days": sorted(result.files),
        "missing_development_days": list(result.missing_days),
        "out_of_scope_day_ids": list(result.out_of_scope_ids),
        "malformed_names": list(result.malformed_names),
        "raw_files_opened": False,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not result.duplicate_ids and not result.malformed_names else 2


def validate(config: ProjectConfig) -> int:
    manifest_path = config.root / "data/validated/manifest.csv"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    from .validation.manifest import read_manifest

    rows = read_manifest(manifest_path)
    available = sorted(int(row["day"]) for row in rows if row["status"] != "missing_source")
    expected = sorted(day for day in config.development_days if day not in range(65, 80))
    payload = {
        "manifest": str(manifest_path),
        "available_development_days": available,
        "missing_development_days": [day for day in config.development_days if day not in available],
        "expected_available_audited_days": expected,
        "holdout_processed_by_validate": False,
    }
    print(json.dumps(payload, indent=2))
    return 0 if available == expected else 2


def _required_files(root: Path, paths: Iterable[str]) -> list[str]:
    return [path for path in paths if not (root / path).is_file()]


def analyze(config: ProjectConfig) -> int:
    required = [
        "results/freeze/development_freeze.json",
        "reports/phase11_integrated_review.md",
        "results/features/feature_taxonomy.csv",
        "results/predictive/aggregate_ic.csv",
        "results/redundancy/pca_summary.csv",
    ]
    missing = _required_files(config.root, required)
    print(json.dumps({"mode": "artifact_verification", "missing": missing, "analysis_rerun": False}, indent=2))
    return 0 if not missing else 2


def holdout(config: ProjectConfig) -> int:
    manifest = config.root / "results/holdout/freeze_manifest.json"
    required = [
        "results/holdout/integrity.csv",
        "results/holdout/window_generalization.csv",
        "results/holdout/feature_hypothesis_validation.csv",
        "results/holdout/ic_validation.csv",
        "results/holdout/regime_validation.csv",
        "results/holdout/distribution_validation.csv",
        "results/holdout/pca_validation.csv",
        "reports/holdout_validation.md",
    ]
    missing = _required_files(config.root, required)
    manifest_data = json.loads(manifest.read_text()) if manifest.is_file() else {}
    freeze = config.root / "results/freeze/development_freeze.json"
    hash_ok = bool(manifest_data) and manifest_data.get("freeze_file_sha256") == _sha256(freeze)
    payload = {
        "mode": "holdout_artifact_verification",
        "expected_holdout_days": len(config.holdout_days),
        "missing_artifacts": missing,
        "freeze_hash_matches": hash_ok,
        "holdout_rerun": False,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not missing and hash_ok else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ebx", description=__doc__)
    parser.add_argument("--root", default=None, help="repository root (default: current directory)")
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "validate", "analyze", "holdout"):
        subparsers.add_parser(name)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(name)s: %(message)s")
    config = ProjectConfig.from_root(_root(args.root))
    return {"inventory": inventory, "validate": validate, "analyze": analyze, "holdout": holdout}[args.command](config)


if __name__ == "__main__":
    raise SystemExit(main())
