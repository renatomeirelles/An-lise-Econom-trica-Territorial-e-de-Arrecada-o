import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd

app = dash.Dash(__name__)
server = app.server   # ESSENCIAL para o Render

# =========================
# Carregar dados
# =========================
df_imoveis = pd.read_excel("data/imoveis_georreferenciados_novembro.xlsx")
df_iptu_itbi = pd.read_excel("data/serie historica iptu itbi.xlsx")
df_selic = pd.read_excel("data/Selic historica.xlsx")

# =========================
# Ajustes nas planilhas
# =========================
# Imóveis
df_imoveis["Preço"] = pd.to_numeric(df_imoveis["Preço"], errors="coerce")
df_imoveis = df_imoveis.dropna(subset=["Preço"])

# IPTU/ITBI → primeira linha é o indicador, colunas são anos
df_iptu_itbi = df_iptu_itbi.melt(id_vars=["ANO"], var_name="Ano", value_name="Valor")
# Corrigir tipos
df_iptu_itbi["Ano"] = pd.to_numeric(df_iptu_itbi["Ano"], errors="coerce")
df_iptu_itbi["Valor"] = pd.to_numeric(df_iptu_itbi["Valor"], errors="coerce")

# Selic → pegar apenas valores de dezembro de cada ano
df_selic["data"] = pd.to_datetime(df_selic["data"], errors="coerce")
df_selic["% a.a."] = pd.to_numeric(df_selic["% a.a."], errors="coerce")
df_selic["ano"] = df_selic["data"].dt.year
df_selic["mes"] = df_selic["data"].dt.month
df_selic_dez = df_selic[df_selic["mes"] == 12].groupby("ano").last().reset_index()

# =========================
# Gráficos
# =========================
# Histograma de preços dos imóveis
fig_imoveis = px.histogram(
    df_imoveis,
    x="Preço",
    nbins=30,
    title="Distribuição de Preços dos Imóveis"
)

# IPTU
fig_iptu = px.line(
    df_iptu_itbi[df_iptu_itbi["ANO"] == "IPTU"],
    x="Ano", y="Valor",
    title="Evolução Histórica do IPTU"
)

# ITBI
fig_itbi = px.line(
    df_iptu_itbi[df_iptu_itbi["ANO"] == "ITBI"],
    x="Ano", y="Valor",
    title="Evolução Histórica do ITBI"
)

# Selic (dezembro de cada ano)
fig_selic = px.line(
    df_selic_dez,
    x="ano", y="% a.a.",
    title="Taxa Selic (dezembro de cada ano)"
)

# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H1("Análise Econômica Territorial"),
    html.P(f"Total de imóveis carregados: {len(df_imoveis)}"),
    html.P(f"Série histórica IPTU/ITBI: {len(df_iptu_itbi)} registros"),
    html.P(f"Série histórica Selic (dezembro): {len(df_selic_dez)} anos"),
    dcc.Graph(figure=fig_imoveis),
    dcc.Graph(figure=fig_iptu),
    dcc.Graph(figure=fig_itbi),
    dcc.Graph(figure=fig_selic)
])

if __name__ == "__main__":
    app.run_server(debug=True)
