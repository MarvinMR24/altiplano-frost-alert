# Artifacts contract (PROPOSAL)

Status: proposal for the ml and backend sessions to review. Nothing here is final until both
sides agree; record changes in `docs/decisions.md`.

`artifacts/` is the only interface between ml (writer) and backend (read-only reader). It is
gitignored except `.gitkeep`. ml writes each file atomically (write to a temp name, then
rename) so the backend never reads a half-written file.

## Files

```
artifacts/
  model_card.json
  model.joblib                 # or model_coefficients.json (see below)
  predictions/
    <YYYY-MM-DD>.parquet       # one file per night
```

### model_card.json

```json
{
  "model_version": "string",
  "model_type": "logistic_regression",
  "condition": "A",
  "trained_years": [0, 0],
  "validation_years": [0, 0],
  "test_years": [0, 0],
  "n_cells": 8,
  "features": ["t2m_1800", "d2m_1800", "..."],
  "decision_threshold": 0.0,
  "metrics": {
    "validation": {"pr_auc": 0.0, "f2": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0,
                   "roc_auc": 0.0, "brier": 0.0, "accuracy": 0.0, "majority_accuracy": 0.0},
    "test": {"...": "same keys"}
  },
  "label_definition": "text, e.g. hourly t2m <= 0 C during the night",
  "data_source": "ERA5-Land reanalysis (Copernicus CDS)",
  "limitations": ["Labels come from the same reanalysis.", "..."],
  "created_at": "ISO 8601 UTC",
  "data_hash": "sha256 of the processed table"
}
```

All numbers above are placeholders for the shape only. The real values are whatever the
code computes (MUSE.md rule 11).

### model.joblib or model_coefficients.json

The backend does not need the model to serve precomputed predictions. It is published for
transparency and for optional on-demand scoring. Prefer `model_coefficients.json`
(`{"intercept": x, "coefficients": {"feature": w}, "scaler": {"mean": {...}, "scale": {...}}}`)
because it avoids pickle version coupling between the two images. `model.joblib` is allowed
if both images pin the same scikit-learn version.

### predictions/<YYYY-MM-DD>.parquet

One row per cell per night. The file name is the night date.

| column | type | notes |
|---|---|---|
| point_id | string | e.g. `el_alto`, from `configs/points.yaml` |
| grid_lat | float64 | ERA5-Land cell latitude |
| grid_lon | float64 | ERA5-Land cell longitude |
| elevation_m | float64 | cell elevation |
| night_date | date | local date of the 18:00 cutoff |
| probability | float64 | 0 to 1, logistic regression output |
| level | string | `low`, `moderate`, `high`, `very_high` (see below) |
| top_drivers | string (JSON) | list of `{feature, effect, weight}`, effect `up` or `down` |
| conditions_1800 | string (JSON) | object of raw 18:00 values with units, e.g. `{"t2m_c": 3.1}` |
| historical_reliability | string (JSON) | `{range, observed_rate, n}` for this probability bin on validation |
| observed_frost | boolean, nullable | label, null if not yet known |
| observed_tmin_c | float64, nullable | observed minimum, null if not yet known |
| model_version | string | matches `model_card.json` |
| data_source | string | `ERA5-Land reanalysis (Copernicus CDS)` |

Levels from probability `p`:

| level | range |
|---|---|
| low | p < 0.3 |
| moderate | 0.3 <= p < 0.5 |
| high | 0.5 <= p < 0.7 |
| very_high | p >= 0.7 |

Rules:
- No feature uses information after 18:00 local time of `night_date`.
- `observed_frost` and `observed_tmin_c` are never sent to Muse.
- The backend treats the latest file in `predictions/` as the latest night.
