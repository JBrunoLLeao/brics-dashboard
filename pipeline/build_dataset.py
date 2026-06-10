"""Build the dashboard's parquet star schema from the BACI zip.

Reads the per-year BACI CSVs in chunks straight from the zip (the
extracted files are ~500 MB/year, never fully loaded). Values arrive in
thousands of current USD, FOB; they are stored in USD.

Outputs (data/):
  fact_hs6.parquet        year, exporter, importer, hs6, value, qty
                          (intra-BRICS+ bilateral flows)
  world_exports.parquet   year, exporter, hs6, value   (BRICS+ exporter -> World)
  world_imports.parquet   year, importer, hs6, value   (World -> BRICS+ importer)
  world_totals.parquet    year, hs6, value             (all exporters -> World)
  dim_product.parquet     hs6, hs2, desc_en
  dim_country.parquet     iso3, name_pt, lat, lon, accession
"""

import sys
import zipfile
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).parent / "cache"
DATA = Path(__file__).parent.parent / "data"
ZIP = CACHE / "BACI_HS12_V202601.zip"

YEARS = range(2015, 2025)
CHUNK_ROWS = 2_000_000

COUNTRIES = [
    # iso3, name_pt, lat, lon, accession year
    ("BRA", "Brasil", -14.2, -51.9, 2009),
    ("RUS", "Rússia", 61.5, 105.3, 2009),
    ("IND", "Índia", 20.6, 79.0, 2009),
    ("CHN", "China", 35.9, 104.2, 2009),
    ("ZAF", "África do Sul", -30.6, 22.9, 2011),
    ("EGY", "Egito", 26.8, 30.8, 2024),
    ("ETH", "Etiópia", 9.1, 40.5, 2024),
    ("IRN", "Irã", 32.4, 53.7, 2024),
    ("SAU", "Arábia Saudita", 23.9, 45.1, 2024),
    ("ARE", "Emirados Árabes Unidos", 23.4, 53.8, 2024),
    ("IDN", "Indonésia", -0.8, 113.9, 2025),
]
ISO3 = [c[0] for c in COUNTRIES]


def load_code_map(zf: zipfile.ZipFile) -> dict[int, str]:
    """BACI numeric country code -> iso3, for the 11 members."""
    with zf.open("country_codes_V202601.csv") as f:
        codes = pd.read_csv(f)
    codes = codes[codes["country_iso3"].isin(ISO3)]
    if len(codes) != len(ISO3):
        sys.exit(f"expected {len(ISO3)} member codes, found {len(codes)}")
    return dict(zip(codes["country_code"], codes["country_iso3"]))


def build_dim_product(zf: zipfile.ZipFile) -> None:
    with zf.open("product_codes_HS12_V202601.csv") as f:
        prod = pd.read_csv(f, dtype={"code": str})
    prod["code"] = prod["code"].str.zfill(6)
    out = pd.DataFrame(
        {"hs6": prod["code"], "hs2": prod["code"].str[:2], "desc_en": prod["description"]}
    )
    out.to_parquet(DATA / "dim_product.parquet", index=False)
    print(f"dim_product.parquet: {len(out)} HS6 codes")


def process_year(zf: zipfile.ZipFile, year: int, code_map: dict[int, str]):
    member_codes = set(code_map)
    bilat_parts, expw_parts, impw_parts, world_parts = [], [], [], []

    with zf.open(f"BACI_HS12_Y{year}_V202601.csv") as f:
        reader = pd.read_csv(
            f,
            usecols=["t", "i", "j", "k", "v", "q"],
            dtype={"k": str},
            chunksize=CHUNK_ROWS,
        )
        for chunk in reader:
            exp_in = chunk["i"].isin(member_codes)
            imp_in = chunk["j"].isin(member_codes)

            bilat_parts.append(chunk[exp_in & imp_in])
            expw_parts.append(
                chunk[exp_in].groupby(["i", "k"], as_index=False)["v"].sum()
            )
            impw_parts.append(
                chunk[imp_in].groupby(["j", "k"], as_index=False)["v"].sum()
            )
            world_parts.append(chunk.groupby("k", as_index=False)["v"].sum())

    bilat = pd.concat(bilat_parts, ignore_index=True)
    bilat = pd.DataFrame(
        {
            "year": year,
            "exporter": bilat["i"].map(code_map),
            "importer": bilat["j"].map(code_map),
            "hs6": bilat["k"].str.zfill(6),
            "value": bilat["v"] * 1000.0,
            "qty": pd.to_numeric(bilat["q"], errors="coerce"),
        }
    )

    def regroup(parts, who_col, out_col):
        df = pd.concat(parts, ignore_index=True)
        df = df.groupby([who_col, "k"], as_index=False)["v"].sum()
        return pd.DataFrame(
            {
                "year": year,
                out_col: df[who_col].map(code_map),
                "hs6": df["k"].str.zfill(6),
                "value": df["v"] * 1000.0,
            }
        )

    expw = regroup(expw_parts, "i", "exporter")
    impw = regroup(impw_parts, "j", "importer")

    world = pd.concat(world_parts, ignore_index=True)
    world = world.groupby("k", as_index=False)["v"].sum()
    world = pd.DataFrame(
        {"year": year, "hs6": world["k"].str.zfill(6), "value": world["v"] * 1000.0}
    )

    print(
        f"{year}: bilat {len(bilat):>7} rows  US$ {bilat['value'].sum() / 1e9:7.1f} bi intra-bloco"
    )
    return bilat, expw, impw, world


def main() -> None:
    DATA.mkdir(exist_ok=True)
    with zipfile.ZipFile(ZIP) as zf:
        code_map = load_code_map(zf)
        build_dim_product(zf)

        per_year = [process_year(zf, y, code_map) for y in YEARS]

    names = ["fact_hs6", "world_exports", "world_imports", "world_totals"]
    for idx, name in enumerate(names):
        df = pd.concat([p[idx] for p in per_year], ignore_index=True)
        df["year"] = df["year"].astype("int16")
        df.to_parquet(DATA / f"{name}.parquet", index=False)
        size_mb = (DATA / f"{name}.parquet").stat().st_size / 1e6
        print(f"{name}.parquet: {len(df)} rows, {size_mb:.1f} MB")

    dim = pd.DataFrame(COUNTRIES, columns=["iso3", "name_pt", "lat", "lon", "accession"])
    dim.to_parquet(DATA / "dim_country.parquet", index=False)
    print(f"dim_country.parquet: {len(dim)} members")


if __name__ == "__main__":
    main()
