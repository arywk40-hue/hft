# Generated results inventory

The result tables in this directory are generated analytical artifacts and
remain local rather than being bulk-committed. They were not changed during
repository organization.

## Scope

- Development: expected 85 days; 70 available (Days 1–64 and 80–85).
- Missing development days: Days 65–79, represented explicitly in scoped tables.
- Holdout: Days 86–108, validated separately after the development freeze.
- Days 109–123: out of scope.

## Main result groups

| Directory | Contents |
|---|---|
| `quality/` | Cleaning policy and Part 1 descriptive statistics |
| `diagnostics/` | Day-local ACF and intraday seasonality |
| `distributions/` | Normality tests, sigma events, tails, and extremes |
| `regimes/` | Per-day regime table, summaries, transitions, durations |
| `features/` | Taxonomy and reverse-engineering candidate evidence |
| `predictive/` | Per-day and aggregate forward-return IC results |
| `redundancy/` | Pairwise redundancy and PCA summaries |
| `missingness/` | Structural missingness, warm-up, and window ladder |
| `freeze/` | Frozen development conclusions |
| `holdout/` | Separate Days 86–108 validation artifacts |

The authoritative mapping is [reports/artifact_index.md](../reports/artifact_index.md).
