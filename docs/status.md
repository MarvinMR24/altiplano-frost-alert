# Status

Last update: 2026-11-04 (final test evaluation and serving artifacts).

## Done
- `pipelines/01_download.py`: CDS downloader for `reanalysis-era5-land-timeseries`. One process (lock file `data/raw/cds/.lock`), one request at a time, 10 s between requests, no automatic retries, resume from `data/raw/cds/manifest.json`. Each file is opened with xarray and checked (variables, units, hourly step, gaps, NaN, returned cells). Every response must contain exactly one cell equal to the expected one, otherwise the script stops.
- `configs/points.yaml` (8 points, `area_mode: node_se`, expected cell per point) and `configs/cds_datasets.yaml` (dataset, variables, test requests, date ranges).
- Test requests for El Alto, July 2025 (all complete in the manifest):
  - `corner` box [-16.4, -68.2, -16.5, -68.1]: one cell (-16.5, -68.1), not the target.
  - `center` box [-16.4, -68.3, -16.6, -68.1]: four cells.
  - `node_se` box [-16.4, -68.3, -16.5, -68.2]: one cell (-16.5, -68.2), assertion PASS, 744 hourly timestamps, 0 NaN, 92 hours with t2m <= 0 C, identical to the same cell in the `center` file.
- Box semantics and cell findings recorded in `docs/decisions.md` and the README data notes.

- Phase 1 full run (`--run --ranges main`), 1985-01-01/2025-12-31, all 8 points complete. Every file passed the one-cell and time assertions (359,400 hourly timestamps, first 1985-01-01 00:00 UTC, last 2025-12-31 23:00 UTC, no gaps) and has 0 NaN in all 10 variables. One request per point, each under about 1 minute.

| point | cell | MB | timestamps | NaN | status | hours t2m <= 0 C |
|---|---|---|---|---|---|---|
| el_alto | (-16.5, -68.2) | 31.8 | 359400 | 0 | complete | 13009 |
| oruro | (-18.0, -67.1) | 31.8 | 359400 | 0 | complete | 16126 |
| patacamaya | (-17.2, -67.9) | 31.8 | 359400 | 0 | complete | 30746 |
| calamarca | (-17.0, -68.1) | 31.8 | 359400 | 0 | complete | 31095 |
| caracollo | (-17.6, -67.2) | 31.8 | 359400 | 0 | complete | 17419 |
| corocoro | (-17.2, -69.1) | 31.8 | 359400 | 0 | complete | 48246 |
| charana | (-17.6, -69.4) | 31.8 | 359400 | 0 | complete | 76692 |
| huanuni | (-18.3, -66.8) | 31.8 | 359400 | 0 | complete | 32637 |

All files have the same size because they have the same array shape; the 8 sha256 values are distinct.

- 2026 year to date (`--run --ranges 2026_ytd`), 2026-01-01/2026-10-26, all 8 points complete, `use: out_of_sample_check` (never training, validation or test; usable for the replay and the manual tick). Every file passed the one-cell and time assertions (7,176 hourly timestamps, 2026-01-01 00:00 to 2026-10-26 23:00 UTC, no gaps) and has 0 NaN.

| point | cell | MB | timestamps | NaN | status | hours t2m <= 0 C |
|---|---|---|---|---|---|---|
| el_alto | (-16.5, -68.2) | 0.78 | 7176 | 0 | complete | 248 |
| oruro | (-18.0, -67.1) | 0.78 | 7176 | 0 | complete | 303 |
| patacamaya | (-17.2, -67.9) | 0.78 | 7176 | 0 | complete | 609 |
| calamarca | (-17.0, -68.1) | 0.78 | 7176 | 0 | complete | 640 |
| caracollo | (-17.6, -67.2) | 0.78 | 7176 | 0 | complete | 443 |
| corocoro | (-17.2, -69.1) | 0.78 | 7176 | 0 | complete | 950 |
| charana | (-17.6, -69.4) | 0.78 | 7176 | 0 | complete | 1651 |
| huanuni | (-18.3, -66.8) | 0.78 | 7176 | 0 | complete | 684 |

- AgERA5 daily series (`agera5_ts`, `sis-agrometeorological-indicators-timeseries`), 1984-12-31/2026-10-25, one `location` request per point with the real city coordinates. All 8 complete: 15,274 daily values each, daily step, no gaps, 0 NaN in the 3 variables, returned point within 0.06 degrees of the request. Rows dated 2026 never enter training, validation or test. Variable roles and the time convention are in `docs/decisions.md`.

