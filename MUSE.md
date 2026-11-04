# Muse.md: strict rules and app flow (frostwatch-altiplano)

Read this file fully at the start of every session. Background, rubric, experiment design and the plan are in `PROJECT_CONTEXT.md`. If the two files conflict, this file wins.

## 1. Mission

Build a reproducible frost-prediction pipeline and a simple iPhone app (Expo Go) that sends email and in-app alerts, each with a Muse Spark explanation, for areas of interest in the Bolivian Altiplano (La Paz to Oruro corridor), covered by the 8 points already downloaded.

Deadline: Wed Nov 4, 10:00 PM Bolivia time (UTC-4). **Code freeze: Mon Nov 2 at midnight.** Builder is unavailable on Monday daytime.

## 2. Strict rules (never break)

Communication
1. Talk to the builder in Spanish, short and direct. Code, comments, docs, commit messages and README in English.
2. No em dashes anywhere (text, comments, docs, UI strings).
3. Act without asking when the intent is clear. Ask only when blocked, before destructive actions (force push, deleting data), or before bulk Meta API spending.
4. When something comes out wrong, fix it immediately and say what changed.

Security and repository
5. Never read, print, log or commit secrets. Keys live only in `.env` (gitignored). No keys in the mobile app.
6. The repo is public. Never commit data, `.env`, `*.db`, the Muse cache, personal data or private notes. Run a secret scan (gitleaks) before every push.
7. Everything must be built between Oct 26 and Nov 4. Do not import code, notebooks or data from earlier projects or thesis drafts.
8. NEVER run any command that writes to git history, the index or the remote: no `git add`, `git commit`, `git push`, `git stash`, `git reset`, `git rebase`, `git merge`, `git tag`, no `git checkout` on files, and no `gh` write commands. Only the builder commits and pushes. Allowed read-only commands: `git status`, `git diff`, `git log`, `git show`. Editing files (including .gitignore) is allowed. When work is ready, list the changed files and suggest a commit message, then stop. This applies to Claude Code and Muse Code alike.

Honesty
9. The data is reanalysis (ERA5-Land from the Copernicus Climate Data Store, CDS), not raw satellite imagery. Never call it satellite data without that note.
10. Labels come from the same reanalysis. State this limitation wherever results are shown.
11. Never invent numbers, thresholds, sources or metrics. A number that the code did not compute does not appear in the README, the app or the video.
12. Report negative results as they are. If Muse does not beat raw data, ship the raw model.
13. No medical or health advice anywhere (app, alerts, explanations). Alerts cover crops, livestock, water pipes, vehicles, road ice and property only.

Machine learning
14. Split chronologically by whole years: 60% train, 20% validation, 20% test. Never random. Choose models, hyperparameters and thresholds on validation only. Touch the test set once per final comparison.
15. No feature may use information after 18:00 local time of the prediction day. Labels are never sent to Muse.
16. Logistic regression is the production model. Tree models (XGBoost, LightGBM, random forest) are for comparison only.
17. Decision metrics: PR-AUC and F2. Always report accuracy next to the majority-class accuracy, plus precision, recall, F1, ROC-AUC and Brier score. Explain each metric in one plain sentence in the README.
18. Every experiment run writes `experiments/<run_id>/config.yaml` and `metrics.json` (git): seed, data hash (content hash of features.parquet), features_manifest SHA-256, package versions and the command that reproduces it. Validation predictions go to `data/processed/predictions/<round>/<run_id>.csv` (DVC). MLflow on DagsHub mirrors the runs; the local folder is the source of truth. No notebook-only results.
19. Only two experiment conditions: **A** raw features, **B** Muse-improved dataset (Muse corrections plus Muse-generated columns and variable combinations). Adopt B only if PR-AUC and F2 both improve by at least 0.02 over A on validation and on test. Otherwise ship A. Say in the README that small gains may be noise (no confidence intervals).

