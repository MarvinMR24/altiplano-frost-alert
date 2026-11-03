# HANDOFF: Part 1 (EDA, night table, DVC)

Produced in an isolated copy of the project. Nothing was committed. Copy the folders as described, review, then commit yourself.

## Where each folder goes
- `HANDOFF/files/` mirrors the project root: copy its contents into the root of your project (same relative paths).
  - `docs/decisions_part1_sections.md` holds only the three sections appended to `docs/decisions.md` (DVC tracking, EDA and night table, Reproducing the data). Append them to your `docs/decisions.md` instead of copying this file.
  - `docs/data_licenses.md` is unchanged from the version you already have.
- `HANDOFF/data_processed/` is the content of `data/processed/` (git-ignored, do not commit). You do not need to copy it: `dvc pull` restores the same files from DagsHub.
- `HANDOFF/README_snippet_data.md`: a section to paste into your README.

## Reproducing the data
- `dvc pull` restores `data/raw/cds/` and the stage outputs in `data/processed/`.
- The `*_unzipped/` folders next to the raw zip files are not versioned (excluded in `.dvcignore`) and not needed: `pipelines/common.py` always extracts each zip into `data/processed/scratch/unzipped/` (also ignored) when it reads it.
- `dvc repro` reruns all stages; they are deterministic (a rerun of the night table gave the same SHA-256 for `features.parquet`).

## Commands
```
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-model.txt
dvc pull                                     # raw data and processed outputs from DagsHub
dvc repro                                    # or the stages one by one:
.venv/bin/python pipelines/02a_eda_era5land.py
.venv/bin/python pipelines/02b_eda_agera5.py
.venv/bin/python pipelines/03_build_night_table.py
.venv/bin/python pipelines/03b_eda_merged.py
.venv/bin/python pipelines/make_notebooks.py
.venv/bin/jupyter nbconvert --execute --to notebook --inplace notebooks/0*.ipynb
.venv/bin/jupyter nbconvert --to html notebooks/0*.ipynb
dvc push && dvc status -c                    # after changes
```
To use the DagsHub remote on a new machine, set the remote credentials locally (they go to `.dvc/config.local`, never to git):
```
dvc remote modify --local dagshub auth basic
dvc remote modify --local dagshub user <your DagsHub user>
```
then set the secret field of the http remote to your DagsHub access key with the same command (see `dvc remote modify --help`, http remote options).

## Packages
Python 3.12.13; 3.67.1 (global install).
```
cdsapi==0.7.7
ipykernel==7.4.0
matplotlib==3.11.2
nbconvert==7.17.2
nbformat==5.11.1
netCDF4==1.7.5.1.post1
numpy==2.5.4
pandas==3.1.0
pyarrow==26.0.0
python-dotenv==1.2.4
PyYAML==6.0.3
xarray==2026.9.0
```

## .gitignore lines to add or check
```
data/
.dvc/config.local
.dvc/cache
.dvc/tmp
```
And make sure these are NOT ignored (they must be committed): `dvc/*.dvc`, `dvc.yaml`, `dvc.lock`, `.dvc/config`, `.dvc/.gitignore`, `.dvcignore`. Note: your current `.gitignore` ignores `logs/*`; that does not affect these files.

## Pointer and pipeline files to commit
- `dvc/raw_cds.dvc` (raw CDS data: 29 files, 263,350,032 bytes)
- `dvc.yaml`, `dvc.lock`
- `.dvc/config` (remote URL only), `.dvc/.gitignore`, `.dvcignore`

## Test downloads inside the tracked raw folder
`data/raw/cds/` also holds 4 small test downloads, versioned in DVC with the rest but never read by the pipeline:
- `data/raw/cds/era5land_ts/test_elalto_2025-07.nc`
- `data/raw/cds/era5land_ts/test_elalto_2025-07_center.nc`
- `data/raw/cds/era5land_ts/test_elalto_2025-07_node_se.nc`
- `data/raw/cds/agera5_ts/test_elalto_2025-07.nc`

