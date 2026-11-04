# Spec audit: ML module requirements vs project specs

Files read (not edited): MUSE.md, CLAUDE.md (identical content except the title and one layout line), docs/project-context.md (the project's PROJECT_CONTEXT.md; there is no PROJECT_CONTEXT.md at the root of this environment) and README.md. Proposed text is in HANDOFF/spec_patch.md.

| requirement | MUSE.md / CLAUDE.md | docs/project-context.md | README.md | verdict |
|---|---|---|---|---|
| Reusable code in a package (src/frostwatch_ml, pip install -e .) | Section 5 layout lists only `src/serve/` | Section 7 layout lists only `src/serve/` | not stated | missing |
| Thin pipeline scripts | Section 3.6 lists `02_features.py`, `03_split.py`, `04_train_eval.py --round 1/2`, `run_experiment.py`, `06_compare.py` | Section 7 layout: `02_features.py 03_split.py 04_train_eval.py ... 06_compare.py run_experiment.py` | not stated | contradicted (names and structure differ from the implemented 02a, 02b, 03, 03b, 04_round1, 05_round2, 05b_export_artifacts, 06_final_eval) |
| Notebooks without logic | Rule 18: "No notebook-only results." | Section 5.7: "Runs never share mutable state." | not stated | partially stated (no notebook-only results), missing the "present only" rule and its check |
| No future information in features | Rule 15: "No feature may use information after 18:00 local time of the prediction day." | Section 5.3: "Features use only information available at or before that time." | not stated | stated |
| Chronological split, validation-only selection, test once | Rule 14: "Split chronologically by whole years ... Choose models, hyperparameters and thresholds on validation only. Touch the test set once per final comparison." | Section 5.4 | not stated | stated (the code lock and single-use stub are missing from the specs) |
| Train-only fitted statistics | not stated | not stated | not stated | missing |
| Explicit feature allowlist, cross-check columns kept apart | not stated | Section 5.3 lists features; nothing on allowlist or cross-checks | Data notes: AgERA5 night minimum "used only to cross-check the frost label in the EDA, never as a model feature" | partially stated |
| Cloud lag (D-1) | not stated | not stated | Data notes: "the night that starts on day D only uses the value of day D-1" | stated in README only |
| Artifact policy (reports/ in git, models/ and data/ in DVC, LR JSON export, no pickle in serving) | Rule 25: "Out of scope, do not build: ... DVC" | Section 0 "Cut now: ... DVC (use data hashes)"; Section 7 `.gitignore` | not stated | contradicted (DVC is now used; artifact policy missing) |
| Automatic sync (DVC push, MLflow mirror on DagsHub) | not stated (DVC out of scope) | Section 5.7 isolated experiments; no MLflow | not stated | missing / contradicted |
| Experiment records | Rule 18: config in `configs/experiments/<id>.yaml`, outputs in `experiments/<run_id>/` | Section 5.7: `experiments/<run_id>/` with config.yaml, metrics.json, predictions.csv | not stated | partially contradicted (config lives in experiments/<run_id>/config.yaml; predictions moved to data/processed/predictions/ under DVC) |
| Tests that prove no leakage (pytest, make test) | Section 5 layout lists `tests/` | Section 7 lists pytest and ruff in requirements | not stated | missing (folder only) |
| Reports in git | not stated | not stated | not stated | missing |
| Per-cell and macro metrics, skill vs baselines | Rule 17 lists metrics, pooled only | Section 5.6 | not stated | missing (per-cell, macro, skill) |
| Model card "validation only; test pending" | not stated | not stated | not stated | missing |
| Model valid only for the 8 covered cells | Section 1: "La Paz to Oruro corridor), covered by the 8 points already downloaded"; Section 3.1 step 2: "only inside the coverage of the 8 downloaded points ... No other places." | Section 1 "Beneficiaries: residents of cities (La Paz, El Alto, Oruro, Potosi, Puno, Juliaca, Cusco)" and the one-liner "Bolivian and Peruvian Altiplano" | not stated | stated in MUSE.md and CLAUDE.md; contradicted in docs/project-context.md |
| Risk levels from the probability | Section 3.1 step 3: "level (none, watch, alert)" | not stated | not stated | mismatch: the model export uses cuts 0.3 / 0.5 / 0.7, which give 4 bands (configs/model.yaml names them none, low, medium, high); the builder must choose the mapping to none / watch / alert |
