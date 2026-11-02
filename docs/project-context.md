# frostwatch-altiplano: project context

Background context for the project: event, rubric, design, experiment, Meta tooling, plan, video and copy. The strict rules and the app flow live in `CLAUDE.md`, which wins on any conflict. Safe to commit: no secrets and no personal data.

## 0. Scope override and design decisions (Nov 2). This section wins over everything below

**Availability:** main build session in the early hours of Mon Nov 2 (now). Unavailable during Monday daytime. Last details Monday night. Video on Tue Nov 3 and Wed Nov 4. Deadline Wed Nov 4, 10:00 PM Bolivia time. **Code freeze: Mon Nov 2 at midnight.** Submit by 2:00 PM on Nov 4. Before stopping the early-hours session, commit, push and write `docs/status.md` (done, next steps, known bugs, how to run).

**Design decisions**
- The core of the project is **reproducible pipelines and an honest experiment**. The app is simple: it receives the model output and shows it with an AI explanation.
- Notifications: **email (local SMTP) and in-app push on iPhone (Expo Go)**. No Telegram.
- Everything runs **locally**: no cloud deploy, SQLite, no web fallback.
- Model: **logistic regression is the production candidate**. Gradient boosting and other models are for comparison only.
- Muse Spark is used in two places: (1) an offline, cached, reproducible **data correction and anomaly analysis pipeline** that is tested as an ablation, and (2) the **explanation** shown in each alert. There is **no autonomous agent, no chat, no tool calling** in this version.
- Muse correction is adopted only if it improves the model on the test set by a margin declared in advance (section 5.8). Otherwise the raw-data logistic regression ships, and the negative result is reported honestly.
- Data is labeled honestly: ERA5-Land and similar are **reanalysis products** (model plus assimilated satellite and surface observations), not raw satellite images. Do not call them "satellite data" in the README without this note.

**Cut now:** cloud deploy, Postgres, web fallback, Android build, 48 h horizon, Telegram, chat, agent and tool calling, Baseten or Glimmer or any open-weights path (no partner credits), MODIS LST (only if everything else is done), DVC (use data hashes), morning-after check.

## 1. Project at a glance

- **Name:** FrostWatch Altiplano (repo: `frostwatch-altiplano`).
- **One-liner:** A mobile early-warning app that sends email and in-app alerts, generated when a night of reanalysis data is processed, when radiation frost is likely in the areas you choose across the Bolivian and Peruvian Altiplano, powered by a reproducible ML pipeline and Meta's Muse Spark for data quality analysis and plain-language explanations.
- **Event:** Meta Global AI Developer Hackathon (Meta + Cerebral Valley). Remote, 10 days. Solo, **Indie track**. Theme: "Build for Your World".
- **Key dates (Bolivia time, UTC-4):** deadline Wed Nov 4, 10:00 PM (9:00 PM ET). Judging Nov 4 to 8. Live finals Nov 9. Community vote winner Nov 16. X engagement closes Nov 8, 11:59 PM ET.
- **Beneficiaries:** residents of cities (La Paz, El Alto, Oruro, Potosi, Puno, Juliaca, Cusco), towns, and producers (crops and livestock). Not only farmers.

## 2. Working agreements

See `CLAUDE.md` (strict rules).

## 3. Official rules (checklist)

- New work only, built during Oct 26 to Nov 4. The demo must show only what was built during the event. If judges cannot tell what is new, the project is disqualified.
- Public repository is mandatory.
- Teams up to 4, solo allowed. One track only (Indie). One person submits, all members added.
- Demo video of **3 minutes** is required and is one of the main scoring items.
- Disqualified: projects that break legal, ethical or platform policies, or use code, data or assets without rights.
- Banned generic projects: AI medical or health advice, basic RAG apps, simple image analyzers, "AI for education" chatbots, job application screeners, nutrition coaches, personality analyzers, sports analyzers or coaches.
- Must fit a theme: "Build for Your World" or "Push the Frontier".
- Submit by Nov 4, 9:00 PM ET at https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit with public repo, working demo video link and all members added.
- Waiver: 18+ and of legal age locally. Not eligible: Meta or Cerebral Valley staff, contractors, government-affiliated people and their households.
- Dates and details may change at Meta's discretion. Re-check the event page and Discord.