| point | requested | returned | MB | days | NaN | status |
|---|---|---|---|---|---|---|
| el_alto | (-16.51, -68.19) | (-16.50, -68.20) | 0.26 | 15274 | 0 | complete |
| oruro | (-17.97, -67.11) | (-18.00, -67.10) | 0.26 | 15274 | 0 | complete |
| patacamaya | (-17.24, -67.92) | (-17.20, -67.90) | 0.26 | 15274 | 0 | complete |
| calamarca | (-17.00, -68.13) | (-17.00, -68.10) | 0.26 | 15274 | 0 | complete |
| caracollo | (-17.64, -67.24) | (-17.60, -67.20) | 0.26 | 15274 | 0 | complete |
| corocoro | (-17.19, -69.07) | (-17.20, -69.10) | 0.26 | 15274 | 0 | complete |
| charana | (-17.59, -69.45) | (-17.60, -69.40) | 0.26 | 15274 | 0 | complete |
| huanuni | (-18.28, -66.84) | (-18.30, -66.80) | 0.26 | 15274 | 0 | complete |

In all 8 points the returned AgERA5 point has the same coordinates as the ERA5-Land cell used for that point.

## Not downloaded yet
- Nothing pending from CDS.

## Next steps
1. Features and label (`02_features.py`): AgERA5 cloud cover with a 1 day lag only; AgERA5 night minimum only for the EDA label check, aligned to date D+1 for the night starting on D, EDA (`02b_eda.py`), split (`03_split.py`).
2. El Alto frost hours per year trend down (often above 300 before 2010, mostly below 300 after). The chronological test years will have fewer frost nights than train. Document this in the README with the split results.

## Known issues
- The CDS response is a zip with one NetCDF per variable group, saved under a `.nc` name. The script extracts it to `<name>_unzipped/` and keeps the original file.
- The old `corner` and `center` tests are kept in the config for reference only. They fail the one-cell assertion if re-run.
- A 41-year request per point was accepted by CDS. If a future request is rejected, the script stops and reports; the range is not split automatically.

## How to run
```
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
# .env must contain CDS_API_KEY (token only); optional CDS_API_URL
.venv/bin/python pipelines/01_download.py --test node_se
.venv/bin/python pipelines/01_download.py --run --ranges main
.venv/bin/python pipelines/01_download.py --run --ranges 2026_ytd
.venv/bin/python pipelines/01_download.py --dataset agera5_ts --test agera5
.venv/bin/python pipelines/01_download.py --dataset agera5_ts --run
```
Outputs: `data/raw/cds/era5land_ts/`, `data/raw/cds/agera5_ts/`, `data/raw/cds/manifest.json`, `logs/cds_download.log` (all gitignored).

## Modules, Docker and mobile app (2026-11-02, 03:45 Bolivia time)

Phase 1 of the module split is done; nothing was moved. ml code still lives at the repo root
and moves into `ml/` in Phase 2, only after the CDS download finishes and `data/raw/cds/.lock`
is gone.

Done
- `docs/architecture.md` (target layout, module contracts), `docs/api_contract.md` (shared
  with the backend session), `docs/artifacts_contract.md` (PROPOSAL for ml and backend).
- `backend/` skeleton: `GET /health`, `python -m app.cli replay|tick` stub (internal
  operations are a CLI, not HTTP, because ngrok forwards every route), requirements, README,
  one test. Image builds; the test passes inside the image; runs as non-root user `app`.
- Dockerfiles with their own ignore files: `backend/Dockerfile`, `mobile/Dockerfile`,
  `ml/Dockerfile` (+ `ml/Dockerfile.dockerignore`, because its build context is the repo root).
  `ml/requirements.txt` is a copy of the root `requirements.txt`.
- `docker-compose.yml`: backend + ngrok by default, `mobile` and `ml` behind profiles.
  `docker compose config --quiet` passes (also with both profiles). `docker compose up` was
  not run (needs `NGROK_AUTHTOKEN`).
- `mobile/`: Expo SDK 58 app (Expo Router, TypeScript) in mock mode with every screen: email
  code login, onboarding, Map, Zones with polygon drawing, History with alert detail and
  model card, Profile. `npx tsc --noEmit` and `npx expo-doctor` (20/20) pass; iOS and Android
  bundles export. Not yet tested on a physical iPhone.

Decisions and deviations
- ngrok uses `--url` (the agent docs mark `--domain` as deprecated).
- `mobile/Dockerfile` uses `node:22-slim`, not `node:20-slim`: Expo SDK 58, React Native 0.88
  and Metro require Node ^22.13.
- `mobile/.npmrc` sets `legacy-peer-deps=true`: the optional web peer `react-dom@19.3.1`
  conflicts with `react@19.3.0` pinned by SDK 58. The app does not target web.
- The mobile container works as far as it can be tested without a phone: Metro starts with
  `--lan` and serves the manifest and the iOS bundle at `exp://<HOST_LAN_IP>:8081`. Expo Go
  on the phone was not tried against the container. Host `npx expo start` stays the supported
  way.
- The API contract adds `purpose: "notification_email"` to the email code endpoints so the
  app can change the notification email by re-running the code flow.
