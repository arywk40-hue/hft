"""Repair-only writer for Phase 8's explicit unavailable volume candidate rows."""

from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.analytics.candidates import VOLUME_CANDIDATES


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "results" / "features" / "candidate_scores.csv"
    existing = pd.read_csv(path)
    taxonomy = pd.read_csv(root / "results" / "features" / "feature_taxonomy.csv")
    features = taxonomy.loc[~taxonomy.family.isin(["PB", "BB"]), "feature"].tolist()
    rows = [{"feature": feature, "candidate": candidate, "candidate_status": "unavailable_raw_volume", "days_scored": 0, "observations_scored": 0} for feature in features for candidate in VOLUME_CANDIDATES]
    pd.concat([existing, pd.DataFrame(rows)], ignore_index=True).to_csv(path, index=False)
    print({"rows": len(existing) + len(rows), "unavailable_rows": len(rows)})


if __name__ == "__main__":
    main()
