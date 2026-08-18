# ML Phase 3 — Temporal Robustness Experiment

This report contains the three pre-specified blocked temporal experiments and
one explicitly post-hoc Day-84 sensitivity diagnostic. No window, threshold,
feature, or Ridge parameter was changed after observing results.

## 1. Design and data boundary

| Window | Training days | Validation days | Training rows | Validation rows |
|---|---|---|---:|---:|
| W1 | 1–44 | 45–54 | 538,648 | 122,420 |
| W2 | 1–54 | 55–64 | 661,068 | 84,632 |
| W3 | 1–64 | 80–85 | 745,700 | 73,452 |

The development scope remains 85 expected days, 70 available days, and missing
Days 65–79. W3 preserves the gap exactly. Days 86–108 were not loaded or
accessed. The target is the exact within-day 300-second future return. Each
window independently refit the existing training-only selection rule over
training-day IC rows, fit preprocessing on training rows only, and fit the same
deterministic Ridge configuration (`alpha=1.0`, fitted intercept).

## 2. Primary feature-selection results

The candidate universe was 691 features across 3,455 feature–horizon
hypotheses. No frozen 197-feature file was used for selection.

| Window | Selected features | BB | PB | PV | Exact selected-feature artifact |
|---|---:|---:|---:|---:|---|
| W1 | 195 | 140 | 45 | 10 | [`W1/selected_features.csv`](../results/ml/temporal_robustness/W1/selected_features.csv) |
| W2 | 194 | 140 | 45 | 9 | [`W2/selected_features.csv`](../results/ml/temporal_robustness/W2/selected_features.csv) |
| W3 | 198 | 140 | 46 | 12 | [`W3/selected_features.csv`](../results/ml/temporal_robustness/W3/selected_features.csv) |

The CSV files are the complete selected feature lists, with family,
subfamily, nominal window, training IC, sign consistency, FDR statistics, and
eligibility fields.

Pairwise feature-set Jaccard overlap:

|  | W1 | W2 | W3 |
|---|---:|---:|---:|
| W1 | 1.000000 | 0.994872 | 0.984848 |
| W2 | 0.994872 | 1.000000 | 0.979798 |
| W3 | 0.984848 | 0.979798 | 1.000000 |

## 3. Primary pooled validation results

| Metric | W1 | W2 | W3 |
|---|---:|---:|---:|
| Pearson IC | 0.0389122675510 | 0.0317589128073 | 0.0707122892894 |
| Spearman IC | 0.0202752137656 | -0.0010580636410 | 0.0557371132606 |
| R² | -0.0281418222923 | -0.0283691955230 | -0.0234135533098 |
| MAE | 0.0004589806004 | 0.0004450741809 | 0.0004355500826 |
| RMSE | 0.0007849736255 | 0.0006437751230 | 0.0006586645683 |
| Directional accuracy | 0.482984806404 | 0.480113904906 | 0.507651255242 |
| Validation rows | 122,420 | 84,632 | 73,452 |

## 4. Primary daily validation results

Each row below reports: validation rows, Pearson IC, Spearman IC, R², MAE,
RMSE, and directional accuracy.

### W1 — Days 45–54

