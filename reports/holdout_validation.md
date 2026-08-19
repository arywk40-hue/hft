# Phase 13 — Untouched Holdout Validation

> Historical Phase 13 record retained for provenance. It is not part of the
> current Phase 11 development package, is not used for new analysis, and must
> not be rerun during packaging. The current README and final report reserve
> Days 86–108 and make no new holdout-generalization claim.

## A. Holdout Coverage

- Expected holdout days: 23
- Available/processed holdout days: 23
- Missing holdout days: none
- Only Days 86–108 were opened. Days 1–85 and 109–123 were excluded.

## B. Integrity Results

See `results/holdout/integrity.csv`, `schema.csv`, and `missingness.csv`. Valid
integrity rows: 23 / 23.
No raw files were modified.

## C. Window Generalization

The frozen nominal ladders were not rediscovered or changed. Results are in
`window_generalization.csv`, with one row per feature so PB exceptions remain
visible. Development observed warm-up is compared to holdout observed warm-up.
Agreement rows: 691 / 691 using median warm-up comparison; mean warm-ups are retained separately.

## D. Feature-Hypothesis Generalization

Frozen best-match hypotheses only: 407. Status counts:
strongly generalizes=153,
partially generalizes=150,
does not generalize=93,
insufficient=11.
No new candidates or features were selected.

## E. Predictive Generalization

Only the frozen development screen was evaluated (543 feature-horizon rows).
Statuses: strongly generalizes=535,
partially generalizes=7,
does not generalize=1.
No holdout FDR or new significance threshold was applied.

## F. Regime Generalization

Development persistent proportion: 0.8714; holdout: 0.8261.
Development inconclusive proportion: 0.1286; holdout: 0.1739. Holdout adjacent transitions: 22, persistence probability: 0.7273.
Frozen thresholds and classification rules were used unchanged. Holdout transitions were not pooled with development transitions.

## G. Distribution/Tail Generalization

The same 1-minute/5-minute return definitions, Jarque–Bera/Anderson–Darling
tests, sigma levels, and descriptive Hill estimator were applied separately.
Normality rejection and positive excess kurtosis generalized at both horizons.
The >3σ ratios remained elevated (holdout 5.6448 at 1m and 4.9152 at 5m),
while >1σ and >2σ ratios were lower than development. Hill alpha also fell
from 3.9907 to 2.3619 at 1m and from 5.5339 to 1.9479 at 5m. See
`distribution_validation.csv`; no development+holdout pooled distribution was calculated.

## H. PCA/Redundancy Generalization

The same per-day z-scoring, complete-row policy, 512-row cap, and PCA method were
used. See `pca_validation.csv` and `redundancy_validation.csv`.

## I. Failures / Non-Generalizing Conclusions

The frozen candidate hypotheses include 93 `does_not_generalize` and 11
`insufficient_holdout_evidence` rows. Predictive validation includes one
`does_not_generalize` and seven partial rows. Sigma-ratio magnitudes and Hill
tail estimates did not fully reproduce development values. These are recorded
failures or differences, not reasons to retune. No threshold, formula, feature
selection, FDR setting, or freeze artifact was changed in response.

## J. Final Verdict

`mostly robust`, with material caveats. Window medians, PCA/redundancy structure,
regime proportions, normality rejection, and the majority of frozen predictive
signals generalized. Feature-formula identity evidence was mixed, and tail
magnitude estimates were not fully stable. This verdict is descriptive only:
statistical persistence is not proof of economic value or feature identity.
