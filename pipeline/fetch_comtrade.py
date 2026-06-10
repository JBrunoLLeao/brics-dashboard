"""Fetch UN Comtrade reference data and reported bilateral totals.

Uses only the keyless public preview API (500 records/call, 1 call/s).
Each per-year totals query returns at most 11 reporters x 12 partners
x 2 flows = 264 rows, under the preview cap.

Outputs (data/):
  dim_hs2.csv             hs2, desc_en
  crosscheck.parquet      year, reporter_iso3, partner_iso3, flow,
                          comtrade_value (reported, current USD)
"""

import csv
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent.parent / "data"

YEARS = range(2015, 2026)

# M49 reporter codes used by Comtrade (India is 699, not ISO 356).
M49_TO_ISO3 = {
    76: "BRA", 643: "RUS", 699: "IND", 156: "CHN", 710: "ZAF",
    818: "EGY", 231: "ETH", 364: "IRN", 682: "SAU", 784: "ARE",
    360: "IDN",
}

PREVIEW_URL = (
    "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
    "?reporterCode={reporters}&period={year}&partnerCode={partners}"
    "&flowCode=X,M&cmdCode=TOTAL&partner2Code=0&motCode=0&customsCode=C00"
)
HS_REF_URL = "https://comtradeapi.un.org/files/v1/app/reference/HS.json"


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "brics-dashboard"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_hs2_names() -> None:
    ref = get_json(HS_REF_URL)
    rows = [
        (item["id"], item["text"].split(" - ", 1)[1].strip())
        for item in ref["results"]
        if len(item["id"]) == 2 and item["id"].isdigit()
    ]
    with open(DATA / "dim_hs2.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hs2", "desc_en"])
        w.writerows(sorted(rows))
    print(f"dim_hs2.csv: {len(rows)} chapters")


def fetch_totals() -> None:
    codes = ",".join(str(c) for c in M49_TO_ISO3)
    partners = "0," + codes
    frames = []
    for year in YEARS:
        url = PREVIEW_URL.format(reporters=codes, partners=partners, year=year)
        payload = get_json(url)
        df = pd.DataFrame(payload["data"])
        if not df.empty:
            frames.append(df)
        print(f"{year}: {len(df)} rows")
        time.sleep(1.2)

    raw = pd.concat(frames, ignore_index=True)
    out = pd.DataFrame(
        {
            "year": raw["period"].astype(int),
            "reporter_iso3": raw["reporterCode"].map(M49_TO_ISO3),
            "partner_code": raw["partnerCode"],
            "flow": raw["flowCode"],
            "comtrade_value": pd.to_numeric(raw["primaryValue"]),
        }
    )
    out["partner_iso3"] = out["partner_code"].map(M49_TO_ISO3).fillna("WLD")
    out = out.drop(columns="partner_code")
    out.to_parquet(DATA / "crosscheck.parquet", index=False)
    print(f"crosscheck.parquet: {len(out)} rows, years {out['year'].min()}-{out['year'].max()}")


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    fetch_hs2_names()
    fetch_totals()
