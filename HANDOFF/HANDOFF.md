# HANDOFF: Part 1 and Part 2 (EDA, night table, ML module, models)

Produced in an isolated copy of the project. Nothing was committed or pushed to git. DVC data was pushed to DagsHub. The test set (2018-2025) was never evaluated.

## Where each folder goes
- `HANDOFF/files/` mirrors the project root: copy its contents into the root of your project (same relative paths). It contains only files created or changed in this work. `pipelines/01_download.py` is not included (unchanged).
  - `docs/decisions_sections_part1_part2.md`: the sections appended to `docs/decisions.md`. Append them to your file instead of copying.
  - `docs/status_section_model.md`: the "Model" section appended to `docs/status.md`. Append it to your file.
- `HANDOFF/dvc_tracked/`: copies of `models/` and `data/processed/` for local use only. They are DVC objects, not for git; `dvc pull` restores the same files.
- `HANDOFF/spec_patch.md`: exact text to add or replace in MUSE.md, CLAUDE.md, docs/project-context.md and README.md (not applied).
- `HANDOFF/README_snippet_data.md`: README section "Data and experiments (DVC + DagsHub)".

## Git-tracked vs DVC-tracked
| git | DVC (DagsHub remote) |
|---|---|
| `src/`, `pipelines/`, `tests/`, `tools/`, `configs/`, `notebooks/` (executed + HTML), `docs/`, `reports/`, `experiments/` | `data/raw/cds/` (pointer `dvc/raw_cds.dvc`) |
| `dvc/raw_cds.dvc`, `dvc.yaml`, `dvc.lock`, `.dvc/config`, `.dvc/.gitignore`, `.dvcignore` | `data/processed/` (stage outputs, including `predictions/`) |
| `pyproject.toml`, `Makefile`, `requirements-model.txt` | `models/<model_version>/` (model.joblib, bundle_meta.json) |

## .gitignore lines to add or check
```
data/
models/
.dvc/config.local
.dvc/cache
.dvc/tmp
src/*.egg-info/
__pycache__/
```
Make sure these are NOT ignored: `reports/`, `experiments/`, `dvc/*.dvc`, `dvc.yaml`, `dvc.lock`, `.dvc/config`, `.dvc/.gitignore`, `.dvcignore`. Your current `.gitignore` ignores `logs/*`; `logs/model/` (pipeline logs) can stay ignored.

## Files to commit
Everything under `HANDOFF/files/` (listed below) except the two section files, which you merge into `docs/decisions.md` and `docs/status.md`.

## Commands
```
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-model.txt
.venv/bin/pip install -e .
dvc pull
make test            # 40 tests (14 leakage and integrity checks)
make lint
make eda             # 02a, 02b, 03b
make features        # 03 night table
make round1          # 04
make round2          # 05
make export          # 05b
make notebooks       # build, execute, export, check
make repro           # dvc repro of the whole chain, then dvc push and dvc status -c
# once, at the very end, by the builder only:
.venv/bin/python pipelines/06_final_eval.py --i-confirm-final
```
Scripts sync to DVC at the end unless `--no-sync`. `FROSTWATCH_MLFLOW=0` disables the MLflow mirror. On a new machine, set the DVC remote credentials locally with `dvc remote modify --local dagshub auth basic`, `dvc remote modify --local dagshub user <user>` and the access-key field of the http remote (see `dvc remote modify --help`); MLflow reads MLFLOW_TRACKING_URI, MLFLOW_TRACKING_USERNAME and the access-key variable from `.env`.

## Packages
Python 3.12; 3.67.1 (global install).
```
cdsapi==0.7.7
ipykernel==7.4.0
joblib==1.6.0
lightgbm==4.7.0
matplotlib==3.11.2
mlflow==3.17.2
nbconvert==7.17.2
nbformat==5.11.1
netCDF4==1.7.5.1.post1
numpy==2.5.4
pandas==3.1.0
pyarrow==25.0.1
pytest==9.2.0
python-dotenv==1.2.4
PyYAML==6.0.3
ruff==0.17.3
scikit-learn==1.9.1
scipy==1.18.1
xarray==2026.9.0
xgboost==3.4.1
```

