"""Cached parquet loaders and shared lookups for all dashboard pages."""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent.parent / "data"

FLOW_COLORS = {"Exportações": "#2ecc71", "Importações": "#e74c3c"}
TIER_ORDER = [
    "Primário",
    "Baseado em recursos",
    "Baixa tecnologia",
    "Média tecnologia",
    "Alta tecnologia",
    "Não classificado",
]
TIER_COLORS = {
    "Primário": "#8d6e63",
    "Baseado em recursos": "#fbc02d",
    "Baixa tecnologia": "#90a4ae",
    "Média tecnologia": "#42a5f5",
    "Alta tecnologia": "#7e57c2",
    "Não classificado": "#cfd8dc",
}


@st.cache_data(show_spinner="Carregando dados...")
def load() -> dict[str, pd.DataFrame]:
    fact = pd.read_parquet(DATA / "fact_hs6.parquet")
    lookup = pd.read_csv(DATA / "lookup_hs6_lall.csv", dtype={"hs6": str})
    dim_lall = pd.read_csv(DATA / "dim_lall.csv")
    dim_product = pd.read_parquet(DATA / "dim_product.parquet")
    dim_hs2 = pd.read_csv(DATA / "dim_hs2.csv", dtype={"hs2": str})

    lall = lookup.merge(dim_lall, on="lall_code", how="left")
    fact["hs2"] = fact["hs6"].str[:2]
    fact = fact.merge(lall[["hs6", "lall_code", "tier"]], on="hs6", how="left")
    fact["tier"] = fact["tier"].fillna("Não classificado")
    for col in ("exporter", "importer", "hs6", "hs2", "lall_code", "tier"):
        fact[col] = fact[col].astype("category")

    return {
        "fact": fact,
        "world_exports": pd.read_parquet(DATA / "world_exports.parquet"),
        "world_imports": pd.read_parquet(DATA / "world_imports.parquet"),
        "world_totals": pd.read_parquet(DATA / "world_totals.parquet"),
        "dim_country": pd.read_parquet(DATA / "dim_country.parquet"),
        "dim_product": dim_product,
        "dim_hs2": dim_hs2,
        "dim_lall": dim_lall,
        "crosscheck": pd.read_parquet(DATA / "crosscheck.parquet"),
    }


def name_map() -> dict[str, str]:
    dim = load()["dim_country"]
    return dict(zip(dim["iso3"], dim["name_pt"]))


def hs2_label_map() -> dict[str, str]:
    dim = load()["dim_hs2"]
    return {h: f"{h} - {d}" for h, d in zip(dim["hs2"], dim["desc_en"])}


def hs6_label_map() -> dict[str, str]:
    dim = load()["dim_product"]
    return {h: f"{h} - {d}" for h, d in zip(dim["hs6"], dim["desc_en"])}


def years() -> list[int]:
    return sorted(load()["fact"]["year"].unique().tolist())


def members_pt() -> list[str]:
    """Member names sorted alphabetically (PT)."""
    return sorted(name_map().values())


def iso_of(name_pt: str) -> str:
    inv = {v: k for k, v in name_map().items()}
    return inv[name_pt]


def hs_level_selector() -> tuple[str, dict[str, str], str]:
    """Sidebar HS2/HS6 toggle, shared across pages via session_state.

    Returns (fact column name, code -> label map, display label).
    """
    choice = st.sidebar.radio(
        "Nível de produto",
        ["Capítulos (HS2)", "Subposições (HS6)"],
        key="hs_level",
        help="HS2: 97 capítulos, leitura agregada. HS6: ~5200 subposições, detalhe fino.",
    )
    if choice.startswith("Capítulos"):
        return "hs2", hs2_label_map(), choice
    return "hs6", hs6_label_map(), choice


def fmt_usd(value: float) -> str:
    """Compact pt-BR style USD figure."""
    if abs(value) >= 1e9:
        return f"US$ {value / 1e9:,.1f} bi"
    if abs(value) >= 1e6:
        return f"US$ {value / 1e6:,.1f} mi"
    return f"US$ {value:,.0f}"


def sidebar_footer() -> None:
    st.sidebar.divider()
    st.sidebar.caption(
        "Fonte: BACI (CEPII), V202601, HS 2012, valores FOB. "
        "Cobertura: 2015-2024."
    )
    st.sidebar.caption("Detalhes na página Metodologia e Fontes.")
