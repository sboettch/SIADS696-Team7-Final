#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import f_oneway
from sklearn.base import clone
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.metrics import (
    calinski_harabasz_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    silhouette_score,
)
from sklearn.model_selection import GridSearchCV, GroupKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_DIR = Path.cwd()
OUT = PROJECT_DIR / "outputs" / "modeling" / "rubric_completion"
OUT.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42


def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def model_pipeline(model, scale=False):
    steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("scale", StandardScaler()))
    steps.append(("model", model))
    return Pipeline(steps)


def load_supervised():
    df = pd.read_csv(PROJECT_DIR / "data" / "processed" / "county_panel_enriched.csv")
    df["geoid"] = df["geoid"].astype(str).str.zfill(5)
    for col in df.select_dtypes(include=[np.number]).columns:
        df.loc[df[col] <= -1e8, col] = np.nan
    df = df.sort_values(["geoid", "year"]).reset_index(drop=True)
    df["next_year"] = df.groupby("geoid")["year"].shift(-1)
    df["next_year_fmd"] = df.groupby("geoid")["mental_health_prevalence"].shift(-1)
    sup = df[df["next_year"].eq(df["year"] + 1)].copy()
    sup["next_year"] = sup["next_year"].astype(int)
    for frame in [sup, df]:
        if "total_population" in frame.columns:
            frame["total_population_numeric"] = (
                frame["total_population"].astype(str).str.replace(",", "", regex=False).replace("nan", np.nan).astype(float)
            )
    exclude = {
        "mental_health_prevalence",
        "lower_ci",
        "upper_ci",
        "next_year_fmd",
        "next_year",
        "acs_source_year",
    }
    id_cols = {"year"}
    numeric_cols = sup.select_dtypes(include=[np.number]).columns.tolist()
    features = [c for c in numeric_cols if c not in exclude | id_cols]
    train = sup[sup["year"] < sup["year"].max()].copy()
    test = sup[sup["year"] == sup["year"].max()].copy()
    return df, sup, train, test, features


def feature_family(col):
    low = col.lower()
    if col.startswith("daily_aqi_"):
        return "Daily AQI exposure"
    if "temp" in low or "precip" in low:
        return "Climate"
    if col.startswith("pct_") and col not in {
        "pct_less_than_hs",
        "pct_hs_or_higher",
        "pct_bachelors_or_higher",
        "pct_uninsured",
        "pct_insured",
    }:
        return "Industry composition"
    if col in {"pct_less_than_hs", "pct_hs_or_higher", "pct_bachelors_or_higher", "pct_uninsured", "pct_insured"}:
        return "Education and health access"
    if col in {"median_income", "poverty_count", "population", "unemployed_count", "total_population_numeric"} or col.startswith("acs_"):
        return "Socioeconomic scale"
    if (
        "aqi" in low
        or "ozone" in low
        or "pm2.5" in low
        or "pm10" in low
        or "unhealthy" in low
        or "hazardous" in low
        or "moderate" in low
        or low in {"days co", "days no2", "days pm2.5", "days pm10", "days ozone", "good days", "moderate days"}
    ):
        return "Annual AQI"
    return "Other"


