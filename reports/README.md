# reports/

Small, human-readable artifacts tracked in git. Binaries (model.joblib) live in models/ and data in data/processed/, both tracked by DVC and stored on DagsHub.
All metrics are on VALIDATION (2010-2017). The test set (2018-2025) is locked: test pending.

| folder | content |
|---|---|
| round1/ | baselines and default models: pooled, macro and per-cell tables, skill vs baselines, PR curves |
| round2/ | LR grid, tree random search, calibration, finalists, LR coefficients, LR vs tree gap |
| lr-20261103-fbbf62c6/ | LR_best (production_candidate): model_card.json, metrics_validation, per_cell_metrics, threshold, features, reliability_bins, lr_export.json, coefficients; PR-AUC 0.8918, F2 0.8757, macro PR-AUC 0.8374; validation metrics only; test pending |
| lightgbm-20261103-fbbf62c6/ | TREE_best (comparison_only): model_card.json, metrics_validation, per_cell_metrics, threshold, features, reliability_bins; PR-AUC 0.9105, F2 0.8819, macro PR-AUC 0.8624; validation metrics only; test pending |
| mlflow_links.json | MLflow run links on DagsHub (no credentials) |
