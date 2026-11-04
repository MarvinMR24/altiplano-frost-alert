# Round 2 finalists (validation only; test pending)

| finalist | model_version | role | params | calibrated | threshold | pr_auc | f2 | macro_pr_auc | macro_f2 |
|---|---|---|---|---|---|---|---|---|---|
| LR_best | lr-20261103-fbbf62c6 | production_candidate | {'C': 1.0, 'class_weight': None, 'penalty': 'l1'} | True | 0.1724 | 0.8918 | 0.8757 | 0.8374 | 0.8570 |
| TREE_best | lightgbm-20261103-fbbf62c6 | comparison_only | {'n_estimators': 800, 'learning_rate': 0.02, 'num_leaves': 31, 'min_child_samples': 100, 'subsample': 0.8, 'subsample_freq': 1, 'colsample_bytree': 0.6, 'reg_lambda': 1.0} | False | 0.1705 | 0.9105 | 0.8819 | 0.8624 | 0.8627 |

Gap LR_best minus TREE_best, pooled: pr_auc -0.0187, f2 -0.0062, roc_auc -0.0086, brier +0.0066; macro: pr_auc -0.0250, f2 -0.0057.