| Day | Rows | Pearson IC | Spearman IC | R² | MAE | RMSE | Directional accuracy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 45 | 12,242 | 0.0632750527345 | 0.0329628982804 | -0.0041027702111 | 0.0003647748945 | 0.0004734593101 | 0.499428198007 |
| 46 | 12,242 | 0.217117020449 | 0.141525639401 | -0.0420596989507 | 0.0002461700545 | 0.0003416647093 | 0.498774710015 |
| 47 | 12,242 | 0.0903088614386 | 0.0875763766099 | -0.0000725517795 | 0.0002946639274 | 0.0003901179715 | 0.515275281817 |
| 48 | 12,242 | -0.0160568803609 | -0.0145261024479 | -0.0399510890254 | 0.0003528299115 | 0.0004463010651 | 0.475167456298 |
| 49 | 12,242 | 0.0646500380466 | -0.0021269958393 | -0.242340038654 | 0.00069699056598 | 0.0009597457181 | 0.411942493057 |
| 50 | 12,242 | -0.0321925428300 | 0.0007251188390 | -0.101773048378 | 0.0003866947728 | 0.0005054156908 | 0.503594183957 |
| 51 | 12,242 | 0.0848225886953 | 0.107864901335 | 0.0016029132133 | 0.0012948639436 | 0.0019445658832 | 0.561182813266 |
| 52 | 12,242 | 0.131104182456 | 0.182022651014 | -0.101869139289 | 0.0001861215914 | 0.0002375297675 | 0.435468060774 |
| 53 | 12,242 | 0.0307523095283 | 0.0200931169984 | -0.0309444573962 | 0.0003400038627 | 0.0004177622364 | 0.496569188041 |
| 54 | 12,242 | -0.0261463493859 | -0.0451400248553 | -0.122731635806 | 0.0004266924798 | 0.0005298318117 | 0.432445678811 |

### W2 — Days 55–64

| Day | Rows | Pearson IC | Spearman IC | R² | MAE | RMSE | Directional accuracy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 55 | 12,242 | 0.0360545354328 | 0.131524671320 | -0.0352013962066 | 0.0005829303516 | 0.0007488664246 | 0.570249959157 |
| 56 | 12,242 | -0.0182707283555 | -0.0209244014873 | -0.0963600224362 | 0.0002571862199 | 0.0003234404980 | 0.440450906715 |
| 57 | 12,242 | 0.0710737632124 | 0.0075955984792 | -0.0077050441882 | 0.0002202241272 | 0.0003039510641 | 0.494281980069 |
| 58 | 12,242 | 0.136564843121 | 0.0646810192138 | 0.0062686175244 | 0.0007900550384 | 0.0010413682620 | 0.448946250613 |
| 59 | 12,242 | -0.108683603553 | -0.0755806251236 | -0.100487804711 | 0.0004107860546 | 0.0005356988898 | 0.480803790230 |
| 60 | 6,182 | -0.151546731505 | -0.0161314148351 | -0.205859724370 | 0.0003728577604 | 0.0005889695370 | 0.473471368489 |
| 61 | 6,038 | -0.0276046538258 | -0.0899072994271 | -0.484239201777 | 0.0005051222477 | 0.0006213993177 | 0.389201722425 |
| 62 | 3,734 | 0.185516305861 | 0.116760253273 | 0.0328084833453 | 0.0002632574215 | 0.0003237334499 | 0.536422067488 |
| 63 | 3,878 | 0.0911355938781 | 0.149556718610 | -0.0295740045716 | 0.0006939175042 | 0.0009837695196 | 0.402011346055 |
| 64 | 3,590 | 0.208053030353 | 0.233810829487 | -0.0005209439194 | 0.0002666240908 | 0.0003292087205 | 0.553760445682 |

The lower W2 row counts on Days 60–64 are retained as observed by the
validity-mask pipeline; no imputation or synthetic rows were introduced.

### W3 — Days 80–85

| Day | Rows | Pearson IC | Spearman IC | R² | MAE | RMSE | Directional accuracy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 80 | 12,242 | 0.0878982608060 | 0.101525123116 | -0.0073013609724 | 0.0002273905961 | 0.0002885005226 | 0.539699395524 |
| 81 | 12,242 | 0.0712716109927 | 0.0810318019864 | -0.0791091395093 | 0.0001887403272 | 0.0002313867951 | 0.477781408267 |
| 82 | 12,242 | 0.0888868981032 | 0.0897281798219 | 0.0034534151638 | 0.0002490465543 | 0.0003228781359 | 0.536677013560 |
| 83 | 12,242 | -0.0175232904359 | 0.0579623458635 | -0.0465813464369 | 0.0006557145424 | 0.0008468456250 | 0.518624407777 |
| 84 | 12,242 | 0.218134976469 | 0.141325053648 | 0.0472895406541 | 0.0006262681231 | 0.0007920807240 | 0.550318575396 |
| 85 | 12,242 | -0.0014522527411 | -0.0199912721959 | -0.128934325715 | 0.0006661403522 | 0.001008698173 | 0.422806730926 |

