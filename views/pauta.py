import pandas as pd
import plotly.express as px
import streamlit as st

from core import data
from core.indicators import hhi

st.title("📦 Estrutura da Pauta Comercial")
st.caption(
    "Composição por produto do comércio intrabloco de cada membro: principais "
    "produtos, concentração, comparação de pautas e intensidade tecnológica."
)

d = data.load()
fact = d["fact"]
names = data.name_map()
years = data.years()
members = data.members_pt()

col1, col2, col3 = st.columns(3)
country_sel = col1.selectbox("País", members, index=members.index("Brasil"))
flow_sel = col2.selectbox("Fluxo", ["Exportações", "Importações"])
year_range = col3.slider("Período", years[0], years[-1], (years[0], years[-1]))
prod_col, labels, level_sel = data.hs_level_selector()

iso = data.iso_of(country_sel)
side = "exporter" if flow_sel == "Exportações" else "importer"

f = fact[
    (fact[side] == iso)
    & (fact["year"] >= year_range[0])
    & (fact["year"] <= year_range[1])
]
if f.empty:
    st.warning("Sem dados para essa seleção.")
    st.stop()

partner_col = "importer" if side == "exporter" else "exporter"

products = (
    f.groupby(prod_col, observed=True)["value"].sum().sort_values(ascending=False)
)
products = products[products > 0]
top = products.head(20).reset_index()
top["produto"] = top[prod_col].astype(str).map(labels)
top["rótulo"] = data.product_label(top[prod_col], labels)
top["v_bi"] = top["value"] / 1e9

col_a, col_b = st.columns(2)

with col_a:
    fig_bar = px.bar(
        top,
        x="v_bi",
        y="rótulo",
        orientation="h",
        color="v_bi",
        color_continuous_scale="Blues",
        labels={"v_bi": "US$ bilhões", "rótulo": ""},
        title=f"Top 20 produtos - {flow_sel.lower()} intrabloco de {country_sel}",
        hover_data={"produto": True, "rótulo": False},
    )
    fig_bar.update_coloraxes(showscale=False)
    fig_bar.update_layout(yaxis={"categoryorder": "total ascending"}, height=550)
    st.plotly_chart(fig_bar, width="stretch")

with col_b:
    fig_tree = px.treemap(
        top,
        path=["rótulo"],
        values="v_bi",
        color="v_bi",
        color_continuous_scale="Blues",
        title="Treemap dos 20 principais produtos",
    )
    fig_tree.update_coloraxes(showscale=False)
    fig_tree.update_layout(height=550)
    st.plotly_chart(fig_tree, width="stretch")

# Concentração (HHI) sobre a pauta completa, não só o top 20
st.subheader("📐 Concentração da pauta (HHI)")
hhi_val = hhi(products)
n_eq = 1 / hhi_val if hhi_val > 0 else float("nan")
if hhi_val < 0.15:
    badge, level = "🟢", "baixa"
elif hhi_val < 0.25:
    badge, level = "🟡", "moderada"
else:
    badge, level = "🔴", "alta"

c1, c2 = st.columns(2)
c1.metric(
    f"{badge} HHI ({level_sel})",
    f"{hhi_val:.4f}",
    help="HHI < 0,15: baixa concentração | 0,15-0,25: moderada | > 0,25: alta",
)
c2.metric(
    "Equivalente em produtos de mesmo peso",
    f"{n_eq:.1f}",
    help="1/HHI: a pauta concentra-se como se houvesse este número de produtos iguais.",
)
st.caption(
    f"Concentração **{level}** da pauta de {flow_sel.lower()} de {country_sel}, "
    f"calculada sobre todos os {len(products)} produtos com comércio no período."
)

# Sunburst produto x parceiro
st.subheader("🌞 Composição por parceiro e produto")
df_sun = (
    f[f[prod_col].isin(top[prod_col].head(12))]
    .groupby([partner_col, prod_col], observed=True)["value"]
    .sum()
    .reset_index()
)
df_sun = df_sun[df_sun["value"] > 0]
df_sun["parceiro"] = df_sun[partner_col].map(names)
df_sun["produto"] = data.product_label(df_sun[prod_col], labels)
fig_sun = px.sunburst(
    df_sun,
    path=["parceiro", "produto"],
    values="value",
    title=f"{flow_sel} de {country_sel} por parceiro (12 principais produtos)",
)
fig_sun.update_layout(height=560)
st.plotly_chart(fig_sun, width="stretch")

# Intensidade tecnológica (Lall 2000)
st.subheader("🔬 Intensidade tecnológica da pauta")
st.caption(
    "Classificação de Lall (2000), atribuída por subposição HS6 via concordância "
    "HS-SITC rev.3 (detalhes na Metodologia)."
)
tech = (
    f.groupby(["year", "tier"], observed=True)["value"].sum().reset_index()
)
tech = tech[tech["value"] > 0]
tech["share"] = tech["value"] / tech.groupby("year")["value"].transform("sum") * 100
fig_tech = px.area(
    tech,
    x="year",
    y="share",
    color="tier",
    category_orders={"tier": data.TIER_ORDER},
    color_discrete_map=data.TIER_COLORS,
    labels={"year": "Ano", "share": "Participação (%)", "tier": "Categoria"},
    title=f"Composição tecnológica das {flow_sel.lower()} intrabloco de {country_sel}",
)
st.plotly_chart(fig_tech, width="stretch")

# Comparação de pautas entre dois países
st.subheader("⚖️ Comparação de pautas")
other_sel = st.selectbox("Comparar com", [c for c in members if c != country_sel])
iso_b = data.iso_of(other_sel)
fb = fact[
    (fact[side] == iso_b)
    & (fact["year"] >= year_range[0])
    & (fact["year"] <= year_range[1])
]

comp_rows = []
for label, frame in ((country_sel, f), (other_sel, fb)):
    t = frame.groupby("tier", observed=True)["value"].sum()
    t = t[t > 0] / t.sum() * 100
    for tier, share in t.items():
        comp_rows.append({"país": label, "tier": tier, "share": share})

comp = pd.DataFrame(comp_rows)
fig_comp = px.bar(
    comp,
    x="share",
    y="país",
    color="tier",
    orientation="h",
    category_orders={"tier": data.TIER_ORDER},
    color_discrete_map=data.TIER_COLORS,
    labels={"share": "Participação (%)", "país": "", "tier": "Categoria"},
    title=f"Composição tecnológica comparada ({flow_sel.lower()} intrabloco)",
)
st.plotly_chart(fig_comp, width="stretch")

data.sidebar_footer()
