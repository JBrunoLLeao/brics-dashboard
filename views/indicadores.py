import pandas as pd
import plotly.express as px
import streamlit as st

from core import data
from core.indicators import grubel_lloyd, grubel_lloyd_aggregate, market_share, rca

st.title("📊 Indicadores de Competitividade")

d = data.load()
fact = d["fact"]
names = data.name_map()
years = data.years()

col1, col2, col3 = st.columns(3)
country_sel = col1.selectbox("País analisado (i)", data.members_pt(), index=data.members_pt().index("Brasil"))
market_opts = ["Bloco BRICS+"] + [c for c in data.members_pt() if c != country_sel]
market_sel = col2.selectbox("Mercado/parceiro (k)", market_opts)
year_sel = col3.selectbox("Ano de referência", years[::-1])
prod_col, prod_labels, level_sel = data.hs_level_selector()

st.caption(
    "Market Share (MS), Vantagem Comparativa Revelada (VCR) e Índice de "
    f"Comércio Intra-Industrial (ICII), calculados por produto no nível "
    f"{level_sel.lower()}."
)

iso = data.iso_of(country_sel)
member_isos = list(names)
market_isos = (
    [m for m in member_isos if m != iso]
    if market_sel == "Bloco BRICS+"
    else [data.iso_of(market_sel)]
)

fy = fact[fact["year"] == year_sel]


def by_level(frame: pd.DataFrame) -> pd.Series:
    s = frame.groupby(prod_col, observed=True)["value"].sum()
    return s[s > 0]


def world_by_level(frame: pd.DataFrame) -> pd.Series:
    if prod_col == "hs2":
        frame = frame.assign(hs2=frame["hs6"].str[:2])
    return frame.groupby(prod_col)["value"].sum()


# ---------- Market Share ----------
st.subheader("📌 Market Share (MS)")
st.latex(r"MS_{ik} = \frac{X_{ik}}{M_k}")
st.caption(
    f"Participação de {country_sel} nas importações totais (de qualquer origem) "
    f"de {market_sel} por produto, em {year_sel}. Mede o espaço do fornecedor "
    "no mercado do parceiro, não a composição da própria pauta."
)

x_ik = by_level(fy[(fy["exporter"] == iso) & (fy["importer"].isin(market_isos))])
wi = d["world_imports"]
m_k = world_by_level(wi[(wi["year"] == year_sel) & (wi["importer"].isin(market_isos))])

ms = market_share(x_ik, m_k).dropna().sort_values(ascending=False)
ms_df = ms.head(15).reset_index()
ms_df.columns = ["code", "MS (%)"]
ms_df["produto"] = ms_df["code"].astype(str).map(prod_labels).str.slice(0, 55)
ms_df["exportado"] = ms_df["code"].astype(str).map(x_ik) / 1e6

if ms_df.empty:
    st.info("Sem exportações nessa seleção.")
else:
    fig_ms = px.bar(
        ms_df,
        x="MS (%)",
        y="produto",
        orientation="h",
        color="MS (%)",
        color_continuous_scale="Blues",
        labels={"produto": ""},
        hover_data={"exportado": ":,.0f"},
        title=f"Maiores market shares de {country_sel} em {market_sel} - {year_sel}",
    )
    fig_ms.update_coloraxes(showscale=False)
    fig_ms.update_layout(yaxis={"categoryorder": "total ascending"}, height=480)
    st.plotly_chart(fig_ms, width="stretch")
    lead = ms_df.iloc[0]
    st.caption(
        f"Interpretação: em {year_sel}, {country_sel} forneceu "
        f"**{lead['MS (%)']:.1f}%** de tudo que {market_sel} importou do mundo em "
        f"_{lead['produto']}_."
    )

# ---------- VCR ----------
st.divider()
st.subheader("📌 Vantagem Comparativa Revelada (VCR - Balassa)")
st.latex(r"VCR_{ip} = \frac{X_{ip}/X_i}{W_p/W}")
st.caption(
    f"Compara o peso do produto na pauta exportadora total de {country_sel} "
    "(para o mundo) com o peso do produto nas exportações mundiais. "
    "VCR > 1: vantagem comparativa revelada; VCR < 1: desvantagem."
)

we = d["world_exports"]
x_ip = world_by_level(we[(we["year"] == year_sel) & (we["exporter"] == iso)])
wt = d["world_totals"]
w_p = world_by_level(wt[wt["year"] == year_sel])

vcr = rca(x_ip, w_p).dropna()
relevant = x_ip[x_ip / x_ip.sum() >= 0.005]  # produtos com >=0,5% da pauta
vcr_top = vcr[vcr.index.isin(relevant.index)].sort_values(ascending=False).head(15)
vcr_df = vcr_top.reset_index()
vcr_df.columns = ["code", "VCR"]
vcr_df["produto"] = vcr_df["code"].astype(str).map(prod_labels).str.slice(0, 55)
vcr_df["status"] = vcr_df["VCR"].apply(
    lambda v: "Com vantagem (VCR > 1)" if v >= 1 else "Sem vantagem (VCR < 1)"
)

