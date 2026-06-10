import plotly.express as px
import streamlit as st

from core import data

st.title("📚 Metodologia e Fontes")

d = data.load()
names = data.name_map()

st.markdown(
    """
## Fonte principal: BACI (CEPII)

Os fluxos bilaterais usam a base **BACI, versão V202601** (HS 2012), do
[CEPII](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37),
construída a partir do UN Comtrade pela metodologia de Gaulier e Zignago (2010):

- **Reconciliação de espelho**: cada fluxo é declarado duas vezes (pelo
  exportador, FOB, e pelo importador, CIF). A BACI funde as duas declarações
  ponderando pela confiabilidade de cada declarante e remove os custos
  CIF, produzindo **um único valor FOB por fluxo**.
- **Cobertura de não declarantes**: quando só um lado declara, a declaração
  existente é aproveitada. É assim que Rússia (sem dados próprios após 2021)
  e Irã (após 2022) permanecem cobertos: pelos registros dos parceiros.
- **Limites**: a base é anual e fecha com ~13 meses de defasagem; a edição
  V202601 termina em **2024**, por isso o painel cobre 2015-2024.

Licença: Etalab 2.0 (uso livre com atribuição).
Citação: Gaulier, G. e Zignago, S. (2010), *BACI: International Trade
Database at the Product-Level*, CEPII Working Paper 2010-23.

## Indicadores

| Indicador | Fórmula | Leitura |
|---|---|---|
| Market Share | $MS_{ik} = X_{ik}/M_k$ | participação do país $i$ nas importações totais do mercado $k$ |
| VCR (Balassa) | $VCR_{ip} = (X_{ip}/X_i)/(W_p/W)$ | especialização relativa ao padrão mundial; > 1 indica vantagem revelada |
| ICII (Grubel-Lloyd) | $ICII_p = (1 - \\frac{|X_p-M_p|}{X_p+M_p}) \\times 100$ | grau de comércio dentro da mesma indústria |
| HHI | $HHI = \\sum_p s_p^2$ | concentração da pauta (>0,25 = alta) |
| CAGR | $(V_n/V_0)^{1/n}-1$ | crescimento médio anual composto |

No VCR, o denominador $W_p/W$ usa as exportações mundiais completas da BACI
(todos os ~200 exportadores), não apenas o bloco.

## Intensidade tecnológica (Lall 2000)

Cada subposição HS6 recebe uma categoria da taxonomia de **Lall (2000)**
(primários, baseados em recursos, baixa, média e alta tecnologia) pelo
caminho: HS2012 (6 dígitos) → SITC rev.3 (concordância WITS/Banco Mundial)
→ categoria Lall (lista publicada pela UNCTAD). A classificação é exata no
nível HS6; agregações por capítulo HS2 somam valores já classificados, sem
aproximação por capítulo.

**Ressalva**: capítulos como 84, 85 e 90 contêm subposições de média e de
alta tecnologia simultaneamente; por isso a classificação nunca é atribuída
ao capítulo inteiro.

Citação: Lall, S. (2000), *The Technological Structure and Performance of
Developing Country Manufactured Exports, 1985-98*, Oxford Development
Studies 28(3).

## Verificação cruzada com o UN Comtrade

Como controle de qualidade, os totais bilaterais da BACI podem ser
comparados com os valores **declarados pelos próprios países** ao UN
Comtrade. O gráfico abaixo mostra quantas células reporter x parceiro x
fluxo cada país declarou por ano: as lacunas (Rússia após 2021, Irã após
2022, Emirados e Etiópia após 2023) são exatamente o que a reconciliação
de espelho da BACI preenche.
"""
)

cc = d["crosscheck"]
avail = (
    cc.groupby(["reporter_iso3", "year"])["comtrade_value"]
    .count()
    .reset_index(name="células")
)
avail["país"] = avail["reporter_iso3"].map(names)
fig = px.density_heatmap(
    avail,
    x="year",
    y="país",
    z="células",
    color_continuous_scale="Greens",
    labels={"year": "Ano", "país": "", "células": "Células declaradas"},
    title="Declarações anuais ao UN Comtrade por país (totais bilaterais)",
)
fig.update_layout(height=420)
st.plotly_chart(fig, width="stretch")

st.markdown(
    """
## Decisões de tratamento

- Valores da BACI chegam em milhares de US$ correntes e são convertidos
  para US$ no pipeline; não há deflacionamento (valores correntes).
- O esquema de dados é estrela: uma tabela fato por nível (fluxos
  bilaterais HS6 intrabloco; exportações e importações de cada membro com
  o mundo; totais mundiais por produto) e dimensões de país, produto e
  categoria tecnológica.
- Todo o pipeline de coleta e transformação está em `pipeline/` no
  repositório e é reexecutável do zero.

**Fontes complementares**: UN Comtrade (verificação cruzada e nomes de
capítulos HS), WITS/Banco Mundial (concordância HS-SITC), UNCTAD
(classificação Lall).
"""
)

data.sidebar_footer()
