# SIADS 696 Team 7 Final Repository

This repository contains the complete codebase used for our SIADS 696 final project, including the data-processing pipeline, analysis scripts, reproducible notebooks, visualization generation, and the working report draft.

> **Note:** The final report submitted for the course was finalized collaboratively by Team 7 members in Google Docs and, as such, is not included in this repository. The materials included here represent the reproducible basis for that submission:
>
> - `reports/final/SIADS_696_Team_7_Final_Report.ipynb` contains the report draft and analysis used to prepare the final submission.
> - `notebooks/06_visualization_generation/Final_Report_Reproducible_Visualizations.ipynb` regenerates the figures used throughout the report. The intention is to have reproducible data visualizations rather than orphaned images in our final report.
> - `reports/final/SIADS_696_Team_7_Final_Report_OriginalStyle_RubricReady.docx` represents a recent repository version of the report draft prior to collaborative editing in Google Docs.

---

## At a Glance

### Report Materials

```
reports/final/
├── SIADS_696_Team_7_Final_Report.ipynb
└── SIADS_696_Team_7_Final_Report_OriginalStyle_RubricReady.docx
```

The visualization notebook used to generate the report figures is located at:

```
notebooks/06_visualization_generation/
└── Final_Report_Reproducible_Visualizations.ipynb
```

### Code

The project code is organized by workflow stage:

```
scripts/
├── 01_data_aggregation/
├── 02_cleaning_harmonization/
├── 03_modeling/
└── 04_reporting_visualizations/
```

Reproducible notebooks mirror the same workflow:

```
notebooks/
├── 01_data_aggregation/
├── 02_eda/
├── 03_harmonization/
├── 04_supervised_learning/
├── 05_unsupervised_learning/
└── 06_visualization_generation/
```

### Data

The project data are organized as follows:

```
data/
├── raw/         # Source-specific raw data extracts
└── processed/   # Final modeling panels and coverage checks
```

Supporting documentation is available in:

```
docs/
├── data_sources/          # CDC PLACES, EPA AirData, ACS, NOAA, and Census documentation
└── data_harmonization.md  # Data cleaning, harmonization, imputation, and leakage prevention
```

For tracking purposes/legacy, we have retained older drafts, intermediate outputs, and archived notebooks in:

```
archive/
```

---

## Reproducing the Analysis

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Final Modeling Pipeline

```bash
python scripts/03_modeling/generate_rubric_analyses.py
```

This script reproduces the primary supervised and unsupervised modeling analyses used throughout the project.

### 3. Regenerate Report Figures

```bash
jupyter nbconvert \
  --to notebook \
  --execute notebooks/06_visualization_generation/Final_Report_Reproducible_Visualizations.ipynb \
  --output Final_Report_Reproducible_Visualizations.executed.ipynb \
  --output-dir archive/notebooks/executed_outputs
```

Generated report figures are written to:

```
outputs/visualizations/reproducible_report_figures/
```

---

## Repository Organization

The repository follows our project's end-to-end workflow:

1. Source data
2. Data aggregation and cleaning
3. Data harmonization
4. Supervised learning
5. Unsupervised learning
6. Visualization generation
7. Report drafting

Our reasoning for this structure was to clearly separate raw data, processing scripts, reproducible notebooks, documentation, and report materials while still preserving the complete analysis pipeline from data ingestion through model development, figure generation, and report preparation. (Ultimately, we hope this organization makes it much easier to follow the project from start to finish and to reproduce individual parts of the workflow without having to dig through unrelated files. Thanks!)
