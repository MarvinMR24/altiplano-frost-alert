# Round 1, validation, skill vs best baseline (pooled)

| model | pr_auc | pr_auc_minus_best_baseline | f2 | f2_minus_best_baseline | brier_skill_vs_climatology |
|---|---|---|---|---|---|
| majority | 0.3353 | -0.4781 | 0.7161 | -0.1309 | -0.8824 |
| climatology | 0.8135 | 0.0000 | 0.8470 | 0.0000 | 0.0000 |
| persistence | 0.6573 | -0.1562 | 0.7594 | -0.0876 | -0.3507 |
| dewpoint_rule | 0.6903 | -0.1232 | 0.8215 | -0.0255 |  |
| lr_none | 0.8917 | 0.0782 | 0.8759 | 0.0289 | 0.2354 |
| lr_balanced | 0.8913 | 0.0778 | 0.8760 | 0.0290 | 0.1868 |
| xgboost | 0.9042 | 0.0907 | 0.8796 | 0.0326 | 0.2608 |
| lightgbm | 0.9070 | 0.0935 | 0.8804 | 0.0333 | 0.2774 |
| random_forest | 0.9011 | 0.0876 | 0.8783 | 0.0313 | 0.2648 |