- Push in Expo Go needs an EAS project id (`npx eas-cli init` or
  `EXPO_PUBLIC_EAS_PROJECT_ID`). On Android Expo Go push is skipped (not supported since SDK 53).

Next
1. Backend session: implement `docs/api_contract.md` with the `mock` DataProvider first, then
   `artifacts`.
2. ml and backend sessions: review `docs/artifacts_contract.md`.
3. Builder: scan the QR with the iPhone (mock mode), then point the app at the backend.
4. Phase 2 (after "CDS finished"): move the ml code into `ml/`.

## Model (2026-11-03, validation only; test locked)
- ML package `src/frostwatch_ml` (`pip install -e .`); thin CLIs in `pipelines/`; `make test` (40 tests, 14 leakage and integrity checks) and `make lint` pass.
- Refactor regression: features, anomalies and crosschecks parquet files are identical in content to Part 1 (`DataFrame.equals`, same dtypes). File SHA-256 differs only through the parquet writer version (pyarrow 26.0.0 then, 25.0.1 now because mlflow 3.17.2 requires pyarrow < 26).
- Round 1 (validation 2010-2017, pooled PR-AUC / F2): climatology 0.8135 / 0.8470, persistence 0.6573 / 0.7594, lr_none 0.8917 / 0.8759, lightgbm 0.9070 / 0.8804.
- Round 2 finalists: LR_best `lr-20261103-fbbf62c6` (C 1.0, L1, no class weight, sigmoid calibration with negligible Brier change) PR-AUC 0.8918, F2 0.8757, macro PR-AUC 0.8374; TREE_best `lightgbm-20261103-fbbf62c6` (comparison only) PR-AUC 0.9105, F2 0.8819, macro PR-AUC 0.8624.
- Artifacts: `reports/<model_version>/` (git), `models/<model_version>/` (DVC). MLflow runs on DagsHub, experiment "frostwatch-altiplano" (links in `reports/mlflow_links.json`). `dvc repro` reproduces the whole chain with identical metrics; `dvc status -c` in sync.
- Next: the builder decides the risk-level mapping (cuts 0.3 / 0.5 / 0.7 give 4 bands vs none / watch / alert in CLAUDE.md 3.1), applies HANDOFF/spec_patch.md, then runs `pipelines/06_final_eval.py --i-confirm-final` once.

## Backend (2026-11-03)
Done
- FastAPI + SQLite backend in `backend/app` implementing every endpoint of `docs/api_contract.md`, plus `GET /health`, `DELETE /me` and `POST /alerts/{id}/read`.
- Email code login (console or SMTP STARTTLS), JWT sessions for 30 days, rate limits, strict validation.
- Coverage (30 km circles, shapely) and AOI validation; AOI risk from the containing cell (highest probability on overlap).
- DataProvider `mock` (everything flagged MOCK) and `artifacts` (read-only, schema validated, clear 503 on errors).
- Alerting: dedupe (one per AOI per night, re-alert on a level rise, at most 2 per 24 h of the night clock), idempotent; deliveries recorded; Expo push batches of 100 with ticket ids.
- Explanations: catalog (producer, resident; ES, EN; no health advice), template, muse-spark only with `MUSE_MOCK=0`, cached by facts hash, number verifier with template fallback.
- CLI: `replay`, `tick`, `seed-demo`. 72 pytest tests and ruff pass (`backend/`).
Pending
- Real artifacts from the ML session (`artifacts/model_card.json`, `artifacts/predictions/*.parquet`) in the contract shape; see `docs/backend_notes.md`.
- A real SMTP send (Gmail app password), a real Expo push to the iPhone, and a real Muse call (`MUSE_MOCK=0`): none was run in this session.
- `docker build` not run (Docker daemon off); a clean venv install from `backend/requirements.txt` was verified instead.
Known issues
- Level names differ between CLAUDE.md, the contract and `lr_export.json`; the backend uses the contract names.
- `.gitignore` (`.env.*`) ignores `backend/.env.backend.example`; needs `!backend/.env.backend.example`.
- In-memory rate limiter (one process). Expo receipts are not polled.
How to run (from `backend/`)
```
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --port 8000
.venv/bin/pytest && .venv/bin/ruff check .
.venv/bin/python -m app.cli seed-demo --email you@example.com
.venv/bin/python -m app.cli replay --night YYYY-MM-DD --email you@example.com [--dry-run]
.venv/bin/python -m app.cli tick [--night YYYY-MM-DD]
```

## Mobile out of Docker, local web testing (2026-11-03)

- Builder decision: the mobile app is not containerized. It runs on the host. Test plan: local
  web first (`cd mobile && npx expo start --web`, backend on `http://localhost:8000`), then
  Expo Go on the iPhone after the backend is deployed to AWS.
