# ML Phase 9 — Controlled LightGBM W3 Benchmark

## Scope and data boundary

This is one fixed LightGBM benchmark using the existing W3 model-ready data. It is not a feature-engineering, feature-selection, tuning, or model-search experiment.

- Expected development days: **85**
- Available development days: **70**
- Missing development days: **65–79 (15 days)**
- Training days: **1–64**; validation days: **80–85**
- Holdout days 86–108: **not loaded, accessed, inspected, or used**
- Training rows: **745700**; validation rows: **73452**
- Features: **198**, from the existing W3 training-only selected-feature artifact

## Fixed model and preprocessing

The existing W3 train-only feature selection and preprocessing artifacts were consumed unchanged. Preprocessing was fitted on Days 1–64; no validation statistics, target values, or early stopping were used.

```json
{
  "configuration": {
    "bagging_fraction": 1.0,
    "bagging_freq": 0,
    "boosting_type": "gbdt",
    "deterministic": true,
    "feature_fraction": 1.0,
    "force_col_wise": true,
    "learning_rate": 0.03,
    "max_depth": 5,
    "min_child_samples": 200,
    "num_boost_round": 200,
    "num_leaves": 15,
    "num_threads": 1,
    "objective": "regression",
    "reg_alpha": 0.001,
    "reg_lambda": 1.0,
    "seed": 20260819,
    "verbosity": -1
  },
  "lightgbm_parameters": {
    "bagging_fraction": 1.0,
    "bagging_freq": 0,
    "bagging_seed": 20260819,
    "boosting_type": "gbdt",
    "data_random_seed": 20260819,
    "deterministic": true,
    "feature_fraction": 1.0,
    "feature_fraction_seed": 20260819,
    "force_col_wise": true,
    "learning_rate": 0.03,
    "max_depth": 5,
    "min_child_samples": 200,
    "num_leaves": 15,
    "num_threads": 1,
    "objective": "regression",
    "reg_alpha": 0.001,
    "reg_lambda": 1.0,
    "seed": 20260819,
    "verbosity": -1
  }
}
```

LightGBM version: `4.6.0`; Python executable: `/Users/ariyanbhakat/miniconda3/bin/python`.
scikit-learn package version: `1.7.2`; import status: `ImportError('scipy._cyutility does not export expected C function slice_memviewslice')`.

## Predictive results

| metric | LightGBM W3 |
| --- | --- |
| pearson_ic | 0.0433187087464854 |
| spearman_ic | 0.0250002876686694 |
| mean_daily_pearson_ic | 0.036225711012676 |
| median_daily_pearson_ic | 0.0421956100543468 |
| std_daily_pearson_ic | 0.109989573392867 |
| directional_accuracy | 0.521360888743669 |
| r2 | -0.0461984817744336 |
| mae | 0.000440417017314885 |
| rmse | 0.000665956347320765 |
| prediction_mean | 5.50147951719895e-05 |
| prediction_std | 0.000169928410122719 |
| target_mean | 7.21679714033874e-05 |
| target_std | 0.000651090976085297 |
| validation_observations | 73452 |

### Validation metrics by day

