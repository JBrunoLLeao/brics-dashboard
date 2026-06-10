import pandas as pd
import plotly.express as px
import streamlit as st

from core import data
from core.indicators import cagr

st.title("🌍 Comércio Intrabloco - BRICS+")
st.caption(
    "Fluxos de comércio de bens entre os 11 países do BRICS ampliado. "
    "Cada fluxo aparece uma única vez, valorado FOB (exportador)."
)

d = data.load()
fact = d["fact"]
names = data.name_map()
years = data.years()

year_range = st.sidebar.slider(
    "Período", min_value=years[0], max_value=years[-1], value=(years[0], years[-1])
)
data.sidebar_footer()

f = fact[(fact["year"] >= year_range[0]) & (fact["year"] <= year_range[1])]

# Cartões agregados
total_intra = f["value"].sum()
by_year = f.groupby("year", observed=True)["value"].sum()
growth = cagr(by_year)
n_pairs = f.groupby(["exporter", "importer"], observed=True).ngroups

c1, c2, c3 = st.columns(3)
c1.metric("Comércio intrabloco (período)", data.fmt_usd(total_intra))
c2.metric("Crescimento médio anual (CAGR)", f"{growth:.1f}% a.a.")
c3.metric("Relações bilaterais ativas", f"{n_pairs} de 110")

st.divider()

# Mapa dos membros
col_map, col_evo = st.columns(2)

with col_map:
    st.subheader("Os 11 membros do BRICS+")
    country_total = (
        f.groupby("exporter", observed=True)["value"]
        .sum()
        .add(f.groupby("importer", observed=True)["value"].sum(), fill_value=0)
        .rename("v")
        .rename_axis("iso3")
        .reset_index()
    )
    geo = d["dim_country"].merge(country_total, on="iso3", how="left")
    fig_map = px.scatter_geo(
        geo,
        lat="lat",
        lon="lon",
        size="v",
        hover_name="name_pt",
        hover_data={"lat": False, "lon": False, "accession": True, "v": ":,.0f"},
        labels={"accession": "Adesão", "v": "Comércio intrabloco (US$)"},
        projection="natural earth",
        size_max=40,
    )
    fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=380)
    st.plotly_chart(fig_map, width="stretch")

with col_evo:
    st.subheader("Evolução do comércio intrabloco")
    evo = by_year.reset_index()
    evo["v_bi"] = evo["value"] / 1e9
    fig_evo = px.area(
        evo,
        x="year",
        y="v_bi",
        labels={"year": "Ano", "v_bi": "US$ bilhões"},
    )
    fig_evo.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=380)
    st.plotly_chart(fig_evo, width="stretch")

# Maiores exportadores e importadores dentro do bloco
st.subheader("🏆 Maiores exportadores e importadores intrabloco")
col_a, col_b = st.columns(2)

exp_rank = (
    f.groupby("exporter", observed=True)["value"].sum().sort_values().reset_index()
)
exp_rank["país"] = exp_rank["exporter"].map(names)
exp_rank["v_bi"] = exp_rank["value"] / 1e9

imp_rank = (
    f.groupby("importer", observed=True)["value"].sum().sort_values().reset_index()
)
imp_rank["país"] = imp_rank["importer"].map(names)
imp_rank["v_bi"] = imp_rank["value"] / 1e9

with col_a:
    fig = px.bar(
        exp_rank,
        x="v_bi",
        y="país",
        orientation="h",
        color="v_bi",
        color_continuous_scale="Greens",
        labels={"v_bi": "US$ bi", "país": ""},
        title="Exportações para o bloco",
    )
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, width="stretch")

with col_b:
    fig = px.bar(
        imp_rank,
        x="v_bi",
        y="país",
        orientation="h",
        color="v_bi",
        color_continuous_scale="Reds",
        labels={"v_bi": "US$ bi", "país": ""},
        title="Importações do bloco",
    )
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, width="stretch")

# Evolução por país
st.subheader("📈 Evolução por país")
sel = st.multiselect(
    "Países", data.members_pt(), default=["Brasil", "China", "Índia", "Rússia"]
)
if sel:
    isos = [data.iso_of(s) for s in sel]
    evo_c = (
        f[f["exporter"].isin(isos)]
        .groupby(["year", "exporter"], observed=True)["value"]
        .sum()
        .reset_index()
    )
    evo_c["país"] = evo_c["exporter"].map(names)
    evo_c["v_bi"] = evo_c["value"] / 1e9
    fig = px.line(
        evo_c,
        x="year",
        y="v_bi",
        color="país",
        markers=True,
        labels={"year": "Ano", "v_bi": "Exportações intrabloco (US$ bi)", "país": ""},
    )
    st.plotly_chart(fig, width="stretch")

# Matriz bilateral
st.subheader("🔢 Matriz de comércio do bloco")
st.caption(
    "Exportações de cada país (linhas) para cada parceiro (colunas), no período "
    "selecionado. A matriz responde quem são os maiores parceiros de cada membro."
)
matrix = (
    f.groupby(["exporter", "importer"], observed=True)["value"]
    .sum()
    .div(1e9)
    .unstack()
    .rename(index=names, columns=names)
)
fig_hm = px.imshow(
    matrix,
    color_continuous_scale="Blues",
    labels={"x": "Importador", "y": "Exportador", "color": "US$ bi"},
    aspect="auto",
    text_auto=".1f",
)
fig_hm.update_layout(height=520)
st.plotly_chart(fig_hm, width="stretch")

# Participação e crescimento por país
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Participação no comércio do bloco")
    share = country_total.copy()
    share["país"] = share["iso3"].map(names)
    fig_pie = px.pie(share, values="v", names="país", hole=0.4)
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pie, width="stretch")

with col_d:
    st.subheader("Crescimento médio anual (CAGR)")
    per_country_year = (
        f.groupby(["exporter", "year"], observed=True)["value"]
        .sum()
        .rename_axis(["iso3", "year"])
        .add(
            f.groupby(["importer", "year"], observed=True)["value"]
            .sum()
            .rename_axis(["iso3", "year"]),
            fill_value=0,
        )
    )
    rows = [
        {"país": names[iso], "CAGR (%)": cagr(per_country_year.loc[iso])}
        for iso in per_country_year.index.get_level_values("iso3").unique()
    ]
    df_cagr = pd.DataFrame(rows).dropna().sort_values("CAGR (%)")
    fig_cagr = px.bar(
        df_cagr,
        x="CAGR (%)",
        y="país",
        orientation="h",
        color="CAGR (%)",
        color_continuous_scale="RdYlGn",
        labels={"país": ""},
    )
    fig_cagr.update_coloraxes(showscale=False)
    st.plotly_chart(fig_cagr, width="stretch")