- Removed: `mobile` service from `docker-compose.yml`, `mobile/Dockerfile`,
  `mobile/.dockerignore`, `HOST_LAN_IP`. `docker compose up` now starts the backend only;
  ngrok moved behind the optional `tunnel` profile.
- Web support for testing: added `react-dom@19.3.0`, `react-native-web@~0.21.4`,
  `@expo/metro-runtime@~58.0.16` (SDK 58 versions). `src/ui/maps.web.tsx` is a schematic map
  stand-in (react-native-maps has no web build); screens import `@/ui/maps`.
  `src/auth/session.web.ts` stores the token in localStorage. New i18n key `map.webPreview`.
- Backend: CORS for the Expo web origin (`CORS_ORIGINS`, default
  `http://localhost:8081,http://127.0.0.1:8081`).
- Specs updated: 01 (acceptance 11 to 13), 03 (test environments, acceptance 9 to 11),
  `docs/architecture.md`, `mobile/README.md`, MUSE.md and CLAUDE.md rule 25.
- Checks: `npx tsc --noEmit` passes; `npx expo export --platform web` bundles; mock flow
  checked in a headless browser (login, map with 8 cells, polygon drawing); backend 72 tests
  pass and ruff is clean; CORS preflight allows localhost:8081 and rejects other origins.
- Not run: `docker build` (Docker off), `npx expo-doctor` (Expo API blocked from the VM).

## Repo cleanup (2026-11-04)

- Removed `HANDOFF/`: the Part 1 and Part 2 delivery from the isolated ML environment. Every
  file in it was already copied into the repo (no differences), the doc sections were
  appended, and the spec patch was applied. `HANDOFF/dvc_tracked/` duplicated `models/` and
  `data/processed/`, which DVC restores with `dvc pull`.
- Removed `ml/` (Dockerfile and a copy of `requirements.txt`) and the `ml` service in
  `docker-compose.yml`: the ML pipeline runs on the host with the root `.venv`.
- Kept `artifacts/`: it is the folder the backend reads (`ARTIFACTS_DIR`, mounted read-only
  in Docker, `docs/artifacts_contract.md`). ML writes its outputs to `reports/<model_version>/`
  and `models/`; the final export must place the contract files in `artifacts/`.
- `Claude outputs/` (Cowork prompts) is gitignored.

## Muse experiment (2026-11-04)

Condition A (LR_best, `lr-20261103-fbbf62c6`) vs condition B (Muse-reviewed corrections B1 plus
Muse-proposed feature formulas B2), validation only. The test split stays locked.

Built:
- `configs/muse.yaml`, `prompts/muse_anomaly_review_v1.txt`, `prompts/muse_feature_proposals_v1.txt`.
- `src/frostwatch_ml/muse/`: `client.py` (Meta Model API, cache by request hash in `logs/muse_cache/`,
  usage in `logs/muse_usage.jsonl`, `MUSE_MOCK=1` default with deterministic fakes, budget check
  before each real call, one attempt, no retries), `masking.py`, `schema.py`, `formula.py`
  (whitelist parser, no eval), `review.py` (B1), `proposals.py` (B2), `costs.py`, `experiment.py`.
- `pipelines/05_muse_correct.py` (`--config --seed --dry-run --no-sync --smoke N`), `make muse`,
  DVC stage `muse_correct` (outs `data/processed/muse`, `data/processed/predictions/muse`,
  `reports/muse_experiment.md`).
- `pipelines/06_final_eval.py` can score B in its single `--i-confirm-final` run if B passed on
  validation; otherwise it records B as "not adopted on validation". Not run.
- `tests/test_15_muse.py`: masking, parser, zero network with `MUSE_MOCK=1`, cache hit, budget
  stop, no retry, physical checks, feature-hour map against the feature code, train-only
  statistics, no locked rows. `make test` (74 passed) and `make lint` pass.

Facts from the run plan: 43160 EDA flags; 38321 precipitation and 802 shortwave tiny negatives are
clipped in code (never sent); 277 hourly jumps (188 t2m, 89 d2m) in train and validation years can
change a feature; all 277 are sampled, 14 review calls plus 1 proposal call. Planning estimate:
about 28.5k input tokens, worst case 0.29 USD (output bounded by max_tokens).

A recheck: recomputing LR_best with the same code reproduces the stored validation metrics exactly.

Real run (2026-11-04, `muse-ab-fbbf62c6`, mirrored to MLflow on DagsHub):
- A first real attempt with max_tokens 4000 failed: Muse Spark counts reasoning tokens toward
  max_tokens, so all 15 answers were cut (invalid JSON, logged, cost counted, not reused). The
  limit is now 16000; the hard cap for this experiment is 10 USD.
- B1: Muse kept all 277 flagged hours (0 corrections), so Muse changed 0 feature values. Clipping
  changed 29009 values of precip_24h_mm by at most about 0.0001 mm.
