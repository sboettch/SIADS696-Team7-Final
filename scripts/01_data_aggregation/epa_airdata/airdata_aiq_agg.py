import pandas as pd
import requests
from pathlib import Path

OUTPUT_DIR = Path("data/raw/airdata_aqi")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://aqs.epa.gov/aqsweb/airdata/annual_aqi_by_county_{}.zip"

for year in range(1980, 2026):

    try:
        url = BASE_URL.format(year)

        response = requests.get(url, timeout=60)

        if response.status_code != 200:
            print(f"Skipping {year} (HTTP {response.status_code})")
            continue

        zip_path = OUTPUT_DIR / f"annual_aqi_by_county_{year}.zip"

        with open(zip_path, "wb") as f:
            f.write(response.content)

        try:
            df = pd.read_csv(zip_path)
        except Exception:
            print(f"Skipping {year} (could not read zip)")
            continue

        if df.empty:
            print(f"Skipping {year} (no data)")
            continue

        df["year_pulled"] = year

        csv_path = OUTPUT_DIR / f"annual_aqi_by_county_{year}.csv"
        df.to_csv(csv_path, index=False)

        print(f"Saved AirData AQI {year}: {len(df):,} rows")

    except Exception as e:
        print(f"Failed {year}: {e}")
        continue

print("EPA AirData AQI download complete.")