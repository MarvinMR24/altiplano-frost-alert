# Backend notes

Notes from the backend session (2026-11-03). `docs/api_contract.md` and
`docs/artifacts_contract.md` were not edited; every change proposed below needs both sessions
to agree and a line in `docs/decisions.md`.

## What the backend does

- FastAPI + SQLite (SQLAlchemy, `create_all`), Python 3.12, in `backend/app`. Every endpoint of
  `docs/api_contract.md` plus `GET /health`.
- Data through a `DataProvider`: `mock` (deterministic, seeded, 5 nights in July 2026, all four
  levels every night, everything flagged `MOCK`) or `artifacts` (read-only, validated).
- Alerts only when a night is processed with the CLI: `replay`, `tick` and `seed-demo`. These
  are not HTTP routes, because the tunnel forwards every route.
- Explanations: a curated catalog, a deterministic template, and muse-spark only with
  `MUSE_MOCK=0`.

## Differences from docs/api_contract.md

All additions are new fields, so existing clients keep working.

| Topic | Contract | Backend | Proposal |
|---|---|---|---|
| `Cell`, `AlertDetail` | `top_drivers` only | adds `driver_groups: [{theme, label_es, label_en, effect, weight}]` | The app shows `driver_groups` instead of `top_drivers` (see Drivers below) |
| `AlertDetail` | | adds `data_source` and `mode` (`replay` or `tick`) | The app shows "Replay" and "MOCK" labels |
| `ModelCard.metrics.test` | `Metrics` (numbers) | every value is `null` while the test is pending; adds `test_status: "pending" \| "available"` and `data_source` | Change the type to `test: Metrics \| null` plus `test_status`. The app's `fmt` already prints `-` for missing values |
| `GET /coverage` | one feature per cell | same; `meta` also has `union_area_km2`. The union of the circles is used for validation | Keep one feature per cell (the app needs `point_id`) |
| `POST /aois` validation | 422 if any vertex or the centroid is outside the coverage | stricter: the whole polygon, edges included, must be inside the union of the circles (150 m tolerance for polygonal circles drawn by the app), plus the centroid. Also: closed ring, no holes, 3 to 12 distinct vertices, area 0.01 to 2000 km2, not self-intersecting | Write the stricter rule in the contract |
| AOI count | | at most 20 per user (409) | Add to the contract |
| Wrong or expired code | not listed | 400 `invalid or expired code` | Add 400 to the error list |
| Code requests | "rate limit per email" | 3 per hour per email, then 429; the request still returns 204 for any email, known or not | |
| `POST /devices` | idempotent | a token moves to the latest user that registers it | |
| `DELETE /me` | user, devices, AOIs, alerts, sessions | also deliveries and auth codes. Sessions end because tokens are checked against `users`. The explanation cache is kept: it holds no personal data | |
| Validation errors | `{"detail": "<message>"}` | FastAPI's list is turned into one string | |

The mobile client (`mobile/src/api`) matches the contract: same paths and bodies.

## Conflicts with MUSE.md / CLAUDE.md (the backend follows the contract and the backend brief)

- **Endpoints (CLAUDE.md 3.5).** CLAUDE.md lists `POST /users`, `GET /risk` and
  `POST /email/confirm`, and runs `uvicorn src.serve.main:app`. The backend follows the
  contract and lives in `backend/app` (`uvicorn app.main:app`).
- **Levels.** Three schemes are in use:

  | Source | Names |
  |---|---|
  | CLAUDE.md 3.1 | none, watch, alert |
  | Contract | low, moderate, high, very_high |
  | `reports/lr-20261103-fbbf62c6/lr_export.json` | none, low, medium, high (same cuts) |

  The backend uses the contract names, and `ArtifactsProvider` rejects a row whose level does
  not match its probability under the contract cuts. The ML side must write the contract names.
- **Observed outcome and the LLM.** The brief lists "historical outcome if known" as a fact
  for the LLM. Rule 15 and the artifacts contract say `observed_*` is never sent to Muse. The
  backend sends only the reliability bin of the probability (observed rate on validation and n).
  The observed frost and tmin of the night appear only in `AlertDetail.outcome`.
- **Where Muse data lives.** Three changes from MUSE.md:
  - Muse cache: rule 21 says `logs/muse_cache/`. Following the brief, the cache is the
    `explanations` table.
  - Usage log: `backend/var/logs/muse_usage.jsonl`, which is gitignored, not
    `logs/muse_usage.jsonl`.
  - Prompt: `backend/app/prompts/explain_v1.txt`, not the root `prompts/`, which is outside the
    backend paths.
- **Batching (rule 24).** Rule 24 says "one call per alert". The backend makes one call per
  (cell, night, level, profile, language), shared by every user with the same facts, so it
  makes fewer calls.
- **Tick flag (CLAUDE.md 3.2).** CLAUDE.md uses `--date`. The CLI uses `--night` and also
  accepts `--date` as an alias.

## Design choices worth checking

- **Dedupe window.** The "at most 2 per 24 hours" rule uses the night clock: 18:00 local of the
  night, which is 22:00 UTC. Wall-clock time would block replays of several past nights run
  back to back. Within one night this allows the first alert and one re-alert after a level
  rise.