- B2: 6 formulas proposed, all 6 accepted by the parser and checks (B has 30 features).
- Validation, pooled: A PR-AUC 0.8918, F2 0.8757; B PR-AUC 0.8924, F2 0.8769. Gain +0.0006 and
  +0.0012, below the pre-declared 0.02. Verdict: ship A. `06_final_eval.py` will record B as
  "not adopted on validation".
- Cost: 31 real calls in the usage log (smoke, failed attempt, real run), 100925 input and
  138262 output tokens, about 0.71 USD estimated (prices marked verify).

Pending for the builder: one cache re-run (must show 0 API calls), then `dvc commit muse_correct`.

## Final test evaluation and serving artifacts (2026-11-04)

- `pipelines/06_final_eval.py --i-confirm-final --no-sync` ran once (MLflow mirror off in the agent
  session). LR_best on test 2018-2025: PR-AUC 0.8930, F2 0.8797, Brier 0.0858, accuracy 0.8233
  (majority 0.6802); macro PR-AUC 0.8361, F2 0.8624. Validation was 0.8918 and 0.8757. Base rates:
  train 0.381, validation 0.335, test 0.320. Muse B recorded as "not adopted on validation".
  Outputs: `reports/final_test_metrics.json` and `.md`; both model cards updated.
- The evaluation logic lives in `frostwatch_ml.evaluation.final` and was rehearsed on validation
  first (`tests/test_16_final_eval.py`: frozen models reproduce the stored validation metrics).
- `pipelines/07_export_serving.py` (`make serving`) writes `artifacts/model_card.json`,
  `artifacts/model_coefficients.json` and 3,221 files in `artifacts/predictions/` (2,922 test
  nights for the replay, 299 nights of 2026 marked `period = out_of_sample_latest`; 2026-10-26 has
  null observed values). Rows come from `leakage.serving_rows`, which works only after the final
  report exists. Probabilities equal the model bundle (max abs diff 0).
- Contract notes: levels use the contract names; `top_drivers` has all 24 signed contributions
  (coefficient times standardized value, logit units); `conditions_1800` uses the keys the app
  labels, without `tcc_pct` (the model only has the previous day's cloud cover, not an 18:00
  value); `elevation_m` is the standard-atmosphere proxy from mean surface pressure; extra column
  `period` (the backend ignores it and logs it once per file).
- Backend check (no backend edits): 72 backend tests pass; with DATA_PROVIDER=artifacts the model
  card loads, `list_nights` takes 7 ms for 3,221 files and one night loads in a few ms. No cap needed.
- Replay: `reports/replay_candidates.md`; recommended night 2024-08-17.
- Pending for the builder: mirror the final run to MLflow if wanted, and the end to end alert.

## Mobile polish (2026-11-04, uncommitted)

Done in `mobile/` plus `mobile/README.md`, spec 03 and this file. No backend or contract edits.
- Map: Apple Maps `mutedStandard` on iPhone (no POIs, no rotation or pitch); Leaflet with
  a real CARTO Voyager base map on web. Initial region fits all 8 cells plus 30 km circles.
  Level markers pair color, text and icon; tapping a cell animates the camera and opens the
  sheet; closing animates back. Native markers use `tracksViewChanges={false}`; heavy map
  children are memoized and tabs are lazy.
- Zone drawing: tap to add (3 to 12), drag vertices (long press and drag on iPhone),
  midpoint handles to insert, tap to select plus Delete vertex, Undo and Clear. Live
  coverage validation with a red outline and disabled Finish. `zones/[id]` shows a small
  read-only map; only name, threshold and channels are editable (PATCH has no polygon).
- Visual identity: navy and beige tokens in `src/ui/theme.ts`, no hex literals in screens;
  level badges pair color, text and icon; navy tab bar and headers; cards with soft radius
  and shadow; 44 pt touch targets. Original SVG logo (`assets/logo.svg`, `logo-mark.svg`),
  `LogoMark` via `react-native-svg` on login, onboarding and Profile; PNGs built with
  `node scripts/build-icons.mjs`; `app.json` splash navy, name FrostWatch.
- Alert detail: level and probability first, then headline, why, actions, caveats,
  conditions, drivers, outcome, and a collapsed How this was computed. Replay tag from
  optional `mode`; explanation label from optional `explanation_source` (mock provides one
  muse and one template alert). The backend detail sends `mode` but the list does not, and
  `explanation_source` is not exposed yet, so real alerts fall back to the template label.
- Checks: `npx tsc --noEmit` passes; `npx expo export --platform web` bundles.
- i18n: new draw hints (tap, drag, long press on iPhone) and history keys exist in es and en.
- Not verified: no headless browser here, so the web flow (login, map with base map and
  8 cells, tap cell, draw, drag, insert and delete vertex, save, History, alert detail)
  was not run and no screenshots were taken; the production bundle speed question is open.
