# Status

Last update: 2026-11-02, 04:35 Bolivia time.

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
