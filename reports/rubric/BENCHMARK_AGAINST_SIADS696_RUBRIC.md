# Benchmark Against SIADS 696 Final Report Rubric

Benchmark source: SIADS 696 Final Report Requirements Google Doc, exported June 28, 2026.

Primary reviewed artifacts:

- `notebooks/SIADS_696_Team_7_Final_Report.ipynb`
- `report/SIADS_696_Team_7_Final_Report_current_cleaned.docx`
- `report/SIADS_696_Team_7_Final_Report_rubric_cleaned.docx`
- `outputs/rubric_completion/`
- `notebooks/Supervised_Unsupervised_FMD_Analysis.ipynb`
- `data/processed/county_panel_enriched.csv`

## Executive Summary

The project package is substantially aligned with the rubric. The strongest submission candidate is the rubric-cleaned report draft because it directly includes CV mean/SD, feature importance, ablation, sensitivity analysis, failure examples, DBSCAN, K-Means, and four unsupervised visuals. The current-cleaned team report has richer prose and more figures, but its supervised model comparison table still needs CV standard deviations to fully satisfy the rubric.

The notebook-form final report, `notebooks/SIADS_696_Team_7_Final_Report.ipynb`, is organized as direct question/answer responses to the rubric prompts and includes explicit integration of Jaeah's EDA work.

Estimated readiness:

- `SIADS_696_Team_7_Final_Report_current_cleaned.docx`: 80-84 / 100 before final link/PDF cleanup.
- `SIADS_696_Team_7_Final_Report_rubric_cleaned.docx`: 86-90 / 100 before final link/PDF cleanup.

The remaining submission blockers are: insert GitHub and Google Doc URLs, export the chosen final report as a self-contained PDF, verify page count is <=15 pages excluding references/appendices, and remove `.DS_Store` files before staging the GitHub repo.

## Rubric Scorecard

| Rubric category | Points | Current-cleaned report | Rubric-cleaned report | Notes |
|---|---:|---:|---:|---|
| Formatting | Required | Mostly aligned | Mostly aligned | Arial/black/single-column structure is present. Need final PDF and page-count check. |
| Introduction | 5 | 4.5 | 4.5 | Problem, impact, motivation, supervised/unsupervised methods, and findings are present. |
| Related Work | 5 | 4.0 | 4.0 | Three studies are present. Could be made more formal and more explicitly contrasted. |
| Data Sources | 5 | 4.0 | 4.5 | Source locations, formats, variables, records, and years are covered. Current-cleaned text should avoid saying only "three sources." |
| Feature Engineering | 6 | 4.5 | 5.0 | Major preprocessing and leakage controls are present. Rubric-cleaned version has cleaner leakage-control framing. |
| Supervised Methods | 8 | 7.0 | 7.5 | Multiple model families are described. Tuning is present. |
| Supervised Overall Evaluation | 8 | 5.5 | 7.5 | Current-cleaned table lacks CV standard deviation. Rubric-cleaned table includes CV RMSE mean and SD. |
| Feature Importance + Ablation | 6 | 5.0 | 5.5 | Both are present. Interpretation could more directly explain why AQI features were weaker. |
| Sensitivity + Tradeoffs | 8 | 6.5 | 7.0 | RF hyperparameter sensitivity and tradeoff language are present. Could expand speed/interpretability tradeoff. |
| Failure Analysis | 5 | 4.0 | 4.5 | Specific high-error records are present. Needs three clearer failure categories for full credit. |
| Unsupervised Methods | 10 | 8.0 | 8.5 | DBSCAN and K-Means are present. Hyperparameter search could be more explicit in main text. |
| Unsupervised Evaluation | 15 | 11.5 | 13.0 | Metrics, ANOVA, and visuals are present. Rubric-cleaned version more clearly has two visuals per method. |
| Discussion | 8 | 7.0 | 7.0 | Explains weak supervised signal, imbalanced clusters, challenges, and future work. |
| Ethics | 4 | 3.5 | 3.5 | Good cautionary notes; could explicitly split Part A vs Part B ethical risks. |
| Statement of Work | 1 | 1.0 | 1.0 | Present. |
| References | 5 | 4.0 | 4.0 | Consistent enough, but add NOAA/Census boundary citations if using them in report. |
| Project Submission | 1 | 0.0 | 0.0 | Needs GitHub URL and Google Doc URL. |

## Highest-Priority Fixes

1. Add project submission links:
   - GitHub repository containing code, PDF report, and data sources.
   - Google Doc version of written report with comments enabled.

2. Pick one final report source:
   - Use `SIADS_696_Team_7_Final_Report_rubric_cleaned.docx` if maximizing rubric coverage is the priority.
   - Use `SIADS_696_Team_7_Final_Report_current_cleaned.docx` if preserving team-authored prose and all current visuals is the priority, but patch in CV SD and clearer two-visual-per-method wording first.

3. Fix the supervised evaluation table in the current-cleaned report if that is the final report:
   - Add `CV RMSE mean` and `CV RMSE SD`.
   - Optionally add `CV R2 mean` and `CV R2 SD`.

4. Make metrics consistent across the final report:
   - Current-cleaned report uses Random Forest holdout RMSE 2.17 in the narrative and 1.98 in later rubric-completion tables.
   - Choose one modeling run and make the narrative, tables, and figures match.

5. Strengthen unsupervised sensitivity:
   - Add a compact DBSCAN `eps/min_samples` search summary or cite `outputs/rubric_completion/unsupervised_method_search.csv`.
   - Add a sentence that K-Means was compared by `k` and selected using silhouette/cluster interpretability.

6. Improve failure-analysis categories:
   - Keep at least three records.
   - Name at least three categories, such as high-distress tail underprediction, Appalachian high-FMD underprediction, rural/sparse-feature underprediction, or monitor/socioeconomic mismatch.

7. Final formatting/submission checks:
   - Export one self-contained PDF.
   - Verify the main report is <=15 pages excluding references/appendices.
   - Confirm all tables and figures are numbered.
   - Remove `.DS_Store` files before staging the GitHub repo.

## Evidence Already Present

The repo contains the key supporting files needed to defend the report:

- `notebooks/Final_Report_Reproducible_Visualizations.ipynb`
- `outputs/reproducible_report_figures/figure_manifest.csv`
- `outputs/rubric_completion/supervised_cv_metrics_with_sd.csv`
- `outputs/rubric_completion/rf_feature_importance.csv`
- `outputs/rubric_completion/rf_feature_family_ablation.csv`
- `outputs/rubric_completion/rf_sensitivity_grid.csv`
- `outputs/rubric_completion/supervised_failure_examples.csv`
- `outputs/rubric_completion/unsupervised_method_comparison.csv`
- `outputs/rubric_completion/unsupervised_method_search.csv`
- `outputs/rubric_completion/unsupervised_fmd_anova.csv`
- `outputs/rubric_completion/figure_dbscan_pca_scatter.png`
- `outputs/rubric_completion/figure_dbscan_cluster_profile.png`
- `outputs/rubric_completion/figure_kmeans_pca_scatter.png`
- `outputs/rubric_completion/figure_kmeans_cluster_profile.png`

## Recommendation

Use the rubric-cleaned report as the final backbone, then borrow the strongest team-authored prose and extra figures from the current-cleaned report only where they improve clarity without reintroducing metric inconsistencies. This gives the safest path to satisfying the rubric.

All final report figures should come from the reproducible visualization notebook or from `scripts/modeling/generate_rubric_analyses.py`. Avoid manually pasted images that cannot be traced to project data.
