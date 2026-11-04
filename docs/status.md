# Status

Last update: 2026-11-04 (Muse experiment section added).

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
