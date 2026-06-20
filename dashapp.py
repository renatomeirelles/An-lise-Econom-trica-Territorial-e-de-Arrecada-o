import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster

app = dash.Dash(__name__)
server = app.server   # ESSENCIAL para o Render

# =========================
# Carregar dados
# =========================
df_imoveis = pd.read_excel("data/imoveis_georreferenciados_novembro.xlsx")
df_series = pd.read_excel("data/serie historica iptu itbi.xlsx")
# =========================
# Ajustes nos imóveis
# =========================
df_imoveis["Preço"] = pd.to_numeric(df_imoveis["Preço"], errors="coerce")
df_imoveis = df_imoveis.dropna(subset=["Preço"])

# Estatísticas imobiliárias
preco_medio_total = df_imoveis["Preço"].mean()
preco_medio_tipo = df_imoveis.groupby("Tipo")["Preço"].mean().reset_index()
preco_medio_bairro_tipo = df_imoveis.groupby(["Bairro", "Tipo"])["Preço"].mean().reset_index()

# =========================
# Ajustes nas séries históricas
# =========================
df_series = df_series.set_index("ANO").T.reset_index()
df_series = df_series.melt(id_vars=["index"], var_name="Indicador", value_name="Valor")
df_series = df_series.rename(columns={"index": "Ano"})
df_series["Ano"] = pd.to_numeric(df_series["Ano"], errors="coerce")
df_series["Valor"] = pd.to_numeric(df_series["Valor"].astype(str).str.replace(",", "."), errors="coerce")
df_series = df_series[df_series["Indicador"].isin(["IPTU", "ITBI"])]
# =========================
# Gráfico único IPTU + ITBI
# =========================
fig_iptu_itbi = px.line(
    df_series,
    x="Ano", y="Valor", color="Indicador",
    title="Evolução Histórica IPTU e ITBI"
)

# =========================
# Função para gerar mapa Folium
# =========================
def gerar_mapa(tipo="Todos", estilo="pontos"):
    mapa = folium.Map(location=[-23.42, -51.93], zoom_start=12)

    # Filtrar imóveis por tipo
    if tipo != "Todos":
        dados = df_imoveis[df_imoveis["Tipo"] == tipo]
    else:
        dados = df_imoveis

    # Adicionar pontos
    if estilo == "pontos":
        for _, row in dados.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=5,
                popup=f"{row['Tipo']} - R$ {row['Preço']:,.0f}",
                color="blue",
                fill=True
            ).add_to(mapa)

    # Cluster
    elif estilo == "cluster":
        cluster = MarkerCluster().add_to(mapa)
        for _, row in dados.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=f"{row['Tipo']} - R$ {row['Preço']:,.0f}"
            ).add_to(cluster)

    # Heatmap
    elif estilo == "calor":
        HeatMap(data=dados[["latitude", "longitude"]].values.tolist()).add_to(mapa)

    return mapa._repr_html_()  # retorna HTML embutido
# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H1("Análise Econômica Territorial"),
    html.P(f"Preço médio geral: R$ {preco_medio_total:,.0f}"),

    # Filtros
    html.Label("Tipo de imóvel:"),
    dcc.Dropdown(
        id="filtro-tipo",
        options=[{"label": "Todos", "value": "Todos"}] +
                [{"label": t, "value": t} for t in df_imoveis["Tipo"].unique()],
        value="Todos"
    ),

    html.Label("Estilo do mapa:"),
    dcc.Dropdown(
        id="filtro-estilo",
        options=[
            {"label": "Pontos", "value": "pontos"},
            {"label": "Cluster", "value": "cluster"},
            {"label": "Calor", "value": "calor"}
        ],
        value="pontos"
    ),

    # Mapa
    html.Iframe(id="mapa", width="100%", height="600"),

    # Histograma dinâmico
    dcc.Graph(id="grafico-precos"),

    # Gráfico IPTU+ITBI
    dcc.Graph(figure=fig_iptu_itbi)
])

# =========================
# Callbacks
# =========================
@app.callback(
    Output("mapa", "srcDoc"),
    Output("grafico-precos", "figure"),
    Input("filtro-tipo", "value"),
    Input("filtro-estilo", "value")
)
def atualizar_mapa(tipo, estilo):
    mapa_html = gerar_mapa(tipo, estilo)

    # Atualizar histograma conforme filtro
    if tipo != "Todos":
        dados = df_imoveis[df_imoveis["Tipo"] == tipo]
    else:
        dados = df_imoveis

    fig_hist = px.histogram(dados, x="Preço", nbins=30, title=f"Distribuição de Preços - {tipo}")

    return mapa_html, fig_hist

if __name__ == "__main__":
    app.run_server(debug=True)