- **Number verifier.**
  - Every number in the generated headline, why, actions and caveats must come from the
    facts: probability %, the reliability range %, the observed rate %, n, and 18 and 0 from
    the 18:00 cutoff.
  - Dates must match the night date exactly. Digits glued to a word (`ERA5`) are not counted
    as numbers, and the sign counts (`-5` is rejected).
  - Banned in the headline and why: real time, instant, live, satellite, health, medical.
  - On a failure the template is used. Invalid JSON gets one retry; nothing else is retried.
- **Driver themes.** The brief's regexes were extended:
  - sky_radiation gets `ssrd`, `tcc` and `lw_down`.
  - humidity gets `precip`, and temperature gets `frost`.
  - `rh`, `sp`, `sin` and `cos` are matched as whole name tokens, so `sp` does not match
    inside another word.
  - With the 24 model features, only `latitude` and `elevation_proxy_m` fall in "other", and
    they are logged.
- **Unconfirmed email.** No alert goes to an unconfirmed address. The login email is
  confirmed by the code, and changing `notification_email` needs a new code.

## Review of docs/artifacts_contract.md (for the ML session)

The backend implements the contract as written:
- **Files:** it reads `artifacts/model_card.json` and `artifacts/predictions/<YYYY-MM-DD>.parquet`
  and ignores other names, so temp files from atomic writes are safe.
- **Rows:** columns as listed (extra columns are ignored and logged), one row per point_id,
  only the 8 known cells, grid lat and lon within 0.051 degrees of `backend/app/data/cells.json`.
- **Values:** `night_date` must equal the file name. The JSON columns are strings. The
  observed columns are both set or both null. `model_version` must equal the model card's.

Problems and proposals:

1. **model_card.json shape.** `reports/lr-20261103-fbbf62c6/model_card.json` does not follow
   the contract:
   - It has `metrics_validation.pooled` and `majority_class_accuracy`.
   - It has no `metrics`, `trained_years`, `n_cells` or `data_source` keys.

   The file written to `artifacts/` must use the contract shape:
   - `trained_years` comes from `data.training_years`.
   - `majority_accuracy` comes from `majority_class_accuracy`.
   - `metrics.test` stays `null` until `06_final_eval.py`.
   - `data_source` is a plain string, e.g. `ERA5-Land reanalysis (Copernicus CDS)`.

   Proposal: the contract allows `test: null` explicitly.
2. **Level names.** As above: `lr_export.json` uses none/low/medium/high. The predictions
   must use low/moderate/high/very_high.
3. **top_drivers.** Proposal: export all 24 signed contributions, not only the top k.
   Contribution = coefficient x standardized value, in logit units, with
   `effect = sign` and `weight = |contribution|` rounded to 3 decimals. Grouping only sums what
   it receives. With a top k, a theme can lose one of two collinear features (strd and sky
   emissivity) and show the wrong sign.
4. **conditions_1800 keys.** The app has labels for `t2m_c`, `d2m_c`, `rh_pct`, `wind_ms`,
   `tcc_pct`, `sp_hpa`, `lw_down_wm2` and `dewpoint_depression_c`. Proposal: use these keys,
   with values in those units.
5. **Driver feature names.** The app has labels like `feature.t2m_c`. The model features are
   named like `t2m_1800_c`, so raw drivers would show raw names. Proposal: the app shows
   `driver_groups`, which has labels in ES and EN.
6. **historical_reliability.** Take it from `reliability_bins.json` (validation) as
   `{range: [lo, hi], observed_rate, n}`. `range` is in probability units, from 0 to 1.
7. **elevation_m.** Proposal: the cell's real elevation (geopotential / 9.80665). The mock
   uses 0.0 because it has no real value.
8. **Model file.** The backend does not load `model.joblib` or coefficients, and its image has
   no scikit-learn. It serves only precomputed predictions.
9. **Replay nights.** The demo replays a test-period night (2018 to 2025) with frost.
   Writing predictions for test nights means scoring the test split. The builder decides when
   to do it (after or as part of `06_final_eval.py`). 2026 nights (out of sample) can be
   written any time for `tick`.

## Repository items outside the backend paths (not edited)

- `.gitignore` line `.env.*` also ignores `backend/.env.backend.example`. Add
  `!backend/.env.backend.example` or the file will not be committed.
- `docker-compose.yml` passes no value for the following, so their defaults apply:
  `APP_ENV`, `EXPO_PUSH_URL`, `MUSE_MAX_TOKENS`, `MUSE_MAX_CALLS_PER_RUN`,
  `COVERAGE_RADIUS_KM`, `RATE_LIMIT_PER_MINUTE`. `PUBLIC_BASE_URL` is passed but unused.
  Add them only if the defaults are not wanted.

## Known issues

- `docker build` was not run: the Docker daemon was not running in this session. Instead, a
  clean Python 3.12 venv with only `backend/requirements.txt` imported `app.main` and answered
  `/health`.
- The rate limiter is in memory, for one process, and resets on restart.
- Expo push receipts are not polled: ticket ids are stored, receipts are not. A
  `DeviceNotRegistered` ticket removes the device.
- Starlette prints a deprecation warning for `TestClient` with httpx. It is filtered in pytest.
