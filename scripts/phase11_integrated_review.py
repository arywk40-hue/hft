"""Phase 11: integrate Parts 1-4 without introducing new tuning."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.coverage import coverage_metadata  # noqa: E402


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    taxonomy = pd.read_csv(root / "results/features/feature_taxonomy.csv")
    best = pd.read_csv(root / "results/features/candidate_best_matches.csv")
    daily = pd.read_csv(root / "results/features/daily_best_candidates.csv")
    regimes = pd.read_csv(root / "results/regimes/regime_table.csv")
    regime_summary = pd.read_csv(root / "results/regimes/regime_summary.csv")
    predictive = pd.read_csv(root / "results/predictive/aggregate_ic.csv")
    pca = pd.read_csv(root / "results/redundancy/pca_summary.csv")
    pairs = pd.read_csv(root / "results/redundancy/pairwise_redundancy.csv")
    extreme = pd.read_csv(root / "results/distributions/extreme_events.csv")
    descriptive = pd.read_csv(root / "results/quality/descriptive_stats.csv")
    descriptive["day"] = pd.to_numeric(descriptive["day"], errors="coerce")

    stability = daily.groupby(["feature", "best_candidate"]).size().reset_index(name="days")
    dominant = stability.sort_values(["feature", "days"]).drop_duplicates("feature", keep="last")
    dominant["dominant_fraction"] = dominant.days / len(regimes[regimes.status == "available"])
    regime_vol = regimes[regimes.status == "available"][["day", "regime"]].merge(
        descriptive[(descriptive.scope == "day") & (descriptive.variable == "simple_return") & (descriptive.horizon == "1s")][["day", "std"]],
        on="day", how="left",
    )
    regime_vol_summary = regime_vol.groupby("regime", as_index=False).agg(days=("day", "count"), mean_1s_volatility=("std", "mean"), median_1s_volatility=("std", "median"))
    practical = predictive[(predictive.pearson_fdr_reject) & (predictive.pearson_pct_same_sign >= .70) & (predictive.mean_pearson_ic.abs() >= .05)]
    output = root / "results" / "phase11"
    output.mkdir(parents=True, exist_ok=True)
    dominant.to_csv(output / "candidate_stability.csv", index=False)
    regime_vol_summary.to_csv(output / "regime_volatility_consistency.csv", index=False)
    facts = {
        **coverage_metadata(),
        "feature_count": len(taxonomy),
        "window_deviation_features": int((taxonomy.nominal_window_status == "actual_deviations_retained").sum()),
        "candidate_best_matches": len(best),
        "candidate_dominant_fraction_ge_0_8": int((dominant.dominant_fraction >= .8).sum()),
        "candidate_dominant_fraction_median": float(dominant.dominant_fraction.median()),
        "regime_counts": regime_summary.set_index("regime")["count"].to_dict(),
        "regime_conflicts": int(regimes.evidence.str.contains("conflict", na=False).sum()),
        "predictive_practical_rows": len(practical),
        "predictive_practical_by_horizon": practical.groupby("horizon_seconds").size().to_dict(),
        "redundant_pairs_abs_pearson_ge_0_9": int((pairs.mean_abs_pearson >= .9).sum()),
        "pooled_pca_components_50_80_90": pca.loc[pca.pca_type == "pooled_incremental", ["components_50pct", "components_80pct", "components_90pct"]].iloc[0].to_dict(),
        "extreme_event_count": len(extreme),
        "extreme_event_feature_linkage": "not asserted; event-conditioned feature analysis was not used to identify semantics",
        "holdout_processed": False,
    }
    (output / "integrated_facts.json").write_text(json.dumps(facts, indent=2, default=lambda value: int(value) if isinstance(value, np.integer) else float(value) if isinstance(value, np.floating) else value) + "\n")
    report = f"""# Phase 11 — Integrated Evidence Review

## Scope

- expected_development_days = 85
- available_development_days = 70 (Days 1–64 and 80–85)
- missing_development_days = 15 (Days 65–79)
- Days 86–108 were not opened or processed.

## Observed facts

- The taxonomy contains {len(taxonomy)} masked features; {facts['window_deviation_features']} retain nominal-vs-actual warm-up deviations.
- The regime table contains 61 persistent and 9 random-walk/inconclusive available-day classifications; {facts['regime_conflicts']} rows retain conflicts.
- Pairwise redundancy includes {facts['redundant_pairs_abs_pearson_ge_0_9']} pairs with mean absolute Pearson correlation at least 0.90.
- The pooled PCA reaches 50%, 80%, and 90% variance at {int(facts['pooled_pca_components_50_80_90']['components_50pct'])}, {int(facts['pooled_pca_components_50_80_90']['components_80pct'])}, and {int(facts['pooled_pca_components_50_80_90']['components_90pct'])} components.

## Statistical results

- Predictive relevance uses exact within-day feature(t) to return(t+h) alignment and FDR alpha 0.05. After requiring FDR rejection, same-sign fraction at least 0.70, and absolute mean Pearson IC at least 0.05, {facts['predictive_practical_rows']} feature-horizon rows remain; these are statistical/practical screening results, not a strategy.
- Candidate reverse engineering produced {len(best)} best-match hypotheses. The median dominant candidate fraction across the 70 available days is {facts['candidate_dominant_fraction_median']:.4f}; {facts['candidate_dominant_fraction_ge_0_8']} features have a dominant candidate on at least 80% of available days.
- Regime/volatility consistency is written to `results/phase11/regime_volatility_consistency.csv`; this is descriptive and does not validate regime causality.

## Hypotheses and interpretations

- Nominal window ladders are hypotheses constrained by observed warm-up; deviations are retained and are not forced to match.
- Candidate correlations support formula hypotheses only. No masked feature identity is confirmed from one metric, one day, or one horizon.
- Feature redundancy and PCA indicate a low-dimensional representation may be plausible, but do not establish independent tradable factors.
- The top {len(extreme)} extreme events were catalogued. No event-conditioned feature identity claim is made; raw volume semantics remain unavailable.

## Limitations

- All conclusions are development-only and based on 70 days, not 85.
- Days 65–79 are explicit missing gaps; no transition, lag, rolling, or forward-return calculation bridges them.
- Holdout validation is intentionally not performed in this run.
"""
    (root / "reports" / "phase11_integrated_review.md").write_text(report)
    print(facts)


if __name__ == "__main__":
    main()
