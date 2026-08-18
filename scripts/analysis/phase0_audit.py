#!/usr/bin/env python3
"""Create the metadata-only PHASE 0 repository and dataset audit.

This script deliberately does not open CSV contents. It inventories filenames
and file metadata only, so it cannot alter or accidentally use development or
holdout observations.
"""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DAY_PATTERN = re.compile(r"^day(?P<day>[1-9]\d*)\.csv$")
PACKAGE_NAMES = (
    "pandas",
    "numpy",
    "scipy",
    "statsmodels",
    "scikit-learn",
    "pyarrow",
    "pytest",
)


@dataclass(frozen=True)
class DayFile:
    day: int
    path: Path
    size_bytes: int


def parse_day_filename(name: str) -> int | None:
    """Return the numeric day for an exact dayN.csv filename."""

    match = DAY_PATTERN.fullmatch(name)
    return int(match.group("day")) if match else None


def discover_days(data_dir: Path) -> tuple[list[DayFile], list[str]]:
    """Discover exact day files and report malformed day-like filenames."""

    discovered: list[DayFile] = []
    malformed: list[str] = []
    for path in sorted(data_dir.iterdir()):
        if not path.is_file() or not path.name.startswith("day"):
            continue
        day = parse_day_filename(path.name)
        if day is None:
            malformed.append(path.name)
            continue
        discovered.append(DayFile(day=day, path=path, size_bytes=path.stat().st_size))

    seen: set[int] = set()
    duplicates: list[str] = []
    for item in discovered:
        if item.day in seen:
            duplicates.append(item.path.name)
        seen.add(item.day)
    if duplicates:
        raise ValueError(f"duplicate day IDs discovered: {duplicates}")
    return sorted(discovered, key=lambda item: item.day), sorted(malformed)


def scope_for_day(day: int) -> str:
    if 1 <= day <= 85:
        return "development"
    if 86 <= day <= 108:
        return "holdout"
    return "out_of_scope"


def git_status(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"unavailable: {exc}"
    return result.stdout.strip() or "clean"


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def write_outputs(repo_root: Path, data_dir: Path) -> None:
    output_dir = repo_root / "results" / "phase0"
    output_dir.mkdir(parents=True, exist_ok=True)
    day_files, malformed = discover_days(data_dir)
    available = {item.day for item in day_files}
    development_expected = set(range(1, 86))
    holdout_expected = set(range(86, 109))
    missing_development = sorted(development_expected - available)
    missing_holdout = sorted(holdout_expected - available)
    total_bytes = sum(item.size_bytes for item in day_files)

    with (output_dir / "dataset_inventory.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["day", "path", "size_bytes", "scope", "development_expected", "holdout_expected"]
        )
        for item in day_files:
            writer.writerow(
                [
                    item.day,
                    str(item.path.relative_to(repo_root)),
                    item.size_bytes,
                    scope_for_day(item.day),
                    item.day in development_expected,
                    item.day in holdout_expected,
                ]
            )

    generated_at = datetime.now(timezone.utc).isoformat()
    environment_lines = [
        "EBX PHASE 0 ENVIRONMENT AUDIT",
        f"generated_at_utc={generated_at}",
        f"python={platform.python_version()}",
        f"python_implementation={platform.python_implementation()}",
        f"platform={platform.platform()}",
        "",
        "package_versions:",
    ]
    environment_lines.extend(f"{name}={package_version(name)}" for name in PACKAGE_NAMES)
    environment_lines.extend(
        [
            "",
            "test_baseline=pytest is not installed; stdlib unittest baseline is used",
        ]
    )
    (output_dir / "environment.txt").write_text("\n".join(environment_lines) + "\n")

    baseline_dirs = (
        "config",
        "src",
        "scripts",
        "tests",
        "notebooks",
        "results",
        "figures",
        "reports",
        "data",
        "data/validated",
        "data/processed",
    )
    audit_lines = [
        "EBX PHASE 0 REPOSITORY AUDIT",
        f"generated_at_utc={generated_at}",
        "",
        "specification_files:",
        f"architecture.md={'present' if (repo_root / 'architecture.md').is_file() else 'missing'}",
        f"implementation.md={'present' if (repo_root / 'implementation.md').is_file() else 'missing'}",
        f"quant.md={'present' if (repo_root / 'quant.md').is_file() else 'missing'}",
        "",
        "baseline_directories:",
    ]
    audit_lines.extend(f"{directory}={'present' if (repo_root / directory).is_dir() else 'missing'}" for directory in baseline_dirs)
    audit_lines.extend(
        [
            "",
            "repository_state:",
            f"git_status={git_status(repo_root)}",
            "",
            "dataset:",
            f"dataset_directory={data_dir.relative_to(repo_root)}",
            f"available_day_file_count={len(day_files)}",
            f"available_day_ids={','.join(str(day) for day in sorted(available))}",
            f"total_size_bytes={total_bytes}",
            f"total_size_gib={total_bytes / (1024**3):.3f}",
            f"development_expected_count={len(development_expected)}",
            f"development_available_count={len(available & development_expected)}",
            f"development_missing_days={','.join(map(str, missing_development)) or 'none'}",
            f"development_complete={not missing_development}",
            f"holdout_expected_count={len(holdout_expected)}",
            f"holdout_available_count={len(available & holdout_expected)}",
            f"holdout_missing_days={','.join(map(str, missing_holdout)) or 'none'}",
            f"holdout_complete={not missing_holdout}",
            f"out_of_scope_days={','.join(str(day) for day in sorted(available - development_expected - holdout_expected)) or 'none'}",
            f"malformed_day_like_filenames={','.join(malformed) or 'none'}",
            "raw_csv_policy=read-only; this audit inspected filenames and file metadata only",
            "development_policy=Days 1-85 only; missing days must not be silently dropped",
            "holdout_policy=Days 86-108 reserved and not used for development",
        ]
    )
    (output_dir / "repository_audit.txt").write_text("\n".join(audit_lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_dir = (args.data_dir or repo_root / "data").resolve()
    if not data_dir.is_dir():
        parser.error(f"data directory does not exist: {data_dir}")
    write_outputs(repo_root, data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
