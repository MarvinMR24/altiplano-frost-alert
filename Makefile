# Run from the project root. PY is the project virtualenv.
PY := .venv/bin/python

.PHONY: test lint eda features round1 round2 export muse serving notebooks repro sync

test:
	$(PY) -m pytest -q

lint:
	.venv/bin/ruff check src pipelines tests tools

eda:
	$(PY) pipelines/02a_eda_era5land.py --no-sync
	$(PY) pipelines/02b_eda_agera5.py --no-sync
	$(PY) pipelines/03b_eda_merged.py --no-sync

features:
	$(PY) pipelines/03_build_night_table.py --no-sync

round1:
	$(PY) pipelines/04_round1.py --no-sync

round2:
	$(PY) pipelines/05_round2.py --no-sync

export:
	$(PY) pipelines/05b_export_artifacts.py --no-sync

# Serving artifacts for the backend (needs reports/final_test_metrics.json).
serving:
	$(PY) pipelines/07_export_serving.py --no-sync

# Muse experiment (MUSE_MOCK=1 by default; MUSE_MOCK=0 for real calls, read from cache on re-runs).
muse:
	$(PY) pipelines/05_muse_correct.py --config configs/muse.yaml --no-sync

notebooks:
	$(PY) pipelines/make_notebooks.py
	.venv/bin/jupyter nbconvert --execute --to notebook --inplace notebooks/0*.ipynb
	.venv/bin/jupyter nbconvert --to html notebooks/0*.ipynb
	$(PY) tools/check_notebooks.py

# Whole chain through DVC (stages skip if inputs did not change), then push.
repro:
	dvc repro
	$(MAKE) sync

# One attempt each; non-fatal. Credentials only in .dvc/config.local.
sync:
	-dvc status
	-dvc push
	-dvc status -c
