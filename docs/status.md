# Status

Last update: 2026-11-02, 03:35 Bolivia time.

## Done
- `pipelines/01_download.py`: CDS downloader for `reanalysis-era5-land-timeseries`. One process (lock file `data/raw/cds/.lock`), one request at a time, 10 s between requests, no automatic retries, resume from `data/raw/cds/manifest.json`. Each file is opened with xarray and checked (variables, units, hourly step, gaps, NaN, returned cells). Every response must contain exactly one cell equal to the expected one, otherwise the script stops.
- `configs/points.yaml` (8 points, `area_mode: node_se`, expected cell per point) and `configs/cds_datasets.yaml` (dataset, variables, test requests, date ranges).
- Test requests for El Alto, July 2025 (all complete in the manifest):
  - `corner` box [-16.4, -68.2, -16.5, -68.1]: one cell (-16.5, -68.1), not the target.
  - `center` box [-16.4, -68.3, -16.6, -68.1]: four cells.
  - `node_se` box [-16.4, -68.3, -16.5, -68.2]: one cell (-16.5, -68.2), assertion PASS, 744 hourly timestamps, 0 NaN, 92 hours with t2m <= 0 C, identical to the same cell in the `center` file.
- Box semantics and cell findings recorded in `docs/decisions.md` and the README data notes.

- Phase 1 full run (`--run --ranges main`), 1985-01-01/2025-12-31, all 8 points complete. Every file passed the one-cell and time assertions (359,400 hourly timestamps, first 1985-01-01 00:00 UTC, last 2025-12-31 23:00 UTC, no gaps) and has 0 NaN in all 10 variables. One request per point, each under about 1 minute.

| point | cell | MB | timestamps | NaN | status | hours t2m <= 0 C |
|---|---|---|---|---|---|---|
| el_alto | (-16.5, -68.2) | 31.8 | 359400 | 0 | complete | 13009 |
| oruro | (-18.0, -67.1) | 31.8 | 359400 | 0 | complete | 16126 |
| patacamaya | (-17.2, -67.9) | 31.8 | 359400 | 0 | complete | 30746 |
| calamarca | (-17.0, -68.1) | 31.8 | 359400 | 0 | complete | 31095 |
| caracollo | (-17.6, -67.2) | 31.8 | 359400 | 0 | complete | 17419 |
| corocoro | (-17.2, -69.1) | 31.8 | 359400 | 0 | complete | 48246 |
| charana | (-17.6, -69.4) | 31.8 | 359400 | 0 | complete | 76692 |
| huanuni | (-18.3, -66.8) | 31.8 | 359400 | 0 | complete | 32637 |

All files have the same size because they have the same array shape; the 8 sha256 values are distinct.

- 2026 year to date (`--run --ranges 2026_ytd`), 2026-01-01/2026-10-26, all 8 points complete, `use: out_of_sample_check` (never training, validation or test; usable for the replay and the manual tick). Every file passed the one-cell and time assertions (7,176 hourly timestamps, 2026-01-01 00:00 to 2026-10-26 23:00 UTC, no gaps) and has 0 NaN.

| point | cell | MB | timestamps | NaN | status | hours t2m <= 0 C |
|---|---|---|---|---|---|---|
| el_alto | (-16.5, -68.2) | 0.78 | 7176 | 0 | complete | 248 |
| oruro | (-18.0, -67.1) | 0.78 | 7176 | 0 | complete | 303 |
| patacamaya | (-17.2, -67.9) | 0.78 | 7176 | 0 | complete | 609 |
| calamarca | (-17.0, -68.1) | 0.78 | 7176 | 0 | complete | 640 |
| caracollo | (-17.6, -67.2) | 0.78 | 7176 | 0 | complete | 443 |
| corocoro | (-17.2, -69.1) | 0.78 | 7176 | 0 | complete | 950 |
| charana | (-17.6, -69.4) | 0.78 | 7176 | 0 | complete | 1651 |
| huanuni | (-18.3, -66.8) | 0.78 | 7176 | 0 | complete | 684 |

## Not downloaded yet
- No cloud-cover dataset.

## Next steps
1. Features and label (`02_features.py`), EDA (`02b_eda.py`), split (`03_split.py`).
2. El Alto frost hours per year trend down (often above 300 before 2010, mostly below 300 after). The chronological test years will have fewer frost nights than train. Document this in the README with the split results.

## Known issues
- The CDS response is a zip with one NetCDF per variable group, saved under a `.nc` name. The script extracts it to `<name>_unzipped/` and keeps the original file.
- The old `corner` and `center` tests are kept in the config for reference only. They fail the one-cell assertion if re-run.
- A 41-year request per point was accepted by CDS. If a future request is rejected, the script stops and reports; the range is not split automatically.

## How to run
```
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
# .env must contain CDS_API_KEY (token only); optional CDS_API_URL
.venv/bin/python pipelines/01_download.py --test node_se
.venv/bin/python pipelines/01_download.py --run --ranges main
.venv/bin/python pipelines/01_download.py --run --ranges 2026_ytd
```
Outputs: `data/raw/cds/era5land_ts/`, `data/raw/cds/manifest.json`, `logs/cds_download.log` (all gitignored).
