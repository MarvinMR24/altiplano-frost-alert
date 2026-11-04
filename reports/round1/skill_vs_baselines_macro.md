# Round 1, validation, skill vs best baseline (macro)

| model | pr_auc | pr_auc_minus_best_baseline | f2 | f2_minus_best_baseline | brier_skill_vs_climatology |
|---|---|---|---|---|---|
| majority | 0.3353 | -0.3956 | 0.6840 | -0.1442 | -0.8824 |
| climatology | 0.7310 | 0.0000 | 0.8281 | 0.0000 | 0.0000 |
| persistence | 0.6060 | -0.1250 | 0.7176 | -0.1105 | -0.3507 |
| dewpoint_rule | 0.6642 | -0.0668 | 0.7952 | -0.0329 |  |
| lr_none | 0.8372 | 0.1062 | 0.8572 | 0.0291 | 0.2354 |
| lr_balanced | 0.8362 | 0.1052 | 0.8573 | 0.0292 | 0.1868 |
| xgboost | 0.8508 | 0.1198 | 0.8600 | 0.0319 | 0.2608 |
| lightgbm | 0.8574 | 0.1265 | 0.8610 | 0.0329 | 0.2774 |
| random_forest | 0.8470 | 0.1160 | 0.8592 | 0.0311 | 0.2648 |
