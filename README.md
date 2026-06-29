# SIADS 696 Team 7 Final Clean Repository

This folder is a fresh, cleaned copy of the project materials for the SIADS 696 final submission. It is organized around the actual workflow:

1. source data,
2. aggregation and cleaning,
3. harmonization,
4. supervised learning,
5. unsupervised learning,
6. visualization generation,
7. final reports.

## Quick Map

- `data/raw/`: source-specific raw data extracts.
- `data/processed/`: final modeling panels and coverage checks.
- `docs/data_sources/`: source-by-source notes for CDC PLACES, EPA AirData, ACS, NOAA, and Census geography.
- `docs/data_harmonization.md`: how the data are merged, cleaned, imputed, and leakage-controlled.
- `scripts/01_data_aggregation/`: scripts for CDC PLACES, ACS, and EPA AirData aggregation.
- `scripts/02_cleaning_harmonization/`: enrichment and geographic imputation scripts.
- `scripts/03_modeling/`: supervised and unsupervised rubric-completion analyses.
- `scripts/04_reporting_visualizations/`: report and figure generation scripts.
- `notebooks/01_data_aggregation/`: source-combining notebook.
- `notebooks/02_eda/`: exploratory data analysis.
- `notebooks/03_harmonization/`: harmonization and cleaning notebook.
- `notebooks/04_supervised_learning/`: supervised-learning notebook.
- `notebooks/05_unsupervised_learning/`: unsupervised-learning notebook.
- `notebooks/06_visualization_generation/`: reproducible report-figure notebook.
- `reports/final/`: final report in `.ipynb` and `.docx` form.
- `archive/`: old drafts, executed notebooks, and files not used as the primary final path.

## Reproduce Key Outputs

Install dependencies:

```bash
pip install -r requirements.txt
```

Run final modeling outputs:

```bash
python scripts/03_modeling/generate_rubric_analyses.py
```

Regenerate report figures:

```bash
jupyter nbconvert --to notebook --execute notebooks/06_visualization_generation/Final_Report_Reproducible_Visualizations.ipynb --output Final_Report_Reproducible_Visualizations.executed.ipynb --output-dir archive/notebooks/executed_outputs
```

## Final Report Files

- `reports/final/SIADS_696_Team_7_Final_Report.ipynb`
- `reports/final/SIADS_696_Team_7_Final_Report_OriginalStyle_RubricReady.docx`

The report figures are generated from project data/model outputs and stored in `outputs/visualizations/reproducible_report_figures/`.
