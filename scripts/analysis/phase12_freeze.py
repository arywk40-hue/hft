"""Phase 12: freeze development-only conclusions before holdout access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    files = [
        root / "config/config.yaml",
        root / "results/regimes/phase6_scope.json",
        root / "results/features/phase7_scope.json",
        root / "results/features/phase8_scope.json",
        root / "results/predictive/phase9_scope.json",
        root / "results/redundancy/phase10_scope.json",
        root / "results/phase11/integrated_facts.json",
    ]
    best = pd.read_csv(root / "results/features/candidate_best_matches.csv")
    facts = json.loads((root / "results/phase11/integrated_facts.json").read_text())
    scope = {
        "expected_development_days": 85,
        "available_development_days": 70,
        "missing_development_days": 15,
        "available_day_ids": list(range(1, 65)) + list(range(80, 86)),
        "missing_day_ids": list(range(65, 80)),
        "holdout_day_ids": list(range(86, 109)),
        "holdout_processed": False,
        "raw_csv_modified": False,
    }
    record = {
        "freeze_status": "development_frozen_before_holdout",
        "scope": scope,
        "configuration_hashes": {str(path.relative_to(root)): sha256(path) for path in files},
        "analysis_parameters": {
            "regime_thresholds": json.loads((root / "results/regimes/phase6_scope.json").read_text())["thresholds"],
            "candidate_evidence_tiers": json.loads((root / "results/features/phase8_scope.json").read_text())["evidence_thresholds"],
            "predictive_horizons_seconds": json.loads((root / "results/predictive/phase9_scope.json").read_text())["horizons_seconds"],
            "fdr_alpha": json.loads((root / "results/predictive/phase9_scope.json").read_text())["fdr_alpha"],
            "pca_row_cap_per_day": json.loads((root / "results/redundancy/phase10_scope.json").read_text())["row_cap_per_day"],
        },
        "frozen_hypotheses": {
            "candidate_best_match_count": len(best),
            "candidate_best_matches_sha256": sha256(root / "results/features/candidate_best_matches.csv"),
            "window_deviation_feature_count": facts["window_deviation_features"],
            "regime_summary": facts["regime_counts"],
            "integrated_facts_sha256": sha256(root / "results/phase11/integrated_facts.json"),
        },
        "evidence_policy": {
            "statistical_significance_is_not_practical_significance": True,
            "feature_identity_requires_more_than_one_metric": True,
            "no_holdout_tuning": True,
            "no_fabricated_missing_days": True,
            "no_day_boundary_crossing": True,
        },
    }
    output = root / "results/freeze"
    output.mkdir(parents=True, exist_ok=True)
    (output / "development_freeze.json").write_text(json.dumps(record, indent=2) + "\n")
    (root / "results/phase12").mkdir(parents=True, exist_ok=True)
    (root / "results/phase12/progress_summary.txt").write_text(
        "PHASE 12 STATUS: ACCEPTED — DEVELOPMENT CONCLUSIONS FROZEN\n\n"
        "The development freeze was written before any holdout access.\n"
        "expected_development_days=85\n"
        "available_development_days=70\n"
        "missing_development_days=15 (Days 65-79)\n"
        "Days 86-108 were not opened or processed.\n"
        "Raw CSV files were not modified.\n"
        "No holdout validation, Part 5, or trading strategy work was performed.\n"
    )
    print({"freeze": str(output / "development_freeze.json"), "hash_count": len(files), "holdout_processed": False})


if __name__ == "__main__":
    main()
