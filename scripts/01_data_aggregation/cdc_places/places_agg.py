import pandas as pd
import requests
from pathlib import Path

OUTPUT_DIR = Path("data/raw/places")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RELEASES = {
    2016: "9z78-nsfp",  # 500 Cities
    2017: "vurf-k5wr",  # 500 Cities
    2018: "6vp6-wxuq",  # 500 Cities
    2019: "rja3-32tc",  # 500 Cities
    2020: "dv4u-3x3q",  # PLACES county
    2021: "pqpp-u99h",  # PLACES county
    2022: "duw2-7jbt",  # PLACES county
    2023: "h3ej-a9ec",  # PLACES county
    2024: "d3i6-k6z5",  # PLACES county GIS-friendly
    2025: "i46a-9kgh",  # PLACES county GIS-friendly
}

MEASURE_ID = "MHLTH"
LIMIT = 50000

for release_year, dataset_id in RELEASES.items():

    try:
        base_url = f"https://data.cdc.gov/resource/{dataset_id}.json"

        all_rows = []
        offset = 0

        while True:
            url = f"{base_url}?$limit={LIMIT}&$offset={offset}"

            response = requests.get(url, timeout=60)

            if response.status_code != 200:
                print(f"Skipping {release_year} (HTTP {response.status_code})")
                print(response.text[:300])
                break

            data = response.json()

            if len(data) == 0:
                break

            all_rows.extend(data)
            offset += LIMIT

        if len(all_rows) == 0:
            print(f"Skipping {release_year} (no data)")
            continue

        df = pd.DataFrame(all_rows)

        df.columns = [c.lower() for c in df.columns]

        if "measureid" in df.columns:
            df = df[df["measureid"].astype(str).str.upper() == MEASURE_ID]

        elif "measure_id" in df.columns:
            df = df[df["measure_id"].astype(str).str.upper() == MEASURE_ID]

        else:
            print(f"Skipping {release_year} (no measure id column)")
            continue

        if df.empty:
            print(f"Skipping {release_year} (no MHLTH rows)")
            continue

        df["release_year"] = release_year

        output_path = OUTPUT_DIR / f"places_mhlth_{release_year}.csv"
        df.to_csv(output_path, index=False)

        print(f"Saved {release_year}: {len(df):,} rows")

    except Exception as e:
        print(f"Failed {release_year}: {e}")
        continue

print("PLACES / 500 Cities download complete.")