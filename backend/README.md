# backend (module 2)

FastAPI + SQLite service that implements `docs/api_contract.md`. Status: skeleton
(`GET /health` only). Another session fills it in.

## Design

- All data access goes through a `DataProvider` interface with two implementations,
  selected by the env var `DATA_PROVIDER`:
  - `mock`: in-memory demo data (8 ERA5-Land cells, a few nights, flagged as mock).
  - `artifacts`: reads the ml outputs from `/app/artifacts` (read-only mount), following
    `docs/artifacts_contract.md`.
- Never imports code from `ml/` or `mobile/`.
- Every endpoint is authenticated with a bearer session token, except `GET /health` and the
  auth endpoints.
- Auth: email code login only for now (`POST /auth/email/request`,
  `POST /auth/email/verify`). Google and Apple come later.
- Internal operations are NOT HTTP endpoints (the public ngrok tunnel forwards every route).
  They run as a CLI:

```
python -m app.cli replay
python -m app.cli tick --date YYYY-MM-DD
```

- SQLite and caches live in `/app/var` (named Docker volume), `DATABASE_URL=sqlite:////app/var/frostwatch.db`.
- Notifications: SMTP email (`EMAIL_PROVIDER=smtp`) and the Expo Push API. Muse explanations
  are cached and verified (MUSE.md rule 24); `MUSE_MOCK=1` for development.

## Run

```
# with Docker (from the repo root)
docker compose up backend

# on the host
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
.venv/bin/pytest
```