How we stay clear of the banned list: no vector search over documents, no image analysis, **no medical or health advice** (alerts cover crops, livestock, water pipes, vehicles, road ice and property only), and the product is a forecasting pipeline with an experiment, not a generic chatbot.

## 4. Judging rubric and bonus prizes

Same rubric in Stage 2 and the final. Scores 0 to 10 per criterion.

| Criterion | Weight | Our plan |
|---|---|---|
| Impact | 30% | Real recurring risk for millions of people across the Altiplano. Alerts for areas people choose |
| Use of Meta AI tooling | 25% | Muse Spark as a data-quality analyst inside a reproducible pipeline, evaluated as an ablation with a pre-declared decision rule, plus Muse Spark explanations in alerts. Creative and measurable, with honest results either way |
| Demo | 25% | Real iPhone, real email and push, replay of a real out-of-sample test night |
| Technical depth | 20% | Chronological 60/20/20 split, baselines, two comparison rounds, rare-event metrics, documented limits |

Bonus prizes (50K USD total): Most Viral 20K (post the demo on X, low effort), Community Vote 10K (genuine community only), Best Agentic 5K (not targeted in this design), Best Open Weights 10K (dropped, no partner credits), Best Creative Build 5K (skip). Some bonuses are flagged in round one, so ask in Discord how.

Credits: 150 USD Meta Model API credits. These are the only credits the builder has.

## 5. System design

### 5.1 Overview
```
Reanalysis data (many years, about 10 points)
  -> features at 18:00 local + label (frost tonight)
  -> chronological split 60/20/20 by whole years
  -> Round 1: baselines and models on raw features (select on validation)
  -> Round 2: tuned variants (select on validation)
  -> Muse correction pipeline (offline, cached) -> ablation on test
  -> decision: raw logistic regression or logistic regression + Muse correction
  -> serving (local): latest CDS data -> probability -> alert -> Muse explanation
  -> email (SMTP) + in-app push (iPhone) -> simple Expo app
```

### 5.2 Data
- **Source:** ERA5-Land (Copernicus and ECMWF) from the Copernicus Climate Data Store (CDS), dataset `reanalysis-era5-land-timeseries`, downloaded with `pipelines/01_download.py`. CDS is the only data source. Requests can queue, so they run one at a time and every file is recorded in a manifest. Optional extra only if time: MODIS night land surface temperature.
- **Years:** as many as possible. Minimum 1990 to 2025 (more if easy). Note possible trend and instrument changes in the README.
- **Points:** about 10: La Paz, El Alto, Oruro, Potosi, Puno, Juliaca, Cusco plus about 3 rural altiplano points (for example Uyuni, Patacamaya, Desaguadero; choose coordinates and record elevation).
- **Variables (hourly):** 2 m temperature, dew point, relative humidity, wind speed, cloud cover, shortwave radiation, surface pressure, precipitation, soil temperature, snow depth if available.
- **Rate limits and licensing:** one CDS request at a time per point and date range, no automatic retries, local files tracked in a manifest. Never commit data, only scripts and configs. Attribute ERA5-Land (Copernicus) and check the Copernicus licence for use in a prize contest.
- **Data snapshot:** record a hash of the final dataset in every experiment so runs are comparable.

### 5.3 Features and label
- **Prediction time:** 18:00 local (22:00 UTC). Features use only information available at or before that time.
- **Label:** frost tonight = the minimum hourly 2 m temperature between 18:00 and 09:00 local is at or below 0 degrees C. Also store the minimum value (optional regression variant).
- **Features:** T and dew point at 18:00, dew point depression, relative humidity, wind, cloud cover, radiation and its afternoon trend, cooling rate from 15:00 to 18:00, pressure, precipitation in the last 24 h, soil temperature, previous night minimum, previous night frost flag, day of year (sine and cosine), elevation, latitude.
- **Limitation to state:** labels come from the same reanalysis, so the model predicts reanalysis-grid frost, which is smoother than station frost in cold hollows. If station data is available, validate on a small subset.