| day | validation_observations | pearson_ic | spearman_ic | r2 | mae | rmse | directional_accuracy | prediction_mean | prediction_std | target_mean | target_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 80 | 12242 | 0.15882438388166 | 0.23209486820517 | 0.0051880920820331 | 0.0002299026736975 | 0.00028670639589 | 0.631514458421827 | 2.33297079112892e-06 | 9.57518322007556e-06 | 2.11452244181223e-05 | 0.0002874647731163 |
| 81 | 12242 | -0.067083414187726 | -0.0019270285195267 | -0.107637520655001 | 0.0001902287380514 | 0.0002344254264994 | 0.464548276425421 | -1.22382512654175e-05 | 4.07581429945089e-05 | 3.73735304014249e-05 | 0.0002227530319321 |
| 82 | 12242 | 0.0312428848253852 | 0.0163527925774986 | -0.0016462401533432 | 0.0002494869158176 | 0.0003237032183251 | 0.516337199803954 | 1.29927293307533e-05 | 1.24482549375394e-05 | -3.40364225764405e-06 | 0.0003234503111836 |
| 83 | 12242 | 0.150969163218644 | 0.189632520157256 | 0.0175493322999958 | 0.0006325071108347 | 0.0008204896920816 | 0.592468550890377 | 2.17552411631708e-05 | 9.15986617705442e-05 | 7.1537889346989e-05 | 0.0008278191940721 |
| 84 | 12242 | -0.109747086945215 | 0.0104854245346064 | -0.136073408534116 | 0.0006866793681556 | 0.0008649523345873 | 0.392746283287045 | 0.0001777199704931 | 0.0001766833214041 | 1.36316626025971e-05 | 0.0008115339939629 |
| 85 | 12242 | 0.0531483352833083 | 0.09950684996136 | -0.106998165200922 | 0.0006536972973322 | 0.0009988501647958 | 0.530550563633393 | 0.0001275261105191 | 0.0003182188894895 | 0.0002927231639088 | 0.0009493899578924 |

### Comparison with existing W3 models

| model | pearson_ic | spearman_ic | mean_daily_pearson_ic | directional_accuracy | r2 | mae | rmse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ridge | 0.0707122892881086 | 0.055737113260556 | 0.0745360338629087 | 0.507651255241518 | -0.0234135533097628 | 0.0004355500825504 | 0.0006586645682637 |
| Elastic Net | 0.0336523172675627 | 0.0167399274548782 | 0.0037559572753988 | 0.508209442901487 | -0.0164686767151991 | 0.0004302557337539 | 0.0006564259175549 |
| LightGBM | 0.0433187087464854 | 0.0250002876686694 | 0.036225711012676 | 0.521360888743669 | -0.0461984817744336 | 0.0004404170173148 | 0.0006659563473207 |

Differences below are LightGBM minus Ridge; relative change is divided by the absolute Ridge value and is descriptive only.

| metric | Ridge | Elastic Net | LightGBM | LightGBM - Ridge | relative_vs_Ridge_% |
| --- | --- | --- | --- | --- | --- |
| pearson_ic | 0.0707122892881086 | 0.0336523172675627 | 0.0433187087464854 | -0.0273935805416232 | -38.7394904300318 |
| spearman_ic | 0.055737113260556 | 0.0167399274548782 | 0.0250002876686694 | -0.0307368255918866 | -55.1460665861904 |
| mean_daily_pearson_ic | 0.0745360338629087 | 0.0037559572753988 | 0.036225711012676 | -0.0383103228502327 | -51.3983919786977 |
| directional_accuracy | 0.507651255241518 | 0.508209442901487 | 0.521360888743669 | 0.0137096335021512 | 2.70060072945722 |
| r2 | -0.0234135533097628 | -0.0164686767151991 | -0.0461984817744336 | -0.0227849284646708 | -97.3151241215921 |
| mae | 0.0004355500825504 | 0.0004302557337539 | 0.0004404170173148 | 4.86693476440002e-06 | 1.11742253288101 |
| rmse | 0.0006586645682637 | 0.0006564259175549 | 0.0006659563473207 | 7.29177905699999e-06 | 1.10705500315916 |

## Economic utility using the existing Part 5 backtest

The exact existing Part 5 mechanics were applied to LightGBM predictions: prediction sign, unit notional, one position at a time, 300-second same-day exact exit, no interpolation or overnight carry, and 5 bps per side with zero fee. This is an assumed baseline cost, not an empirically calibrated spread estimate.

