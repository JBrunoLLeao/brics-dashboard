import streamlit as st

st.set_page_config(
    page_title="BRICS+ Trade Dashboard",
    page_icon="🌐",
    layout="wide",
)

st.markdown(
    """
<style>
  [data-testid="stMetricValue"] { font-size: 1.4rem; }
  .block-container { padding-top: 1.5rem; }
</style>
""",
    unsafe_allow_html=True,
)

nav = st.navigation(
    [
        st.Page("views/overview.py", title="Visão Geral", icon="🌍", default=True),
        st.Page("views/pauta.py", title="Estrutura da Pauta", icon="📦"),
        st.Page("views/bilateral.py", title="Fluxos Bilaterais", icon="🔄"),
        st.Page("views/indicadores.py", title="Indicadores de Competitividade", icon="📊"),
        st.Page("views/metodologia.py", title="Metodologia e Fontes", icon="📚"),
    ]
)
nav.run()
