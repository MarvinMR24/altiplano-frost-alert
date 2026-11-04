# Spec patch (ready to paste)

From docs/spec_audit.md. Nothing here has been applied: MUSE.md, CLAUDE.md, docs/project-context.md and README.md were not edited. Apply the same MUSE.md / CLAUDE.md changes to both files.

## MUSE.md and CLAUDE.md

### Section 2, rule 18: REPLACE
```
18. Every experiment has a config in `configs/experiments/<id>.yaml`, fixed seeds, a data hash, outputs in `experiments/<run_id>/` and a single command that reproduces it. No notebook-only results.
```
WITH
```
18. Every experiment run writes `experiments/<run_id>/config.yaml` and `metrics.json` (git): seed, data hash (content hash of features.parquet), features_manifest SHA-256, package versions and the command that reproduces it. Validation predictions go to `data/processed/predictions/<round>/<run_id>.csv` (DVC). MLflow on DagsHub mirrors the runs; the local folder is the source of truth. No notebook-only results.
```

### Section 2, rule 25: REPLACE
```
25. Out of scope, do not build: Telegram, chat, agent or tool calling, cloud deploy, Postgres, web version, Android, 48 h horizon, open-weights hosting, DVC, MODIS (only if everything else is done).
```
WITH
```
25. Out of scope, do not build: Telegram, chat, agent or tool calling, cloud deploy, Postgres, web version, Android, 48 h horizon, open-weights hosting, MODIS (only if everything else is done). DVC with the DagsHub remote is in scope for data and model binaries only.
```

### Section 2: ADD a new group after "Machine learning" (use the next free rule numbers)
```
ML module
- Reusable ML code lives in the package `src/frostwatch_ml` (installed with `pip install -e .`). Scripts in `pipelines/` are thin CLIs with `--config`, `--seed`, `--dry-run` and `--no-sync`. `pipelines/01_download.py` stays as it is.
- Features are an explicit allowlist in `configs/features.yaml`, never "all columns". The AgERA5 night minimum and RH at 15:00 live only in `data/processed/crosschecks.parquet`. Cloud cover enters with a one-day lag (D-1).
- Every fitted statistic (scaler, percentiles, climatology, calibration) is fitted on training years only; any cross-validation inside train is grouped by year.
- The test split is locked: model code reads rows through `leakage.model_rows` (train and validation only); only `pipelines/06_final_eval.py --i-confirm-final` may load the test split, once, writing `reports/final_test_metrics.json`.
- Every metric is reported pooled, per cell and as the macro-average over the 8 cells, with skill against the best baseline (climatology, persistence).
- `make test` (pytest, leakage and integrity tests) and `make lint` (ruff) must pass before any result is reported. Notebooks only present saved outputs and import only `frostwatch_ml` (`tools/check_notebooks.py`).
- Artifact policy: `reports/` (small text and PNG) and `experiments/` in git; `data/` and `models/` in DVC (DagsHub). The model card says "validation metrics only; test pending" until the final evaluation exists. The backend serves the logistic regression from `reports/<model_version>/lr_export.json` with `frostwatch_ml.inference.predict` (numpy and pandas only, no pickle).
- Pipeline scripts run `dvc status`, `dvc push`, `dvc status -c` at the end (one attempt, non-fatal) unless `--no-sync`; on 401 or 403 they stop syncing and report.
- The model is valid only for the 8 cells in `configs/points.yaml`.
```

### Section 3.1 step 3: REPLACE
```
3. **Risk view per AOI:** the night's date, the label "reanalysis data", probability, level (none, watch, alert), conditions for that night, time the night was processed.
```
WITH (builder to confirm the mapping)
```
3. **Risk view per AOI:** the night's date, the label "reanalysis data", probability, level from the cuts in `lr_export.json` (p < 0.3 none; 0.3 to 0.7 watch; >= 0.7 alert), conditions for that night, time the night was processed.
```

