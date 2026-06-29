#!/usr/bin/env python3
"""
Save holdout predictions for all 3 tuned models, then generate the three-panel scatter.
Run from the repo root:  python generate_three_panel.py
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import root_mean_squared_error as rmse, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

RANDOM_STATE = 42
DATA_PATH = "data/processed/county_panel_imputed.csv"
TARGET = "next_year_fmd"
OUT_CSV = "outputs/modeling/rubric_completion/all_model_holdout_predictions.csv"
OUT_PNG = "outputs/visualizations/reproducible_report_figures/figure_01_three_panel_model_accuracy.png"

# ── 1. Load & Prep (mirrors Supervised_FMD_Analysis.ipynb) ──────────────
print("Loading data...")
raw = pd.read_csv(DATA_PATH)
raw = raw.sort_values(["geoid", "year"])
raw["next_year"] = raw.groupby("geoid")["year"].shift(-1)
raw["next_year_fmd"] = raw.groupby("geoid")["mental_health_prevalence"].shift(-1)
raw = raw.dropna(subset=["next_year_fmd"])
raw = raw[raw["next_year"] == raw["year"] + 1]

ID_COLS = ["geoid", "county_name", "state_name", "year", "next_year"]
DROP_COLS = ID_COLS + [TARGET, "mental_health_prevalence"]
feature_cols = [c for c in raw.columns if c not in DROP_COLS and raw[c].dtype in ["float64", "int64"]]

df = raw.dropna(subset=feature_cols + [TARGET])
HOLDOUT_YEAR = df["year"].max()
train_df = df[df["year"] < HOLDOUT_YEAR]
test_df = df[df["year"] == HOLDOUT_YEAR]

X_train, y_train = train_df[feature_cols], train_df[TARGET]
X_test, y_test = test_df[feature_cols], test_df[TARGET]
groups = train_df["year"]
cv = GroupKFold(n_splits=min(5, train_df["year"].nunique()))

print(f"Train: {len(X_train):,} | Test: {len(X_test):,} | Features: {len(feature_cols)}")

# ── 2. Train (same grids as notebook) ───────────────────────────────────
print("Training ElasticNet...", flush=True)
en = GridSearchCV(
    Pipeline([("scale", StandardScaler()),
              ("model", ElasticNet(max_iter=50_000, random_state=RANDOM_STATE))]),
    {"model__alpha": [0.001, 0.01, 0.1, 1.0, 10.0],
     "model__l1_ratio": [0.1, 0.5, 0.9]},
    scoring="neg_root_mean_squared_error", cv=cv, n_jobs=1)
en.fit(X_train, y_train, groups=groups)

print("Training Random Forest...", flush=True)
rf = GridSearchCV(
    RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=1),
    {"n_estimators": [250, 500], "max_features": ["sqrt", 0.7],
     "min_samples_leaf": [1, 3, 8]},
    scoring="neg_root_mean_squared_error", cv=cv, n_jobs=1)
rf.fit(X_train, y_train, groups=groups)

print("Training Gradient Boosting...", flush=True)
gb = GridSearchCV(
    GradientBoostingRegressor(random_state=RANDOM_STATE),
    {"n_estimators": [100, 250], "learning_rate": [0.03, 0.07, 0.1],
     "max_depth": [2, 3]},
    scoring="neg_root_mean_squared_error", cv=cv, n_jobs=1)
gb.fit(X_train, y_train, groups=groups)

# ── 3. Save all predictions to CSV ─────────────────────────────────────
pred_df = test_df[["geoid", "county_name", "state_name", "year", "next_year", TARGET]].copy()
pred_df["pred_elasticnet"] = en.predict(X_test)
pred_df["pred_random_forest"] = rf.predict(X_test)
pred_df["pred_gradient_boosting"] = gb.predict(X_test)
pred_df.to_csv(OUT_CSV, index=False)
print(f"\n✅ Predictions saved: {OUT_CSV}")

# Print metrics
for name, col in [("ElasticNet", "pred_elasticnet"),
                   ("Random Forest", "pred_random_forest"),
                   ("Gradient Boosting", "pred_gradient_boosting")]:
    pred = pred_df[col]
    actual = pred_df[TARGET]
    print(f"  {name}: RMSE={rmse(actual, pred):.3f}, MAE={mean_absolute_error(actual, pred):.3f}, R²={r2_score(actual, pred):.3f}")

# ── 4. Three-panel scatter ──────────────────────────────────────────────
models = [
    ("Tuned ElasticNet", pred_df["pred_elasticnet"].values),
    ("Tuned Random Forest", pred_df["pred_random_forest"].values),
    ("Tuned XGBoost", pred_df["pred_gradient_boosting"].values),
]
y_actual = pred_df[TARGET].values

fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
labels = ["(a)", "(b)", "(c)"]

for ax, (name, pred), lbl in zip(axes, models, labels):
    ax.scatter(y_actual, pred, alpha=0.35, s=14, edgecolors="none", color="#4C72B0")
    lims = [min(y_actual.min(), pred.min()) - 0.5, max(y_actual.max(), pred.max()) + 0.5]
    ax.plot(lims, lims, color="black", linestyle="--", linewidth=1)
    r2 = r2_score(y_actual, pred)
    ax.text(0.05, 0.95,
            f"RMSE = {rmse(y_actual, pred):.2f}\nMAE  = {mean_absolute_error(y_actual, pred):.2f}\nR²   = {r2:.3f}",
            transform=ax.transAxes, va="top", fontsize=10, family="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#cccccc", alpha=0.9))
    ax.set_title(f"{lbl} {name}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Actual Next-Year FMD (%)", fontsize=11)
    if ax == axes[0]:
        ax.set_ylabel("Predicted Next-Year FMD (%)", fontsize=11)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.grid(True, alpha=0.2)

plt.suptitle("Hyperparameter-Tuned Model Accuracy", fontsize=15, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=200, bbox_inches="tight", facecolor="white")
print(f"✅ Figure saved: {OUT_PNG}")
