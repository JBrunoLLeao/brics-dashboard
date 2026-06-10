import pandas as pd
import plotly.express as px
import streamlit as st

from core import data

st.title("🔄 Fluxos Bilaterais")
st.caption(
    "Comércio entre um par de membros: selecione exportador, importador, "
    "período e produto/setor."
)

d = data.load()
fact = d["fact"]
names = data.name_map()
years = data.years()
hs2_labels = data.hs2_label_map()

col1, col2, col3, col4 = st.columns(4)
exp_sel = col1.selectbox("País exportador", data.members_pt(), index=data.members_pt().index("Brasil"))
imp_options = [c for c in data.members_pt() if c != exp_sel]
imp_sel = col2.selectbox("País importador", imp_options, index=imp_options.index("China") if "China" in imp_options else 0)
year_range = col3.slider("Período", years[0], years[-1], (years[0], years[-1]))
chapters = ["Todos os setores"] + [hs2_labels[h] for h in sorted(hs2_labels)]
chapter_sel = col4.selectbox("Produto/setor (capítulo HS2)", chapters)
prod_col, prod_labels, level_sel = data.hs_level_selector()

iso_a, iso_b = data.iso_of(exp_sel), data.iso_of(imp_sel)

pair = fact[
    (fact["year"] >= year_range[0])
    & (fact["year"] <= year_range[1])
    & (
        ((fact["exporter"] == iso_a) & (fact["importer"] == iso_b))
        | ((fact["exporter"] == iso_b) & (fact["importer"] == iso_a))
    )
]
if chapter_sel != "Todos os setores":
    pair = pair[pair["hs2"] == chapter_sel.split(" - ")[0]]

if pair.empty:
    st.warning("Sem dados para essa seleção.")
    st.stop()

ab = pair[pair["exporter"] == iso_a]  # exportador selecionado -> importador
ba = pair[pair["exporter"] == iso_b]  # fluxo reverso

v_ab, v_ba = ab["value"].sum(), ba["value"].sum()
saldo = v_ab - v_ba

c1, c2, c3 = st.columns(3)
c1.metric(f"{exp_sel} → {imp_sel}", data.fmt_usd(v_ab))
c2.metric(f"{imp_sel} → {exp_sel}", data.fmt_usd(v_ba))
c3.metric(
    f"Saldo de {exp_sel} na relação",
    data.fmt_usd(saldo),
    delta="Superávit" if saldo >= 0 else "Déficit",
    delta_color="normal" if saldo >= 0 else "inverse",
)

asym = abs(saldo) / (v_ab + v_ba) * 100 if (v_ab + v_ba) > 0 else float("nan")
st.caption(
    f"Índice de assimetria da relação: **{asym:.0f}%** do comércio bilateral é "
    f"desequilíbrio (0% = fluxo equilibrado, 100% = comércio em um sentido só)."
)

# Evolução temporal nos dois sentidos
serie = (
    pair.groupby(["year", "exporter"], observed=True)["value"].sum().reset_index()
)
serie["sentido"] = serie["exporter"].map(
    {iso_a: f"{exp_sel} → {imp_sel}", iso_b: f"{imp_sel} → {exp_sel}"}
)
serie["v_bi"] = serie["value"] / 1e9
fig_serie = px.line(
    serie,
    x="year",
    y="v_bi",
    color="sentido",
    markers=True,
    color_discrete_sequence=["#2ecc71", "#e74c3c"],
    labels={"year": "Ano", "v_bi": "US$ bilhões", "sentido": ""},
    title=f"{exp_sel} ↔ {imp_sel}: evolução temporal",
)
st.plotly_chart(fig_serie, width="stretch")

# Pautas dos dois sentidos
st.subheader(f"Pauta da relação bilateral ({level_sel})")
col_a, col_b = st.columns(2)


def top_products(frame: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    out = (
        frame.groupby(prod_col, observed=True)["value"]
        .sum()
        .sort_values(ascending=False)
        .head(n)
        .reset_index()
    )
    out["produto"] = out[prod_col].astype(str).map(prod_labels).str.slice(0, 55)
    out["v_mi"] = out["value"] / 1e6
    return out[out["value"] > 0]


with col_a:
    st.markdown(f"**🟢 {exp_sel} exporta para {imp_sel}**")
    prod_ab = top_products(ab)
    if not prod_ab.empty:
        fig = px.bar(
            prod_ab,
            x="v_mi",
            y="produto",
            orientation="h",
            color="v_mi",
            color_continuous_scale="Greens",
            labels={"v_mi": "US$ milhões", "produto": ""},
        )
        fig.update_coloraxes(showscale=False)
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=480)
        st.plotly_chart(fig, width="stretch")

with col_b:
    st.markdown(f"**🔴 {imp_sel} exporta para {exp_sel}**")
    prod_ba = top_products(ba)
    if not prod_ba.empty:
        fig = px.bar(
            prod_ba,
            x="v_mi",
            y="produto",
            orientation="h",
            color="v_mi",
            color_continuous_scale="Reds",
            labels={"v_mi": "US$ milhões", "produto": ""},
        )
        fig.update_coloraxes(showscale=False)
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=480)
        st.plotly_chart(fig, width="stretch")

# Evolução dos principais produtos do sentido selecionado
st.subheader(f"Evolução dos principais produtos ({exp_sel} → {imp_sel})")
top5 = top_products(ab, n=5)[prod_col].tolist()
if top5:
    df_top = (
        ab[ab[prod_col].isin(top5)]
        .groupby(["year", prod_col], observed=True)["value"]
        .sum()
        .reset_index()
    )
    df_top["produto"] = df_top[prod_col].astype(str).map(prod_labels).str.slice(0, 45)
    df_top["v_mi"] = df_top["value"] / 1e6
    fig_area = px.area(
        df_top,
        x="year",
        y="v_mi",
        color="produto",
        labels={"year": "Ano", "v_mi": "US$ milhões", "produto": "Produto"},
    )
    st.plotly_chart(fig_area, width="stretch")

data.sidebar_footer()
