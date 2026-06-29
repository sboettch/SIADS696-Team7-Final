# Data Harmonization and Cleaning

## Unit of Analysis

The final unit of analysis is county-year. County GEOID is the preferred merge key. County and state names are retained for interpretability and validation.

## Source Harmonization

- CDC PLACES yearly files are combined into `data/processed/PLACES_Combined.csv`.
- EPA AirData annual county summaries and daily AQI summaries are aligned by county/year.
- ACS enrichment is joined by county/year where available.
- NOAA climate variables are joined by county/year.
- Census county geometry is used for spatial visualization and residual maps.

## Cleaning and Feature Engineering

- Sentinel/missing values are cleaned before modeling.
- Raw counts are converted into rates where needed, including poverty, unemployment, good-air-day ratio, and bad-air-day ratio.
- Missing numeric values are imputed inside modeling pipelines or through the geographic imputation workflow, depending on the feature.
- The supervised target is next-year FMD, created by shifting FMD forward within each county.
- FMD and FMD confidence intervals are excluded from unsupervised clustering to prevent leakage.

## Main Implementation Files

- `scripts/01_data_aggregation/cdc_places/places_agg.py`
- `scripts/01_data_aggregation/epa_airdata/airdata_aiq_agg.py`
- `scripts/01_data_aggregation/acs/download_acs.py`
- `scripts/01_data_aggregation/acs/acs_agg.py`
- `scripts/02_cleaning_harmonization/enrich_county_panel.py`
- `scripts/02_cleaning_harmonization/geo_imputation.py`
- `notebooks/03_harmonization/Harmonization_and_Data_Cleaning.ipynb`