fig_vcr = px.bar(
    vcr_df,
    x="VCR",
    y="produto",
    orientation="h",
    color="status",
    color_discrete_map={
        "Com vantagem (VCR > 1)": "#2ecc71",
        "Sem vantagem (VCR < 1)": "#e74c3c",
    },
    labels={"produto": "", "status": ""},
    title=f"VCR de {country_sel} - {year_sel} (produtos com ao menos 0,5% da pauta)",
)
fig_vcr.add_vline(x=1, line_dash="dash", line_color="gray", annotation_text="VCR = 1")
fig_vcr.update_layout(yaxis={"categoryorder": "total ascending"}, height=480)
st.plotly_chart(fig_vcr, width="stretch")

n_adv = int((vcr[vcr.index.isin(relevant.index)] > 1).sum())
st.caption(
    f"Interpretação: dos {len(relevant)} produtos com peso relevante na pauta de "
    f"{country_sel}, **{n_adv}** apresentam vantagem comparativa revelada em {year_sel}. "
    "O denominador usa as exportações mundiais (BACI), não apenas o bloco."
)

# ---------- ICII ----------
st.divider()
st.subheader("📌 Índice de Comércio Intra-Industrial (ICII / Grubel-Lloyd)")
st.latex(r"ICII_p = \left(1 - \frac{|X_p - M_p|}{X_p + M_p}\right)\times 100")
st.caption(
    f"Mede quanto do comércio entre {country_sel} e {market_sel} é troca dentro "
    "da mesma indústria (exporta e importa o mesmo tipo de produto). "
    "0 = comércio interindustrial puro; 100 = intraindustrial puro."
)
if prod_col == "hs6":
    st.caption(
        "Nota: no nível HS6 o índice tende a ser menor que no HS2, porque a "
        "desagregação separa produtos que um capítulo inteiro mistura."
    )

x_pair = by_level(fy[(fy["exporter"] == iso) & (fy["importer"].isin(market_isos))])
m_pair = by_level(fy[(fy["importer"] == iso) & (fy["exporter"].isin(market_isos))])

icii_agg = grubel_lloyd_aggregate(x_pair, m_pair)
if icii_agg >= 60:
    badge, level = "🟢", "alta"
elif icii_agg >= 30:
    badge, level = "🟡", "moderada"
else:
    badge, level = "🔴", "baixa"

st.metric(f"{badge} ICII agregado", f"{icii_agg:.1f}")
st.caption(
    f"Integração intraindustrial **{level}** entre {country_sel} e {market_sel} "
    f"em {year_sel}. Valores baixos indicam pauta complementar (ex.: commodities "
    "por manufaturas); valores altos, estruturas produtivas integradas."
)

icii = grubel_lloyd(x_pair, m_pair).dropna()
trade_weight = (
    x_pair.reindex(icii.index, fill_value=0) + m_pair.reindex(icii.index, fill_value=0)
)
icii_top = icii[trade_weight >= trade_weight.sum() * 0.005]

col_a, col_b = st.columns(2)

with col_a:
    top_df = icii_top.sort_values(ascending=False).head(15).reset_index()
    top_df.columns = ["code", "ICII"]
    top_df["produto"] = top_df["code"].astype(str).map(prod_labels).str.slice(0, 50)
    fig_icii = px.bar(
        top_df,
        x="ICII",
        y="produto",
        orientation="h",
        color="ICII",
        color_continuous_scale="Purples",
        range_x=[0, 100],
        labels={"produto": ""},
        title="Produtos com maior ICII (peso relevante no comércio)",
    )
    fig_icii.update_coloraxes(showscale=False)
    fig_icii.update_layout(yaxis={"categoryorder": "total ascending"}, height=480)
    st.plotly_chart(fig_icii, width="stretch")

with col_b:
    faixas = pd.cut(
        icii,
        bins=[0, 20, 40, 60, 80, 100],
        labels=["0-20", "20-40", "40-60", "60-80", "80-100"],
        include_lowest=True,
    )
    hist = faixas.value_counts().sort_index().reset_index()
    hist.columns = ["Faixa", "Produtos"]
    fig_hist = px.bar(
        hist,
        x="Faixa",
        y="Produtos",
        labels={"Faixa": "Faixa de ICII", "Produtos": "Número de produtos"},
        title="Distribuição dos produtos por grau de integração",
    )
    fig_hist.update_layout(height=480)
    st.plotly_chart(fig_hist, width="stretch")

data.sidebar_footer()
