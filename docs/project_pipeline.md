# Project Pipeline

The project begins with source-specific county-level data, harmonizes those sources into a county-year panel, and then uses that panel for supervised prediction and unsupervised county profiling.

1. CDC PLACES provides the frequent mental distress outcome.
2. EPA AirData provides annual AQI summaries, pollutant-defining days, and daily AQI exposure summaries.
3. ACS provides socioeconomic, education, insurance, and industry context.
4. NOAA provides county climate variables.
5. Census geography provides county boundaries and GEOID-based spatial structure.
6. The enriched panel is cleaned/imputed and then used for modeling.
7. Final figures are regenerated from model-output CSVs, not manually drawn.