### 5.4 Split
Chronological by **whole years**: first 60% of years for train, next 20% for validation, last 20% for test. No random split. Validation is used for all choices (models, hyperparameters, thresholds). **Test is touched once per final comparison** and never used for selection.

### 5.5 Baselines and models
- **Reference baselines:** majority class, climatology by day of year, persistence (frost last night), dew point rule.
- **Round 1 (raw features, default settings, compared on validation):** logistic regression (with and without class weights), XGBoost, LightGBM, random forest.
- **Round 2 (compared on validation):** tuned logistic regression (regularization strength and class weights) and the best tree model (small random search), with optional probability calibration. Fix the decision threshold on validation to maximize F2.
- **Recommendation:** logistic regression is the production candidate: cheap, interpretable, well calibrated, trivial to run locally. Tree models are likely to match or slightly beat it on raw features, so they are reported for comparison only. This is an expectation, not a result.

### 5.6 Metrics (report on validation and test)
- **Primary metrics for decisions:** PR-AUC and F2. F2 weights recall more, because missing a frost is worse than a false alarm.
- **Also report:** accuracy (always next to the majority-class accuracy, because frost nights are a minority and accuracy alone is misleading), precision, recall, F1, ROC-AUC, and the Brier score (the error of the predicted probabilities, lower is better). Optional plot: calibration curve.
- Keep the math light: explain each metric in one plain sentence in the README.

### 5.7 Isolated experiments
Each experiment lives in `experiments/<run_id>/` with `config.yaml`, `metrics.json`, `predictions.csv`, the data hash, seeds and package versions. A single command reproduces it (for example `python pipelines/run_experiment.py configs/experiments/<id>.yaml`). Runs never share mutable state. A comparison script builds the final tables.

### 5.8 Muse correction pipeline (added value)
Goal: test whether Muse Spark can improve the data, and with it the logistic regression, in a way that is reproducible, cheap and easy to explain.
- **EDA first, done by us (`pipelines/02b_eda.py`, results in `docs/eda.md`):** missing values, impossible or inconsistent values (for example dew point above temperature, humidity outside 0 to 100, radiation that does not match cloud cover), sudden jumps and outliers. The EDA produces an **anomaly list with exact positions** (row id, field, reason). Muse does not search the whole history for problems.
- **Muse correction (`pipelines/05_muse_correct.py`):** Muse receives only the flagged records with a little surrounding context (neighbor hours or days), in batches, and returns strict JSON: corrected value, confidence, reason. A correction is applied only if confidence is high and the value is physically plausible. Every change is logged.
- **Muse-generated columns (contribution to the dataset):** for the sampled rows, Muse also adds a `daily_summary` category (clear and calm, cloudy, windy, humid and cold) and a `frost_likelihood` between 0 and 1, based only on data up to 18:00. Optional, one single call: Muse proposes useful variable combinations from the EDA summary and our code computes them (Muse proposes, code computes).
- **Reproducibility:** temperature 0, pinned model id, versioned prompts in `prompts/`, every call cached by hash in `logs/muse_cache/`, scripts re-run from the cache without calling the API. The API is not guaranteed deterministic, so the cache is the source of truth. Commit configs, prompts, metrics and a small sample of calls. Keep the raw cache local unless data licenses allow committing it.
- **Leakage controls:** Muse never sees labels or future data. Dates and locations are masked so it cannot recall real historical weather.
- **Budget:** corrections are cheap because only flagged records are sent. The generated columns need one pass over a capped sample (about 5,000 to 20,000 rows, stratified by split). Rough estimate 5 to 15 USD, hard cap 25 USD.
- **Conditions, same rows and same split (only two, to save time):** A = logistic regression on raw features. B = logistic regression on the Muse-improved dataset (Muse corrections plus the Muse-generated columns and variable combinations). Also report A on the full dataset and the best tree model for reference. B bundles all Muse contributions, so we cannot say which part helped. State this in the README.
- **Decision rule (simple, declared before running):** adopt B only if PR-AUC and F2 improve by at least 0.02 over A on BOTH validation and test. Otherwise ship A. Differences are measured on one test set without confidence intervals, so say in the README that small gains may be noise. Either outcome goes in the README.
- **Runtime use if adopted:** each tick or replay applies the same EDA checks to the selected night's data, sends only the flagged records to Muse in one batched call for all points, applies the corrections, and then runs the model. The generated columns and variable combinations for that night's rows come from the same call. Cost is a fraction of a cent per processed night. The model in use must be the one trained on corrected data.
- **Time box:** Monday night, 2.5 hours. If there is no result by 10:30 PM, report what exists as partial and ship A.

