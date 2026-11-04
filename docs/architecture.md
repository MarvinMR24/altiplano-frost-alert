# Architecture

The system is split into three modules that never import code from each other. They talk
only through files (`artifacts/`) and HTTP (the backend API).

## Target layout

```
frostwatch-altiplano/
  MUSE.md  README.md  docker-compose.yml  .env.example  .gitignore
  docs/        shared: api_contract.md, artifacts_contract.md, architecture.md, status.md, ...
  artifacts/   contract folder between ml and backend (gitignored except .gitkeep)
  ml/          module 1: pipelines, configs, prompts, experiments, data, tests
               (it still lives at the repo root today; it moves in Phase 2)
  backend/     module 2: FastAPI, SQLite, notifications, Muse explanations
  mobile/      module 3: Expo app
```

Current state (Phase 1): the ml code is still at the repo root (`pipelines/`, `configs/`,
`data/`, `prompts/`, `experiments/`, `logs/`, `requirements.txt`). It moves into `ml/` in
Phase 2, after the CDS download finishes and `data/raw/cds/.lock` is gone.

## Module contracts

```
  ml  --writes-->  artifacts/  --read-only-->  backend  <--HTTP (bearer token)--  mobile
```

| Module | Owns | Produces | Consumes |
|---|---|---|---|
| ml | CDS download, features, split, training, evaluation, Muse dataset experiment | files in `artifacts/` (see `docs/artifacts_contract.md`) | CDS reanalysis (one process, lock file) |
| backend | users, sessions, AOIs, alerts, notifications (email, Expo push), Muse alert explanations | the HTTP API in `docs/api_contract.md` | `artifacts/` mounted read-only |
| mobile | the Expo app (web for local testing, Expo Go on iPhone), run on the host, not in Docker | nothing persistent besides the session token on the device | the HTTP API only |

Rules:
1. ml publishes files into `artifacts/`. It never calls the backend.
2. backend reads `artifacts/` read-only (`./artifacts:/app/artifacts:ro`). It never writes
   there and never imports ml code. Any feature logic it needs must come from the artifacts
   (precomputed predictions, model card, coefficients).
3. mobile talks to the backend only through the HTTP API. It holds no secrets.
4. No module imports code from another. Shared definitions live in `docs/` as contracts.

## Runtime (docker-compose)

| Service | Started by | Purpose |
|---|---|---|
| backend | `docker compose up` | FastAPI on port 8000, SQLite in a named volume at `/app/var` |

The ML pipeline is not in Compose either: it runs on the host with the root `.venv` (`make test`, `dvc repro`).
The mobile app is not in Compose. It runs on the host: `cd mobile && npx expo start --web`
for local testing, then Expo Go on the iPhone once the backend is deployed to AWS.

Secrets come from `.env` through `${VAR}` substitution, and each service gets only the
variables it needs. The backend never receives `CDS_API_KEY`.

## Internal operations

A public URL (AWS) forwards every HTTP route, so replay and manual tick are not HTTP
endpoints. They run as a CLI inside the backend container:

```
docker compose exec backend python -m app.cli replay
docker compose exec backend python -m app.cli tick --date YYYY-MM-DD
```

This supersedes the `/internal/*` endpoints listed in MUSE.md section 3.5.

## Data honesty

All predictions come from ERA5-Land reanalysis (Copernicus CDS), not live forecasts and not
raw satellite imagery. Every screen and alert shows the night date and "Reanalysis data".
