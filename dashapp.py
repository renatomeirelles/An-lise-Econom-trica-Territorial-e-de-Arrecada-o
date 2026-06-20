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

# IPTU/ITBI → colunas: "ANO", "IPTU", "ITBI"
df_iptu_itbi["ANO"] = pd.to_numeric(df_iptu_itbi["ANO"], errors="coerce")
df_iptu_itbi["IPTU"] = pd.to_numeric(df_iptu_itbi["IPTU"], errors="coerce")
df_iptu_itbi["ITBI"] = pd.to_numeric(df_iptu_itbi["ITBI"], errors="coerce")

# Selic → colunas: "data", "% a.a."
df_selic["data"] = pd.to_datetime(df_selic["data"], errors="coerce")
df_selic["% a.a."] = pd.to_numeric(df_selic["% a.a."], errors="coerce")

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

# Série temporal IPTU
fig_iptu = px.line(
    df_iptu_itbi,
    x="ANO",
    y="IPTU",
    title="Evolução Histórica do IPTU"
)

# Série temporal ITBI
fig_itbi = px.line(
    df_iptu_itbi,
    x="ANO",
    y="ITBI",
    title="Evolução Histórica do ITBI"
)

# Série temporal Selic
fig_selic = px.line(
    df_selic,
    x="data",
    y="% a.a.",
    title="Taxa Selic ao longo do tempo"
)

# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H1("Análise Econômica Territorial"),
    html.P(f"Total de imóveis carregados: {len(df_imoveis)}"),
    html.P(f"Série histórica IPTU: {len(df_iptu_itbi)} anos"),
    html.P(f"Série histórica Selic: {len(df_selic)} registros"),
    dcc.Graph(figure=fig_imoveis),
    dcc.Graph(figure=fig_iptu),
    dcc.Graph(figure=fig_itbi),
    dcc.Graph(figure=fig_selic)
])

if __name__ == "__main__":
    app.run_server(debug=True)