def supervised_analyses():
    enriched, sup, train, test, features = load_supervised()
    X_train, y_train = train[features], train["next_year_fmd"]
    X_test, y_test = test[features], test["next_year_fmd"]
    groups = train["year"]
    cv = GroupKFold(n_splits=train["year"].nunique())
    scoring = {"rmse": "neg_root_mean_squared_error", "mae": "neg_mean_absolute_error", "r2": "r2"}

    models = {
        "Dummy mean baseline": model_pipeline(DummyRegressor(strategy="mean")),
        "ElasticNet tuned": GridSearchCV(
            model_pipeline(ElasticNet(max_iter=50_000, random_state=RANDOM_STATE), scale=True),
            {"model__alpha": [0.001, 0.01, 0.1, 1, 10], "model__l1_ratio": [0.1, 0.5, 0.9]},
            scoring="neg_root_mean_squared_error",
            cv=cv,
            n_jobs=-1,
        ),
        "Random Forest tuned": GridSearchCV(
            model_pipeline(RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1)),
            {
                "model__n_estimators": [250],
                "model__max_features": ["sqrt", 0.7],
                "model__min_samples_leaf": [1, 3, 8],
            },
            scoring="neg_root_mean_squared_error",
            cv=cv,
            n_jobs=-1,
        ),
        "Gradient Boosting tuned": GridSearchCV(
            model_pipeline(GradientBoostingRegressor(random_state=RANDOM_STATE)),
            {
                "model__n_estimators": [100, 250],
                "model__learning_rate": [0.03, 0.07, 0.1],
                "model__max_depth": [2, 3],
            },
            scoring="neg_root_mean_squared_error",
            cv=cv,
            n_jobs=-1,
        ),
    }

    rows = []
    fitted = {}
    for name, estimator in models.items():
        if isinstance(estimator, GridSearchCV):
            estimator.fit(X_train, y_train, groups=groups)
            fitted_est = estimator.best_estimator_
            best_params = estimator.best_params_
            cv_rmse_mean = -estimator.best_score_
            cv_scores = cross_validate(fitted_est, X_train, y_train, cv=cv, groups=groups, scoring=scoring, n_jobs=-1)
        else:
            fitted_est = estimator.fit(X_train, y_train)
            best_params = {}
            cv_scores = cross_validate(estimator, X_train, y_train, cv=cv, groups=groups, scoring=scoring, n_jobs=-1)
            cv_rmse_mean = -cv_scores["test_rmse"].mean()
        pred = fitted_est.predict(X_test)
        rows.append(
            {
                "model": name,
                "holdout_rmse": rmse(y_test, pred),
                "holdout_mae": mean_absolute_error(y_test, pred),
                "holdout_r2": r2_score(y_test, pred),
                "cv_rmse_mean": cv_rmse_mean,
                "cv_rmse_sd": cv_scores["test_rmse"].std(),
                "cv_mae_mean": -cv_scores["test_mae"].mean(),
                "cv_mae_sd": cv_scores["test_mae"].std(),
                "cv_r2_mean": cv_scores["test_r2"].mean(),
                "cv_r2_sd": cv_scores["test_r2"].std(),
                "best_params": str(best_params),
            }
        )
        fitted[name] = fitted_est

    metrics = pd.DataFrame(rows).sort_values("holdout_rmse")
    metrics.to_csv(OUT / "supervised_cv_metrics_with_sd.csv", index=False)

    best_rf = fitted["Random Forest tuned"]
    rf_model = best_rf.named_steps["model"]
    importance = pd.DataFrame({"feature": features, "importance": rf_model.feature_importances_})
    importance["family"] = importance["feature"].map(feature_family)
    importance = importance.sort_values("importance", ascending=False)
    importance.to_csv(OUT / "rf_feature_importance.csv", index=False)

    plt.figure(figsize=(8, 6))
    sns.barplot(data=importance.head(15).iloc[::-1], x="importance", y="feature", hue="family", dodge=False)
    plt.title("Top Random Forest feature importances")
    plt.xlabel("Impurity-based importance")
    plt.ylabel("")
    plt.legend(loc="lower right", fontsize=7)
    plt.tight_layout()
    plt.savefig(OUT / "figure_rf_feature_importance.png", dpi=200)
    plt.close()

    full_pred = best_rf.predict(X_test)
    full_rmse = rmse(y_test, full_pred)
    families = sorted(set(map(feature_family, features)))
    ablation_rows = [{"removed_family": "None (full model)", "features_removed": 0, "holdout_rmse": full_rmse, "rmse_delta": 0.0}]
    base_params = rf_model.get_params()
    base_params.pop("n_jobs", None)
    base_params.pop("random_state", None)
    for fam in families:
        keep = [c for c in features if feature_family(c) != fam]
        model = model_pipeline(RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1, **base_params))
        model.fit(train[keep], y_train)
        pred = model.predict(test[keep])
        score = rmse(y_test, pred)
        ablation_rows.append(
            {
                "removed_family": fam,
                "features_removed": len(features) - len(keep),
                "holdout_rmse": score,
                "rmse_delta": score - full_rmse,
            }
        )
    ablation = pd.DataFrame(ablation_rows).sort_values("rmse_delta", ascending=False)
    ablation.to_csv(OUT / "rf_feature_family_ablation.csv", index=False)

    plt.figure(figsize=(8, 4.8))
    plot = ablation[ablation["removed_family"] != "None (full model)"].sort_values("rmse_delta")
    sns.barplot(data=plot, x="rmse_delta", y="removed_family", color="#4C78A8")
    plt.axvline(0, color="black", linewidth=1)
    plt.title("Random Forest family ablation")
    plt.xlabel("RMSE change after removing feature family")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(OUT / "figure_rf_ablation.png", dpi=200)
    plt.close()

    sensitivity_rows = []
    for min_leaf in [1, 3, 8, 15]:
        for max_features in ["sqrt", 0.5, 0.7, 1.0]:
            model = model_pipeline(
                RandomForestRegressor(
                    n_estimators=250,
                    min_samples_leaf=min_leaf,
                    max_features=max_features,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                )
            )
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            sensitivity_rows.append(
                {
                    "min_samples_leaf": min_leaf,
                    "max_features": max_features,
                    "holdout_rmse": rmse(y_test, pred),
                    "holdout_mae": mean_absolute_error(y_test, pred),
                    "holdout_r2": r2_score(y_test, pred),
                }
            )
    sensitivity = pd.DataFrame(sensitivity_rows).sort_values("holdout_rmse")
    sensitivity.to_csv(OUT / "rf_sensitivity_grid.csv", index=False)

    best_pred_df = test[["geoid", "county_name", "state_name", "year", "next_year", "next_year_fmd"]].copy()
    best_pred_df["prediction"] = full_pred
    best_pred_df["residual"] = best_pred_df["next_year_fmd"] - best_pred_df["prediction"]
    best_pred_df["abs_residual"] = best_pred_df["residual"].abs()
    fail = best_pred_df.sort_values("abs_residual", ascending=False).head(12).copy()
    fail["failure_category"] = np.select(
        [
            fail["state_name"].eq("West Virginia"),
            fail["residual"].gt(4),
            fail["residual"].lt(-2),
        ],
        [
            "Appalachian high-FMD underprediction",
            "High-distress tail underprediction",
            "Overprediction / low-FMD county",
        ],
        default="Large residual outlier",
    )
    fail.to_csv(OUT / "supervised_failure_examples.csv", index=False)
    best_pred_df.to_csv(OUT / "best_rf_holdout_predictions.csv", index=False)
    return enriched, features


