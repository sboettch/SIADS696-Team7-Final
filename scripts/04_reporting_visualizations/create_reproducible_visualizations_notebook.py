#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import textwrap

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notebooks" / "06_visualization_generation" / "Final_Report_Reproducible_Visualizations.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


cells = [
    md(
        """
        # Final Report Reproducible Visualizations

        This notebook regenerates the final-report visualizations from data and derived outputs stored in this repository.

        It is intended to make the report figures auditable: every plot is produced from project files under `data/` or `outputs/`, then saved to `outputs/visualizations/reproducible_report_figures/`.
        """
    ),
    code(
        """
        from pathlib import Path
        import re

        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
        import seaborn as sns

        try:
            import geopandas as gpd
        except ImportError:
            gpd = None

        sns.set_theme(style="whitegrid", context="notebook")

        cwd = Path.cwd().resolve()
        ROOT = next(
            (p for p in [cwd, *cwd.parents] if (p / "data").exists() and (p / "outputs").exists()),
            cwd,
        )
        FIG_DIR = ROOT / "outputs" / "visualizations" / "reproducible_report_figures"
        FIG_DIR.mkdir(parents=True, exist_ok=True)

        RUBRIC = ROOT / "outputs" / "modeling" / "rubric_completion"
        PRIMARY = ROOT / "outputs" / "modeling" / "primary_notebook"

        print(f"Repository root: {ROOT}")
        print(f"Figure output directory: {FIG_DIR}")
        """
    ),
    md("## Load Project Data"),
    code(
        """
        metrics = pd.read_csv(RUBRIC / "supervised_cv_metrics_with_sd.csv")
        predictions = pd.read_csv(RUBRIC / "best_rf_holdout_predictions.csv", dtype={"geoid": str})
        importance = pd.read_csv(RUBRIC / "rf_feature_importance.csv")
        ablation = pd.read_csv(RUBRIC / "rf_feature_family_ablation.csv")
        sensitivity = pd.read_csv(RUBRIC / "rf_sensitivity_grid.csv")
        unsup_search = pd.read_csv(RUBRIC / "unsupervised_method_search.csv")
        unsup_assign = pd.read_csv(RUBRIC / "unsupervised_two_method_assignments.csv", dtype={"geoid": str})
        db_profile = pd.read_csv(RUBRIC / "dbscan_cluster_profile.csv")
        km_profile = pd.read_csv(RUBRIC / "kmeans_cluster_profile.csv")

        county_panel = pd.read_csv(ROOT / "data" / "processed" / "county_panel_enriched.csv", dtype={"geoid": str})

        predictions["geoid"] = predictions["geoid"].str.zfill(5)
        unsup_assign["geoid"] = unsup_assign["geoid"].str.zfill(5)

        display(metrics)
        display(unsup_search.tail())
        """
    ),
    md("## Helper Functions"),
    code(
        """
        def savefig(name, width=8, height=5):
            path = FIG_DIR / name
            plt.gcf().set_size_inches(width, height)
            plt.tight_layout()
            plt.savefig(path, dpi=220, bbox_inches="tight")
            print(f"saved {path.relative_to(ROOT)}")
            return path

        def clean_label(value):
            return str(value).replace("_", " ").title()
        """
    ),
    md("## Supervised Figure 1: Model Comparison With Cross-Validation"),
    code(
        """
        plot_df = metrics.sort_values("holdout_rmse").copy()
        order = plot_df["model"].tolist()

        fig, ax = plt.subplots(figsize=(9, 5))
        x = np.arange(len(plot_df))
        ax.bar(x - 0.18, plot_df["holdout_rmse"], width=0.36, label="Holdout RMSE", color="#4C78A8")
        ax.bar(x + 0.18, plot_df["cv_rmse_mean"], width=0.36, yerr=plot_df["cv_rmse_sd"], capsize=4,
               label="CV RMSE mean +/- SD", color="#F58518", alpha=0.9)
        ax.set_xticks(x)
        ax.set_xticklabels(order, rotation=25, ha="right")
        ax.set_ylabel("RMSE")
        ax.set_title("Supervised model comparison")
        ax.legend()
        savefig("figure_01_supervised_model_comparison.png", 9, 5)
        plt.show()
        """
    ),
    md("## Supervised Figure 2: Prediction Error Pattern"),
    code(
        """
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))

        sns.scatterplot(
            data=predictions,
            x="next_year_fmd",
            y="prediction",
            hue="abs_residual",
            palette="viridis",
            s=28,
            linewidth=0,
            ax=axes[0],
            legend=False,
        )
        lo = min(predictions["next_year_fmd"].min(), predictions["prediction"].min())
        hi = max(predictions["next_year_fmd"].max(), predictions["prediction"].max())
        axes[0].plot([lo, hi], [lo, hi], color="black", linewidth=1, linestyle="--")
        axes[0].set_xlabel("Actual next-year FMD")
        axes[0].set_ylabel("Predicted next-year FMD")
        axes[0].set_title("Predicted vs. actual")

        sns.histplot(predictions["residual"], bins=35, kde=True, color="#4C78A8", ax=axes[1])
        axes[1].axvline(0, color="black", linewidth=1)
        axes[1].set_xlabel("Residual (actual - predicted)")
        axes[1].set_title("Residual distribution")

        savefig("figure_02_predictions_residuals.png", 11, 4.8)
        plt.show()
        """
    ),
    md("## Supervised Figure 3: Geographic Residual Map"),
    code(
        """
        if gpd is None:
            print("geopandas is not installed; skipping residual map.")
        else:
            census_zip = ROOT / "data" / "raw" / "census_geography" / "cb_2023_us_county_500k.zip"
            if not census_zip.exists():
                census_zip = ROOT / "data" / "raw" / "census" / "cb_2023_us_county_500k.zip"
            if not census_zip.exists():
                raise FileNotFoundError(f"Missing Census county boundary zip: {census_zip}")

            counties = gpd.read_file(f"zip://{census_zip}")
            counties["GEOID"] = counties["GEOID"].astype(str).str.zfill(5)
            lower_48_plus_dc = {
                "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
                "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
                "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
                "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
                "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
            }
            counties = counties[counties["STUSPS"].isin(lower_48_plus_dc)].copy()
            mapped = counties.merge(predictions, left_on="GEOID", right_on="geoid", how="left")
            mapped = mapped.to_crs("EPSG:5070")

            fig, ax = plt.subplots(figsize=(11, 6.2))
            mapped.plot(
                column="residual",
                cmap="RdBu_r",
                legend=True,
                legend_kwds={"label": "Residual (actual - predicted)", "shrink": 0.58, "pad": 0.015},
                missing_kwds={"color": "lightgrey", "label": "No prediction"},
                ax=ax,
                linewidth=0.05,
                edgecolor="white",
            )
            minx, miny, maxx, maxy = mapped.total_bounds
            ax.set_xlim(minx - 80_000, maxx + 80_000)
            ax.set_ylim(miny - 80_000, maxy + 80_000)
            ax.set_axis_off()
            ax.set_title("Random Forest holdout residuals by county\\npositive = actual FMD higher than predicted")
            savefig("figure_03_residual_map.png", 11, 6.2)
            plt.show()
        """
    ),
    md("## Supervised Figure 4: Random Forest Feature Importance"),
    code(
        """
        top = importance.head(15).iloc[::-1]
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.barplot(data=top, x="importance", y="feature", hue="family", dodge=False, ax=ax)
        ax.set_xlabel("Impurity-based importance")
        ax.set_ylabel("")
        ax.set_title("Top Random Forest feature importances")
        ax.legend(loc="lower right", fontsize=8)
        savefig("figure_04_rf_feature_importance.png", 8, 6)
        plt.show()
        """
    ),
    md("## Supervised Figure 5: Feature-Family Ablation"),
    code(
        """
        plot_df = ablation[ablation["removed_family"] != "None (full model)"].sort_values("rmse_delta")
        fig, ax = plt.subplots(figsize=(8, 4.8))
        sns.barplot(data=plot_df, x="rmse_delta", y="removed_family", color="#4C78A8", ax=ax)
        ax.axvline(0, color="black", linewidth=1)
        ax.set_xlabel("RMSE change after removing feature family")
        ax.set_ylabel("")
        ax.set_title("Random Forest family ablation")
        savefig("figure_05_rf_ablation.png", 8, 4.8)
        plt.show()
        """
    ),
    md("## Supervised Figure 6: Random Forest Sensitivity"),
    code(
        """
        sens = sensitivity.copy()
        sens["max_features"] = sens["max_features"].astype(str)
        fig, ax = plt.subplots(figsize=(8, 4.8))
        sns.lineplot(data=sens, x="min_samples_leaf", y="holdout_rmse", hue="max_features", marker="o", ax=ax)
        ax.set_xlabel("min_samples_leaf")
        ax.set_ylabel("Holdout RMSE")
        ax.set_title("Random Forest sensitivity to hyperparameters")
        savefig("figure_06_rf_sensitivity.png", 8, 4.8)
        plt.show()
        """
    ),
    md("## Unsupervised Figure 1: DBSCAN PCA Scatter"),
    code(
        """
        fig, ax = plt.subplots(figsize=(8, 5.5))
        scatter = sns.scatterplot(
            data=unsup_assign,
            x="pca_1",
            y="pca_2",
            hue="dbscan_cluster",
            palette="tab10",
            s=26,
            linewidth=0,
            ax=ax,
        )
        ax.set_title("DBSCAN clusters on PCA embedding")
        ax.set_xlabel("PCA 1")
        ax.set_ylabel("PCA 2")
        ax.legend(title="DBSCAN cluster", bbox_to_anchor=(1.02, 1), loc="upper left")
        savefig("figure_07_dbscan_pca_scatter.png", 8, 5.5)
        plt.show()
        """
    ),
    md("## Unsupervised Figure 2: DBSCAN Cluster Profiles"),
    code(
        """
        profile_cols = [c for c in db_profile.columns if c.startswith("avg_") and c != "avg_fmd"]
        db_long = db_profile.melt(id_vars=["dbscan_cluster"], value_vars=profile_cols, var_name="feature", value_name="value")
        db_long["feature"] = db_long["feature"].str.replace("avg_", "", regex=False).map(clean_label)

        fig, ax = plt.subplots(figsize=(9, 5))
        sns.barplot(data=db_long, x="feature", y="value", hue="dbscan_cluster", ax=ax)
        ax.set_title("DBSCAN cluster profiles")
        ax.set_xlabel("")
        ax.set_ylabel("Average value")
        ax.tick_params(axis="x", rotation=30)
        ax.legend(title="Cluster")
        savefig("figure_08_dbscan_cluster_profile.png", 9, 5)
        plt.show()
        """
    ),
    md("## Unsupervised Figure 3: K-Means PCA Scatter"),
    code(
        """
        fig, ax = plt.subplots(figsize=(8, 5.5))
        sns.scatterplot(
            data=unsup_assign,
            x="pca_1",
            y="pca_2",
            hue="kmeans_cluster",
            palette="Set2",
            s=26,
            linewidth=0,
            ax=ax,
        )
        ax.set_title("K-Means clusters on PCA embedding")
        ax.set_xlabel("PCA 1")
        ax.set_ylabel("PCA 2")
        ax.legend(title="K-Means cluster", bbox_to_anchor=(1.02, 1), loc="upper left")
        savefig("figure_09_kmeans_pca_scatter.png", 8, 5.5)
        plt.show()
        """
    ),
    md("## Unsupervised Figure 4: K-Means Cluster Profiles"),
    code(
        """
        profile_cols = [c for c in km_profile.columns if c.startswith("avg_") and c != "avg_fmd"]
        km_long = km_profile.melt(id_vars=["kmeans_cluster"], value_vars=profile_cols, var_name="feature", value_name="value")
        km_long["feature"] = km_long["feature"].str.replace("avg_", "", regex=False).map(clean_label)

        fig, ax = plt.subplots(figsize=(9, 5))
        sns.barplot(data=km_long, x="feature", y="value", hue="kmeans_cluster", ax=ax)
        ax.set_title("K-Means cluster profiles")
        ax.set_xlabel("")
        ax.set_ylabel("Average value")
        ax.tick_params(axis="x", rotation=30)
        ax.legend(title="Cluster")
        savefig("figure_10_kmeans_cluster_profile.png", 9, 5)
        plt.show()
        """
    ),
    md("## Unsupervised Sensitivity Figure: Parameter Search"),
    code(
        """
        search = unsup_search.copy()
        dbscan = search[search["method"].eq("DBSCAN")].copy()
        dbscan["eps"] = dbscan["params"].str.extract(r"eps=([0-9.]+)").astype(float)
        dbscan["min_samples"] = dbscan["params"].str.extract(r"min_samples=([0-9]+)").astype(int)

        kmeans = search[search["method"].eq("KMeans")].copy()
        kmeans["k"] = kmeans["params"].str.extract(r"k=([0-9]+)").astype(int)

        dbscan_n = len(dbscan)
        kmeans_n = len(kmeans)
        print(f"DBSCAN settings: {dbscan_n}; K-Means settings: {kmeans_n}; total search rows: {dbscan_n + kmeans_n}")

        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        sns.lineplot(data=dbscan, x="eps", y="silhouette_embedding", hue="min_samples", marker="o", ax=axes[0])
        axes[0].set_title(f"DBSCAN sensitivity search ({dbscan_n} settings)")
        axes[0].set_ylabel("Silhouette on embedding")
        axes[0].set_xlabel("eps")

        sns.lineplot(data=kmeans, x="k", y="silhouette_embedding", marker="o", color="#54A24B", ax=axes[1])
        axes[1].set_title(f"K-Means k sensitivity search ({kmeans_n} settings)")
        axes[1].set_ylabel("Silhouette on embedding")
        axes[1].set_xlabel("k")

        savefig("figure_11_unsupervised_parameter_search.png", 12, 4.8)
        plt.show()
        """
    ),
    md("## Generated Figure Manifest"),
    code(
        """
        generated_figures = [
            "figure_01_supervised_model_comparison.png",
            "figure_02_predictions_residuals.png",
            "figure_03_residual_map.png",
            "figure_04_rf_feature_importance.png",
            "figure_05_rf_ablation.png",
            "figure_06_rf_sensitivity.png",
            "figure_07_dbscan_pca_scatter.png",
            "figure_08_dbscan_cluster_profile.png",
            "figure_09_kmeans_pca_scatter.png",
            "figure_10_kmeans_cluster_profile.png",
            "figure_11_unsupervised_parameter_search.png",
        ]

        missing = [name for name in generated_figures if not (FIG_DIR / name).exists()]
        if missing:
            raise FileNotFoundError(f"Missing generated figure files: {missing}")

        manifest = pd.DataFrame(
            {
                "figure_file": generated_figures,
                "source": "Generated by notebooks/06_visualization_generation/Final_Report_Reproducible_Visualizations.ipynb from project data/outputs",
            }
        )
        manifest.to_csv(FIG_DIR / "figure_manifest.csv", index=False)
        display(manifest)
        """
    ),
]

nb = nbf.v4.new_notebook(
    cells=cells,
    metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
)

OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print(OUT)
