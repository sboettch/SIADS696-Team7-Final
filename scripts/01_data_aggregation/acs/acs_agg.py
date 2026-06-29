import pandas as pd
import requests
from pathlib import Path

API_KEY = "a7345c054e3a321496f164b814be21cc4babd4b0"

OUTPUT_DIR = Path("data/raw/acs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ACS_VARS = {
    "median_income": "B19013_001E",
    "poverty_count": "B17001_002E",
    "population": "B01003_001E",
    "unemployment": "B23025_005E"
}

vars_string = ",".join(ACS_VARS.values())

for year in range(2000, 2026):

    try:

        url = (
            f"https://api.census.gov/data/{year}/acs/acs5"
            f"?get=NAME,{vars_string}"
            "&for=county:*"
            f"&key={API_KEY}"
        )

        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            print(f"Skipping {year} (HTTP {response.status_code})")
            continue

        try:
            data = response.json()
        except Exception:
            print(f"Skipping {year} (invalid JSON response)")
            continue

        if len(data) <= 1:
            print(f"Skipping {year} (no data)")
            continue

        df = pd.DataFrame(
            data[1:],
            columns=data[0]
        )

        df["year"] = year

        df.to_csv(
            OUTPUT_DIR / f"acs_{year}.csv",
            index=False
        )

        print(f"Saved ACS {year}")

    except Exception as e:
        print(f"Failed {year}: {e}")
        continue

print("ACS download complete.")