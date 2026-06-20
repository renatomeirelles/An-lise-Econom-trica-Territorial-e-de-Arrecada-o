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

