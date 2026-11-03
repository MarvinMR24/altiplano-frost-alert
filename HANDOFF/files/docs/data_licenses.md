# Data licenses and attribution

All input data comes from the Copernicus Climate Change Service (C3S) Climate Data Store (CDS) and is licensed under CC-BY 4.0.

| Dataset | DOI | Used for |
|---|---|---|
| ERA5-Land hourly time-series data from 1950 to present | [10.24381/ee82e357](https://doi.org/10.24381/ee82e357) | Hourly features and the frost label |
| Agrometeorological indicators time-series from 1979 to present derived from reanalysis (AgERA5) | [10.24381/f9c1f09d](https://doi.org/10.24381/f9c1f09d) | Daily cloud cover (feature, 1 day lag) and night minimum temperature (label cross-check only) |

## Attribution

Generated using Copernicus Climate Change Service information [2026].

## Disclaimer

Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains.

## Notes

- Raw and processed data are not committed to git. They are versioned with DVC and stored in the project's DagsHub remote.
- Both datasets are reanalysis products (a weather model combined with assimilated observations), not raw satellite imagery.
