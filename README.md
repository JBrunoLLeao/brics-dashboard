# BRICS+ Trade Dashboard

Dashboard interativo de análise do comércio internacional entre os 11
países do BRICS ampliado (Brasil, Rússia, Índia, China, África do Sul,
Egito, Etiópia, Irã, Arábia Saudita, Emirados Árabes Unidos e Indonésia),
construído com Streamlit + Plotly.

> Primeiro acesso após inatividade pode levar de 30 a 60 segundos
> (hibernação do Streamlit Community Cloud).

## Páginas

1. **Visão Geral**: mapa dos membros, comércio total do bloco, maiores
   exportadores/importadores, evolução temporal, matriz bilateral 11x11,
   participação e crescimento médio anual (CAGR).
2. **Estrutura da Pauta**: principais produtos (HS2 e HS6), treemap,
   sunburst, concentração (HHI), comparação de pautas e intensidade
   tecnológica (Lall 2000).
3. **Fluxos Bilaterais**: seleção de exportador, importador, período e
   setor; séries nos dois sentidos, saldo, assimetria e pautas da relação.
4. **Indicadores de Competitividade**: Market Share, VCR (Balassa) e
   ICII (Grubel-Lloyd), com fórmulas e leitura interpretativa.
5. **Metodologia e Fontes**: base de dados, fórmulas, classificação
   tecnológica e verificação cruzada com o UN Comtrade.

## Dados

Fonte principal: **BACI V202601** (CEPII), fluxos bilaterais anuais
HS 2012 a 6 dígitos, valores FOB em US$ correntes, 2015-2024. Fontes
complementares: UN Comtrade, WITS/Banco Mundial, UNCTAD. Detalhes e
citações na página Metodologia.

Os parquet em `data/` já estão prontos; o app não consulta APIs em
execução. Para reconstruir tudo do zero:

```sh
python pipeline/download_baci.py    # ~1,3 GB, uma única vez
python pipeline/fetch_comtrade.py   # referências e verificação cruzada
python pipeline/build_tech_map.py   # classificação tecnológica (Lall)
python pipeline/build_dataset.py    # parquet finais em data/
```

`build_tech_map.py` precisa de dois arquivos de origem baixados **manualmente**
para `pipeline/cache/` (esse diretório é ignorado pelo git e não vem no
repositório):

- `lall_hierarchy.pdf` — UNCTAD, *"SITC rev.3 products, by technological
  categories (Lall (2000))"*.
- `JobID-84_Concordance_H4_to_S3.CSV` — concordância WITS, HS 2012 (H4) 6
  dígitos → SITC rev.3 (gerada como um job de concordância no site do WITS).

Sem eles o script falha com `No such file or directory`. Também requer o
utilitário `pdftotext` (pacote `poppler-utils`) no PATH. Os lookups que ele
gera (`data/lookup_hs6_lall.csv` e `data/dim_lall.csv`) já estão versionados,
então só é preciso reexecutá-lo para reconstruir a classificação do zero.

## Execução local

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

O Streamlit imprime o endereço no terminal e costuma abrir o navegador
sozinho; se não abrir, acesse <http://localhost:8501>. Para usar outra
porta: `streamlit run app.py --server.port 8600`. Encerre com `Ctrl+C`.

Testes dos indicadores:

```sh
python -m pytest tests/
```

## Estrutura

```
app.py            entrada (st.navigation)
views/            uma página por arquivo
core/data.py      carga dos parquet (cacheada)
core/indicators.py  MS, VCR, ICII, HHI, CAGR (funções puras, testadas)
pipeline/         coleta e tratamento (reexecutável)
data/             esquema estrela em parquet + lookups
```
