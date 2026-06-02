import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# CONFIGURAÇÃO
# =====================================================

st.set_page_config(
    page_title="BRICS Trade Dashboard",
    page_icon="🌎",
    layout="wide"
)

# =====================================================
# LEITURA DOS DADOS
# =====================================================

@st.cache_data
def load_data():

    total = pd.read_csv("trade_total.csv")
    hs2 = pd.read_csv("trade_hs2.csv")

    # valor comercial

    if "cifvalue" in total.columns and "fobvalue" in total.columns:

        total["trade_value"] = total.apply(
            lambda x: x["cifvalue"]
            if x["flowCode"] == "M"
            else x["fobvalue"],
            axis=1
        )

    if "cifvalue" in hs2.columns and "fobvalue" in hs2.columns:

        hs2["trade_value"] = hs2.apply(
            lambda x: x["cifvalue"]
            if x["flowCode"] == "M"
            else x["fobvalue"],
            axis=1
        )

    return total, hs2


total, hs2 = load_data()

# =====================================================
# MENU
# =====================================================

page = st.sidebar.radio(
    "Navegação",
    [
        "Visão Geral",
        "Parceiros Comerciais",
        "Estrutura Comercial",
        "Fluxos Bilaterais"
    ]
)

# =====================================================
# VISÃO GERAL
# =====================================================

if page == "Visão Geral":

    st.title("🌎 Comércio Internacional BRICS")

    exports = total[
        total["flowCode"] == "X"
    ]["trade_value"].sum()

    imports = total[
        total["flowCode"] == "M"
    ]["trade_value"].sum()

    balance = exports - imports

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Exportações",
        f"US$ {exports:,.0f}"
    )

    c2.metric(
        "Importações",
        f"US$ {imports:,.0f}"
    )

    c3.metric(
        "Saldo Comercial",
        f"US$ {balance:,.0f}"
    )

    st.divider()

    trade_year = (
        total
        .groupby(["refYear", "flowDesc"])
        ["trade_value"]
        .sum()
        .reset_index()
    )

    fig = px.line(
        trade_year,
        x="refYear",
        y="trade_value",
        color="flowDesc",
        markers=True,
        title="Evolução Temporal"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# PARCEIROS
# =====================================================

elif page == "Parceiros Comerciais":

    st.title("🏆 Ranking de Parceiros")

    ranking = (
        total
        .groupby("partnerDesc")
        ["trade_value"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .reset_index()
    )

    fig = px.bar(
        ranking,
        x="trade_value",
        y="partnerDesc",
        orientation="h",
        title="Principais Parceiros Comerciais"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# ESTRUTURA COMERCIAL
# =====================================================

elif page == "Estrutura Comercial":

    st.title("📦 Estrutura da Pauta Comercial")

    flow = st.selectbox(
        "Fluxo",
        hs2["flowDesc"].unique()
    )

    temp = hs2[
        hs2["flowDesc"] == flow
    ]

    products = (
        temp
        .groupby("cmdDesc")
        ["trade_value"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
        .reset_index()
    )

    col1, col2 = st.columns(2)

    with col1:

        fig_bar = px.bar(
            products,
            x="trade_value",
            y="cmdDesc",
            orientation="h",
            title="Top Produtos"
        )

        st.plotly_chart(
            fig_bar,
            use_container_width=True
        )

    with col2:

        fig_tree = px.treemap(
            products,
            path=["cmdDesc"],
            values="trade_value",
            title="Treemap"
        )

        st.plotly_chart(
            fig_tree,
            use_container_width=True
        )

# =====================================================
# FLUXOS BILATERAIS
# =====================================================

elif page == "Fluxos Bilaterais":

    st.title("🔄 Fluxos Bilaterais")

    exporters = sorted(
        hs2["reporterISO"].dropna().unique()
    )

    partners = sorted(
        hs2["partnerISO"].dropna().unique()
    )

    exporter = st.selectbox(
        "Exportador",
        exporters
    )

    partner = st.selectbox(
        "Importador/Parceiro",
        partners
    )

    temp = hs2[
        (hs2["reporterISO"] == exporter)
        &
        (hs2["partnerISO"] == partner)
    ]

    if len(temp) > 0:

        serie = (
            temp
            .groupby("refYear")
            ["trade_value"]
            .sum()
            .reset_index()
        )

        fig = px.line(
            serie,
            x="refYear",
            y="trade_value",
            markers=True,
            title=f"{exporter} x {partner}"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader(
            "Produtos Mais Comercializados"
        )

        products = (
            temp
            .groupby("cmdDesc")
            ["trade_value"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .reset_index()
        )

        fig2 = px.bar(
            products,
            x="trade_value",
            y="cmdDesc",
            orientation="h"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

    else:

        st.warning(
            "Não há dados para essa combinação."
        )