- iPhone LAN steps are in `mobile/README.md` (docker compose publishes 8000 on all
  interfaces; `ipconfig getifaddr en0`; `mobile/.env.local`; QR scan; Safari health check;
  `CORS_ORIGINS` with the phone port for web; EAS project id options).
- Pending for the builder: run the iPhone LAN test, try the web production bundle, and
  decide whether the backend should expose `explanation_source` and list `mode`.

## App v2 (2026-11-04, uncommitted)

Password auth, custom icons, detailed logo, Aymara and Quechua, searchable pickers,
threshold explanation and calendar night picker.

Backend (88 tests pass, ruff clean; was 72):
- `users` gains `password_hash` (scrypt, stdlib only), `phone` and `email_verified`;
  idempotent `ALTER TABLE` migration at startup marks pre-existing rows verified.
- New endpoints: `POST /auth/register` (202, no email leak), verify with purpose
  `register`, `POST /auth/login` (generic 401, 403 `email_not_verified` with a new code,
  5 fails per 15 min then 429), `POST /auth/password/forgot` (always 202),
  `POST /auth/password/reset` (session), `POST /auth/password/change` (Bearer). Code login
  unchanged and now marks the email verified. Secrets never logged (tested).
- Language is `es | en | ay | qu`; emails, push and explanations fall back to Spanish
  for ay/qu (tested). `DELETE /me` still removes everything.
- New suite `backend/tests/test_password_auth.py` (16 tests).

Mobile (`npx tsc --noEmit` passes, `npx expo export --platform web` bundles,
`node scripts/check-i18n.mjs` passes with 264 keys, `node scripts/unit-tests.mjs`
passes with 41 assertions):
- Custom SVG icon set (`src/ui/icons/`, 50+ names, `<Icon name="..." />`); Ionicons only
  for the Google/Apple brand glyphs. New `Field` (left icon, focus/error states),
  large buttons, six-box `CodeInput`, password meter, social buttons (visual only).
- Auth flow: welcome (logo, tagline, 4 language chips, social), 4-step sign up with
  slide transitions, sign in with password or code, forgot password, change password.
  Mock mode supports every new endpoint offline.
- Aymara (95 keys) and Quechua (99 keys) dictionaries; the rest falls back to Spanish,
  listed in `docs/i18n_review.md` for a native speaker.
- Catalogs: 42 crops in 6 categories, 14 livestock, one searchable `CatalogPicker`
  (chips, grouped results, modal on phones, inline on wide screens). Old tag ids kept.
- Threshold is now "Alert me from" with an info sheet (0-100 bar, level colors at
  30/50/70); same component in sign up, Profile and zone screens.
- Map night selector is a calendar sheet (`src/date/calendar.ts`, Monday first, year and
  month jump, only available nights enabled, latest marked); markers flash on change.
- Profile rebuilt as icon cards: language, profile type, crops, livestock, alerts,
  account (change email, change password, sign out), danger zone with confirm sheet.
- Logo redesigned (night sky, moon, three ranges, snowcaps, plain, snowflakes, red dot):
  `assets/logo.svg`, `logo-horizontal.svg`, `logo-mono.svg`, `src/ui/logo.tsx` in sync;
  PNGs regenerated. Old `assets/logo-mark.svg` is stale and can be deleted.

Docs: contract (password endpoints, new fields), spec 03 (v2), `mobile/README.md`,
`docs/i18n_review.md` (new), MUSE.md/CLAUDE.md 3.5 store list (builder decision).

Not verified: no web run or screenshots (builder tests in the app directly). Manual
checks pending: full sign up, password login, code login, forgot password, ay/qu UI,
picker searches, threshold sheet, calendar jump, push on the iPhone.

## App v2 fixes and field UX (2026-11-04, uncommitted, Claude Code)

Fixes from `reviews/muse_app_v2_review.md`:
- H1: "Go to map" no longer stays loading after onboarding (`onboarding.tsx` resets `busy`).
- H2 and M1: `POST /auth/email/request` with purpose `register` resends the sign up code
  (only for an unverified account, always 204). Sign up resend uses it; a 403 on password
  login opens the verify step with purpose `register`.
- M2: login always runs scrypt (dummy hash for unknown emails). L1: register returns 202
  when the code limit is hit. L2: "missing bearer token" strings restored. L3: log test
  checks the real phone. 4 new backend tests (92 pass, ruff clean).
- M3: logo SVGs and `logo.tsx` share the same paths (clearer snowflake, real crescent
  moon); `node scripts/check-logo.mjs` checks the sync; PNGs regenerated.
- M4: web map uses keyless OpenStreetMap tiles. M5: signed out visitors land on Welcome
  (`Stack.Protected redirectTo`). M6, L4: password rules always visible, error names the
  first failing rule. M7: new cow, horse, llama and solar tent icons. L5: mock hint fixed.
  L8: one step indicator; resident sees "Alerts". L9: `@types/leaflet` is a dev dependency.
  Color literals moved to the `colors.backdrop` token. The 6-digit code now auto submits
  with the full code.

