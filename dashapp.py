import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd

app = dash.Dash(__name__)
server = app.server

# =========================
# Carregar dados reais
# =========================
df_imoveis = pd.read_excel("data/imoveis_georreferenciados_novembro.xlsx")
df_iptu_itbi = pd.read_excel("data/serie historica iptu itbi.xlsx")
df_selic = pd.read_excel("data/Selic historica.xlsx")
# =========================
# Ajustes nas planilhas
# =========================

# Imóveis: garantir que preço é numérico
df_imoveis["Preço"] = pd.to_numeric(df_imoveis["Preço"], errors="coerce")

# IPTU/ITBI: converter coluna de data para datetime
df_iptu_itbi["Data"] = pd.to_datetime(df_iptu_itbi["Data"], errors="coerce")

# Selic: converter coluna de data para datetime
df_selic["Data"] = pd.to_datetime(df_selic["Data"], errors="coerce")

# Remover linhas com valores nulos nas colunas principais
df_imoveis = df_imoveis.dropna(subset=["Preço"])
df_iptu_itbi = df_iptu_itbi.dropna(subset=["Data"])
df_selic = df_selic.dropna(subset=["Data"])

# =========================
# Layout inicial
# =========================
app.layout = html.Div([
    html.H1("Análise Econômica Territorial"),
    html.P(f"Total de imóveis carregados: {len(df_imoveis)}"),
    html.P(f"Série histórica IPTU/ITBI: {len(df_iptu_itbi)} registros"),
    html.P(f"Série histórica Selic: {len(df_selic)} registros"),
    dcc.Graph(
        figure=px.histogram(df_imoveis, x="Preço", nbins=30, title="Distribuição de Preços dos Imóveis")
    )
])

if __name__ == "__main__":
    app.run_server(debug=True)