ML module
32. Reusable ML code lives in the package `src/frostwatch_ml` (installed with `pip install -e .`). Scripts in `pipelines/` are thin CLIs with `--config`, `--seed`, `--dry-run` and `--no-sync`. `pipelines/01_download.py` stays as it is.
33. Features are an explicit allowlist in `configs/features.yaml`, never "all columns". The AgERA5 night minimum and RH at 15:00 live only in `data/processed/crosschecks.parquet`. Cloud cover enters with a one-day lag (D-1).
34. Every fitted statistic (scaler, percentiles, climatology, calibration) is fitted on training years only; any cross-validation inside train is grouped by year.
35. The test split is locked: model code reads rows through `leakage.model_rows` (train and validation only); only `pipelines/06_final_eval.py --i-confirm-final` may load the test split, once, writing `reports/final_test_metrics.json`.
36. Every metric is reported pooled, per cell and as the macro-average over the 8 cells, with skill against the best baseline (climatology, persistence).
37. `make test` (pytest, leakage and integrity tests) and `make lint` (ruff) must pass before any result is reported. Notebooks only present saved outputs and import only `frostwatch_ml` (`tools/check_notebooks.py`).
38. Artifact policy: `reports/` (small text and PNG) and `experiments/` in git; `data/` and `models/` in DVC (DagsHub). The model card says "validation metrics only; test pending" until the final evaluation exists. The backend serves the logistic regression from `reports/<model_version>/lr_export.json` with `frostwatch_ml.inference.predict` (numpy and pandas only, no pickle).
39. Pipeline scripts run `dvc status`, `dvc push`, `dvc status -c` at the end (one attempt, non-fatal) unless `--no-sync`; on 401 or 403 they stop syncing and report.
40. The model is valid only for the 8 cells in `configs/points.yaml`.

Muse usage
20. Use `muse-spark-1.3` through the Meta Model API in Standard mode. Temperature 0, strict JSON output, versioned prompts in `prompts/`.
21. Every Muse call is cached by hash in `logs/muse_cache/` and its token usage is appended to `logs/muse_usage.jsonl`. Re-runs read from the cache.
22. Muse receives only the records flagged by our EDA or the capped sample, with dates and locations masked and no labels. Never send the full history.
23. Budget: the Muse experiment is capped at 25 USD and everything at a soft cap of 60 USD. Use `MUSE_MOCK=1` for development. No retry loops. Check usage before and after each run.
24. Alert explanations: one batched, cached call per alert. Verify every number against the model output, and fall back to a template if the check fails. Skip the LLM when risk is below the watch level.

Scope
25. Out of scope, do not build: Telegram, chat, agent or tool calling, Postgres, a shipped web version (Expo web is used only for local testing), Android, 48 h horizon, open-weights hosting, MODIS (only if everything else is done). DVC with the DagsHub remote is in scope for data and model binaries only. A backend deploy to AWS is planned by the builder; the mobile app is never containerized.
26. Cut order if behind: Round 2 extras, random forest and LightGBM, custom pin, English dictionary, Muse explanations (use templates), the Muse experiment (report as future work and ship A).
27. Never cut: chronological split with baselines and honest metrics, the final logistic regression, email and push for a replayed test night, the README with results and a "Meta tooling used" table, the 3-minute video.
28. Before ending any session: update docs/status.md and list what is ready for the builder to commit.

External services
29. Copernicus CDS (ECMWF is suspending accounts for abusive activity): submit requests strictly one at a time, never in parallel or in batches, with a single process (lock file). Run one tiny test request before each new dataset or area scheme. Never retry an invalid request: stop and report the error. Use only the official cdsapi and only request templates generated by the dataset's own form. Wait at least 10 seconds between requests.
30. All data comes from CDS only. No weather or forecast APIs are used.
31. If CDS is slow or the account is suspended, stop and report to the builder. Do not switch data sources on your own.

## 3. App and system flow

### 3.1 User flow (iPhone, Expo Go)
1. **Onboarding:** language (Spanish by default), profile (producer or resident), optional crops and livestock, optional email (double opt-in with a confirmation link), notification permission.
2. **Select areas of interest (AOI):** only inside the coverage of the 8 downloaded points in `configs/points.yaml` (El Alto, Oruro, Patacamaya, Calamarca, Caracollo, Corocoro, Charana, Huanuni), one ERA5-Land cell each. No other places. Each AOI has a user threshold of 30, 50 or 70 percent.
3. **Risk view per AOI:** the night's date, the label "reanalysis data", probability, level from the cuts in `lr_export.json` (p < 0.3 none; 0.3 to 0.7 watch; >= 0.7 alert), conditions for that night, time the night was processed.
4. **Alert arrives** by email and by in-app push.
5. **Alert detail:** headline, why, what to do (by profile), caveats, and "how this was computed" (model version and a validation metrics summary).
6. **Feed:** alert history per AOI.
7. **Settings:** language, profile, thresholds, email on or off, delete my data.

There is no chat and no agent.

### 3.2 System flow (replay or manual tick, no scheduler)
There is no periodic scheduler. CDS reanalysis is published a few days late, so there is no live "tonight" forecast in this version. A night is processed in one of two modes only:
- **Replay:** a held-out test-period night with a simulated clock (section 3.3).
- **Manual tick:** `python -m app.cli tick --date YYYY-MM-DD` (default: the latest night available in the processed table) runs steps 2 to 6 for that night.

Replay and tick are a CLI inside the backend container, never HTTP endpoints (ngrok forwards every route).