## Files in HANDOFF/files
| file | bytes | sha256 |
|---|---|---|
| `.dvc/.gitignore` | 26 | `cda3fc1a4ce9659cb19818bb065eee8c5271795484f49f314ca0357b4daec6ef` |
| `.dvc/config` | 124 | `6582f36a34ee5ac1a33d90ecc033763cf53079efb594e93dc93e9b14d68a1c69` |
| `.dvcignore` | 456 | `6a06f77dd02c8069b9cee36482d602bb826fc1eff83bf307031b2ce664ec6cf1` |
| `configs/frost.yaml` | 1616 | `566ee341f4b9168d874e95259925d08ca01746fe404efe3cef8257f365cf3da2` |
| `docs/data_licenses.md` | 1111 | `5b00304d335b795a3fd7f69505c383b2c20ef069e66d9cb10dcf3edd33772f19` |
| `docs/decisions_part1_sections.md` | 2839 | `eb640652446fedba3e860018ec4ad7e3d3b925f599bc410deb1d72e324c12c2f` |
| `docs/eda_agera5.md` | 5907 | `05098d334bd9adc3d87fec390814aac3085150c4d0769962e671a41b9f2608ce` |
| `docs/eda_era5land.md` | 8731 | `2723c60a899b776d09fbbcf7a170a3d13efee3b91254cf30bb680180e1a088c1` |
| `docs/eda_merged.md` | 7197 | `eaadd69fc5a8da229bd82c273869e53b09a923a4b7a20ddbf5ca4889273af21b` |
| `docs/figures/agera5_cloud_cover_by_month.png` | 119700 | `aa7a44cb96a46f045b2adc7115baf1001e38f62b19a4ced19f2927fb6d4c9f4c` |
| `docs/figures/agera5_vs_era5land_tmin_el_alto.png` | 89031 | `8508f65d1d984aaa95032fa00da015d90d375b85d5bd45ab0c7a2e80adc97f73` |
| `docs/figures/era5land_frost_nights_by_year.png` | 142691 | `893437bcf7386ed4dcb676df8716cedd8f7d25798f6f720eeac14548afb32be5` |
| `docs/figures/era5land_frost_rate_by_month.png` | 119236 | `0d4bc814e9584f4f7b59b7130501bd5c31a58bd8e08ea6678f1c9855059f1391` |
| `docs/figures/merged_corr_with_label_train.png` | 65415 | `d72d9d952bd475b3fc472fde86dd3daa8df325e9e02db00f5497476741344581` |
| `docs/figures/merged_frost_rate_by_year.png` | 55551 | `090498d7a18556db9eab98179d0c0e777448e6de5b69811e9f2897d949a6d0d8` |
| `dvc/raw_cds.dvc` | 117 | `1ade5323bb4cbd04f2b46d12d8f2c0a3a7f66d565aa67f5b0b0fcdf14418ff04` |
| `dvc.lock` | 4797 | `cfd3b6a798568bc6f75c79cda33617a94abadfb19f45c661270e79ce012caf36` |
| `dvc.yaml` | 2179 | `7780df4ce311c549fa932880a2c1009b9614d8e7363a28158bd948b5dfb29d91` |
| `notebooks/01_eda_era5land.html` | 547440 | `61499a795541d1adededc843d303ddac7488560b17b67745012c8c966be29671` |
| `notebooks/01_eda_era5land.ipynb` | 276645 | `92d60eb2b2b934b5485c18494fa5a225aa3aeec347e5e8870ccebc7c26520199` |
| `notebooks/02_eda_agera5.html` | 651642 | `20bd258eb20ceba6127bffd4356a515baaf338278b7ef9d2b3a97dae1b54b855` |
| `notebooks/02_eda_agera5.ipynb` | 376313 | `52bb03003ea03b9da05b28e02ae0db7360e5e96a5f0599b293fd60e150d9426f` |
| `notebooks/03_night_table_and_eda.html` | 433999 | `915bf6179d5cc5dcb49a7a2e958c942ef9ff94a4e442409cfbb8e210c33e3e27` |
| `notebooks/03_night_table_and_eda.ipynb` | 166401 | `f64233ab0f0e9d8dca0e206a773ee56fd8ea2c02b24edf4fd3d6b09c4d8488a7` |
| `pipelines/02a_eda_era5land.py` | 11682 | `2e9c5ffdc8b3cd3ab8b16a597c6fc945ed690fdac8b2d2f335b47c517fe10bd1` |
| `pipelines/02b_eda_agera5.py` | 9819 | `f953c19391078a4f0aa7d5376e99821bf26a3ecddd04b46d3906523f4693ec37` |
| `pipelines/03_build_night_table.py` | 10587 | `cd98f8995581562f282372bbfe8d2227ce60e0f03f1eedb00e3c0d1be89c6342` |
| `pipelines/03b_eda_merged.py` | 9355 | `f7cba90c465f8b7180fdc692773ac66cf26c5581b5034e85fb7ed0c0ee29a355` |
| `pipelines/common.py` | 7165 | `3cdcb9bf171ec460ea5dbcbda570461a74b71bba91265daeb16967b909ed3f7c` |
| `pipelines/make_notebooks.py` | 6956 | `73d85729675dbfbee4d1b291fd95065f8c8da3fe412c8ac470f075c1a15f965d` |
| `requirements-model.txt` | 259 | `2d43591e65185ec9c08382d24a291e4359c949705f04360cf7f8a19482337bf2` |

