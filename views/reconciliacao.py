import pandas as pd
import plotly.express as px
import streamlit as st

from core import data

st.title("🔎 Reconciliação BACI × Comtrade")

d = data.load()
names = data.name_map()
dim = d["dim_country"]

st.caption(
    "Compara, ano a ano e por país, o total de comércio com o mundo segundo a "
    "**BACI** (valor reconciliado por espelho, FOB) com o total **declarado pelo "
    "próprio país ao UN Comtrade**. É o controle de qualidade numérico que "
    "acompanha o mapa de cobertura da página Metodologia."
)

col1, col2 = st.columns([1, 2])
flow_sel = col1.radio("Fluxo", ["Exportações", "Importações"], horizontal=True)
threshold = col2.slider(
    "Limiar de divergência sinalizada (|diferença| acima de)",
    min_value=5,
    max_value=30,
    value=10,
    step=1,
    format="%d%%",
)

flow_code = "X" if flow_sel == "Exportações" else "M"
baci_tbl = "world_exports" if flow_code == "X" else "world_imports"
party_col = "exporter" if flow_code == "X" else "importer"

# --- BACI total para o mundo, por país e ano (soma de todos os HS6) ---
baci = (
    d[baci_tbl]
    .groupby(["year", party_col], observed=True)["value"]
    .sum()
    .reset_index()
    .rename(columns={party_col: "iso3", "value": "baci"})
)

# --- Comtrade: total auto-declarado (partner == mundo) ---
cc = d["crosscheck"]
comtrade = (
    cc[(cc["partner_iso3"] == "WLD") & (cc["flow"] == flow_code)]
    .rename(columns={"reporter_iso3": "iso3", "comtrade_value": "comtrade"})
    [["year", "iso3", "comtrade"]]
)

# left merge: mantém todos os pares país-ano da BACI; NaN onde o país não
# declarou ao Comtrade (são exatamente as lacunas que a BACI preenche).
rec = baci.merge(comtrade, on=["year", "iso3"], how="left")
rec["diff_pct"] = (rec["baci"] - rec["comtrade"]) / rec["comtrade"] * 100
rec["país"] = rec["iso3"].map(names)
declared = rec.dropna(subset=["diff_pct"]).copy()

# --- Resumo ---
n_total = len(declared)
n_flag = int((declared["diff_pct"].abs() > threshold).sum())
median_abs = declared["diff_pct"].abs().median()
n_gap = int(rec["comtrade"].isna().sum())

m1, m2, m3 = st.columns(3)
m1.metric("Divergência absoluta mediana", f"{median_abs:.1f}%")
m2.metric(
    f"Pares país-ano sinalizados (> {threshold}%)",
    f"{n_flag} de {n_total}",
)
m3.metric("Sem declaração ao Comtrade", f"{n_gap} pares")

if flow_code == "M":
    st.info(
        "Nas **importações**, o Comtrade traz valores **CIF** (incluem frete e "
        "seguro) enquanto a BACI usa **FOB**. Espera-se, portanto, que a BACI "
        "fique sistematicamente **abaixo** do declarado: uma diferença negativa "
        "de ~5–10% é o gap CIF/FOB, não um erro.",
        icon="ℹ️",
    )
else:
    st.info(
        "Nas **exportações**, ambos os lados são FOB e diretamente comparáveis. "
        "Diferenças positivas grandes costumam indicar países que sub-declaram e "
        "cuja exportação a BACI recompõe a partir das importações dos parceiros "
        "(reconciliação de espelho).",
        icon="ℹ️",
    )

# --- Heatmap país × ano da diferença percentual ---
order = [i for i in dim["iso3"] if i in set(rec["iso3"])]
pivot = (
    declared.pivot(index="iso3", columns="year", values="diff_pct")
    .reindex(order)
)
pivot.index = [names[i] for i in pivot.index]

fig = px.imshow(
    pivot,
    color_continuous_scale="RdBu_r",
    color_continuous_midpoint=0,
    range_color=[-25, 25],
    aspect="auto",
    text_auto=".0f",
    labels={"x": "Ano", "y": "", "color": "BACI vs Comtrade (%)"},
    title=f"Diferença BACI − Comtrade (%) — {flow_sel.lower()} totais ao mundo",
)
fig.update_xaxes(type="category", tickmode="linear")
fig.update_traces(
    hovertemplate="%{y} · %{x}<br>BACI vs Comtrade: %{z:.1f}%<extra></extra>"
)
fig.update_layout(height=460)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Azul: BACI acima do declarado; vermelho: BACI abaixo. Células em branco "
    "(sem valor) são pares país-ano sem declaração ao Comtrade — onde não há "
    "com o que reconciliar e a BACI depende inteiramente dos dados de espelho."
)

# --- Tabela detalhada, sinalizando as maiores divergências ---
st.subheader("Detalhamento")
tbl = declared.sort_values("diff_pct", key=lambda s: s.abs(), ascending=False).copy()
tbl["Sinalizado"] = tbl["diff_pct"].abs() > threshold
out = pd.DataFrame(
    {
        "País": tbl["país"],
        "Ano": tbl["year"],
        "BACI": tbl["baci"].map(data.fmt_usd),
        "Comtrade": tbl["comtrade"].map(data.fmt_usd),
        "Diferença": tbl["diff_pct"].map(lambda v: f"{v:+.1f}%"),
        "Sinalizado": tbl["Sinalizado"].map({True: "⚠️", False: ""}),
    }
)
st.dataframe(out, hide_index=True, width="stretch")

data.sidebar_footer()