Field UX (people in rural communities; Android and iOS through Expo Go):
- Bigger text and touch targets (buttons 52 to 58 px, body 16 px), icons next to labels.
- "Listen" button (`expo-speech`) reads the alert or the place risk aloud; Aymara and
  Quechua are read with the Spanish voice and the app says so.
- Haptics (`expo-haptics`) on taps, selections, success and errors; Android ripple.
- Risk meter: icon, level word, percent and a 4-step scale that fills up to the level.
- Map: summary card with the night's highest risk (tap opens it); high and very high
  markers pulse. Alert detail leads with numbered actions.
- Motion kit `src/ui/motion.tsx` (fade in, stagger, pop, pulse, shake, breathing logo),
  all disabled when the system "reduce motion" setting is on.

Verified: tsc, i18n parity, 41 unit assertions, logo check, backend suite; Playwright on
the web build against a local backend: Welcome first, sign up with resend, onboarding to
map, map summary and risk sheet, sign out to Welcome, unverified login to verify (10 of
10). Not verified: Android and iOS devices (builder tests).

## Satellite maps, place search, compact night pill (2026-11-04, uncommitted)

- Maps default to satellite with place names (hybrid) on the Map tab, zone drawing and zone
  detail; round layers button toggles the street map, remembered per device. Web uses Esri
  World Imagery plus labels, or OpenStreetMap. Coverage circles, zones and the drawing
  line have a light halo; markers and vertex handles have a white border and shadow.
- Search bar on the Map tab and the draw screen (`src/geo/search.ts`): coverage cells
  first, then Photon with Nominatim fallback, debounce, 1 request per second, cache,
  cancellation. Outside results are dimmed (Map tab: camera moves plus a toast; draw
  screen: not selectable). Selected place shows a temporary pin (0.05 degree view on the
  map, 0.01 on the draw screen). "My location" with `expo-location` after an explanation;
  hidden for the session if denied. Privacy line added to Profile.
- Each coverage circle shows its place name (label at the top edge of the circle) on the
  Map tab and the draw screen (`CoverageLabels` in `src/ui/mapShapes.tsx`).
- The big night card was replaced by a navy pill (short date) and a "Reanalysis" chip.
- The HTTP client now times out after 12 s, so an unreachable backend shows an error with
  Retry instead of an endless loading screen.
- Checks: tsc, i18n parity, 59 unit assertions (18 new for search), logo check, web,
  Android and iOS bundles export. Not run on devices (builder tests).

## Zone drawing modes (2026-11-04, uncommitted)

- Three big mode buttons under the map: Add (tap the map adds a point, white midpoints
  insert one between two), Move (pencil: tap a point, then tap where it goes, or drag it)
  and Delete point (trash: tap a point to remove it). Undo, Clear all and Finish stay.
- Kept from the previous pass: coverage circles and labels memoized, drag updates once per
  frame, `moveOnMarkerPress={false}` on Android, haptics. Removed: tap to zoom when zoomed
  out and tap-to-move without a mode (the builder found them confusing).

## Muse place explanations and simpler screens (2026-11-04, uncommitted)

- Backend: `GET /map/{point_id}/explain` (service `place_explain.py`, prompt
  `place_explain_v1.txt`): Muse explains the selected place and night on request in es, en,
  ay or qu, with what happened, what came next (the following processed night, if any),
  catalog actions and sources from a fixed, checked list (SENAMHI, Defensa Civil, Radio San
  Gabriel, ABI, Copernicus). Placeholders keep the place and date out of the prompt. Stored
  by facts hash; API errors and the per-user limit (30 per hour) are not stored. 7 new
  tests, 99 pass, ruff clean. No live Muse call was made from this session.
- App: the map sheet shows risk, the observed outcome in one sentence and the Muse card
  (thinking animation, listen button, numbered actions, links that open in the browser).
  Drivers, conditions, reliability and model metrics moved into a closed "Technical
  information" section, also on the alert detail.
- Pending: the alert explainer (`explain.py`) still sends the place name and night date to
  Muse, unlike spec 02; ay and qu UI labels for the new screens fall back to Spanish.
- To use it: rebuild the backend container (`docker compose up -d --build backend`).

## Muse reply fix and Aymara/Quechua listening (2026-11-04, uncommitted)

- Bug: `GET /map/{point_id}/explain` returned 500 because Muse Spark spent the whole
  `max_tokens` (default 700) on reasoning and replied with empty content. The default is now
  8000 (`MUSE_MAX_TOKENS`, also used by alert explanations, which were silently falling back
  to the template), the HTTP timeout 120 s (`MUSE_TIMEOUT_S`). Empty or cut replies fall
  back to the template, are not stored, and are logged with `finish_reason` and reasoning
  tokens. This exceeds the spec 02 target of 400 tokens, which a reasoning model cannot meet.
  The app waits up to 150 s for this call. 100 backend tests pass.
