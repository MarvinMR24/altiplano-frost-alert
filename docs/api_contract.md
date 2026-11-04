# API contract (backend <-> mobile)

Shared source of truth between the backend session and the mobile session. Any change is
made here first and noted in `docs/decisions.md`.

## Conventions

- JSON in and out, UTF-8. Dates are `YYYY-MM-DD` (night date, local), timestamps ISO 8601 UTC.
- Every endpoint requires `Authorization: Bearer <session_token>`, except `GET /health`,
  `POST /auth/email/request` and `POST /auth/email/verify` (login purpose).
- Errors: `{"detail": "<message>"}` with a proper status (401 no or bad token, 404 not
  found, 409 conflict, 422 validation, 429 rate limited).
- Levels from probability `p`: `low` p < 0.3, `moderate` 0.3 <= p < 0.5, `high`
  0.5 <= p < 0.7, `very_high` p >= 0.7.
- All risk data is ERA5-Land reanalysis (Copernicus CDS), not a live forecast. Every payload
  that carries risk includes `night_date` and, where listed, `data_source`.
- Internal operations (replay, manual tick) are a CLI (`python -m app.cli replay|tick`),
  never HTTP routes.

## Types

```
User {
  id: string
  email: string
  name: string | null
  phone: string | null          // optional, digits, spaces and + only
  email_verified: boolean
  language: "es" | "en" | "ay" | "qu"
  profile: "producer" | "resident"
  crops: string[]               // catalog ids, e.g. "potato", "quinoa"
  livestock: string[]           // catalog ids, e.g. "llama", "sheep"
  default_threshold: 30 | 50 | 70
  notification_email: string    // defaults to email
  onboarded: boolean
}
// The password hash is never returned. Alert emails and explanations exist only in
// es and en; ay and qu users get the Spanish version.

Driver { feature: string, effect: "up" | "down", weight: number }

Reliability {
  range: [number, number]       // probability bin, e.g. [0.5, 0.7]
  observed_rate: number         // share of nights with frost in that bin (validation)
  n: number                     // nights in the bin
}

Conditions1800 = { [name: string]: number }   // keys carry units, e.g. "t2m_c", "wind_ms"

Cell {
  point_id: string
  name: string
  lat: number
  lon: number
  elevation_m: number
  probability: number           // 0..1
  level: Level
  top_drivers: Driver[]
  conditions_1800: Conditions1800
  historical_reliability: Reliability
  observed?: { frost: boolean, tmin_c: number }   // only for past nights with labels
}

Polygon = GeoJSON Polygon geometry { type: "Polygon", coordinates: [[[lon, lat], ...]] }
          // one closed outer ring, 3 to 12 distinct vertices

Aoi {
  id: string
  name: string
  polygon: Polygon
  threshold: 30 | 50 | 70
  channels: { push: boolean, email: boolean }
  current?: {
    night_date: string
    probability: number
    level: Level
    cell_used: string           // point_id of the cell used
    distance_km: number         // from the AOI centroid to that cell
  }
}

AlertSummary {
  id: string
  aoi_id: string
  aoi_name: string
  night_date: string
  level: Level
  probability: number
  channels_sent: ("push" | "email")[]
  sent_at: string
  read: boolean
  headline: string
}

AlertDetail = AlertSummary + {
  explanation: { headline: string, why: string, actions: string[], caveats: string[] }
  conditions_1800: Conditions1800
  top_drivers: Driver[]
  historical_reliability: Reliability
  outcome: { frost: boolean, tmin_c: number } | null
  model_card_summary: string
}

ModelCard {
  model_version: string
  trained_years: [number, number]
  n_cells: number
  metrics: { validation: Metrics, test: Metrics }
  limitations: string[]
}
Metrics = { pr_auc, f2, precision, recall, f1, roc_auc, brier, accuracy, majority_accuracy: number }
```

## Endpoints

### Auth (email code)

| Method | Path | Body | Response |
|---|---|---|---|
| POST | /auth/email/request | `{email, purpose?}` | 204 |
| POST | /auth/email/verify | `{email, code, purpose?}` | `{session_token, user}` |

- The code has 6 digits, expires after 10 minutes, and is single use. Rate limit per email.
- `purpose` is `"login"` (default) or `"notification_email"`. With `"notification_email"`
  both calls require the bearer token; a successful verify sets the caller's
  `notification_email` to `email` and returns `{user}` without a new session. This is how
  the app changes the notification email.
- Google and Apple sign-in come later (backend-driven flow, opened with
  `WebBrowser.openAuthSessionAsync`). Not part of this version.