Alerts are generated when a night is processed. Never describe them as real time or instant.

1. For each AOI point, read the processed CDS reanalysis rows for the selected night.
2. Build the 18:00 features with the same code used in training.
3. If B was adopted: run the EDA checks, send only the flagged records to Muse in one batched call for all points, apply the corrections and add the generated columns.
4. Logistic regression returns the probability. Compare it with the threshold fixed on validation and with the user's threshold.
5. If it crosses and was not already alerted, create the alert: one per AOI per night, re-alert only if the level rises, at most 2 per 24 hours.
6. Generate the Muse explanation (cached and verified), send the email (SMTP) and the Expo push, store the alert in the feed and log everything.
7. Below the watch level: no LLM call.

### 3.3 Replay (demo)
Pick a night from the **test period** where frost occurred. Run steps 2 to 6 with a simulated clock, the final model, a real Muse explanation, a real push to the iPhone and a real email. Label it clearly as a replay. Keep one honest miss or false alarm for the README.

### 3.4 Notifications
- Email: SMTP with a dedicated Gmail account and an app password, through a pluggable `EmailSender` (`EMAIL_PROVIDER=smtp`). No alert is sent to an unconfirmed email.
- Push: Expo Push API. Works in Expo Go on iPhone only.

### 3.5 Backend (FastAPI + SQLite, local)
Endpoints:
- `POST /users`, `DELETE /users/me`
- `POST /devices` (Expo push token)
- `POST /aois`, `GET /aois`, `DELETE /aois/{id}`
- `GET /risk?aoi_id=`
- `GET /alerts`, `GET /alerts/{id}`
- `POST /email/confirm`

Tables: `users`, `devices`, `aois`, `alerts`, `explanations` (cache), `runs`.

Store only email, name, optional phone, password hash, push token, language, profile, crops, livestock, default threshold and AOI coordinates. Provide data deletion.

### 3.6 Commands to implement
```
python pipelines/01_download.py --config configs/points.yaml
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
python pipelines/05_muse_correct.py --config configs/muse.yaml
dvc repro          # the whole chain
python pipelines/06_final_eval.py --i-confirm-final   # once, at the end
uvicorn src.serve.main:app --reload
cd mobile && npx expo start
```

### 3.7 Definition of done (checkpoints)
- Meta API test call returns strict JSON.
- Round 1 and Round 2 tables exist on validation.
- A fake alert reaches the iPhone as push and the inbox as email.
- Experiment A versus B has a result table, or a partial report by 10:30 PM Monday.
- The chosen model runs in the serving flow and a real alert goes end to end.
- The replay runs from one command.
- README has results, limits and the "Meta tooling used" table. Repo is public with no secrets.

## 4. Environment variable names (values only in `.env`)
`META_API_KEY`, `META_API_BASE_URL`, `MUSE_MODEL`, `MUSE_MOCK`, `MUSE_MAX_TOKENS`, `EMAIL_PROVIDER`, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`, `EMAIL_FROM`, `EXPO_PUSH_URL`, `CDS_API_KEY`, `CDS_API_URL`, `DATABASE_URL`, `DEMO_REPLAY`.

## 5. Repository layout
```
frostwatch-altiplano/
  README.md  muse.md  PROJECT_CONTEXT.md  .env.example  .gitignore  requirements.txt
  configs/       points.yaml, cds_datasets.yaml, frost.yaml, features.yaml, model.yaml, muse.yaml
  pipelines/     thin CLIs: 01_download, 02a/02b EDA, 03 night table, 03b EDA, 04_round1, 05_round2, 05b_export_artifacts, 06_final_eval
  src/frostwatch_ml/  ML package (data io, features, leakage guards, models, evaluation, artifacts, inference)
  prompts/       versioned Muse prompts
  reports/       git: model cards, lr_export.json, validation tables, figures
  models/        DVC: model.joblib per model version
  experiments/   git: <run_id>/ config.yaml metrics.json
  dvc/           DVC pointer files (raw_cds.dvc); dvc.yaml, dvc.lock at the root
  src/serve/     API, tick and replay, notify, explain
  mobile/        Expo app
  docs/          decisions.md, eda.md, metrics.md, status.md, muse_usage.md
  logs/          sample_muse_calls.jsonl (sanitized)
  tests/         pytest leakage and integrity tests
  tools/         check_notebooks.py
  data/          gitignored
```
`.gitignore` must include: `.env`, `.venv/`, `node_modules/`, `__pycache__/`, `data/`, `*.db`, `.muse/`, `.expo/`, `.claude/settings.local.json`, `logs/muse_cache/` and raw files in `logs/`, plus `models/`, `.dvc/config.local`, `.dvc/cache` and `.dvc/tmp`.