### 5.9 Serving and app

See `CLAUDE.md`, section 3 (app and system flow), which is the authoritative description of the serving pipeline, notifications, API contract and screens.

## 6. Meta tooling

### 6.1 Roles
| Use | Model or tool | Where |
|---|---|---|
| Data anomaly analysis, corrections, daily summary and likelihood (experiment) | Muse Spark 1.3 (Meta Model API) | Offline, cached |
| Alert explanation | Muse Spark 1.3 | Runtime, small volume |
| Optional bounded modules | Muse Code, `[muse-code]` commits | Development |

### 6.2 Muse Code setup
- Install (macOS or Linux): `curl -fsSL https://dev.meta.ai/install.sh | bash`. Windows PowerShell: `irm https://dev.meta.ai/install.ps1 | iex`. Check `muse --version`.
- First run in the repo: `muse` opens the browser to sign in. Usage bills to the monthly plan or, on pay-as-you-go, to the Meta Model API (it consumes hackathon credits).
- API key: create in the Model API dashboard. Muse Code reads `META_API_KEY` first, then a key stored with `muse auth set`, then the browser session. `muse exec "<task>"` runs non-interactive tasks.
- Do not export `META_API_KEY` in the global shell. Keep it in the app's `.env`.
- Use Standard mode. Make sure Contributor mode (training on prompts and code) is off.

### 6.3 Meta Model API from Python
OpenAI-compatible (verify against dev.meta.ai/docs):

```python
import os
from openai import OpenAI

client = OpenAI(base_url=os.environ.get("META_API_BASE_URL", "https://api.meta.ai/v1"),
                api_key=os.environ["META_API_KEY"])
r = client.chat.completions.create(
    model=os.environ.get("MUSE_MODEL", "muse-spark-1.3"),
    messages=[{"role": "user", "content": "ping"}],
    temperature=0,
    max_tokens=50,
)
print(r.choices[0].message.content, r.usage)
```

Test strict JSON output early. Log `usage` for every call.

### 6.4 Evidence of Meta tooling
How organizers verify usage is not documented. Ask in Discord. Meanwhile: README table "Meta tooling used" (where, why, call counts); `docs/muse_usage.md` generated from logs; `logs/sample_muse_calls.jsonl` (sanitized sample); the ablation results table; screenshot of the usage dashboard with keys hidden; explanations visible in the app and the video; Muse Code event log and `[muse-code]` commits if used.

### 6.5 Budget guardrails (150 USD)
- Prices per the guide reviewed (verify): Muse Spark 1.25 USD per million input tokens, 4.25 USD per million output.
- Muse experiment cap 25 USD. Alert explanations small. Soft cap for everything 60 USD with checks at 20 and 40.
- `MUSE_MOCK=1` serves recorded fixtures for UI and API work.
- Cap `max_tokens`, batch days per call, short reused prompts, cache every call, no retry loops.
- Log tokens to `logs/muse_usage.jsonl` (gitignored) and check it before and after each run.

## 7. Development environment

- Python 3.11+, Node 20+. VS Code extensions: Python, Pylance, Ruff, ESLint, Prettier, Claude Code, Expo Tools.
- `requirements.txt` (pin versions): `pandas`, `numpy`, `scikit-learn`, `xgboost`, `lightgbm`, `scipy`, `statsmodels`, `matplotlib`, `pyyaml`, `httpx`, `python-dotenv`, `openai`, `fastapi`, `uvicorn[standard]`, `pydantic`, `sqlalchemy`, `pytest`, `ruff`.

`.env.example`:
```
META_API_KEY=
META_API_BASE_URL=https://api.meta.ai/v1
MUSE_MODEL=muse-spark-1.3
MUSE_MOCK=0
MUSE_MAX_TOKENS=800
EMAIL_PROVIDER=smtp
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=
EMAIL_SMTP_PASSWORD=
EMAIL_FROM=
EXPO_PUSH_URL=https://exp.host/--/api/v2/push/send
CDS_API_KEY=
CDS_API_URL=https://cds.climate.copernicus.eu/api
DATABASE_URL=sqlite:///./frostwatch.db
DEMO_REPLAY=0
```

