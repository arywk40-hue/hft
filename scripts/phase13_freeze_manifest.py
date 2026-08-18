"""Create the immutable development-artifact manifest before holdout access."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    freeze = root / "results/freeze/development_freeze.json"
    review = root / "reports/phase11_integrated_review.md"
    config = root / "config/config.yaml"
    record = {
        "manifest_type": "phase13_holdout_freeze_manifest",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_file": str(freeze.relative_to(root)),
        "freeze_file_sha256": digest(freeze),
        "integrated_review_file": str(review.relative_to(root)),
        "integrated_review_sha256": digest(review),
        "configuration_file": str(config.relative_to(root)),
        "configuration_sha256": digest(config),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "git_worktree_note": "uncommitted Phase 8-12 implementation files are included by path/hash only through the frozen result artifacts; no holdout result is fed back into development",
        "holdout_start_day": 86,
        "holdout_end_day": 108,
        "holdout_expected_days": 23,
        "development_access_policy": "development source data is not opened by Phase 13 processing scripts",
    }
    output = root / "results/holdout"
    output.mkdir(parents=True, exist_ok=True)
    (output / "freeze_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    print(record)


if __name__ == "__main__":
    main()
