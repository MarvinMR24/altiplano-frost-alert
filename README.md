# altiplano-frost-alert

## Data notes

- Source: ERA5-Land reanalysis (Copernicus Climate Change Service, ECMWF), dataset `reanalysis-era5-land-timeseries` from the Copernicus Climate Data Store (CDS). Reanalysis combines a weather model with assimilated observations, including satellite data; it is not raw satellite imagery.
- One ERA5-Land grid cell (0.1 degree) per point. CDS area boxes appear to return the cells with S <= lat < N and W < lon <= E. This was inferred from two test requests and confirmed by a third, so each point uses the box [lat0 + 0.1, lon0 - 0.1, lat0, lon0] for its target cell (lat0, lon0), and the download checks that exactly that cell comes back.
- The choice of cell matters. In July 2025 near El Alto, the hours with 2 m temperature at or below 0 C were 92, 66, 68 and 13 in four neighboring cells.

## Future work

Future work: live forecast ingestion. The pipeline currently runs on CDS reanalysis, which is published a few days late, so there is no 'tonight' prediction yet. A forecast source such as the Open-Meteo forecast API could be added later, with care: its free tier is for non-commercial use and limited (about 10,000 weighted calls per day, 5,000 per hour and 600 per minute), a commercial deployment needs a paid plan, and its variables must match the training features (for example it does not provide downward longwave radiation, so that feature would have to be dropped or approximated).
