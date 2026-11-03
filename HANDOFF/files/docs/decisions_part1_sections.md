## 2026-11-03: DVC tracking of the raw CDS data
- DVC 3.67.1 is initialised with `dvc init --no-scm` (plain `dvc init` can stage files in git). Default remote `dagshub` (`https://dagshub.com/SNARF3/altiplano-frost.dvc`); credentials only in `.dvc/config.local`, written with `dvc remote modify --local`.
- `dvc add --file` does not exist in DVC 3.67.1 (`unrecognized arguments: --file`), and a plain `dvc add data/raw/cds` would write its pointer inside `data/raw/`, which must stay untouched. The pointer was therefore written by hand as `dvc/raw_cds.dvc` with only `outs: - path: ../data/raw/cds`, and `dvc commit -f dvc/raw_cds.dvc` filled in the hashes and the cache. A listing of `data/raw/` (names, sizes, modification times) was identical before and after.
- `.dvcignore` excludes `data/raw/cds/**/*_unzipped/` (extracted copies that duplicate the zip archives, written by `pipelines/01_download.py` during inspection) and `data/processed/scratch/`. The tracked raw directory has 29 files and 263,350,032 bytes: 24 data files, 4 small test downloads and `manifest.json`.

## 2026-11-03: EDA and night table (Part 1)
- ERA5-Land zip archives are always extracted from the zip into `data/processed/scratch/unzipped/<name>_<sha16>/` by `pipelines/common.py`; the pipeline never reads the `*_unzipped/` folders.
- EDA anomaly rules and thresholds are screening choices in `configs/frost.yaml`. Flags are listed in `data/processed/anomalies.parquet`; nothing is fixed or dropped.
- Night D is the local date of the 18:00 snapshot (22:00 UTC). Features use hours up to 22:00 UTC of D. The label window is 22:00 UTC of D to 13:00 UTC of D+1 (16 values).
- Split by whole years of D: train 1985-2009, validation 2010-2017, test 2018-2025; 2026 is `out_of_sample_check`. The elevation proxy (mean surface pressure) and the clearness reference (95th percentile, +-7 day window) are computed on training years only.
- The first night (1985-01-01) is dropped (no previous night). The last night (2026-10-26) is kept with a null label and `use = latest_available_night`. The label of night 2025-12-31 (test) uses hours of 2026-01-01 from the 2026 file; that is label data only.
- AgERA5 alignment: cloud cover of D-1 for night D; the AgERA5 night minimum dated D+1 for the night starting on D (cross-check only, in `data/processed/crosschecks.parquet`).

## Reproducing the data
- `dvc pull` restores `data/raw/cds/` (the zip archives, the AgERA5 files and the manifest) and the stage outputs under `data/processed/`. The `*_unzipped/` folders are not versioned and are not needed: `pipelines/common.py` extracts each zip into `data/processed/scratch/` when it reads it.
- `dvc repro` reruns the stages in `dvc.yaml` with `.venv/bin/python`. The stages are deterministic: a rerun of the night table gave the same SHA-256 for `features.parquet`.
