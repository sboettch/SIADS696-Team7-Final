#!/usr/bin/env python3
"""
Generate the three-panel Hyperparameter-Tuned Model Accuracy figure.

Uses the same data loading and model pipeline as generate_rubric_analyses.py
(county_panel_enriched.csv, SimpleImputer + StandardScaler, same HP grids)
to produce numbers consistent with the report.

Run from the repo root:
    python scripts/03_modeling/generate_three_panel_figure.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")

PROJECT_DIR = Path(__file__).resolve().parents[2]   # repo root
OUT_FIG = PROJECT_DIR / "outputs" / "visualizations" / "reproducible_report_figures"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_DATA = PROJECT_DIR / "outputs" / "modeling" / "rubric_completion"
OUT_DATA.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42


def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def model_pipeline(model, scale=False):
    steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("scale", StandardScaler()))
    steps.append(("model", model))
    return Pipeline(steps)


# ── 1. Load data (identical to generate_rubric_analyses.py) ─────────────
print("Loading county_panel_enriched.csv …")
df = pd.read_csv(PROJECT_DIR / "data" / "processed" / "county_panel_enriched.csv")
df["geoid"] = df["geoid"].astype(str).str.zfill(5)
for col in df.select_dtypes(include=[np.number]).columns:
    df.loc[df[col] <= -1e8, col] = np.nan
df = df.sort_values(["geoid", "year"]).reset_index(drop=True)
df["next_year"] = df.groupby("geoid")["year"].shift(-1)
df["next_year_fmd"] = df.groupby("geoid")["mental_health_prevalence"].shift(-1)
sup = df[df["next_year"].eq(df["year"] + 1)].copy()
sup["next_year"] = sup["next_year"].astype(int)
if "total_population" in sup.columns:
    sup["total_population_numeric"] = (
        sup["total_population"].astype(str).str.replace(",", "", regex=False)
        .replace("nan", np.nan).astype(float)
    )

exclude = {"mental_health_prevalence", "lower_ci", "upper_ci",
           "next_year_fmd", "next_year", "acs_source_year"}
id_cols = {"year"}
numeric_cols = sup.select_dtypes(include=[np.number]).columns.tolist()
features = [c for c in numeric_cols if c not in exclude | id_cols]

train = sup[sup["year"] < sup["year"].max()].copy()
test = sup[sup["year"] == sup["year"].max()].copy()

X_train, y_train = train[features], train["next_year_fmd"]
X_test, y_test = test[features], test["next_year_fmd"]
groups = train["year"]
cv = GroupKFold(n_splits=train["year"].nunique())

print(f"  Train: {len(X_train):,} | Test: {len(X_test):,} | Features: {len(features)}")

# ── 2. Train models (same grids as generate_rubric_analyses.py) ─────────
models = {
    "Tuned ElasticNet": GridSearchCV(
        model_pipeline(ElasticNet(max_iter=50_000, random_state=RANDOM_STATE), scale=True),
        {"model__alpha": [0.001, 0.01, 0.1, 1, 10], "model__l1_ratio": [0.1, 0.5, 0.9]},
        scoring="neg_root_mean_squared_error", cv=cv, n_jobs=1,
    ),
    "Tuned Random Forest": GridSearchCV(
        model_pipeline(RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=1)),
        {"model__n_estimators": [250], "model__max_features": ["sqrt", 0.7],
         "model__min_samples_leaf": [1, 3, 8]},
        scoring="neg_root_mean_squared_error", cv=cv, n_jobs=1,
    ),
    "Tuned XGBoost": GridSearchCV(
        model_pipeline(GradientBoostingRegressor(random_state=RANDOM_STATE)),
        {"model__n_estimators": [100, 250], "model__learning_rate": [0.03, 0.07, 0.1],
         "model__max_depth": [2, 3]},
        scoring="neg_root_mean_squared_error", cv=cv, n_jobs=1,
    ),
}

predictions = {}
for name, grid in models.items():
    print(f"Training {name} …", flush=True)
    grid.fit(X_train, y_train, groups=groups)
    pred = grid.best_estimator_.predict(X_test)
    predictions[name] = pred
    print(f"  Best: {grid.best_params_}")
    print(f"  RMSE={rmse(y_test, pred):.3f}  MAE={mean_absolute_error(y_test, pred):.3f}  R²={r2_score(y_test, pred):.3f}")

# ── 3. Save all predictions ────────────────────────────────────────────
pred_df = test[["geoid", "county_name", "state_name", "year", "next_year", "next_year_fmd"]].copy()
pred_df["pred_elasticnet"] = predictions["Tuned ElasticNet"]
pred_df["pred_random_forest"] = predictions["Tuned Random Forest"]
pred_df["pred_gradient_boosting"] = predictions["Tuned XGBoost"]
pred_df.to_csv(OUT_DATA / "all_model_holdout_predictions.csv", index=False)
print(f"\n✅ Predictions saved: {OUT_DATA / 'all_model_holdout_predictions.csv'}")

# ── 4. Three-panel scatter figure ──────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
panel_items = [
    ("(a)", "Tuned ElasticNet"),
    ("(b)", "Tuned Random Forest"),
    ("(c)", "Tuned XGBoost"),
]

for ax, (label, name) in zip(axes, panel_items):
    pred = predictions[name]
    ax.scatter(y_test, pred, alpha=0.35, s=14, edgecolors="none", color="#4C72B0")
    lims = [min(y_test.min(), pred.min()) - 0.5, max(y_test.max(), pred.max()) + 0.5]
    ax.plot(lims, lims, color="black", linestyle="--", linewidth=1)
    r2 = r2_score(y_test, pred)
    ax.text(
        0.05, 0.95,
        f"RMSE = {rmse(y_test, pred):.2f}\nMAE  = {mean_absolute_error(y_test, pred):.2f}\nR²   = {r2:.3f}",
        transform=ax.transAxes, va="top", fontsize=10, family="monospace",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#cccccc", alpha=0.9),
    )
    ax.set_title(f"{label} {name}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Actual Next-Year FMD (%)", fontsize=11)
    if ax is axes[0]:
        ax.set_ylabel("Predicted Next-Year FMD (%)", fontsize=11)
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.grid(True, alpha=0.2)

plt.suptitle("Hyperparameter-Tuned Model Accuracy", fontsize=15, fontweight="bold", y=1.02)
plt.tight_layout()
out_path = OUT_FIG / "figure_01_three_panel_model_accuracy.png"
plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
print(f"✅ Figure saved: {out_path}")
