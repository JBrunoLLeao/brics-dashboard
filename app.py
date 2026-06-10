import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="BRICS+ Trade Dashboard",
    page_icon="🌐",
    layout="wide",
)

st.markdown("""
<style>
  [data-testid="stMetricValue"] { font-size: 1.4rem; }
  .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# algumas correções para leitura dos dados (vírgula sobrando no final de cada linha de dados no csv, fazendo o pandas achar que há 48 colunas quando o cabeçalho tem 47. Isso desloca todos os nomes de colunas em uma posição)
def fix_csv(path: str) -> pd.DataFrame:

    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = content.replace("\r\n", "\n").split("\n")
    fixed = "\n".join(line.rstrip(",") for line in lines)
    return pd.read_csv(io.StringIO(fixed))


@st.cache_data
def load_data():
    total = fix_csv("trade_total.csv")
    hs2   = fix_csv("trade_hs2.csv")

    for df in (total, hs2):
        # comércio: CIF pra importação, FOB pra exportação
        df["trade_value"] = df.apply(
            lambda r: r["cifvalue"] if r["flowCode"] == "M" else r["fobvalue"],
            axis=1,
        )
        df["trade_value"] = pd.to_numeric(df["trade_value"], errors="coerce").fillna(0)

    return total, hs2


total, hs2 = load_data()

BRICS_PARTNERS = sorted(total["partnerDesc"].dropna().unique())
YEARS = sorted(total["refYear"].dropna().unique().astype(int))

page = st.sidebar.radio(
    "📌 Navegação",
    [
        "🌍 Visão Geral",
        "📦 Estrutura da Pauta",
        "🔄 Fluxos Bilaterais",
        "📊 Indicadores de Competitividade",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Fonte: UN Comtrade | Países BRICS+")
st.sidebar.caption(f"Período: {YEARS[0]}–{YEARS[-1]}")

# PAGE 1 – VISÃO GERAL
if page == "🌍 Visão Geral":
    st.title("🌍 Comércio Internacional – Brasil & BRICS+")
    st.caption("Dados de exportações e importações do Brasil com os parceiros do BRICS ampliado.")

    # total de importações, exportações e saldo
    exp_total = total[total["flowCode"] == "X"]["trade_value"].sum()
    imp_total = total[total["flowCode"] == "M"]["trade_value"].sum()
    balance   = exp_total - imp_total

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Exportações (total período)", f"US$ {exp_total/1e9:,.1f} bi")
    c2.metric("🔴 Importações (total período)", f"US$ {imp_total/1e9:,.1f} bi")
    c3.metric(
        "⚖️ Saldo Comercial",
        f"US$ {balance/1e9:,.1f} bi",
        delta=f"{'Superávit' if balance >= 0 else 'Déficit'}",
        delta_color="normal" if balance >= 0 else "inverse",
    )

    st.divider()

    # Evolução temporal -> Análise das exportações/importações por ano
    trade_year = (
        total.groupby(["refYear", "flowCode"])["trade_value"]
        .sum()
        .reset_index()
    )
    trade_year["Fluxo"] = trade_year["flowCode"].map({"X": "Exportações", "M": "Importações"})
    trade_year["trade_value_bi"] = trade_year["trade_value"] / 1e9

    fig_line = px.line(
        trade_year,
        x="refYear",
        y="trade_value_bi",
        color="Fluxo",
        markers=True,
        color_discrete_map={"Exportações": "#2ecc71", "Importações": "#e74c3c"},
        labels={"refYear": "Ano", "trade_value_bi": "Valor (US$ bilhões)"},
        title="Evolução Temporal do Comércio (Brasil × BRICS+)",
    )
    fig_line.update_layout(legend_title_text="")
    st.plotly_chart(fig_line, use_container_width=True)

    # Ranking de parceiros 
    st.subheader("🏆 Principais Parceiros Comerciais")

    col_a, col_b = st.columns(2)

    with col_a:
        ranking_exp = (
            total[total["flowCode"] == "X"]
            .groupby("partnerDesc")["trade_value"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        ranking_exp["trade_value_bi"] = ranking_exp["trade_value"] / 1e9
        fig_exp = px.bar(
            ranking_exp,
            x="trade_value_bi",
            y="partnerDesc",
            orientation="h",
            color="trade_value_bi",
            color_continuous_scale="Greens",
            labels={"trade_value_bi": "US$ bi", "partnerDesc": ""},
            title="Exportações por Parceiro",
        )
        fig_exp.update_coloraxes(showscale=False)
        st.plotly_chart(fig_exp, use_container_width=True)

    with col_b:
        ranking_imp = (
            total[total["flowCode"] == "M"]
            .groupby("partnerDesc")["trade_value"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        ranking_imp["trade_value_bi"] = ranking_imp["trade_value"] / 1e9
        fig_imp = px.bar(
            ranking_imp,
            x="trade_value_bi",
            y="partnerDesc",
            orientation="h",
            color="trade_value_bi",
            color_continuous_scale="Reds",
            labels={"trade_value_bi": "US$ bi", "partnerDesc": ""},
            title="Importações por Parceiro",
        )
        fig_imp.update_coloraxes(showscale=False)
        st.plotly_chart(fig_imp, use_container_width=True)

    # Participação no comércio do bloco
    st.subheader("📈 Participação no Comércio do Bloco")
    share = (
        total.groupby("partnerDesc")["trade_value"]
        .sum()
        .reset_index()
        .sort_values("trade_value", ascending=False)
    )
    share["share_%"] = share["trade_value"] / share["trade_value"].sum() * 100

    fig_pie = px.pie(
        share,
        values="share_%",
        names="partnerDesc",
        hole=0.4,
        title="Participação de cada parceiro no comércio total do Brasil com BRICS+",
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)

    # Crescimento médio anual --> crescimento anual via fórmula do CAGR (Compound Annual Growth Rate)
    st.subheader("📉 Crescimento Médio Anual por Parceiro")
    growth_data = []
    for partner in BRICS_PARTNERS:
        df_p = (
            total[total["partnerDesc"] == partner]
            .groupby("refYear")["trade_value"]
            .sum()
            .reset_index()
            .sort_values("refYear")
        )
        if len(df_p) >= 2:
            v0, vn = df_p["trade_value"].iloc[0], df_p["trade_value"].iloc[-1]
            n = len(df_p) - 1
            cagr = ((vn / v0) ** (1 / n) - 1) * 100 if v0 > 0 else 0 # fórmula CAGR
            growth_data.append({"Parceiro": partner, "CAGR (%)": round(cagr, 1)})
    df_cagr = pd.DataFrame(growth_data).sort_values("CAGR (%)", ascending=True)
    fig_cagr = px.bar(
        df_cagr,
        x="CAGR (%)",
        y="Parceiro",
        orientation="h",
        color="CAGR (%)",
        color_continuous_scale="RdYlGn",
        title="Crescimento Médio Anual do Comércio (CAGR)",
    )
    fig_cagr.update_coloraxes(showscale=False)
    st.plotly_chart(fig_cagr, use_container_width=True)



# PAGE 2 – ESTRUTURA DA PAUTA

elif page == "📦 Estrutura da Pauta":
    st.title("📦 Estrutura da Pauta Comercial por Produto (HS2)")

    col_f1, col_f2, col_f3 = st.columns(3)
    flow_sel    = col_f1.selectbox("Fluxo", ["Exportações", "Importações"])
    partner_sel = col_f2.selectbox("Parceiro", ["Todos"] + BRICS_PARTNERS)
    year_range  = col_f3.slider("Período", min_value=YEARS[0], max_value=YEARS[-1],
                                 value=(YEARS[0], YEARS[-1]))

    flow_code = "X" if flow_sel == "Exportações" else "M"

    mask = (
        (hs2["flowCode"] == flow_code)
        & (hs2["refYear"] >= year_range[0])
        & (hs2["refYear"] <= year_range[1])
    )
    if partner_sel != "Todos":
        mask &= hs2["partnerDesc"] == partner_sel

    df_filt = hs2[mask]

    products = (
        df_filt.groupby("cmdDesc")["trade_value"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
        .reset_index()
    )
    products["trade_value_bi"] = products["trade_value"] / 1e9

    if products.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        fig_bar = px.bar(
            products,
            x="trade_value_bi",
            y="cmdDesc",
            orientation="h",
            color="trade_value_bi",
            color_continuous_scale="Blues",
            labels={"trade_value_bi": "US$ bilhões", "cmdDesc": "Produto (HS2)"},
            title=f"Top 20 Produtos – {flow_sel}",
        )
        fig_bar.update_coloraxes(showscale=False)
        fig_bar.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        fig_tree = px.treemap(
            products,
            path=["cmdDesc"],
            values="trade_value_bi",
            color="trade_value_bi",
            color_continuous_scale="Blues",
            title=f"Treemap – {flow_sel}",
        )
        fig_tree.update_coloraxes(showscale=False)
        st.plotly_chart(fig_tree, use_container_width=True)

    # Sunburst: produto × parceiro
    st.subheader("🌞 Sunburst – Produtos por Parceiro")
    df_sun = (
        df_filt.groupby(["partnerDesc", "cmdDesc"])["trade_value"]
        .sum()
        .reset_index()
    )
    top_products = products["cmdDesc"].tolist()[:15]
    df_sun = df_sun[df_sun["cmdDesc"].isin(top_products)]
    if not df_sun.empty:
        fig_sun = px.sunburst(
            df_sun,
            path=["partnerDesc", "cmdDesc"],
            values="trade_value",
            title=f"Composição por Parceiro e Produto – {flow_sel}",
        )
        st.plotly_chart(fig_sun, use_container_width=True)

    # Concentração exportadora (HHI)
    st.subheader("📐 Concentração da Pauta (HHI)")
    total_val = df_filt["trade_value"].sum()
    if total_val > 0:
        hhi_df = df_filt.groupby("cmdDesc")["trade_value"].sum().reset_index()
        hhi_df["share"] = hhi_df["trade_value"] / total_val
        hhi = (hhi_df["share"] ** 2).sum()
        color = "🟢" if hhi < 0.15 else ("🟡" if hhi < 0.25 else "🔴")
        level = "Baixa" if hhi < 0.15 else ("Moderada" if hhi < 0.25 else "Alta")
        st.metric(
            f"{color} Índice de Concentração (HHI)",
            f"{hhi:.4f}",
            help="HHI < 0,15: baixa concentração | 0,15–0,25: moderada | > 0,25: alta"
        )
        st.caption(f"Concentração **{level}** da pauta de {flow_sel.lower()}.")

# PAGE 3 – FLUXOS BILATERAIS

elif page == "🔄 Fluxos Bilaterais":
    st.title("🔄 Fluxos Bilaterais")
    st.caption("Analise o comércio entre o Brasil e um parceiro específico do BRICS+.")

    col_f1, col_f2, col_f3 = st.columns(3)
    partner_sel = col_f1.selectbox("Parceiro", BRICS_PARTNERS)
    year_range  = col_f2.slider("Período", YEARS[0], YEARS[-1], (YEARS[0], YEARS[-1]))
    flow_sel    = col_f3.selectbox("Fluxo", ["Ambos", "Exportações", "Importações"])

    mask = (
        (hs2["partnerDesc"] == partner_sel)
        & (hs2["refYear"] >= year_range[0])
        & (hs2["refYear"] <= year_range[1])
    )
    if flow_sel == "Exportações":
        mask &= hs2["flowCode"] == "X"
    elif flow_sel == "Importações":
        mask &= hs2["flowCode"] == "M"

    df_bil = hs2[mask]

    if df_bil.empty:
        st.warning("Sem dados para essa seleção.")
        st.stop()

    # Evolução temporal bilateral
    serie = df_bil.groupby(["refYear", "flowCode"])["trade_value"].sum().reset_index()
    serie["Fluxo"] = serie["flowCode"].map({"X": "Exportações", "M": "Importações"})
    serie["valor_bi"] = serie["trade_value"] / 1e9

    fig_bil = px.line(
        serie,
        x="refYear",
        y="valor_bi",
        color="Fluxo",
        markers=True,
        color_discrete_map={"Exportações": "#2ecc71", "Importações": "#e74c3c"},
        labels={"refYear": "Ano", "valor_bi": "Valor (US$ bilhões)"},
        title=f"Brasil ↔ {partner_sel}: Evolução Temporal",
    )
    st.plotly_chart(fig_bil, use_container_width=True)

    # Saldo bilateral
    exp_bi = df_bil[df_bil["flowCode"] == "X"]["trade_value"].sum()
    imp_bi = df_bil[df_bil["flowCode"] == "M"]["trade_value"].sum()
    saldo  = exp_bi - imp_bi

    c1, c2, c3 = st.columns(3)
    c1.metric("Exportações", f"US$ {exp_bi/1e9:,.2f} bi")
    c2.metric("Importações", f"US$ {imp_bi/1e9:,.2f} bi")
    c3.metric(
        "Saldo",
        f"US$ {saldo/1e9:,.2f} bi",
        delta="Superávit" if saldo >= 0 else "Déficit",
        delta_color="normal" if saldo >= 0 else "inverse",
    )

    st.divider()

    # Pauta de exportações x importações
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader(f"🟢 O Brasil exporta para {partner_sel}")
        prod_exp = (
            df_bil[df_bil["flowCode"] == "X"]
            .groupby("cmdDesc")["trade_value"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .reset_index()
        )
        prod_exp["valor_bi"] = prod_exp["trade_value"] / 1e9
        if not prod_exp.empty:
            fig_e = px.bar(
                prod_exp,
                x="valor_bi",
                y="cmdDesc",
                orientation="h",
                color="valor_bi",
                color_continuous_scale="Greens",
                labels={"valor_bi": "US$ bi", "cmdDesc": ""},
            )
            fig_e.update_coloraxes(showscale=False)
            fig_e.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_e, use_container_width=True)

    with col_b:
        st.subheader(f"🔴 O Brasil importa de {partner_sel}")
        prod_imp = (
            df_bil[df_bil["flowCode"] == "M"]
            .groupby("cmdDesc")["trade_value"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .reset_index()
        )
        prod_imp["valor_bi"] = prod_imp["trade_value"] / 1e9
        if not prod_imp.empty:
            fig_i = px.bar(
                prod_imp,
                x="valor_bi",
                y="cmdDesc",
                orientation="h",
                color="valor_bi",
                color_continuous_scale="Reds",
                labels={"valor_bi": "US$ bi", "cmdDesc": ""},
            )
            fig_i.update_coloraxes(showscale=False)
            fig_i.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_i, use_container_width=True)

    # Composição por produto ao longo do tempo (top 5)
    st.subheader("📊 Evolução dos Principais Produtos Exportados")
    top5_exp = prod_exp["cmdDesc"].head(5).tolist() if not prod_exp.empty else []
    if top5_exp:
        df_top = (
            df_bil[(df_bil["flowCode"] == "X") & (df_bil["cmdDesc"].isin(top5_exp))]
            .groupby(["refYear", "cmdDesc"])["trade_value"]
            .sum()
            .reset_index()
        )
        df_top["valor_bi"] = df_top["trade_value"] / 1e9
        # Shorten labels for display
        df_top["produto_curto"] = df_top["cmdDesc"].apply(lambda x: x[:40] + "..." if len(x) > 40 else x)
        fig_stack = px.area(
            df_top,
            x="refYear",
            y="valor_bi",
            color="produto_curto",
            labels={"refYear": "Ano", "valor_bi": "US$ bi", "produto_curto": "Produto"},
            title="Evolução dos Top 5 Produtos Exportados",
        )
        st.plotly_chart(fig_stack, use_container_width=True)



# PAGE 4 – INDICADORES DE COMPETITIVIDADE

elif page == "📊 Indicadores de Competitividade":
    st.title("📊 Indicadores de Competitividade")
    st.caption("Market Share (MS), Vantagem Comparativa Revelada (VCR) e Índice de Comércio Intra-Industrial (ICII).")

    col_f1, col_f2 = st.columns(2)
    partner_sel = col_f1.selectbox("Parceiro", ["Todos"] + BRICS_PARTNERS)
    year_sel    = col_f2.selectbox("Ano de referência", YEARS[::-1])

    df_year = hs2[hs2["refYear"] == year_sel].copy()
    if partner_sel != "Todos":
        df_year_p = df_year[df_year["partnerDesc"] == partner_sel]
    else:
        df_year_p = df_year.copy()

    # Market Share 
    st.subheader("📌 Market Share (MS)")
    st.latex(r"MS_{ik} = \frac{X_{ik}}{X_k}")
    st.caption("Participação do Brasil nas exportações de cada produto para o(s) parceiro(s) selecionado(s).")

    exp_year = df_year_p[df_year_p["flowCode"] == "X"]
    xk_total = exp_year["trade_value"].sum()

    ms_df = (
        exp_year.groupby("cmdDesc")["trade_value"]
        .sum()
        .reset_index()
        .rename(columns={"trade_value": "Xik"})
    )
    ms_df["MS (%)"] = ms_df["Xik"] / xk_total * 100 if xk_total > 0 else 0
    ms_df = ms_df.sort_values("MS (%)", ascending=False).head(20)
    ms_df["Xik_bi"] = ms_df["Xik"] / 1e9

    if not ms_df.empty:
        fig_ms = px.bar(
            ms_df,
            x="MS (%)",
            y="cmdDesc",
            orientation="h",
            color="MS (%)",
            color_continuous_scale="Blues",
            labels={"cmdDesc": "Produto"},
            title=f"Market Share por Produto – {year_sel}",
        )
        fig_ms.update_coloraxes(showscale=False)
        fig_ms.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_ms, use_container_width=True)

    #  VCR 
    st.divider()
    st.subheader("📌 Vantagem Comparativa Revelada (VCR – Balassa)")
    st.latex(r"VCR = \frac{X_{ik}/X_i}{X_k/X}")
    st.caption("VCR > 1: o Brasil tem vantagem comparativa revelada nesse produto. VCR < 1: desvantagem.")

    # Xi = exportações do Brasil (reporter) para todos os parceiros, por produto
    df_all_exp = hs2[(hs2["refYear"] == year_sel) & (hs2["flowCode"] == "X")]
    xi_df = df_all_exp.groupby("cmdDesc")["trade_value"].sum().reset_index()
    xi_df.columns = ["cmdDesc", "Xi"]
    Xi_total = xi_df["Xi"].sum()  # total exportado pelo Brasil (X_i)

    # Xk = exportações totais do Brasil para o(s) parceiro(s) selecionado(s), por produto
    xk_df = (
        exp_year.groupby("cmdDesc")["trade_value"]
        .sum()
        .reset_index()
    )
    xk_df.columns = ["cmdDesc", "Xik"]
    Xk_total = xk_df["Xik"].sum()  # total para o parceiro (X_k)

    vcr_df = xk_df.merge(xi_df, on="cmdDesc", how="inner")
    if Xi_total > 0 and Xk_total > 0:
        vcr_df["VCR"] = (vcr_df["Xik"] / Xk_total) / (vcr_df["Xi"] / Xi_total)
    else:
        vcr_df["VCR"] = 0

    vcr_df = vcr_df.sort_values("VCR", ascending=False).head(20)
    vcr_df["Vantagem"] = vcr_df["VCR"].apply(
        lambda v: "✅ Com vantagem (VCR > 1)" if v >= 1 else "❌ Sem vantagem (VCR < 1)"
    )

    if not vcr_df.empty:
        fig_vcr = px.bar(
            vcr_df,
            x="VCR",
            y="cmdDesc",
            orientation="h",
            color="Vantagem",
            color_discrete_map={
                "✅ Com vantagem (VCR > 1)": "#2ecc71",
                "❌ Sem vantagem (VCR < 1)": "#e74c3c",
            },
            labels={"cmdDesc": "Produto"},
            title=f"VCR por Produto – {year_sel}",
        )
        fig_vcr.add_vline(x=1, line_dash="dash", line_color="gray", annotation_text="VCR = 1")
        fig_vcr.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_vcr, use_container_width=True)

    # ICII
    st.divider()
    st.subheader("📌 Índice de Comércio Intra-Industrial (ICII)")

    st.latex(
        r"ICII_i = \left(1 - \frac{|X_i - M_i|}{X_i + M_i}\right)\times100"
    )

    st.caption(
        "O gráfico mostra os produtos com maior integração intra-industrial. "
        "A métrica agregada abaixo responde à pergunta: "
        "'Qual o grau de comércio intraindustrial entre o Brasil e o parceiro selecionado?'"
    )

    exp_p = (
        df_year_p[df_year_p["flowCode"] == "X"]
        .groupby("cmdDesc")["trade_value"]
        .sum()
        .rename("Xk")
    )

    imp_p = (
        df_year_p[df_year_p["flowCode"] == "M"]
        .groupby("cmdDesc")["trade_value"]
        .sum()
        .rename("Mk")
    )

    icii_df = (
        pd.concat([exp_p, imp_p], axis=1)
        .fillna(0)
        .reset_index()
    )

    icii_df = icii_df[(icii_df["Xk"] + icii_df["Mk"]) > 0]

    icii_df["ICII"] = (
        1 - abs(icii_df["Xk"] - icii_df["Mk"])
        / (icii_df["Xk"] + icii_df["Mk"])
    ) * 100

    numerador = (
        (icii_df["Xk"] + icii_df["Mk"]).sum()
        - abs(icii_df["Xk"] - icii_df["Mk"]).sum()
    )

    denominador = (
        icii_df["Xk"] + icii_df["Mk"]
    ).sum()

    icii_agregado = (
        100 * numerador / denominador
        if denominador > 0
        else 0
    )

    if icii_agregado >= 60:
        nivel = "Alta"
        emoji = "🟢"
    elif icii_agregado >= 30:
        nivel = "Moderada"
        emoji = "🟡"
    else:
        nivel = "Baixa"
        emoji = "🔴"

    st.metric(
        f"{emoji} ICII Agregado (Grubel-Lloyd)",
        f"{icii_agregado:.1f}",
    )

    st.caption(
        f"Integração intra-industrial **{nivel.lower()}** "
        f"entre o Brasil e "
        f"{'os países BRICS+' if partner_sel == 'Todos' else partner_sel} "
        f"em {year_sel}."
    )

    st.subheader("Produtos com Maior ICII")

    icii_top = (
        icii_df
        .sort_values("ICII", ascending=False)
        .head(20)
    )

    if not icii_top.empty:

        fig_icii = px.bar(
            icii_top,
            x="ICII",
            y="cmdDesc",
            orientation="h",
            color="ICII",
            color_continuous_scale="Purples",
            range_x=[0, 100],
            labels={
                "cmdDesc": "Produto",
                "ICII": "ICII (0–100)"
            },
            title=f"Top 20 Produtos com Maior ICII – {year_sel}",
        )

        fig_icii.update_coloraxes(showscale=False)
        fig_icii.update_layout(
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(
            fig_icii,
            use_container_width=True
        )

    st.subheader("Distribuição dos Produtos por Faixa de ICII")

    faixas = pd.cut(
        icii_df["ICII"],
        bins=[0, 20, 40, 60, 80, 100],
        include_lowest=True
    )

    hist_df = (
        faixas.value_counts()
        .sort_index()
        .reset_index()
    )

    hist_df.columns = ["Faixa", "Quantidade"]

    fig_hist = px.bar(
        hist_df,
        x="Faixa",
        y="Quantidade",
        labels={
            "Faixa": "Faixa de ICII",
            "Quantidade": "Número de Produtos"
        },
        title="Distribuição dos Produtos por Grau de Integração"
    )

    st.plotly_chart(
        fig_hist,
        use_container_width=True
    )

