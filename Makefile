# Run from the project root. PY is the project virtualenv.
PY := .venv/bin/python

.PHONY: test lint eda features round1 round2 export notebooks repro sync

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