## 5. Cross-window analysis

| Statistic | Value |
|---|---:|
| Mean window Pearson IC | 0.0471278232159 |
| Median window Pearson IC | 0.0389122675510 |
| Std. dev. of window Pearson IC (sample) | 0.0207355467977 |
| Minimum window Pearson IC | 0.0317589128073 |
| Maximum window Pearson IC | 0.0707122892894 |
| Window IC range | 0.0389533764821 |
| Positive-IC windows | 3 |
| Negative-IC windows | 0 |
| Feature-count mean | 195.666666667 |
| Feature-count population std. dev. | 1.69967317120 |
| Feature-count coefficient of variation | 0.008686574981 |

| Window | Mean daily Pearson IC | Median daily Pearson IC | Positive validation-day fraction |
|---|---:|---:|---:|
| W1 | 0.0607634280771 | 0.0639625453905 | 0.700000 (7/10) |
| W2 | 0.0422292354619 | 0.0535641493226 | 0.600000 (6/10) |
| W3 | 0.0745360338656 | 0.0795849358993 | 0.666667 (4/6) |

All three windows have positive pooled Pearson IC and positive mean daily
Pearson IC. This is descriptively consistent with persistence, but the signal
is not uniformly positive by day, and pooled R² is negative for all windows.

## 6. Post-hoc Day-84 sensitivity diagnostic

This section is not a primary result. W3 was not retrained, feature selection
was not changed, and only the reported validation aggregation was recalculated
after removing Day 84.

| Metric | Normal W3 | W3 excluding Day 84 | Difference |
|---|---:|---:|---:|
| Pearson IC | 0.0707122892894 | 0.0110372673106 | -0.0596750219788 |
| Spearman IC | 0.0557371132606 | 0.0298415023461 | -0.0258956109144 |
| R² | -0.0234135533098 | -0.0504060274432 | -0.0269924741334 |
| MAE | 0.0004355500826 | 0.0003974064744 | -0.0000381436081 |
| RMSE | 0.0006586645683 | 0.0006285924288 | -0.0000300721395 |
| Directional accuracy | 0.507651255242 | 0.499117791211 | -0.008533464031 |
| Validation rows | 73,452 | 61,210 | -12,242 |

Day 84 is materially influential: removing it reduces pooled Pearson IC to
0.0110373, while the result remains barely positive. W1 and W2 also contain
large positive daily observations (Days 46 and 64 respectively), but their
mean daily Pearson IC remains positive after removing their highest daily IC
(0.0433908 for W1 and 0.0238044 for W2). The only formal post-hoc sensitivity
experiment performed was the required Day-84 diagnostic.

## 7. Artifacts, tests, and limitations

Artifacts are isolated under
[`results/ml/temporal_robustness/`](../results/ml/temporal_robustness/), with
per-window models, preprocessing manifests, selected feature tables,
selection tables, predictions, pooled/daily metrics, run manifests, and
reproducibility manifests. Aggregate outputs include
[`feature_overlap_matrix.csv`](../results/ml/temporal_robustness/feature_overlap_matrix.csv),
[`aggregate_robustness.json`](../results/ml/temporal_robustness/aggregate_robustness.json),
and [`day84_sensitivity.json`](../results/ml/temporal_robustness/day84_sensitivity.json).

The existing baseline, Phase 2 train-only-selection artifacts, frozen feature
definitions, freeze manifest, and predictive aggregate were not modified.
The selection input is the existing day-level IC artifact with only the
explicit training-day rows retained for each window; the t-tests, FDR, and
eligibility rule were refit independently per window. This is not a fresh raw
IC recomputation and is noted for reproducibility.

The experiment is descriptive, uses overlapping training periods, has no
untouched holdout evaluation, and does not establish trading or economic
utility. No ML model beyond the fixed Ridge model, hyperparameter search,
strategy, transaction-cost model, or backtest was implemented.
