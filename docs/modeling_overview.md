# Modeling Overview

## Supervised Learning

The supervised task predicts next-year frequent mental distress from current-year county features. Active materials:

- `notebooks/04_supervised_learning/Supervised_FMD_Analysis.ipynb`
- `scripts/03_modeling/generate_rubric_analyses.py`
- `outputs/modeling/rubric_completion/supervised_cv_metrics_with_sd.csv`
- `outputs/modeling/rubric_completion/rf_feature_importance.csv`
- `outputs/modeling/rubric_completion/rf_feature_family_ablation.csv`
- `outputs/modeling/rubric_completion/rf_sensitivity_grid.csv`
- `outputs/modeling/rubric_completion/supervised_failure_examples.csv`

## Unsupervised Learning

The unsupervised task clusters counties using non-FMD features and evaluates FMD afterward as a held-out outcome. Active materials:

- `notebooks/05_unsupervised_learning/Unsupervised_FMD_Analysis.ipynb`
- `outputs/modeling/rubric_completion/unsupervised_method_comparison.csv`
- `outputs/modeling/rubric_completion/unsupervised_method_search.csv`
- `outputs/modeling/rubric_completion/unsupervised_fmd_anova.csv`
- `outputs/modeling/rubric_completion/dbscan_cluster_profile.csv`
- `outputs/modeling/rubric_completion/kmeans_cluster_profile.csv`
