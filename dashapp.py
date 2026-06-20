import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd

app = dash.Dash(__name__)
server = app.server

# =========================
# Carregar dados
# =========================
df_imoveis = pd.read_excel("data/imoveis_georreferenciados_novembro.xlsx")
df_iptu_itbi = pd.read_excel("data/serie historica iptu itbi.xlsx")
df_selic = pd.read_excel("data/Selic historica.xlsx")

# =========================
# Layout inicial
# =========================
app.layout = html.Div([
    html.H1("Análise Econômica Territorial"),
    html.P("Site inicial pronto para evoluir")
])
# Ajustes nas planilhas
df_imoveis["Preço"] = pd.to_numeric(df_imoveis["Preço"], errors="coerce")
df_iptu_itbi["Data"] = pd.to_datetime(df_iptu_itbi["Data"], errors="coerce")
df_selic["Data"] = pd.to_datetime(df_selic["Data"], errors="coerce")

# Remover linhas inválidas
df_imoveis = df_imoveis.dropna(subset=["Preço"])
df_iptu_itbi = df_iptu_itbi.dropna(subset=["Data"])
df_selic = df_selic.dropna(subset=["Data"])

if __name__ == "__main__":
    app.run_server(debug=True)
# Histograma de preços
fig_imoveis = px.histogram(df_imoveis, x="Preço", nbins=30, title="Distribuição de Preços dos Imóveis")

# Série temporal IPTU/ITBI
fig_iptu = px.line(df_iptu_itbi, x="Data", y="Valor", title="Evolução Histórica IPTU/ITBI")

# Layout atualizado
app.layout = html.Div([
    html.H1("Análise Econômica Territorial"),
    html.P(f"Total de imóveis carregados: {len(df_imoveis)}"),
    html.P(f"Série histórica IPTU/ITBI: {len(df_iptu_itbi)} registros"),
    html.P(f"Série histórica Selic: {len(df_selic)} registros"),
    dcc.Graph(figure=fig_imoveis),
    dcc.Graph(figure=fig_iptu)
])