| model | gross_pnl | transaction_costs | net_pnl | sharpe | maximum_drawdown | turnover | trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ridge | 0.0212814442527203 | 0.246 | -0.22471855574728 | -106.280913201702 | -0.191784071897383 | 492 | 246 |
| Elastic Net | 0.0028984477555441 | 0.246 | -0.243101552244456 | -266.695935904906 | -0.21124492850084 | 492 | 246 |
| LightGBM | 0.0014348715600488 | 0.246 | -0.244565128439951 | -169.225097054269 | -0.214755152304664 | 492 | 246 |

| metric | Ridge | Elastic Net | LightGBM | LightGBM - Ridge | relative_vs_Ridge_% |
| --- | --- | --- | --- | --- | --- |
| gross_pnl | 0.0212814442527203 | 0.0028984477555441 | 0.0014348715600488 | -0.0198465726926715 | -93.2576401159175 |
| transaction_costs | 0.246 | 0.246 | 0.246 | 0 | 0 |
| net_pnl | -0.22471855574728 | -0.243101552244456 | -0.244565128439951 | -0.0198465726926715 | -8.83174628222118 |
| sharpe | -106.280913201702 | -266.695935904906 | -169.225097054269 | -62.9441838525675 | -59.2243536081695 |
| maximum_drawdown | -0.191784071897383 | -0.21124492850084 | -0.214755152304664 | -0.022971080407281 | -11.9775746651015 |
| turnover | 492 | 492 | 492 | 0 | 0 |
| trades | 246 | 246 | 246 | 0 | 0 |

### LightGBM W3 economic summary

| metric | LightGBM W3 |
| --- | --- |
| gross_pnl | 0.0014348715600488 |
| transaction_costs | 0.246 |
| net_pnl | -0.244565128439951 |
| sharpe | -169.225097054269 |
| maximum_drawdown | -0.214755152304664 |
| turnover | 492 |
| trades | 246 |
| win_rate | 0.0609756097560975 |
| average_trade_return | -0.0009941671887802 |
| median_trade_return | -0.0009834275527701 |
| daily_pnl_std | 0.0038236557134499 |
| average_exposure | 0.527014867817816 |
| maximum_exposure | 1 |

### Day-84 sensitivity (post-hoc aggregation only)

Day 84 remains in the primary W3 result. The exclusion is a diagnostic aggregation only; there was no retraining or refitting.

| aggregation | pearson_ic | spearman_ic | r2 | mae | rmse | directional_accuracy | validation_observations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W3 including Day 84 | 0.0433187087464854 | 0.0250002876686694 | -0.0461984817744336 | 0.000440417017314885 | 0.000665956347320765 | 0.521360888743669 | 73452 |
| W3 excluding Day 84 | 0.109987584475101 | 0.126622194106289 | -0.017017903181944 | 0.000391164547146741 | 0.000618521559545463 | 0.547083809834994 | 61210 |

| aggregation | gross_pnl | transaction_costs | net_pnl | sharpe | maximum_drawdown | turnover | trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W3 including Day 84 | 0.00143487156004884 | 0.246 | -0.244565128439951 | -169.225097054269 | -0.214755152304664 | 492 | 246 |
| W3 excluding Day 84 | 0.00799346834460235 | 0.205 | -0.197006531655398 | -297.756778733972 | -0.165319860799562 | 410 | 205 |

## Sanity review and conclusion

Sanity flags: **none**.
Classification: **C — LightGBM does not improve the Ridge baseline**.
The benchmark does not establish production readiness, alpha, profitability, or holdout generalization. The original Ridge and Elastic Net artifacts were read for comparison only and were not retrained or modified.

## Reproducibility and integrity

Research-bearing outputs are deterministic under the fixed seed, single-threaded configuration, and fixed input artifacts. `run_manifest.json` contains a run timestamp; stable output hashes are recorded in `reproducibility.json`.

- `holdout_days_loaded: []`
- frozen namespaces were not modified
- missing Days 65–79 were not fabricated
- no strategy search, hyperparameter search, or additional model was run