## Files in HANDOFF/files (size in bytes, sha256 prefix)
| file | bytes | sha256 |
|---|---|---|
| `.dvc/.gitignore` | 26 | `cda3fc1a4ce9659c` |
| `.dvc/config` | 124 | `6582f36a34ee5ac1` |
| `.dvcignore` | 556 | `a4e0a40e27ef6640` |
| `Makefile` | 1047 | `38dd661e484298ae` |
| `configs/features.yaml` | 3262 | `675afaea17892001` |
| `configs/frost.yaml` | 1616 | `566ee341f4b9168d` |
| `configs/model.yaml` | 1803 | `aa80ed116a770a33` |
| `docs/data_licenses.md` | 1111 | `5b00304d335b795a` |
| `docs/decisions_sections_part1_part2.md` | 4897 | `00a8649d4b448dd2` |
| `docs/eda_agera5.md` | 5907 | `05098d334bd9adc3` |
| `docs/eda_era5land.md` | 8731 | `2723c60a899b776d` |
| `docs/eda_merged.md` | 7197 | `eaadd69fc5a8da22` |
| `docs/figures/agera5_cloud_cover_by_month.png` | 119700 | `aa7a44cb96a46f04` |
| `docs/figures/agera5_vs_era5land_tmin_el_alto.png` | 89031 | `8508f65d1d984aaa` |
| `docs/figures/era5land_frost_nights_by_year.png` | 142691 | `893437bcf7386ed4` |
| `docs/figures/era5land_frost_rate_by_month.png` | 119236 | `0d4bc814e9584f4f` |
| `docs/figures/merged_corr_with_label_train.png` | 65415 | `d72d9d952bd475b3` |
| `docs/figures/merged_frost_rate_by_year.png` | 55551 | `090498d7a18556db` |
| `docs/ml_spec.md` | 7317 | `a4a8c13c0c57fef1` |
| `docs/model_round1.md` | 7868 | `72a6085194a8a10e` |
| `docs/model_round2.md` | 5595 | `4bd9397829ea07a5` |
| `docs/spec_audit.md` | 4395 | `0f7ee38f09c6ec04` |
| `docs/status_section_model.md` | 1429 | `e7f5bf4e3e5c4eb7` |
| `dvc/raw_cds.dvc` | 117 | `1ade5323bb4cbd04` |
| `dvc.lock` | 9344 | `e94f5d0be85fdbcd` |
| `dvc.yaml` | 3793 | `efec5ee661c52b1d` |
| `experiments/r1-climatology-fbbf62c6/config.yaml` | 1023 | `fad67d537c0bf528` |
| `experiments/r1-climatology-fbbf62c6/metrics.json` | 5625 | `1f9d7430b7951a78` |
| `experiments/r1-dewpoint_rule-fbbf62c6/config.yaml` | 1013 | `35548c61ca7eb946` |
| `experiments/r1-dewpoint_rule-fbbf62c6/metrics.json` | 5624 | `9a62eae29246cb43` |
| `experiments/r1-lightgbm-fbbf62c6/config.yaml` | 998 | `75d432fa2f3f595e` |
| `experiments/r1-lightgbm-fbbf62c6/metrics.json` | 5778 | `ed30b22954c3b92b` |
| `experiments/r1-lr_balanced-fbbf62c6/config.yaml` | 1020 | `e716facef787ed48` |
| `experiments/r1-lr_balanced-fbbf62c6/metrics.json` | 5780 | `edbe5dca42af1644` |
| `experiments/r1-lr_none-fbbf62c6/config.yaml` | 1008 | `d4052770abf53ac3` |
| `experiments/r1-lr_none-fbbf62c6/metrics.json` | 5756 | `0c51ff88434506c8` |
| `experiments/r1-majority-fbbf62c6/config.yaml` | 998 | `ecae74d1964a8143` |
| `experiments/r1-majority-fbbf62c6/metrics.json` | 5494 | `e709d09fee5c9e09` |
| `experiments/r1-persistence-fbbf62c6/config.yaml` | 1007 | `b1f7552c589d21e4` |
| `experiments/r1-persistence-fbbf62c6/metrics.json` | 5594 | `f0c8bece6e8d054b` |
| `experiments/r1-random_forest-fbbf62c6/config.yaml` | 1013 | `eca5b0865733e5f8` |
| `experiments/r1-random_forest-fbbf62c6/metrics.json` | 5631 | `79fde75d800a551d` |
| `experiments/r1-xgboost-fbbf62c6/config.yaml` | 995 | `93bb54965205cd4b` |
| `experiments/r1-xgboost-fbbf62c6/metrics.json` | 5758 | `0dbb696e13991a1f` |
| `experiments/r2-LR_best-fbbf62c6/config.yaml` | 1050 | `e8daeca79a55c01b` |
| `experiments/r2-LR_best-fbbf62c6/metrics.json` | 6105 | `9b098afc12521130` |
| `experiments/r2-TREE_best-fbbf62c6/config.yaml` | 1180 | `79d657140b95eb73` |
| `experiments/r2-TREE_best-fbbf62c6/metrics.json` | 6115 | `bd201a3dc2d756f2` |
| `notebooks/01_eda_era5land.html` | 558508 | `27b8c57c2e5e3965` |
| `notebooks/01_eda_era5land.ipynb` | 290557 | `f31940f6cc70f342` |
| `notebooks/02_eda_agera5.html` | 649557 | `183ca84e1600202d` |
| `notebooks/02_eda_agera5.ipynb` | 377733 | `23a194735eb82cbe` |
| `notebooks/03_night_table_and_eda.html` | 448946 | `34b96db497c05197` |
| `notebooks/03_night_table_and_eda.ipynb` | 182870 | `eafb02af4e31289d` |
| `notebooks/04_round1_models.html` | 381315 | `e7dff0193a1c25b1` |
| `notebooks/04_round1_models.ipynb` | 102642 | `1f4e0d5404ff44a1` |
| `notebooks/05_round2_tuning.html` | 338530 | `745850c96baf944f` |
| `notebooks/05_round2_tuning.ipynb` | 68524 | `07d16de31d139490` |
| `pipelines/02a_eda_era5land.py` | 681 | `a1e7737d5d9e4688` |
| `pipelines/02b_eda_agera5.py` | 682 | `bcdddafffac69bea` |
| `pipelines/03_build_night_table.py` | 1053 | `9375c8cea2efe66a` |
| `pipelines/03b_eda_merged.py` | 657 | `b9a0193b4a5eb6df` |
| `pipelines/04_round1.py` | 6074 | `1f785c1d96bb2f44` |
| `pipelines/05_round2.py` | 12076 | `2edf195ad8d74d04` |
| `pipelines/05b_export_artifacts.py` | 7651 | `32cc851a5dd4b2a2` |
| `pipelines/06_final_eval.py` | 2324 | `8e1387eecb08a1c9` |
| `pipelines/make_notebooks.py` | 8012 | `9efca3d182d5f242` |
| `pyproject.toml` | 837 | `d203c4652391bf0e` |
| `reports/README.md` | 1085 | `256814ed72a3827c` |
| `reports/lightgbm-20261103-fbbf62c6/features.json` | 628 | `f76de34ede8da701` |
| `reports/lightgbm-20261103-fbbf62c6/figures/reliability.png` | 34136 | `754ce3e8aae8867a` |
| `reports/lightgbm-20261103-fbbf62c6/metrics_validation.csv` | 580 | `e0b910b35cc1cfee` |
| `reports/lightgbm-20261103-fbbf62c6/metrics_validation.json` | 882 | `836a623d85b16ff1` |
| `reports/lightgbm-20261103-fbbf62c6/model_card.json` | 4367 | `d300b813fdcba79e` |
| `reports/lightgbm-20261103-fbbf62c6/per_cell_metrics.csv` | 2025 | `7189acaf88c3cfd3` |
| `reports/lightgbm-20261103-fbbf62c6/reliability_bins.csv` | 673 | `a0d4c5b0fb3aac12` |
| `reports/lightgbm-20261103-fbbf62c6/reliability_bins.json` | 1694 | `d75f592557bd3684` |
| `reports/lightgbm-20261103-fbbf62c6/threshold.json` | 209 | `381eebe628eb1da5` |
| `reports/lr-20261103-fbbf62c6/coefficients.csv` | 1793 | `92bdc022ea619c13` |
| `reports/lr-20261103-fbbf62c6/features.json` | 628 | `f76de34ede8da701` |
| `reports/lr-20261103-fbbf62c6/figures/reliability.png` | 33804 | `ab7b2ba691a7cadc` |
| `reports/lr-20261103-fbbf62c6/lr_export.json` | 5149 | `b1dac170aec4753a` |
| `reports/lr-20261103-fbbf62c6/metrics_validation.csv` | 579 | `7f82278581a7fc1a` |
| `reports/lr-20261103-fbbf62c6/metrics_validation.json` | 881 | `45e21fd44948c3ef` |
| `reports/lr-20261103-fbbf62c6/model_card.json` | 4416 | `cf4170e408fb7470` |
| `reports/lr-20261103-fbbf62c6/per_cell_metrics.csv` | 2023 | `635b2f3f47f88faf` |
| `reports/lr-20261103-fbbf62c6/reliability_bins.csv` | 676 | `56547a277bdef9f2` |
| `reports/lr-20261103-fbbf62c6/reliability_bins.json` | 1697 | `24414a73a75fe9c3` |
| `reports/lr-20261103-fbbf62c6/threshold.json` | 209 | `c02eab17556b787a` |
| `reports/mlflow_links.json` | 1526 | `ff61f34dc7f0586f` |
| `reports/round1/comparison_macro.csv` | 1868 | `bdb09fb6381863ec` |
| `reports/round1/comparison_macro.json` | 3499 | `545906464c252fac` |
| `reports/round1/comparison_macro.md` | 1156 | `80e527a1e7803d41` |
| `reports/round1/comparison_pooled.csv` | 1996 | `f579a7fbb9a27bab` |
| `reports/round1/comparison_pooled.json` | 3779 | `7460e9ae0e6af144` |
| `reports/round1/comparison_pooled.md` | 1247 | `953b0df8a7dc73f1` |
| `reports/round1/figures/pr_curves_validation.png` | 66432 | `39e3507bb13dafc3` |
| `reports/round1/per_cell_metrics.csv` | 17299 | `fc0be7a681a57a6b` |
| `reports/round1/runs.json` | 1188 | `9e2b91981b5cacb6` |
| `reports/round1/skill_vs_baselines.csv` | 1008 | `9e6ed5e30f85610a` |
| `reports/round1/skill_vs_baselines.json` | 2279 | `e725fff40dc21c4e` |
| `reports/round1/skill_vs_baselines.md` | 730 | `7f917633b97177f0` |
| `reports/round1/skill_vs_baselines_macro.csv` | 1015 | `fe42fb65f64b036d` |
| `reports/round1/skill_vs_baselines_macro.json` | 2286 | `25576c398a3e42ce` |
| `reports/round1/skill_vs_baselines_macro.md` | 729 | `3cd00fa81b5c8b95` |
| `reports/round1/thresholds.json` | 286 | `b48cffe92f689128` |
| `reports/round2/calibration.csv` | 364 | `58b0f67761647a15` |
| `reports/round2/calibration.json` | 585 | `64171cc76783a8d2` |
| `reports/round2/calibration.md` | 318 | `6f38f9d67ad5665b` |
| `reports/round2/comparison_macro.csv` | 812 | `641afa171ce90dd0` |
| `reports/round2/comparison_macro.json` | 1423 | `188764440d894178` |
| `reports/round2/comparison_macro.md` | 593 | `1296ae18fb9b4ff1` |
| `reports/round2/comparison_pooled.csv` | 871 | `fdc86f78d8afb0c8` |
| `reports/round2/comparison_pooled.json` | 1544 | `e2d439d32529211c` |
| `reports/round2/comparison_pooled.md` | 635 | `4e7a6f4bb1deae46` |
| `reports/round2/finalists.md` | 788 | `f9d58ade1ee971eb` |
| `reports/round2/gap_lr_vs_tree.json` | 278 | `ade14648d197ab50` |
| `reports/round2/lr_coefficients.csv` | 867 | `ce84f8eda533d28b` |
| `reports/round2/lr_grid.csv` | 6664 | `a5a96113053bac80` |
| `reports/round2/skill_vs_baselines.csv` | 477 | `76096a38c75734dd` |
| `reports/round2/skill_vs_baselines.json` | 990 | `11cc3f0c37177ca5` |
| `reports/round2/skill_vs_baselines.md` | 418 | `4f3ec19791e4726a` |
| `reports/round2/skill_vs_baselines_macro.csv` | 482 | `e978e66e2593450f` |
| `reports/round2/skill_vs_baselines_macro.json` | 995 | `76fbcb3d32d40d32` |
| `reports/round2/skill_vs_baselines_macro.md` | 417 | `80bfdc0b7a3226ef` |
| `reports/round2/tree_search.csv` | 5356 | `29e071ffa471cd3c` |
| `requirements-model.txt` | 464 | `0bbce70fc334d494` |
| `src/frostwatch_ml/__init__.py` | 127 | `8803e048ab72adba` |
| `src/frostwatch_ml/artifacts/__init__.py` | 28 | `c7d89fecdc6b7e40` |
| `src/frostwatch_ml/artifacts/bundle.py` | 1960 | `7783476881a540dd` |
| `src/frostwatch_ml/artifacts/export_lr.py` | 1773 | `9fdac19d1439e02c` |
| `src/frostwatch_ml/artifacts/model_card.py` | 3467 | `c2526850f25a6d36` |
| `src/frostwatch_ml/cli.py` | 1219 | `2d246aefb1e32fde` |
| `src/frostwatch_ml/config.py` | 3463 | `dadcdb5bb679590f` |
| `src/frostwatch_ml/dataio/__init__.py` | 25 | `51911c4e8a9ad1f7` |
| `src/frostwatch_ml/dataio/cds_reader.py` | 3326 | `00043922c91a0107` |
| `src/frostwatch_ml/dataio/manifest.py` | 1345 | `2ccded0e602c189e` |
| `src/frostwatch_ml/dataio/tables.py` | 1905 | `3b79116fba52216f` |
| `src/frostwatch_ml/eda/__init__.py` | 22 | `2d1edf8946e09d8f` |
| `src/frostwatch_ml/eda/agera5.py` | 9712 | `fc0c52633554d318` |
| `src/frostwatch_ml/eda/common.py` | 988 | `d84999fd75949c8e` |
| `src/frostwatch_ml/eda/era5land.py` | 9270 | `1f4730cd062f2c00` |
| `src/frostwatch_ml/eda/merged.py` | 9249 | `ee7d97da989f12fc` |
| `src/frostwatch_ml/evaluation/__init__.py` | 29 | `5e5a376352c42a2d` |
| `src/frostwatch_ml/evaluation/cells.py` | 1770 | `d30747ff56e253fc` |
| `src/frostwatch_ml/evaluation/metrics.py` | 2774 | `09d7fd6db3b13cf7` |
| `src/frostwatch_ml/evaluation/notebook.py` | 1795 | `0449fba22fba1259` |
| `src/frostwatch_ml/evaluation/plots.py` | 2395 | `a3016719aabb7e92` |
| `src/frostwatch_ml/evaluation/reports.py` | 1341 | `8081e84c66df4141` |
| `src/frostwatch_ml/evaluation/thresholds.py` | 1470 | `3c05913065fcac1d` |
| `src/frostwatch_ml/features/__init__.py` | 27 | `0c715519d4faf0a5` |
| `src/frostwatch_ml/features/cloud.py` | 565 | `058222251405cd02` |
| `src/frostwatch_ml/features/fitted.py` | 2466 | `5f5c3fd4ecf945c1` |
| `src/frostwatch_ml/features/labels.py` | 1502 | `e31779c537fce073` |
| `src/frostwatch_ml/features/night_table.py` | 7057 | `41615427549f8d2f` |
| `src/frostwatch_ml/features/snapshot.py` | 3036 | `769afd38ee564ea6` |
| `src/frostwatch_ml/inference/__init__.py` | 28 | `e70184b623cf5627` |
| `src/frostwatch_ml/inference/predict.py` | 2596 | `7fcf76fcfe6e7a7f` |
| `src/frostwatch_ml/leakage.py` | 3257 | `c38a3bffed68f472` |
| `src/frostwatch_ml/models/__init__.py` | 25 | `fe6d3ddccb347678` |
| `src/frostwatch_ml/models/base.py` | 1766 | `f6d99e8f7c973393` |
| `src/frostwatch_ml/models/baselines.py` | 2778 | `7b1c66e9db20a9d7` |
| `src/frostwatch_ml/models/calibration.py` | 1592 | `d47b7d583f9abead` |
| `src/frostwatch_ml/models/logistic.py` | 1063 | `c71c021b40c2782b` |
| `src/frostwatch_ml/models/registry.py` | 1259 | `b7b425f00104bc38` |
| `src/frostwatch_ml/models/trees.py` | 1205 | `3fb31aea8ab541c6` |
| `src/frostwatch_ml/prep/__init__.py` | 23 | `92f410cdfaa4e4a0` |
| `src/frostwatch_ml/prep/physics.py` | 1068 | `a201563c09521272` |
| `src/frostwatch_ml/prep/quality.py` | 2951 | `29b2fb7adb50b6dd` |
| `src/frostwatch_ml/prep/units.py` | 894 | `ceb8a5fd28d2f28b` |
| `src/frostwatch_ml/runner.py` | 5951 | `6b78e4145ea81175` |
| `src/frostwatch_ml/splits.py` | 1554 | `e17ca9a2d2becbd4` |
| `src/frostwatch_ml/tracking/__init__.py` | 27 | `3f9eb2189916f855` |
| `src/frostwatch_ml/tracking/dvc_sync.py` | 2105 | `53259d196d1bbd09` |
| `src/frostwatch_ml/tracking/mlflow_logger.py` | 3501 | `e6de6dd67e10e839` |
| `tests/conftest.py` | 778 | `d4c97911d7ba166a` |
| `tests/expected_hashes.json` | 985 | `03a08e8c2619b1c9` |
| `tests/test_01_future_perturbation.py` | 2553 | `fee4a58c21a9680e` |
| `tests/test_02_feature_allowlist.py` | 1374 | `80c317732082c88f` |
| `tests/test_03_crosschecks_only.py` | 488 | `343e666b9b858e93` |
| `tests/test_04_cloud_lag.py` | 764 | `32f890ad0dfd0b44` |
| `tests/test_05_train_only_statistics.py` | 2430 | `ecf7845f65a7dba3` |
| `tests/test_06_split_integrity.py` | 1423 | `5074ab5c1aef8b34` |
| `tests/test_07_test_set_guard.py` | 1773 | `7748d6a3010d4600` |
| `tests/test_08_validation_only_selection.py` | 987 | `bfa56223cb9dafc9` |
| `tests/test_09_no_time_index_features.py` | 1310 | `33277e53201c97e9` |
| `tests/test_10_determinism.py` | 918 | `807657a06bd3aa61` |
| `tests/test_11_hash_regression.py` | 1053 | `ad3967a3eef41ce6` |
| `tests/test_12_serving_parity.py` | 2615 | `03840d3d1337f67d` |
| `tests/test_13_artifact_schema.py` | 1535 | `42efb80ef7dd8ca2` |
| `tests/test_14_notebooks.py` | 394 | `bed741bbdc5f7919` |
| `tools/check_notebooks.py` | 1611 | `70698b7e51d9ca28` |