### Section 3.6: REPLACE the ML lines of the command block
```
python pipelines/02_features.py
python pipelines/02b_eda.py
python pipelines/03_split.py
python pipelines/04_train_eval.py --round 1
python pipelines/04_train_eval.py --round 2
python pipelines/run_experiment.py configs/experiments/<id>.yaml
python pipelines/06_compare.py
```
WITH
```
pip install -e .
dvc pull
make test && make lint
python pipelines/02a_eda_era5land.py
python pipelines/02b_eda_agera5.py
python pipelines/03_build_night_table.py
python pipelines/03b_eda_merged.py
python pipelines/04_round1.py
python pipelines/05_round2.py
python pipelines/05b_export_artifacts.py
dvc repro          # the whole chain
python pipelines/06_final_eval.py --i-confirm-final   # once, at the end
```

### Section 5 (layout): REPLACE the lines for configs, pipelines, experiments, src and tests
```
  configs/       points.yaml, split.yaml, muse.yaml, experiments/
  pipelines/     numbered scripts and run_experiment.py
  experiments/   <run_id>/ config.yaml metrics.json predictions.csv
  src/serve/     API, tick and replay, notify, explain
  tests/
```
WITH
```
  configs/       points.yaml, cds_datasets.yaml, frost.yaml, features.yaml, model.yaml, muse.yaml
  pipelines/     thin CLIs: 01_download, 02a/02b EDA, 03 night table, 03b EDA, 04_round1, 05_round2, 05b_export_artifacts, 06_final_eval
  src/frostwatch_ml/  ML package (data io, features, leakage guards, models, evaluation, artifacts, inference)
  src/serve/     API, tick and replay, notify, explain
  reports/       git: model cards, lr_export.json, validation tables, figures
  models/        DVC: model.joblib per model version
  experiments/   git: <run_id>/ config.yaml metrics.json
  dvc/           DVC pointer files (raw_cds.dvc); dvc.yaml, dvc.lock at the root
  tests/         pytest leakage and integrity tests
  tools/         check_notebooks.py
```
and in the `.gitignore` sentence ADD `models/`, `.dvc/config.local`, `.dvc/cache`, `.dvc/tmp`.

## docs/project-context.md

### Section 0, "Cut now": REPLACE `DVC (use data hashes)` WITH `(DVC is used for data and model binaries with a DagsHub remote; see CLAUDE.md)`.

### Section 1, Beneficiaries: REPLACE
```
- **Beneficiaries:** residents of cities (La Paz, El Alto, Oruro, Potosi, Puno, Juliaca, Cusco), towns, and producers (crops and livestock). Not only farmers.
```
WITH
```
- **Beneficiaries:** residents and producers (crops and livestock) in the La Paz to Oruro corridor covered by the 8 ERA5-Land cells (El Alto, Oruro, Patacamaya, Calamarca, Caracollo, Corocoro, Charana, Huanuni). Not only farmers.
```

### Section 5.5: ADD at the end
```
- Baselines and models are reported pooled, per cell and as the macro-average over the 8 cells, with skill against the best baseline. Calibration (sigmoid) is fitted on training years with a year-grouped CV and kept only if it lowers the validation Brier score.
```

### Section 5.7: REPLACE
```
Each experiment lives in `experiments/<run_id>/` with `config.yaml`, `metrics.json`, `predictions.csv`, the data hash, seeds and package versions.
```
WITH
```
Each experiment lives in `experiments/<run_id>/` with `config.yaml` and `metrics.json` (seed, data hash, package versions); validation predictions are DVC outputs in `data/processed/predictions/`. MLflow on DagsHub mirrors every run.
```

### Section 7, layout: apply the same layout change as CLAUDE.md section 5.

## README.md

### ADD a section (see HANDOFF/README_snippet_data.md for the full text)
```
## Data and experiments (DVC + DagsHub)
```
### ADD under "Data notes"
```
- Leakage controls: features use only hours up to 18:00 local of the night (22:00 UTC), cloud cover enters with a one-day lag, every fitted statistic uses training years only, and the test years (2018-2025) are locked until a single final evaluation. `make test` runs the checks.
- The model is valid only for the 8 cells listed in configs/points.yaml.
```