- `purpose` also accepts `"register"` and `"reset_password"` for the password flows below. With
  `"register"` the request resends the sign up code only when the email has an unverified account;
  it always returns 204.
- Code login keeps working exactly as before and marks the email verified.

### Auth (password)

Password policy: at least 8 characters, at least one letter and one number.
Passwords, hashes and codes are never logged and never appear in responses.

| Method | Path | Body | Response |
|---|---|---|---|
| POST | /auth/register | `{name, email, password, phone?, language?}` | 202 |
| POST | /auth/login | `{email, password}` | `{session_token, user}` |
| POST | /auth/password/forgot | `{email}` | 202 |
| POST | /auth/password/reset | `{email, code, new_password}` | `{session_token, user}` |
| POST | /auth/password/change | `{current_password, new_password}` (Bearer) | 204 |

- `POST /auth/register` creates the user unverified (or updates an unverified one) and
  sends a code with purpose `"register"`. It returns 202 even when the email is already
  verified, sending nothing new, so the endpoint does not leak which emails exist.
- `POST /auth/email/verify` with purpose `"register"` returns `{session_token, user}` and
  marks the email verified.
- `POST /auth/login` returns 401 with one generic message for any wrong combination, and
  403 `{"detail": "email_not_verified"}` when the password is right but the email is not
  verified (a new code is sent). At most 5 failed password attempts per email per 15
  minutes, then 429.
- `POST /auth/password/forgot` always returns 202; it sends a code with purpose
  `"reset_password"` only when the user exists. The code is redeemed with
  `POST /auth/password/reset` (not with `/auth/email/verify`).
- `POST /auth/password/change` needs the Bearer token and returns 401 when the current password
  is wrong.

### Me and devices

| Method | Path | Body | Response |
|---|---|---|---|
| GET | /me | | `User` |
| PATCH | /me | partial `{name, language, profile, crops, livestock, default_threshold, onboarded}` | `User` |
| DELETE | /me | | 204, deletes the user, devices, AOIs, alerts and sessions |
| POST | /devices | `{expo_push_token}` | 204 (idempotent) |

`notification_email` is not writable through PATCH; use the code flow above.

### Coverage and risk

| Method | Path | Response |
|---|---|---|
| GET | /coverage | GeoJSON `FeatureCollection` of Polygon features (one per cell, `properties.point_id`, `properties.name`) plus `meta: {radius_km}` |
| GET | /nights | `{latest: string, available: string[]}` (ascending) |
| GET | /map?night=YYYY-MM-DD | `{night_date, data_source, model_version, cells: Cell[]}`; without `night`, the latest |

#### GET /map/{point_id}/explain?night=YYYY-MM-DD&lang=es|en|ay|qu (Bearer)

Plain explanation of one place and night for the app, written by muse-spark when the user
opens the place (template when MUSE_MOCK=1, Muse is not configured, the call fails or the
answer fails verification). Generated from the current processed data and stored by a hash
of the facts, so the same facts reuse the text and new or reprocessed data produce a new one.
At most 30 Muse calls per user per hour (stored answers do not count). Muse never receives
the place name, the date, coordinates or the observed outcome; every number is checked
against the facts and sources come from a fixed list (no free URLs).

```json
{"point_id": "oruro", "night_date": "2024-08-17", "language": "ay", "source": "muse",
 "headline": "...", "what_happened": "...", "what_next": "...", "actions": ["..."],
 "sources": [{"name": "SENAMHI Bolivia", "url": "https://senamhi.gob.bo", "why": "..."}]}
```

`language` is the language of the text: for ay and qu it falls back to `es` when the
template is used. 404 for an unknown point or night.

### Areas of interest

| Method | Path | Body | Response |
|---|---|---|---|
| GET | /aois | | `Aoi[]` |
| POST | /aois | `{name, polygon, threshold, channels}` | `Aoi` (201); 422 if any vertex or the centroid is outside the coverage |
| PATCH | /aois/{id} | partial `{name, threshold, channels}` | `Aoi` |
| DELETE | /aois/{id} | | 204 |

### Alerts and model card

| Method | Path | Response |
|---|---|---|
| GET | /alerts | `AlertSummary[]`, newest first |
| GET | /alerts/{id} | `AlertDetail` |
| POST | /alerts/{id}/read | 204 |
| GET | /model-card | `ModelCard` |

### Push payload

Expo push messages carry `data: {alert_id: string}` so a tap opens the alert detail.

### Health

`GET /health` -> `{"status": "ok"}` (no auth, used by the Docker healthcheck).