## Files in HANDOFF/dvc_tracked
| file | bytes | sha256 |
|---|---|---|
| `data/processed/anomalies.parquet` | 389185 | `c820a877fa1545b0` |
| `data/processed/crosschecks.parquet` | 3096874 | `fc7c512290f55be7` |
| `data/processed/eda_agera5/cloud_cover_by_month.csv` | 1111 | `1c531f47998ec4b9` |
| `data/processed/eda_agera5/coverage.csv` | 888 | `1cd1853e0ba6fc9c` |
| `data/processed/eda_agera5/crosschecks.csv` | 1813 | `1d45e4d493c31596` |
| `data/processed/eda_agera5/daily_crosscheck.parquet` | 4361412 | `fbc60e9c6e1f3f93` |
| `data/processed/eda_agera5/summary.json` | 392 | `80632e7d09d9096d` |
| `data/processed/eda_era5land/anomaly_counts.csv` | 144 | `4f5fef3a44736de7` |
| `data/processed/eda_era5land/coverage.csv` | 1002 | `37eda558d4ba12a5` |
| `data/processed/eda_era5land/frost_by_cell.csv` | 394 | `faf537a3ac706847` |
| `data/processed/eda_era5land/frost_nights_by_year.csv` | 2127 | `e916df51473ab787` |
| `data/processed/eda_era5land/frost_rate_by_month.csv` | 1974 | `51cbcf13a6a8596f` |
| `data/processed/eda_era5land/nights_label.parquet` | 1002380 | `15ce14c74dadc4e3` |
| `data/processed/eda_era5land/summary.json` | 379 | `beb1db97e6e691b1` |
| `data/processed/eda_era5land/trends.csv` | 580 | `a8f92d8b2a67b650` |
| `data/processed/eda_era5land/value_ranges.csv` | 6364 | `f168d7f2b6031c3b` |
| `data/processed/eda_merged/class_balance.csv` | 306 | `d83a91357c384d66` |
| `data/processed/eda_merged/corr_with_label_train.csv` | 916 | `0a80aa407d7f0d2f` |
| `data/processed/eda_merged/drift_std_mean_diff.csv` | 1956 | `3675f78ec0296c4b` |
| `data/processed/eda_merged/feature_means_by_split.csv` | 2228 | `c782662c8a08b7e5` |
| `data/processed/eda_merged/frost_by_cell_split.csv` | 743 | `4252e505e878f55d` |
| `data/processed/eda_merged/frost_by_month_train.csv` | 1765 | `0dd7566b3ee667a6` |
| `data/processed/eda_merged/frost_by_year.csv` | 1039 | `8fd3d51c3e3b179f` |
| `data/processed/eda_merged/label_vs_agera5.csv` | 799 | `26ada04a880b2f08` |
| `data/processed/eda_merged/missing.csv` | 72 | `1c5c2b02fad200d8` |
| `data/processed/eda_merged/summary.json` | 1252 | `d5a14fad1257752b` |
| `data/processed/features.parquet` | 14457921 | `2c3d9e63dbeb5dca` |
| `data/processed/features_manifest.json` | 4774 | `79bab44990b5a8a2` |
| `data/processed/fitted_stats.json` | 72512 | `5f80f08df17e3d86` |
| `data/processed/model_candidates.json` | 4043 | `831f826c5141dcb8` |
| `data/processed/predictions/r1/r1-climatology-fbbf62c6.csv` | 894840 | `5993de8f611ec07f` |
| `data/processed/predictions/r1/r1-dewpoint_rule-fbbf62c6.csv` | 981285 | `6f5c0ca1822e0fe4` |
| `data/processed/predictions/r1/r1-lightgbm-fbbf62c6.csv` | 1022752 | `643324251499d2b8` |
| `data/processed/predictions/r1/r1-lr_balanced-fbbf62c6.csv` | 1017468 | `437f74d63dabf179` |
| `data/processed/predictions/r1/r1-lr_none-fbbf62c6.csv` | 1020104 | `8d9e8532781ba48a` |
| `data/processed/predictions/r1/r1-majority-fbbf62c6.csv` | 1022742 | `e8ae7916e8d6ef06` |
| `data/processed/predictions/r1/r1-persistence-fbbf62c6.csv` | 648726 | `0b3f71bd388dd930` |
| `data/processed/predictions/r1/r1-random_forest-fbbf62c6.csv` | 665041 | `82227d0e81605d33` |
| `data/processed/predictions/r1/r1-xgboost-fbbf62c6.csv` | 825465 | `d4f69aea29c7470b` |
| `data/processed/predictions/r2/r2-LR_best-fbbf62c6.csv` | 1020262 | `6de3d762648a13dc` |
| `data/processed/predictions/r2/r2-TREE_best-fbbf62c6.csv` | 1024487 | `809d014755e53b37` |
| `models/lightgbm-20261103-fbbf62c6/bundle_meta.json` | 1402 | `804b41d14fcd63d5` |
| `models/lightgbm-20261103-fbbf62c6/model.joblib` | 2811631 | `7d1499217bd8c1f0` |
| `models/lr-20261103-fbbf62c6/bundle_meta.json` | 1426 | `0e1e9544144b6b52` |
| `models/lr-20261103-fbbf62c6/model.joblib` | 2686 | `d6e2756df6c5b8be` |