- App: "Read and listen in" chips (Spanish, English, Aymara, Quechua) on the Muse card:
  picking a language generates the text in it, shows it, then reads it aloud. Phones have
  no Aymara or Quechua voice, so those texts are read with the Spanish voice (apostrophes
  removed) and the app says so.

## One explanation, translated (2026-11-04, uncommitted)

- Place explanations are generated once per place and night in Spanish (prompt
  `place-explain-v2` key) and translated by Muse for en, ay and qu (`place_translate_v1.txt`).
  Translations keep the `{place}`/`{night}` placeholders, the item counts and only numbers
  from the facts; a failed translation is stored so it is not re-sent, and the Spanish text
  is shown. API field `translated`. 102 backend tests pass.

## New logo (2026-11-04, uncommitted)

- Logo replaced by design D from the builder (map pin with peak, snowflake and red dot on
  beige): `src/ui/logo.tsx`, `assets/logo.svg`, `logo-horizontal.svg`, `logo-mono.svg`
  (mask cut-outs), `scripts/check-logo.mjs` updated. Icons regenerated; app icon and Android
  adaptive background are beige, the Android foreground is padded to the safe zone, splash
  background is beige (`app.json`). New theme token `logoMountain`.

## Sign in with Apple and Google (2026-11-04, uncommitted)

- Backend: `app/auth/social.py`, `app/routers/social.py` (`/auth/providers`, `/auth/apple`,
  `/auth/google/start`, `/auth/google/callback`, `/auth/ticket`); RS256 verification with
  provider keys (new dependency `cryptography==50.0.2`); accounts matched by verified email.
  14 new tests (signed test tokens, no network), 116 pass, ruff clean.
- App: `expo-apple-authentication` (official button, iOS only, hidden on Android) and the
  Google flow through the system browser with a one-time ticket (`src/auth/providers.ts`).
  The Google button stays "coming soon" until the backend has the Google settings.
- `.env.example`: Google and Apple settings; `MUSE_MAX_TOKENS` raised to 8000.
- Builder: rebuild the backend image (new dependency); for Google create the OAuth client
  and a public https backend URL (see `.env.example`).

## Deploy and Android (2026-11-04, uncommitted)

- Backend deploy files: `docker-compose.prod.yml` (port 8000 not published, restart
  unless-stopped, uvicorn proxy headers so rate limits see client addresses, log rotation),
  `caddy` service under the `prod` profile in `docker-compose.yml`, `deploy/Caddyfile`
  (HTTPS, zstd/gzip, HSTS and other headers, 1 MB body limit, 150 s read timeout for Muse),
  `.env.production.example`, `deploy/scripts/` (sync_artifacts, sync_env, server_bootstrap,
  deploy, backup_db) and `docs/deploy_aws.md`.
- `docker-compose.yml` now passes APP_ENV, MUSE_MAX_TOKENS, MUSE_TIMEOUT_S,
  MUSE_MAX_CALLS_PER_RUN, EXPO_PUSH_URL, GOOGLE_*, APPLE_AUDIENCES and RATE_LIMIT_PER_MINUTE
  (they were not reaching the container), with defaults equal to the backend defaults where
  an empty value would override them (MUSE_MODEL, APPLE_AUDIENCES, EXPO_PUSH_URL).
- Production guards already in place: no start without SESSION_SECRET, no console email.
- Mobile: `app.config.ts` replaces `app.json` (package com.marvinmr24.frostwatch, version
  1.0.0, versionCode from ANDROID_VERSION_CODE, Google Maps key from
  GOOGLE_MAPS_ANDROID_API_KEY, splash through the expo-splash-screen plugin as SDK 58
  requires, expo-location permission text, EAS project id), `eas.json` (preview APK,
  production AAB), Google Maps provider on Android in `src/ui/maps.tsx`, Expo dependencies
  aligned with `expo install --fix`. Guide: `docs/android_build.md`.
- Checks: compose config (default and prod) valid, port 8000 absent in prod; backend tests
  and ruff pass; tsc, unit tests, web and Android bundles; the Maps key appears in the
  prebuild config only when the env var is set. Not verified: an actual EAS build, the EC2
  deploy and certificates (need accounts).

## Apple sign in removed (2026-11-04, uncommitted)

- Builder decision: only Google sign in. Removed `/auth/apple`, the Apple token check,
  `APPLE_AUDIENCES`, the Apple button, `expo-apple-authentication` and the `welcome.apple`
  string; `/auth/providers` returns `{google}`. The old unused Google/Apple stubs in
  `app/auth/providers.py` are gone. Google tests now also cover token checks, account
  linking and secrets not logged. 116 backend tests pass.
