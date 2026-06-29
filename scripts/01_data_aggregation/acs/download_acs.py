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

for year in range(2019, 2024):

    vars_string = ",".join(ACS_VARS.values())

    url = (
        f"https://api.census.gov/data/{year}/acs/acs5"
        f"?get=NAME,{vars_string}"
        "&for=county:*"
        f"&key={API_KEY}"
    )

    response = requests.get(url)

    data = response.json()

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