# Spec 01: Backend and serving

Status: approved
Module: `backend/` (FastAPI + SQLite, local, exposed through ngrok)
Depends on: `docs/api_contract.md`, `docs/artifacts_contract.md`, spec 02

## Why

The app needs one local service that turns the model output in `artifacts/` into risk per
area of interest, creates alerts with clear rules, and delivers them by email and push. The
demo depends on a replay of a real test-period frost night that runs from one command.

## What

1. Implement every endpoint and type in `docs/api_contract.md`.
2. A `DataProvider` interface with two implementations, selected by an environment variable:
   - `mock`: fixed, clearly marked mock data, so the app and the tests work before ml
     publishes artifacts.
   - `artifacts`: reads `artifacts/model_card.json` and `artifacts/predictions/*.parquet`
     read-only.
3. Coverage: the 8 points in `configs/points.yaml` (El Alto, Oruro, Patacamaya, Calamarca,
   Caracollo, Corocoro, Charana, Huanuni), one ERA5-Land cell each. `GET /coverage` is built
   from the point list and the cell coordinates, never hardcoded in the app.
4. AOI to cell: the cell nearest to the AOI centroid. `422` if any vertex or the centroid is
   outside the coverage, as in the contract.
5. Alert rules, applied when a night is processed:
   - an alert is created when the cell probability crosses the AOI threshold;
   - one alert per AOI per night; re-alert only if the level rises; at most 2 per AOI per 24 h;
   - below the watch level no alert and no LLM call.
6. Notifications through pluggable senders:
   - `EmailSender` (`EMAIL_PROVIDER=smtp`), only to a verified `notification_email`;
   - Expo Push API, payload `data: {alert_id}`;
   - every send is logged with status; a failed channel does not block the other.
7. Internal operations as a CLI, never HTTP (ngrok forwards every route):
   - `python -m app.cli replay`: picks a test-period night with observed frost from the
     artifacts, runs steps 4 to 6 with a simulated clock, marks the alert `replay: true`;
   - `python -m app.cli tick --date YYYY-MM-DD`: same flow for one night, default the latest
     file in `artifacts/predictions/`.
8. Privacy: store only email, notification email, push token, language, profile, crops,
   livestock and AOI polygons. `DELETE /me` removes all of it.

## Acceptance criteria

1. Every endpoint in `docs/api_contract.md` exists, returns the documented types and error
   codes, and has at least one test against the `mock` provider.
2. With the `artifacts` provider, `/map`, `/nights`, `/model-card` and `/aois` values match
   the artifact files exactly (test with a small fixture artifact set).
3. `/coverage` returns exactly the 8 points of `configs/points.yaml`.
4. The backend never writes to `artifacts/` (mounted `:ro`) and never imports ml code.
5. Alert rules: tests cover first alert, same level next run (no alert), level rise
   (re-alert), the 2 per 24 h cap and below-watch (no alert, no LLM call).
6. A fake alert reaches the builder's iPhone as a push and the inbox as an email (manual
   check, recorded in `docs/status.md`).
7. `python -m app.cli replay` runs end to end from one command inside the backend container
   and the resulting alert says "Replay" in the API payload, the push and the email.
8. No email is sent to an unverified address (test).
9. `DELETE /me` leaves no rows for that user in any table (test).
10. No secret appears in logs, responses or error messages (test with a fake key value).
11. `docker compose up` starts backend and ngrok, and `GET /health` answers through the
    public URL.

## Open items

- `Cell.elevation_m` is required by the contract. Its value must come from the data (ml
  artifacts). If ml cannot provide it, change the contract to make it optional instead of
  filling in a guessed value.