`.gitignore` must include: `.env`, `.venv/`, `node_modules/`, `__pycache__/`, `data/`, `*.db`, `.muse/`, `.expo/`, `.claude/settings.local.json`, `logs/muse_cache/`, raw `logs/` files (keep only sanitized samples).

Repo layout:
```
frostwatch-altiplano/
  README.md  CLAUDE.md  .env.example  .gitignore  requirements.txt
  configs/       points.yaml, split.yaml, experiments/
  pipelines/     01_download.py  02_features.py  03_split.py
                 04_train_eval.py  05_muse_correct.py  06_compare.py  run_experiment.py
  prompts/       versioned Muse prompts
  experiments/   <run_id>/ config.yaml metrics.json predictions.csv
  src/serve/     API, tick and replay, notify, explain
  mobile/        Expo app
  docs/          decisions.md  metrics.md  status.md  muse_usage.md  architecture.md
  logs/          sample_muse_calls.jsonl
  tests/
  data/          gitignored
```

Scan the repo history for secrets before the first public push and before submitting (for example gitleaks).

## 8. Plan: Nov 2 to Nov 4 (Bolivia time)

Assumption: little or nothing is built yet. Skip whatever already exists.

| Block | When | Goal | Checkpoint |
|---|---|---|---|
| 0 | Now, first 45 min (manual) | Meta API key and one test call with strict JSON output. Gmail account for the project with an app password. Expo Go on the iPhone. Public repo with `.gitignore` and `.env` | Test call works, repo pushed |
| 1 | Now, next 3 to 4 h (three parallel sessions) | A: pipelines 01 to 03 (download as many years as possible for about 10 points, features, split), Round 1 and Round 2 on validation, metrics doc. B: FastAPI + SQLite, serving skeleton, SMTP email, Expo push fake alert. C: Expo scaffold, AOI presets, push token registration, risk screen, alert feed | Round 1 table on validation exists. A fake alert reaches the iPhone and the inbox |
| 2 | Now, last 30 min | Handoff: commit, push, `docs/status.md`, then sleep. Fix a hard stop for this session (5 to 6 hours total) | `docs/status.md` pushed |
| - | Mon Nov 2, daytime | Builder unavailable | |
| 3 | Mon evening (about 2.5 h) | Muse correction pipeline (stages A, B, C) on the capped sample, ablation A vs B, decision by the pre-declared rule | Result table, or a partial report by 10:30 PM |
| 4 | Mon evening (about 2 h) | Chosen model into serving. Muse explanations. Real alert end to end. Replay of an out-of-sample test night. README with results and limits, Meta tooling table, secret scan, repo public | Replay runs from one command. README done |
| 5 | Until midnight | Last details. **Code freeze at midnight** | Frozen, pushed |
| 6 | Tue Nov 3 | Script, rehearse, record clips (phone screen, push, email, explanation, results tables). First edit | Raw clips and video v1 |
| 7 | Wed Nov 4, morning | Final 3-minute cut in English, upload, test the link in a private window. Submit by 2:00 PM. Post on X and share the vote link | **Submitted** |

Cut order if behind (cut from the top): Round 2 extras, random forest and LightGBM, custom pin, English dictionary, Muse explanations (use templates), Muse correction experiment (report as future work and ship raw logistic regression).

Never cut: chronological split with baselines and honest metrics, final logistic regression, push and email for a replayed test night, README with results and the Meta tooling table, the 3-minute video.

## 9. Demo mode, video and submission

**Replay mode (`DEMO_REPLAY=1`):** pick a night from the **test period** (never seen in training or selection) where frost occurred. Run it through the serving pipeline with a simulated clock: real probability from the final model, real Muse explanation, real push to the iPhone and real email. Label it clearly as a replay. Also show one honest miss or false alarm in the README.