def unsupervised_analyses(enriched, supervised_features):
    latest = enriched[enriched["year"].eq(enriched["year"].max())].copy()
    latest["geoid"] = latest["geoid"].astype(str).str.zfill(5)
    for col in latest.select_dtypes(include=[np.number]).columns:
        latest.loc[latest[col] <= -1e8, col] = np.nan
    exclude = {"mental_health_prevalence", "lower_ci", "upper_ci", "year", "acs_source_year", "next_year", "next_year_fmd"}
    numeric_cols = latest.select_dtypes(include=[np.number]).columns.tolist()
    features = [c for c in numeric_cols if c not in exclude]
    X = latest[features]
    X_scaled = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]).fit_transform(X)
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    embed = pca.fit_transform(X_scaled)
    latest["pca_1"] = embed[:, 0]
    latest["pca_2"] = embed[:, 1]

    method_rows = []
    # DBSCAN search
    best_db = None
    for eps in np.round(np.linspace(0.15, 2.0, 14), 2):
        for min_samples in [5, 10, 20, 35, 50]:
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(embed)
            non_noise = labels != -1
            n_clusters = len(set(labels[non_noise]))
            noise_pct = 1 - non_noise.mean()
            sil_embed = np.nan
            sil_scaled = np.nan
            if n_clusters >= 2 and non_noise.sum() > n_clusters:
                sil_embed = silhouette_score(embed[non_noise], labels[non_noise])
                sil_scaled = silhouette_score(X_scaled[non_noise], labels[non_noise])
            row = {
                "method": "DBSCAN",
                "params": f"eps={eps}, min_samples={min_samples}",
                "clusters": n_clusters,
                "noise_pct": noise_pct,
                "silhouette_embedding": sil_embed,
                "silhouette_scaled_features": sil_scaled,
            }
            method_rows.append(row)
            if n_clusters >= 2 and 2 <= n_clusters <= 12:
                if best_db is None or (np.nan_to_num(sil_embed, nan=-99), np.nan_to_num(sil_scaled, nan=-99)) > (
                    np.nan_to_num(best_db[0]["silhouette_embedding"], nan=-99),
                    np.nan_to_num(best_db[0]["silhouette_scaled_features"], nan=-99),
                ):
                    best_db = (row, labels)
    if best_db is None:
        db_rows = [r for r in method_rows if r["method"] == "DBSCAN"]
        row = sorted(db_rows, key=lambda r: (r["clusters"], -r["noise_pct"]), reverse=True)[0]
        eps = float(row["params"].split(",")[0].split("=")[1])
        min_samples = int(row["params"].split("=")[2])
        db_labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(embed)
    else:
        row, db_labels = best_db

    # KMeans search
    best_km = None
    for k in range(2, 7):
        labels = KMeans(n_clusters=k, n_init=25, random_state=RANDOM_STATE).fit_predict(X_scaled)
        sil_embed = silhouette_score(embed, labels)
        sil_scaled = silhouette_score(X_scaled, labels)
        ch = calinski_harabasz_score(X_scaled, labels)
        row = {
            "method": "KMeans",
            "params": f"k={k}",
            "clusters": k,
            "noise_pct": 0.0,
            "silhouette_embedding": sil_embed,
            "silhouette_scaled_features": sil_scaled,
            "calinski_harabasz": ch,
        }
        method_rows.append(row)
        if best_km is None or sil_scaled > best_km[0]["silhouette_scaled_features"]:
            best_km = (row, labels)

    method_df = pd.DataFrame(method_rows)
    method_df.to_csv(OUT / "unsupervised_method_search.csv", index=False)
    best_methods = pd.DataFrame([best_db[0] if best_db else {}, best_km[0]]).fillna("")
    best_methods.to_csv(OUT / "unsupervised_method_comparison.csv", index=False)

    latest["dbscan_cluster"] = db_labels
    latest["kmeans_cluster"] = best_km[1]
    latest[["geoid", "county_name", "state_name", "mental_health_prevalence", "pca_1", "pca_2", "dbscan_cluster", "kmeans_cluster"]].to_csv(
        OUT / "unsupervised_two_method_assignments.csv", index=False
    )

    anova_rows = []
    for method, col in [("DBSCAN", "dbscan_cluster"), ("KMeans", "kmeans_cluster")]:
        groups = [g["mental_health_prevalence"].dropna().values for _, g in latest[latest[col] != -1].groupby(col)]
        if len(groups) >= 2:
            f_stat, p_val = f_oneway(*groups)
        else:
            f_stat, p_val = np.nan, np.nan
        anova_rows.append({"method": method, "f_stat": f_stat, "p_value": p_val, "groups": len(groups)})
    pd.DataFrame(anova_rows).to_csv(OUT / "unsupervised_fmd_anova.csv", index=False)

    for method, col, filename in [
        ("DBSCAN", "dbscan_cluster", "figure_dbscan_pca_scatter.png"),
        ("K-Means", "kmeans_cluster", "figure_kmeans_pca_scatter.png"),
    ]:
        plt.figure(figsize=(8, 5.5))
        sns.scatterplot(data=latest, x="pca_1", y="pca_2", hue=col, palette="tab10", s=18, linewidth=0, alpha=0.8)
        plt.title(f"{method} clusters on PCA embedding")
        plt.xlabel("PCA 1")
        plt.ylabel("PCA 2")
        plt.legend(title="Cluster", bbox_to_anchor=(1.02, 1), loc="upper left")
        plt.tight_layout()
        plt.savefig(OUT / filename, dpi=200)
        plt.close()

        profile = latest.groupby(col).agg(
            counties=("geoid", "count"),
            avg_fmd=("mental_health_prevalence", "mean"),
            avg_median_aqi=("Median AQI", "mean"),
            avg_max_aqi=("Max AQI", "mean"),
            avg_pct_uninsured=("pct_uninsured", "mean"),
            avg_pct_bachelors_or_higher=("pct_bachelors_or_higher", "mean"),
            avg_temp_anomaly=("annual_temp_anomaly_f", "mean"),
            avg_pct_manufacturing=("pct_manufacturing", "mean"),
        )
        profile.to_csv(OUT / f"{col}_profile.csv")
        plot_profile = profile[["avg_fmd", "avg_median_aqi", "avg_pct_uninsured", "avg_pct_bachelors_or_higher", "avg_temp_anomaly", "avg_pct_manufacturing"]].copy()
        plot_profile = plot_profile.apply(lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) else 0)
        plt.figure(figsize=(8.5, 5))
        plot_profile.plot(kind="bar", ax=plt.gca())
        plt.axhline(0, color="black", linewidth=1)
        plt.title(f"{method} standardized cluster profiles")
        plt.xlabel("Cluster")
        plt.ylabel("Standard deviations from method mean")
        plt.legend(fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left")
        plt.tight_layout()
        plt.savefig(OUT / f"figure_{col}_profile.png", dpi=200)
        plt.close()


def main():
    enriched, features = supervised_analyses()
    unsupervised_analyses(enriched, features)
    print(OUT)


if __name__ == "__main__":
    main()
