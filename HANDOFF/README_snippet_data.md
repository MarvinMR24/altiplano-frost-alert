## Data and experiments (DVC + DagsHub)

Raw data and pipeline outputs are not stored in git. They are versioned with [DVC](https://dvc.org) and stored in the DagsHub repository [SNARF3/altiplano-frost](https://dagshub.com/SNARF3/altiplano-frost):

- `dvc/raw_cds.dvc` tracks `data/raw/cds/`: ERA5-Land hourly series (8 cells, 1985-01-01 to 2026-10-26) and AgERA5 daily series (8 points, 1984-12-31 to 2026-10-25), downloaded from the Copernicus Climate Data Store with `pipelines/01_download.py`, plus the download manifest.
- `dvc.yaml` and `dvc.lock` define and pin the pipeline stages (EDA, night table) and their outputs in `data/processed/`.

Get the data and rebuild the outputs:

```
.venv/bin/pip install -r requirements.txt -r requirements-model.txt
dvc pull        # download raw data and processed outputs from DagsHub
dvc repro       # rerun any stage whose code, config or inputs changed
```

Experiments are tracked with MLflow on the same DagsHub repository: https://dagshub.com/SNARF3/altiplano-frost.mlflow (runs are added in the modeling step).

The data is ERA5-Land and AgERA5 reanalysis (a weather model combined with assimilated observations), not raw satellite imagery, and the frost labels come from the same reanalysis. See `docs/data_licenses.md`.

Generated using Copernicus Climate Change Service information [2026].