Video storyboard (3:00, English):
- 0:00 to 0:20: the problem and who it affects.
- 0:20 to 1:30: phone demo. Choose an area (El Alto), start the replay, push and email arrive, open the alert, read the explanation.
- 1:30 to 2:30: the pipeline and the experiment: data, split, baselines, model comparison, and the Muse correction ablation with its result (positive or negative).
- 2:30 to 2:50: honest limits (reanalysis labels, 9 km grid, no station validation).
- 2:50 to 3:00: impact and close.

Submission checklist: public repo with clean history and no secrets; README (problem, beneficiaries, architecture, how to run, results tables, limits, "Built during the hackathon", "Meta tooling used", data licenses and attributions, links); 3-minute video linked; Indie track, one submission, bonuses flagged if applicable, X link submitted.

## 10. Copy blocks (English)

**One-liner:** FrostWatch Altiplano is a mobile early-warning app that sends email and in-app alerts, generated when a night of reanalysis data is processed, when radiation frost is likely in the areas you choose across the Bolivian and Peruvian Altiplano, built on a reproducible ML pipeline with Meta Muse Spark for data quality analysis and plain-language explanations.

**Short description:** Frost damages crops, livestock, water pipes and roads across the Altiplano, and most people hear about it too late. We built a reproducible pipeline that downloads decades of reanalysis data, trains and compares frost classifiers under a chronological 60/20/20 split, and tests whether Muse Spark can improve the data through cached, leak-controlled anomaly analysis. The cheapest model that performs best ships in a simple iPhone app where residents and producers choose areas of interest and receive email and in-app alerts for each processed night, each with a Muse Spark explanation checked against the model output.

## 11. Positioning

- **Peru (SENAMHI):** frost and friaje alerts, a monthly agroclimatic risk bulletin and the Atlas de Heladas (2010, with FAO). CENEPRED publishes low-temperature risk scenarios. What was found is regional or seasonal, not a per-location alert on a phone. Bolivian SENAMHI frost products were not reviewed in detail.
- **Kenya (SERVIR/RCMRD):** frost potential tool for tea regions with up to 3 days of warning. A published model there reported 81% accuracy and AUC 0.88 (different task and region, context only).
- **Our difference:** user-chosen areas, per-area alerts on a phone, a rigorous comparison of models and of an LLM-based data correction step with honest results. Do not claim "lower cost" as a differentiator.

## 12. Risks and open questions

- Scope is large for the time left. Respect the time boxes and the cut order.
- Labels from reanalysis (circular, smoother than stations). State it clearly.
- Muse correction may show no gain. That is an acceptable, reportable result.
- Without confidence intervals, small metric gains may be noise. State it in the README.
- LLM calls are not strictly deterministic: rely on the cache and report call counts.
- CDS queue times, request size limits and licence terms for a prize contest. Verify early.
- Email deliverability from a Gmail account. Test early.
- Expo Go limits: iPhone only for push.
- Credits: only Meta API credits. Keep the cap.
- Questions for Discord: what evidence of Meta tooling the submission requires, how bonuses are flagged, whether AI-assisted coding with non-Meta tools and third-party data APIs are fine, and the finals format on Nov 9.

## 13. Sources

- Event page: https://cerebralvalley.ai/e/meta-ai-developer-hackathon
- Submission page: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit
- Prize and dates guide (third party): https://reconscribe.com/meta-global-ai-developer-hackathon-2026/
- Meta Model API docs: https://dev.meta.ai/docs/pricing-rate-limits
- Expo notifications docs: https://docs.expo.dev/versions/v57.0.0/sdk/notifications.md
- Atlas de Heladas del Peru (SENAMHI and FAO): https://web2.senamhi.gob.pe/load/file/01404SENA-1.pdf
- CENEPRED low-temperature risk scenario: https://sigrid.cenepred.gob.pe/sigridv3/documento/3590/descargar
- Frost risk mapping over the Bolivian Altiplano (IRD, 1999): https://horizon.documentation.ird.fr/exl-doc/pleins_textes/divers21-03/010025917.pdf
- SERVIR frost monitoring in Kenya: https://servirglobal.net/resources/frost-monitoring-kenya
- Kotikot et al. 2020, frost zones in Kenya: https://modis.gsfc.nasa.gov/sci_team/pubs/abstract_new.php?id=39760