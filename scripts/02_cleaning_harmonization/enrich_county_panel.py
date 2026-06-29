#!/usr/bin/env python3
"""
Download and merge supplemental county-level data for the mental-distress project.

Outputs:
- data/raw/census_geography/cb_2023_us_county_500k.zip
- data/raw/acs/acs_county_enrichment_2019_2023.csv
- data/raw/epa_airdata/daily_aqi_features_2019_2023.csv
- data/raw/noaa/noaa_climate_county_2019_2023.csv
- data/processed/county_panel_enriched.csv
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_PROJECT_DIR = Path.cwd()
YEARS = list(range(2019, 2024))

STATE_FIPS_TO_ABBR = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
}

INDUSTRY_VARS = {
    "S2405_C01_001E": "acs_employed_total",
    "S2405_C01_002E": "industry_ag_mining",
    "S2405_C01_003E": "industry_construction",
    "S2405_C01_004E": "industry_manufacturing",
    "S2405_C01_005E": "industry_wholesale_trade",
    "S2405_C01_006E": "industry_retail_trade",
    "S2405_C01_007E": "industry_transport_utilities",
    "S2405_C01_008E": "industry_information",
    "S2405_C01_009E": "industry_finance_real_estate",
    "S2405_C01_010E": "industry_professional_admin",
    "S2405_C01_011E": "industry_education_health",
    "S2405_C01_012E": "industry_arts_food",
    "S2405_C01_013E": "industry_other_services",
    "S2405_C01_014E": "industry_public_admin",
}

EDU_VARS = [f"B15003_{i:03d}E" for i in range(1, 26)]
HEALTH_VARS = {
    "S2701_C01_001E": "acs_civilian_noninstitutionalized_total",
    "S2701_C04_001E": "acs_uninsured_count",
    "S2701_C05_001E": "pct_uninsured",
}


def log(message: str) -> None:
    print(message, flush=True)


def ensure_dirs(project_dir: Path) -> dict[str, Path]:
    paths = {
        "external": project_dir / "Data" / "External",
        "census": project_dir / "Data" / "External" / "census",
        "acs": project_dir / "Data" / "External" / "acs",
        "epa": project_dir / "Data" / "External" / "epa",
        "epa_raw": project_dir / "Data" / "External" / "epa" / "raw",
        "noaa": project_dir / "Data" / "External" / "noaa",
        "imputation": project_dir / "imputation",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def request_json(url: str, retries: int = 3, sleep: float = 0.8) -> object:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "county-fmd-enrichment/1.0"})
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(sleep * (attempt + 1))
    raise RuntimeError(f"Failed JSON request after {retries} attempts: {url}") from last_error


def download_file(url: str, output_path: Path, force: bool = False) -> None:
    if output_path.exists() and output_path.stat().st_size > 0 and not force:
        log(f"Already downloaded: {output_path}")
        return
    log(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "county-fmd-enrichment/1.0"})
    with urllib.request.urlopen(req, timeout=180) as response:
        output_path.write_bytes(response.read())
    log(f"Saved {output_path} ({output_path.stat().st_size / 1_000_000:.1f} MB)")


def load_base_panel(project_dir: Path) -> pd.DataFrame:
    path = project_dir / "imputation" / "county_panel_imputed.csv"
    df = pd.read_csv(path)
    df["geoid"] = df["geoid"].astype(str).str.zfill(5)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df


def read_acs_bulk_table(year: int, table: str, columns: list[str], paths: dict[str, Path], force: bool = False) -> pd.DataFrame:
    cache_dir = paths["acs"] / "bulk_selected"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"acsdt5y{year}-{table.lower()}_county_selected.csv"
    if cache_path.exists() and not force:
        return pd.read_csv(cache_path, dtype={"GEO_ID": str})

    url = (
        "https://www2.census.gov/programs-surveys/acs/summary_file/"
        f"{year}/table-based-SF/data/5YRData/acsdt5y{year}-{table.lower()}.dat"
    )
    log(f"Reading ACS bulk table {table} for {year}")
    usecols = ["GEO_ID", *columns]
    frame = pd.read_csv(url, sep="|", usecols=usecols, dtype={"GEO_ID": str}, low_memory=False)
    frame = frame[frame["GEO_ID"].str.startswith("0500000US", na=False)].copy()
    frame["geoid"] = frame["GEO_ID"].str[-5:]
    for col in columns:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame.to_csv(cache_path, index=False)
    return frame


def build_acs_features(
    project_dir: Path,
    paths: dict[str, Path],
    base_df: pd.DataFrame,
    force: bool = False,
) -> pd.DataFrame:
    output_path = paths["acs"] / "acs_county_enrichment_2019_2023.csv"
    if output_path.exists() and not force:
        log(f"Loading existing ACS features: {output_path}")
        return pd.read_csv(output_path, dtype={"geoid": str})

    available_years = [2021, 2022, 2023]
    rows = []
    industry_cols = [f"C24050_E{i:03d}" for i in range(1, 15)]
    industry_names = {
        "C24050_E001": "acs_employed_total",
        "C24050_E002": "industry_ag_mining",
        "C24050_E003": "industry_construction",
        "C24050_E004": "industry_manufacturing",
        "C24050_E005": "industry_wholesale_trade",
        "C24050_E006": "industry_retail_trade",
        "C24050_E007": "industry_transport_utilities",
        "C24050_E008": "industry_information",
        "C24050_E009": "industry_finance_real_estate",
        "C24050_E010": "industry_professional_admin",
        "C24050_E011": "industry_education_health",
        "C24050_E012": "industry_arts_food",
        "C24050_E013": "industry_other_services",
        "C24050_E014": "industry_public_admin",
    }
    education_cols = [f"B15003_E{i:03d}" for i in range(1, 26)]
    health_cols = ["B27010_E001", "B27010_E017", "B27010_E033", "B27010_E050", "B27010_E066"]

    for source_year in available_years:
        log(f"Building ACS features from bulk tables for {source_year}")
        industry = read_acs_bulk_table(source_year, "C24050", industry_cols, paths, force=force).rename(columns=industry_names)
        for clean_name in [v for v in industry_names.values() if v.startswith("industry_")]:
            industry[f"pct_{clean_name.removeprefix('industry_')}"] = (
                industry[clean_name] / industry["acs_employed_total"].replace(0, np.nan)
            )

        education = read_acs_bulk_table(source_year, "B15003", education_cols, paths, force=force)
        edu_total = education["B15003_E001"].replace(0, np.nan)
        less_hs_cols = [f"B15003_E{i:03d}" for i in range(2, 17)]
        hs_plus_cols = [f"B15003_E{i:03d}" for i in range(17, 26)]
        bachelors_plus_cols = [f"B15003_E{i:03d}" for i in range(22, 26)]
        education["acs_education_25plus_total"] = education["B15003_E001"]
        education["pct_less_than_hs"] = education[less_hs_cols].sum(axis=1) / edu_total
        education["pct_hs_or_higher"] = education[hs_plus_cols].sum(axis=1) / edu_total
        education["pct_bachelors_or_higher"] = education[bachelors_plus_cols].sum(axis=1) / edu_total

        health = read_acs_bulk_table(source_year, "B27010", health_cols, paths, force=force)
        health["acs_civilian_noninstitutionalized_total"] = health["B27010_E001"]
        health["acs_uninsured_count"] = health[["B27010_E017", "B27010_E033", "B27010_E050", "B27010_E066"]].sum(axis=1)
        health["pct_uninsured"] = health["acs_uninsured_count"] / health["acs_civilian_noninstitutionalized_total"].replace(0, np.nan)
        health["pct_insured"] = 1.0 - health["pct_uninsured"]

        keep_industry = ["geoid", "acs_employed_total", *[c for c in industry.columns if c.startswith("pct_")]]
        keep_education = [
            "geoid",
            "acs_education_25plus_total",
            "pct_less_than_hs",
            "pct_hs_or_higher",
            "pct_bachelors_or_higher",
        ]
        keep_health = [
            "geoid",
            "acs_civilian_noninstitutionalized_total",
            "acs_uninsured_count",
            "pct_uninsured",
            "pct_insured",
        ]

        merged = (
            industry[keep_industry]
            .merge(education[keep_education], on="geoid", how="outer")
            .merge(health[keep_health], on="geoid", how="outer")
        )
        merged["acs_source_year"] = source_year
        rows.append(merged)

    acs_by_source_year = pd.concat(rows, ignore_index=True)
    panel_keys = base_df[["geoid", "year"]].drop_duplicates().copy()
    panel_keys["acs_source_year"] = panel_keys["year"].clip(lower=min(available_years), upper=max(available_years))
    acs = panel_keys.merge(acs_by_source_year, on=["geoid", "acs_source_year"], how="left")
    acs.to_csv(output_path, index=False)
    log(f"Saved ACS features: {output_path} ({acs.shape[0]:,} rows, {acs.shape[1]:,} columns)")
    return acs


def build_epa_daily_aqi_features(paths: dict[str, Path], force: bool = False) -> pd.DataFrame:
    output_path = paths["epa"] / "daily_aqi_features_2019_2023.csv"
    if output_path.exists() and not force:
        log(f"Loading existing EPA daily AQI features: {output_path}")
        return pd.read_csv(output_path, dtype={"geoid": str})

    feature_frames = []
    for year in YEARS:
        zip_path = paths["epa_raw"] / f"daily_aqi_by_county_{year}.zip"
        download_file(
            f"https://aqs.epa.gov/aqsweb/airdata/daily_aqi_by_county_{year}.zip",
            zip_path,
            force=force,
        )
        log(f"Aggregating EPA daily AQI {year}")
        with zipfile.ZipFile(zip_path) as zf:
            csv_names = [name for name in zf.namelist() if name.endswith(".csv")]
            if not csv_names:
                raise RuntimeError(f"No CSV found in {zip_path}")
            with zf.open(csv_names[0]) as handle:
                daily = pd.read_csv(handle)

        daily["State Code"] = daily["State Code"].astype(str).str.zfill(2)
        daily["County Code"] = daily["County Code"].astype(str).str.zfill(3)
        daily["geoid"] = daily["State Code"] + daily["County Code"]
        daily["Date"] = pd.to_datetime(daily["Date"], errors="coerce")
        daily["year"] = daily["Date"].dt.year
        daily["month"] = daily["Date"].dt.month
        daily["AQI"] = pd.to_numeric(daily["AQI"], errors="coerce")
        daily = daily[daily["year"].eq(year)].copy()

        daily["aqi_over_100"] = daily["AQI"].gt(100)
        daily["aqi_over_150"] = daily["AQI"].gt(150)
        daily["aqi_over_200"] = daily["AQI"].gt(200)
        daily["category_unhealthy_or_worse"] = daily["Category"].isin(
            ["Unhealthy for Sensitive Groups", "Unhealthy", "Very Unhealthy", "Hazardous"]
        )

        monthly_mean = (
            daily.groupby(["geoid", "year", "month"], as_index=False)["AQI"]
            .mean()
            .rename(columns={"AQI": "monthly_mean_aqi"})
        )
        monthly_agg = (
            monthly_mean.groupby(["geoid", "year"])
            .agg(
                daily_aqi_monthly_mean_std=("monthly_mean_aqi", "std"),
                daily_aqi_monthly_mean_max=("monthly_mean_aqi", "max"),
                daily_aqi_months_observed=("monthly_mean_aqi", "count"),
            )
            .reset_index()
        )

        agg = (
            daily.groupby(["geoid", "year"])
            .agg(
                daily_aqi_observed_days=("AQI", "count"),
                daily_aqi_mean=("AQI", "mean"),
                daily_aqi_std=("AQI", "std"),
                daily_aqi_median=("AQI", "median"),
                daily_aqi_p90=("AQI", lambda s: s.quantile(0.90)),
                daily_aqi_max=("AQI", "max"),
                daily_aqi_days_over_100=("aqi_over_100", "sum"),
                daily_aqi_days_over_150=("aqi_over_150", "sum"),
                daily_aqi_days_over_200=("aqi_over_200", "sum"),
                daily_aqi_unhealthy_or_worse_days=("category_unhealthy_or_worse", "sum"),
                daily_aqi_reporting_sites_mean=("Number of Sites Reporting", "mean"),
            )
            .reset_index()
        )

        param_counts = pd.crosstab(
            [daily["geoid"], daily["year"]],
            daily["Defining Parameter"].astype(str).str.lower().str.replace(".", "", regex=False),
        )
        param_counts.columns = [f"daily_aqi_defining_param_days_{c.replace(' ', '_')}" for c in param_counts.columns]
        param_counts = param_counts.reset_index()

        category_counts = pd.crosstab([daily["geoid"], daily["year"]], daily["Category"])
        category_counts.columns = [
            "daily_aqi_category_days_" + c.lower().replace(" ", "_").replace("/", "_")
            for c in category_counts.columns
        ]
        category_counts = category_counts.reset_index()

        feature_frames.append(
            agg.merge(monthly_agg, on=["geoid", "year"], how="left")
            .merge(param_counts, on=["geoid", "year"], how="left")
            .merge(category_counts, on=["geoid", "year"], how="left")
        )

    features = pd.concat(feature_frames, ignore_index=True).fillna(0)
    features.to_csv(output_path, index=False)
    log(f"Saved EPA features: {output_path} ({features.shape[0]:,} rows, {features.shape[1]:,} columns)")
    return features


def noaa_location_id(geoid: str) -> str | None:
    geoid = str(geoid).zfill(5)
    abbr = STATE_FIPS_TO_ABBR.get(geoid[:2])
    if not abbr:
        return None
    return f"{abbr}-{geoid[-3:]}"


def fetch_noaa_series(location_id: str, parameter: str) -> dict[str, float | None]:
    url = (
        "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/"
        f"county/time-series/{urllib.parse.quote(location_id)}/{parameter}/12/12/data.json?raw=1"
    )
    try:
        data = request_json(url, retries=2, sleep=0.5)
        if isinstance(data, dict):
            return data
    except Exception as exc:  # noqa: BLE001
        return {"__error__": str(exc)}
    return {"__error__": "unexpected NOAA response"}


def build_noaa_climate_features(
    base_df: pd.DataFrame,
    paths: dict[str, Path],
    force: bool = False,
    workers: int = 16,
) -> pd.DataFrame:
    output_path = paths["noaa"] / "noaa_climate_county_2019_2023.csv"
    if output_path.exists() and not force:
        log(f"Loading existing NOAA climate features: {output_path}")
        return pd.read_csv(output_path, dtype={"geoid": str})

    unique_counties = (
        base_df[["geoid", "county_name", "state_name"]]
        .drop_duplicates("geoid")
        .sort_values("geoid")
        .copy()
    )
    unique_counties["noaa_location_id"] = unique_counties["geoid"].map(noaa_location_id)
    request_items = [
        (row.geoid, row.noaa_location_id, parameter)
        for row in unique_counties.itertuples(index=False)
        if isinstance(row.noaa_location_id, str)
        for parameter in ["tavg", "pcp"]
    ]

    log(f"Fetching NOAA climate data for {len(unique_counties):,} counties ({len(request_items):,} requests)")
    cache: dict[tuple[str, str], dict[str, float | None]] = {}
    errors = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_noaa_series, location_id, parameter): (geoid, location_id, parameter)
            for geoid, location_id, parameter in request_items
        }
        for i, future in enumerate(as_completed(futures), start=1):
            geoid, location_id, parameter = futures[future]
            series = future.result()
            if "__error__" in series:
                errors.append({"geoid": geoid, "noaa_location_id": location_id, "parameter": parameter, "error": series["__error__"]})
                series = {}
            cache[(geoid, parameter)] = series
            if i % 500 == 0:
                log(f"NOAA requests completed: {i:,}/{len(request_items):,}")

    rows = []
    for county in unique_counties.itertuples(index=False):
        for year in YEARS:
            tavg = cache.get((county.geoid, "tavg"), {}).get(str(year))
            pcp = cache.get((county.geoid, "pcp"), {}).get(str(year))
            rows.append(
                {
                    "geoid": county.geoid,
                    "year": year,
                    "noaa_location_id": county.noaa_location_id,
                    "annual_avg_temp_f": pd.to_numeric(tavg, errors="coerce"),
                    "annual_precip_inches": pd.to_numeric(pcp, errors="coerce"),
                }
            )
    climate = pd.DataFrame(rows)

    baseline_rows = []
    for county in unique_counties.itertuples(index=False):
        tavg_series = cache.get((county.geoid, "tavg"), {})
        pcp_series = cache.get((county.geoid, "pcp"), {})
        tavg_baseline = pd.to_numeric(pd.Series({k: v for k, v in tavg_series.items() if "1901" <= k <= "2000"}), errors="coerce").mean()
        pcp_baseline = pd.to_numeric(pd.Series({k: v for k, v in pcp_series.items() if "1901" <= k <= "2000"}), errors="coerce").mean()
        baseline_rows.append({"geoid": county.geoid, "temp_1901_2000_mean": tavg_baseline, "precip_1901_2000_mean": pcp_baseline})
    baselines = pd.DataFrame(baseline_rows)
    climate = climate.merge(baselines, on="geoid", how="left")
    climate["annual_temp_anomaly_f"] = climate["annual_avg_temp_f"] - climate["temp_1901_2000_mean"]
    climate["annual_precip_anomaly_inches"] = climate["annual_precip_inches"] - climate["precip_1901_2000_mean"]

    climate.to_csv(output_path, index=False)
    log(f"Saved NOAA climate features: {output_path} ({climate.shape[0]:,} rows, {climate.shape[1]:,} columns)")
    if errors:
        errors_path = paths["noaa"] / "noaa_climate_errors.csv"
        pd.DataFrame(errors).to_csv(errors_path, index=False)
        log(f"NOAA errors saved: {errors_path} ({len(errors):,} rows)")
    return climate


def build_enriched_panel(
    base: pd.DataFrame,
    acs: pd.DataFrame,
    epa: pd.DataFrame,
    climate: pd.DataFrame,
    project_dir: Path,
) -> pd.DataFrame:
    enriched = base.copy()
    for frame in (acs, epa, climate):
        frame["geoid"] = frame["geoid"].astype(str).str.zfill(5)
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")

    enriched = enriched.merge(acs, on=["geoid", "year"], how="left")
    enriched = enriched.merge(epa, on=["geoid", "year"], how="left")
    enriched = enriched.merge(climate, on=["geoid", "year"], how="left")

    output_path = project_dir / "imputation" / "county_panel_enriched.csv"
    enriched.to_csv(output_path, index=False)

    coverage = (
        enriched.assign(
            has_acs=enriched["pct_uninsured"].notna(),
            has_epa_daily=enriched["daily_aqi_mean"].notna(),
            has_noaa_climate=enriched["annual_avg_temp_f"].notna(),
        )
        .groupby("year")[["has_acs", "has_epa_daily", "has_noaa_climate"]]
        .mean()
        .round(3)
    )
    coverage_path = project_dir / "Data" / "External" / "enrichment_coverage_by_year.csv"
    coverage.to_csv(coverage_path)

    log(f"Saved enriched panel: {output_path} ({enriched.shape[0]:,} rows, {enriched.shape[1]:,} columns)")
    log(f"Saved coverage summary: {coverage_path}")
    log(str(coverage))
    return enriched


def download_county_boundaries(paths: dict[str, Path], force: bool = False) -> Path:
    output_path = paths["census"] / "cb_2023_us_county_500k.zip"
    download_file(
        "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip",
        output_path,
        force=force,
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--force", action="store_true", help="Re-download and rebuild all supplemental files.")
    parser.add_argument("--skip-noaa", action="store_true", help="Skip NOAA climate download.")
    parser.add_argument("--noaa-workers", type=int, default=16)
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    paths = ensure_dirs(project_dir)
    base = load_base_panel(project_dir)

    download_county_boundaries(paths, force=args.force)
    acs = build_acs_features(project_dir, paths, base, force=args.force)
    epa = build_epa_daily_aqi_features(paths, force=args.force)
    if args.skip_noaa:
        climate = pd.DataFrame({"geoid": base["geoid"].unique().repeat(len(YEARS))})
        climate["year"] = YEARS * base["geoid"].nunique()
    else:
        climate = build_noaa_climate_features(base, paths, force=args.force, workers=args.noaa_workers)

    build_enriched_panel(base, acs, epa, climate, project_dir)


if __name__ == "__main__":
    main()