## Files in HANDOFF/data_processed
| file | bytes | sha256 |
|---|---|---|
| `anomalies.parquet` | 389185 | `d3a78b004d8c2652d54b4c2a5b12b39419393a4f019fe3ff1dad8e06597946d7` |
| `crosschecks.parquet` | 3096874 | `cfdb3ae3812b0d40e6794e52ee15245240fbe686e9a2e049ecf3647fc84b3727` |
| `eda_agera5/cloud_cover_by_month.csv` | 1111 | `1c531f47998ec4b9ad60623aedb553777d225ce3275ca9d9a02737be857be76c` |
| `eda_agera5/coverage.csv` | 888 | `1cd1853e0ba6fc9cc820408417bb57629ac649b8e5eb8974c020a7bea37771c1` |
| `eda_agera5/crosschecks.csv` | 1813 | `1d45e4d493c31596c96df7430d33b82ccb9ba55945777cfea82aab7bd41de3c2` |
| `eda_agera5/daily_crosscheck.parquet` | 4361412 | `dddde9c4ec00a5cb3e357986f74bca91ad88081b1661ef1d1eaf4e1e09a7479d` |
| `eda_agera5/summary.json` | 392 | `80632e7d09d9096d04be01644877079a2270e449c67c9ba1a23a30e19a70b5d8` |
| `eda_era5land/anomaly_counts.csv` | 144 | `4f5fef3a44736de792ae6b146953b4ca7d8a5210a310adffab786b721c7d4ce0` |
| `eda_era5land/coverage.csv` | 1002 | `37eda558d4ba12a5a09b80b244cff75f588813a67dabd8f3303a1a7db94c4b40` |
| `eda_era5land/frost_by_cell.csv` | 394 | `faf537a3ac706847ab66c45799940cf0eeae8fe990ec8e1e7977390836d0a3b6` |
| `eda_era5land/frost_nights_by_year.csv` | 2127 | `e916df51473ab787060eb24dbbad06a7d85b142f6e28453a5a91d92fd1cb2684` |
| `eda_era5land/frost_rate_by_month.csv` | 1974 | `51cbcf13a6a8596f145ad08b1fafdd4e2930947c850bd049c065d7fbdd138893` |
| `eda_era5land/nights_label.parquet` | 1002380 | `b47bf2cf144a6523668609eff285acac48f0dec73360540b6ac7746950f5f543` |
| `eda_era5land/summary.json` | 379 | `beb1db97e6e691b188e70491f1a21640ae022606e3b77a111a16aa29fe223698` |
| `eda_era5land/trends.csv` | 580 | `a8f92d8b2a67b650fd4124ffaf47564c8ddf0cbab1fa473cad6663428da3c0cc` |
| `eda_era5land/value_ranges.csv` | 6364 | `f168d7f2b6031c3bb5cd23feeed5281ccb1cda7f621f8a350dafb1819291d6ee` |
| `eda_merged/class_balance.csv` | 306 | `d83a91357c384d6642bc8367f83f964ddcb16d7c76943a75b348100413f11c73` |
| `eda_merged/corr_with_label_train.csv` | 916 | `0a80aa407d7f0d2f5f65d0735d4bf2f58f4374e74d73985aeaeb93513a18cf8e` |
| `eda_merged/drift_std_mean_diff.csv` | 1956 | `3675f78ec0296c4bdec45d998dea0ce3ace7e62f8be8db364b2fefab814b7af5` |
| `eda_merged/feature_means_by_split.csv` | 2228 | `c782662c8a08b7e5f528600b4bd9bc44bd0f37ad6cb27833092a24a96159263a` |
| `eda_merged/frost_by_cell_split.csv` | 743 | `4252e505e878f55d926c3a636c95ae36ef47b60178e18c68bd3d7c25f32dd90e` |
| `eda_merged/frost_by_month_train.csv` | 1765 | `0dd7566b3ee667a6c9598dc9b029b681ad8aed86266c78ce7f5a65fbc47015c9` |
| `eda_merged/frost_by_year.csv` | 1039 | `8fd3d51c3e3b179f63ee51aa0b823b8ef116de77de66b42e7755ce8158c4ecf5` |
| `eda_merged/label_vs_agera5.csv` | 799 | `26ada04a880b2f087b31db8aff4f71d177496cb2772210798ce9e3b98ea0db85` |
| `eda_merged/missing.csv` | 72 | `1c5c2b02fad200d8a5afbd578c1ed1f76ffade1195ce5f5a6d5583c31f4dbc1f` |
| `eda_merged/summary.json` | 1252 | `d5a14fad1257752ba68be8d62d2ba3970ddb19898fcf71286cfaff71a693afc2` |
| `features.parquet` | 14457921 | `5a6679e27e011c9b7831795194d00a35b151299284b80666402e494c6587113e` |
| `features_manifest.json` | 4665 | `5c2da269a1171961da685f5056dda31aacdffb80871647696e95c1222e6f701d` |
