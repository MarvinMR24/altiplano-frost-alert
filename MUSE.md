# Muse.md: strict rules and app flow (frostwatch-altiplano)

Read this file fully at the start of every session. Background, rubric, experiment design and the plan are in `PROJECT_CONTEXT.md`. If the two files conflict, this file wins.

## 1. Mission

Build a reproducible frost-prediction pipeline and a simple iPhone app (Expo Go) that sends email and in-app alerts, each with a Muse Spark explanation, for areas of interest across the Bolivian and Peruvian Altiplano.

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
7. Everything must be built between Oct 26 and Nov 4. Do not import code, notebooks or data from earlier projects or thesis drafts. Commit small and often. Tag Muse Code work with `[muse-code]`.

Honesty
8. The data is reanalysis (ERA5 and ERA5-Land through Open-Meteo), not raw satellite imagery. Never call it satellite data without that note.
9. Labels come from the same reanalysis. State this limitation wherever results are shown.
10. Never invent numbers, thresholds, sources or metrics. A number that the code did not compute does not appear in the README, the app or the video.
11. Report negative results as they are. If Muse does not beat raw data, ship the raw model.
12. No medical or health advice anywhere (app, alerts, explanations). Alerts cover crops, livestock, water pipes, vehicles, road ice and property only.

Machine learning
13. Split chronologically by whole years: 60% train, 20% validation, 20% test. Never random. Choose models, hyperparameters and thresholds on validation only. Touch the test set once per final comparison.
14. No feature may use information after 18:00 local time of the prediction day. Labels are never sent to Muse.
15. Logistic regression is the production model. Tree models (XGBoost, LightGBM, random forest) are for comparison only.
16. Decision metrics: PR-AUC and F2. Always report accuracy next to the majority-class accuracy, plus precision, recall, F1, ROC-AUC and Brier score. Explain each metric in one plain sentence in the README.
17. Every experiment has a config in `configs/experiments/<id>.yaml`, fixed seeds, a data hash, outputs in `experiments/<run_id>/` and a single command that reproduces it. No notebook-only results.
18. Only two experiment conditions: **A** raw features, **B** Muse-improved dataset (Muse corrections plus Muse-generated columns and variable combinations). Adopt B only if PR-AUC and F2 both improve by at least 0.02 over A on validation and on test. Otherwise ship A. Say in the README that small gains may be noise (no confidence intervals).

Muse usage
19. Use `muse-spark-1.3` through the Meta Model API in Standard mode. Temperature 0, strict JSON output, versioned prompts in `prompts/`.
20. Every Muse call is cached by hash in `logs/muse_cache/` and its token usage is appended to `logs/muse_usage.jsonl`. Re-runs read from the cache.
21. Muse receives only the records flagged by our EDA or the capped sample, with dates and locations masked and no labels. Never send the full history.
22. Budget: the Muse experiment is capped at 25 USD and everything at a soft cap of 60 USD. Use `MUSE_MOCK=1` for development. No retry loops. Check usage before and after each run.
23. Alert explanations: one batched, cached call per alert. Verify every number against the model output, and fall back to a template if the check fails. Skip the LLM when risk is below the watch level.

Scope
24. Out of scope, do not build: Telegram, chat, agent or tool calling, cloud deploy, Postgres, web version, Android, 48 h horizon, open-weights hosting, DVC, MODIS (only if everything else is done).
25. Cut order if behind: Round 2 extras, random forest and LightGBM, custom pin, English dictionary, Muse explanations (use templates), the Muse experiment (report as future work and ship A).
26. Never cut: chronological split with baselines and honest metrics, the final logistic regression, email and push for a replayed test night, the README with results and a "Meta tooling used" table, the 3-minute video.
27. Before ending any session: commit, push and update `docs/status.md` (done, next steps, known bugs, how to run).

## 3. App and system flow

### 3.1 User flow (iPhone, Expo Go)
1. **Onboarding:** language (Spanish by default), profile (producer or resident), optional crops and livestock, optional email (double opt-in with a confirmation link), notification permission.
2. **Select areas of interest (AOI):** city presets La Paz, El Alto, Oruro, Potosi, Puno, Juliaca, Cusco. A custom pin only if time allows. Each AOI has a user threshold of 30, 50 or 70 percent.
3. **Risk view per AOI:** probability, level (none, watch, alert), expected conditions tonight, time of last update.
4. **Alert arrives** by email and by in-app push.
5. **Alert detail:** headline, why, what to do (by profile), caveats, and "how this was computed" (model version and a validation metrics summary).
6. **Feed:** alert history per AOI.
7. **Settings:** language, profile, thresholds, email on or off, delete my data.

There is no chat and no agent.

### 3.2 System flow (every 30 minutes, and for the replay)
1. For each AOI point, fetch the Open-Meteo forecast.
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
- `POST /internal/tick`, `POST /internal/replay` (local only, secret header)

Tables: `users`, `devices`, `aois`, `alerts`, `explanations` (cache), `runs`.

Store only email, push token, language, profile and AOI coordinates. Provide data deletion.

### 3.6 Commands to implement
```
python pipelines/01_download.py --config configs/points.yaml
python pipelines/02_features.py
python pipelines/02b_eda.py
python pipelines/03_split.py
python pipelines/04_train_eval.py --round 1
python pipelines/04_train_eval.py --round 2
python pipelines/05_muse_correct.py --config configs/muse.yaml
python pipelines/run_experiment.py configs/experiments/<id>.yaml
python pipelines/06_compare.py
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
`META_API_KEY`, `META_API_BASE_URL`, `MUSE_MODEL`, `MUSE_MOCK`, `MUSE_MAX_TOKENS`, `EMAIL_PROVIDER`, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`, `EMAIL_FROM`, `EXPO_PUSH_URL`, `OPEN_METEO_BASE_URL`, `DATABASE_URL`, `DEMO_REPLAY`.

## 5. Repository layout
```
frostwatch-altiplano/
  README.md  muse.md  PROJECT_CONTEXT.md  .env.example  .gitignore  requirements.txt
  configs/       points.yaml, split.yaml, muse.yaml, experiments/
  pipelines/     numbered scripts and run_experiment.py
  prompts/       versioned Muse prompts
  experiments/   <run_id>/ config.yaml metrics.json predictions.csv
  src/serve/     API, scheduler, notify, explain
  mobile/        Expo app
  docs/          decisions.md, eda.md, metrics.md, status.md, muse_usage.md
  logs/          sample_muse_calls.jsonl (sanitized)
  tests/
  data/          gitignored
```
`.gitignore` must include: `.env`, `.venv/`, `node_modules/`, `__pycache__/`, `data/`, `*.db`, `.muse/`, `.expo/`, `.claude/settings.local.json`, `logs/muse_cache/` and raw files in `logs/`.