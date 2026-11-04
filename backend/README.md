# backend (module 2)

FastAPI + SQLite (SQLAlchemy, Python 3.12) service that implements `docs/api_contract.md`.
Notes, contract differences and proposals: `docs/backend_notes.md`.

## Design

- Risk data is precomputed offline per cell and night and read through a `DataProvider`
  (`DATA_PROVIDER`): `mock` (deterministic synthetic data, everything flagged `MOCK`) or
  `artifacts` (`artifacts/model_card.json` and `artifacts/predictions/<YYYY-MM-DD>.parquet`,
  read-only, validated; any problem returns 503 with a clear message, no silent fallback).
- No live data and no scheduler. Alerts are created only when a night is processed with the
  CLI (replay or manual tick). They are never described as real time.
- Auth: email code only (6 digits, hashed, 10 minutes, 3 requests per hour per email, 5
  attempts per code), passwords (scrypt), and Google sign in (`app/auth/social.py`, backend
  driven OAuth with a one-time login ticket). JWT HS256 sessions for 30 days.
- Coverage: a 30 km circle around each of the 8 ERA5-Land cells (shapely, local azimuthal
  equidistant projection). AOIs must lie entirely inside it. AOI risk uses the cell whose
  circle contains the AOI centroid (the highest probability if several).
- Alerts: one per AOI per night, a re-alert only if the level rises, at most 2 per 24 hours of
  the night clock; idempotent. Email (SMTP STARTTLS or console) and Expo push, every delivery
  recorded without secrets.
- Explanations: a curated actions catalog (producer, resident; ES and EN, no health advice), a
  deterministic template, and muse-spark only when `MUSE_MOCK=0`, cached by a hash of the facts,
  every number checked against the facts. Token usage goes to `var/logs/muse_usage.jsonl`.

```
app/
  main.py config.py db.py models.py schemas.py security.py deps.py serializers.py cli.py
  auth/providers.py
  routers/   auth me geo map aois alerts model
  services/  coverage risk alerting explain notify_email notify_push drivers dedupe
  providers/ base mock artifacts
  data/cells.json  prompts/explain_v1.txt
tests/  (pytest, fixtures/ with a small synthetic artifacts set)
```

## Run

```
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --port 8000
.venv/bin/pytest && .venv/bin/ruff check .
```

Internal operations (never HTTP routes):

```
.venv/bin/python -m app.cli seed-demo [--email X]                       # demo user + 2 AOIs, flagged DEMO
.venv/bin/python -m app.cli replay --night YYYY-MM-DD [--email X] [--dry-run]
.venv/bin/python -m app.cli tick [--night YYYY-MM-DD] [--dry-run]       # default: latest night
# in Docker: docker compose exec backend python -m app.cli replay --night YYYY-MM-DD
```

Variables: `backend/.env.backend.example`.
