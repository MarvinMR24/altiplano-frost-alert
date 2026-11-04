# Spec 02: Muse alert explanations

Status: approved
Module: `backend/` (explain step of the serving flow)
Depends on: spec 01, `artifacts/model_card.json`, `artifacts/predictions/*.parquet`

## Why

A probability alone does not tell a producer what to do tonight. Muse Spark turns numbers the
model already computed into a short, plain explanation. Muse never computes, predicts or
looks up anything: it only explains the metrics it is given, so the cost stays minimal and
every number can be verified.

## What

1. Model and mode: `muse-spark-1.3` through the Meta Model API, in the lowest-cost mode the
   API offers (the least reasoning or effort level available). The exact mode name is
   verified against the Meta API docs by the implementing agent and set by environment
   variable, not hardcoded. Temperature 0, strict JSON output, low `MUSE_MAX_TOKENS`.
2. Input: a small JSON built only from fields on an allow list:
   - `probability`, `level`, `threshold` (the AOI threshold);
   - `top_drivers` (feature, effect, weight);
   - `conditions_1800` (values with units);
   - `historical_reliability` (range, observed rate, n);
   - validation metrics from the model card (PR-AUC, recall, precision, Brier);
   - user `profile`, `crops`, `livestock`, `language`.

   Never sent: raw time series, real dates, place names or coordinates, labels
   (`observed_frost`, `observed_tmin_c`), user email or any id.
3. Output (strict JSON, validated): `headline`, `why`, `actions[]`, `caveats[]`, in the
   user's language only. Actions cover crops, livestock, water pipes, vehicles, road ice and
   property only. No health or medical advice.
4. Cost control:
   - no call below the watch level;
   - one batched call per processed night, covering the unique combinations of
     (cell, level, profile, crops, livestock, language) that produced alerts;
   - every call cached by request hash in `logs/muse_cache/`; a re-run reads the cache;
   - token usage and estimated cost appended to `logs/muse_usage.jsonl`;
   - `MUSE_MOCK=1` returns a fixed mock explanation with no network call;
   - no retry loops: one failure falls back to the template.
5. Verification: every number in the Muse text must match a number in the input payload
   (same value, same rounding rule). Any mismatch, invalid JSON, missing field or forbidden
   topic triggers the template fallback.
6. Template fallback: a deterministic ES and EN template filled from the same payload, so an
   alert always has an explanation.
7. Labeling: the API marks each explanation `source: "muse"` or `source: "template"`, and the
   app shows it.
8. Prompts are versioned in `prompts/` (for example `prompts/explain_v1.md`) and the prompt
   version is stored with each explanation.

## Acceptance criteria

1. A test builds the payload for a fixture alert and asserts it contains only allow-listed
   keys and no date, place name, coordinate, label or email.
2. The payload for one alert is under 800 input tokens (estimated) and `MUSE_MAX_TOKENS` is
   at most 400. Both are targets that can be tuned, and the measured values are written to
   `docs/status.md`.
3. Running the same night twice makes zero API calls the second time (cache hit, test with a
   mocked client).
4. A night where every cell is below the watch level makes zero Muse calls (test).
5. A Muse response with a number not in the payload, invalid JSON or health advice falls
   back to the template (three tests).
6. `logs/muse_usage.jsonl` gets one line per real call with tokens and estimated cost.
7. With `MUSE_MOCK=1` the whole replay runs offline.
8. One real call with the configured low-cost mode returns valid JSON for the replay night
   (manual check, cost recorded in `docs/status.md`).

## Out of scope

The Muse dataset correction experiment (A vs B) belongs to the ml session.

## Addendum (2026-11-04): place explanations on demand

Builder decision: when a user opens a place on the map, Muse writes a plain explanation of
that night (what happened, what came next, what to do, where to read more) in es, en, ay or
qu, generated on demand from the current processed data (`GET /map/{point_id}/explain`,
`backend/app/services/place_explain.py`, prompt `place-explain-v1`). It follows the rules
above: allow-listed facts only, no place name, date, coordinates or labels sent (Muse writes
`{place}` and `{night}` placeholders), number verification, catalog actions, a fixed list of
information sources, template fallback, usage logged. Unlike alerts it also runs below the
watch level, because the user asked for it; cost is bounded by caching identical facts and
30 calls per user per hour. "What came next" uses only the model output for the following
processed night; Muse never forecasts on its own. The app shows the explanation first and
moves model numbers and metrics into a closed "Technical information" section.
