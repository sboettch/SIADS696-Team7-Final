# Data

The raw folder is organized by source:

- `raw/cdc_places/`
- `raw/epa_airdata/`
- `raw/acs/`
- `raw/noaa/`
- `raw/census_geography/`

Processed files:

- `processed/county_panel_imputed.csv`: imputed county-year panel used for modeling.
- `processed/county_panel_enriched.csv`: enriched final panel with external features.
- `processed/enrichment_coverage_by_year.csv`: coverage audit by year.
- `processed/PLACES_Combined.csv`: combined PLACES outcome data.
