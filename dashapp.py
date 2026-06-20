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
df_series = pd.read_excel("data/serie historica iptu itbi.xlsx")
df_selic = pd.read_excel("data/Selic historica.xlsx")
# =========================
# Ajustes nos imóveis
# =========================
df_imoveis["Preço"] = pd.to_numeric(df_imoveis["Preço"], errors="coerce")
df_imoveis = df_imoveis.dropna(subset=["Preço"])

# =========================
# Ajustes nas séries históricas
# =========================
# Primeira coluna é o indicador, demais são anos
df_series = df_series.set_index("ANO").T.reset_index()
df_series = df_series.melt(id_vars=["index"], var_name="Indicador", value_name="Valor")
df_series = df_series.rename(columns={"index": "Ano"})
df_series["Ano"] = pd.to_numeric(df_series["Ano"], errors="coerce")
df_series["Valor"] = pd.to_numeric(df_series["Valor"].astype(str).str.replace(",", "."), errors="coerce")

# Remover série "Numero de ITBIs"
df_series = df_series[df_series["Indicador"] != "Numero de ITBIs"]

# =========================
# Ajustes na Selic
# =========================
df_selic.columns = df_selic.columns.str.strip().str.lower()
for col in df_selic.columns:
    if "a.a" in col or "taxa" in col:
        df_selic = df_selic.rename(columns={col: "taxa"})

df_selic["data"] = pd.to_datetime(df_selic["data"], errors="coerce")
df_selic["taxa"] = pd.to_numeric(df_selic["taxa"], errors="coerce")
df_selic["ano"] = df_selic["data"].dt.year
df_selic["mes"] = df_selic["data"].dt.month
df_selic_dez = df_selic[df_selic["mes"] == 12].groupby("ano").last().reset_index()
# =========================
# Gráficos
# =========================
fig_imoveis = px.histogram(df_imoveis, x="Preço", nbins=30, title="Distribuição de Preços dos Imóveis")

# Gerar gráficos para todas as séries
graficos_series = []
for indicador in df_series["Indicador"].unique():
    fig = px.line(
        df_series[df_series["Indicador"] == indicador],
        x="Ano", y="Valor",
        title=f"Evolução Histórica - {indicador}"
    )
    graficos_series.append(dcc.Graph(figure=fig))

# Gráfico da Selic
fig_selic = px.line(df_selic_dez, x="ano", y="taxa", title="Taxa Selic (dezembro de cada ano)")

# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H1("Análise Econômica Territorial"),
    html.P(f"Total de imóveis carregados: {len(df_imoveis)}"),
    html.P(f"Séries históricas: {len(df_series['Indicador'].unique())} indicadores"),
    html.P(f"Série histórica Selic (dezembro): {len(df_selic_dez)} anos"),
    dcc.Graph(figure=fig_imoveis),
    *graficos_series,   # todos os gráficos das séries
    dcc.Graph(figure=fig_selic)
])

if __name__ == "__main__":
    app.run_server(debug=True)
