# Data layout and boundary

Raw CSV files are external, read-only inputs and are excluded from version
control. The configured development scope is Days 1–85, of which Days 1–64
and 80–85 are available. Days 65–79 are explicit missing days. Days 86–108
are holdout data and Days 109–123 are out of scope.

Generated validated and processed data are local artifacts. Do not modify raw
CSV files, fabricate missing days, or use holdout data for development.
