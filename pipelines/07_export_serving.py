"""Export the serving artifacts for the backend (docs/artifacts_contract.md) and the replay candidates.

Needs reports/final_test_metrics.json (the single final evaluation). Writes artifacts/model_card.json,
artifacts/model_coefficients.json and artifacts/predictions/<YYYY-MM-DD>.parquet for every test-period
night (replay demo) and every 2026 out-of-sample night (latest available nights), plus
reports/replay_candidates.md. Probabilities come from the numpy export and are checked against the
model bundle. Nothing is fitted or selected here.

Run: .venv/bin/python pipelines/07_export_serving.py [--dry-run] [--no-sync]
"""

import time

import joblib
import numpy as np
import pandas as pd

from frostwatch_ml import cli, config, leakage
from frostwatch_ml.artifacts import serving
from frostwatch_ml.dataio.tables import read_json
from frostwatch_ml.models.calibration import apply_platt


def main() -> None:
    args = cli.parser(__doc__, "configs/model.yaml").parse_args()
    final = read_json(config.ROOT / leakage.FINAL_REPORT)
    version = final["finalists"]["LR_best"]["model_version"]
    export, lr_card, bins = serving.load_inputs(version)
    df = pd.read_parquet(config.PROCESSED / "features.parquet")
    rows = leakage.serving_rows(df)
    print(f"model {version}; serving rows {len(rows)}, nights {rows['night_date'].nunique()} "
          f"({rows['night_date'].min().date()} to {rows['night_date'].max().date()})")
    if args.dry_run:
        return

    model = joblib.load(config.MODELS / version / "model.joblib")
    bundle_p = apply_platt(model.decision_score(rows), export["calibration"]) if export["calibration"] else model.predict_proba(rows)
    cells = {p["id"]: p["cell"] for p in config.load_yaml("configs/points.yaml")["points"]}
    t0 = time.monotonic()
    table = serving.prediction_table(rows, export, bins, cells)
    diff = float(np.max(np.abs(table["probability"].to_numpy() - bundle_p)))
    if diff > 1e-9:
        raise SystemExit(f"serving parity failed: {diff}")
    muse = final.get("muse_condition_b", {}).get("status", "not evaluated")
    serving.write_card_files(serving.model_card(lr_card, final, export, muse), serving.coefficients(export))
    n = serving.write_predictions(table)
    print(f"wrote {n} prediction files in {time.monotonic() - t0:.1f}s (parity max abs diff {diff:.2e}); "
          f"periods: {table.groupby('period')['night_date'].nunique().to_dict()}")
    rep = serving.replay_candidates(table, config.REPORTS / "replay_candidates.md")
    print("replay:", rep)
    cli.finish("07_export_serving", args)


if __name__ == "__main__":
    main()
