import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.neighbors import BallTree

FILE_NAME = "county_panel_imputed.csv"

# K-Nearest-Neighbors algorithm
def knn_impute(gdf, missing_cols, k=10):
    print("Running KNN imputation with K =", k)
    gdf_imputed = gdf.copy()
    for year, group in gdf_imputed.groupby("year"):
        observed = group.dropna(subset=missing_cols)
        missing = group[group[missing_cols].isna().all(axis=1)]

        print("----------------")
        print(year)
        print("Valid Rows:", len(observed))
        print("Rows to be imputed:", len(missing))

        if observed.empty or missing.empty:
            continue

        observed_coords = np.radians(
            np.column_stack([
                observed.geometry.y,
                observed.geometry.x
            ])
        )

        tree = BallTree(
            observed_coords,
            metric="haversine"
        )

        missing_coords = np.radians(
            np.column_stack([
                missing.geometry.y,
                missing.geometry.x
            ])
        )

        distances, indices = tree.query(
            missing_coords,
            k=k
        )

        for row_idx, neighbor_idx, dists in zip(
            missing.index,
            indices,
            distances
        ):

            neighbors = observed.iloc[neighbor_idx]

            weights = 1 / dists

            weighted_values = np.average(
                neighbors[missing_cols],
                axis=0,
                weights=weights
            )

            gdf_imputed.loc[row_idx, missing_cols] = weighted_values
    return gdf_imputed.copy()


# Puerto Rico doesn't have PLACES data, so we can drop rows with it
df = pd.read_csv("county_panel_raw.csv")
df = df[df["state_name"] != "Puerto Rico"]

# Dont want to impute target variables, as they could influence our ML processes
# adult_population also doesn't exist for a large portion of our columns, so we can drop that column.
drop_df = df.dropna(subset=["mental_health_prevalence"])
drop_df = drop_df.drop(columns=["adult_population"])

# Get the GeoLocation from PLACES
places_df = pd.read_csv("PLACES_Combined.csv")
places_df = places_df[["State", "County", "Geolocation"]]
places_df = places_df.drop_duplicates(subset=["State", "County"])
merged_df = pd.merge(drop_df, places_df, how="left", left_on=["state_name", "county_name"], right_on=["State", "County"]).drop(columns=["State", "County"])

# Construct GeoDataFrame using Geolocation
gdf = gpd.GeoDataFrame(merged_df, geometry=gpd.GeoSeries.from_wkt(merged_df["Geolocation"]), crs="EPSG:4326")
gdf = gdf.drop(columns="Geolocation")
print("GeoDataFrame Size: ", len(gdf))
print("Rows with missing AirData to be imputed:", gdf.isna().any(axis=1).sum())
missing_cols = list(gdf.columns[12:-1])
print("Columns to be imputed: ", missing_cols)

# Run KNN imputation
gdf_imputed = knn_impute(gdf, missing_cols)
print("----------------")
print("NaN Summary")
print(gdf_imputed.isnull().sum())

gdf_imputed.to_csv(FILE_NAME, index=False)
print("Saved to", FILE_NAME)

