import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap, MarkerCluster

app = dash.Dash(__name__)
server = app.server   # ESSENCIAL para o Render

# =========================
# Carregar dados
# =========================
df_imoveis = pd.read_excel("data/imoveis_georreferenciados_novembro.xlsx")
df_series = pd.read_excel("data/serie historica iptu itbi.xlsx")

# Carregar shapefile dos bairros
gdf_bairros = gpd.read_file("data/municipio_completo.shp")

# =========================
# Ajustes nos imóveis
# =========================
df_imoveis["Preço"] = pd.to_numeric(df_imoveis["Preço"], errors="coerce")
df_imoveis["Preço por m²"] = pd.to_numeric(df_imoveis["Preço por m²"], errors="coerce")
df_imoveis = df_imoveis.dropna(subset=["Preço", "latitude", "longitude"])

# Estatísticas por bairro e tipo
def calcular_stats(dados):
    stats = dados.groupby("Bairro").agg(
        preco_medio=("Preço", "mean"),
        preco_max=("Preço", "max"),
        preco_min=("Preço", "min"),
        preco_m2_medio=("Preço por m²", "mean"),
        preco_m2_max=("Preço por m²", "max"),
        preco_m2_min=("Preço por m²", "min")
    ).reset_index()
    # Variação percentual vs média do município
    media_municipio = dados["Preço"].mean()
    stats["variacao_vs_municipio"] = ((stats["preco_medio"] - media_municipio) / media_municipio) * 100
    return stats

stats_bairros = calcular_stats(df_imoveis)

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
def gerar_mapa(tipo="Todos", estilo="coropletico"):
    mapa = folium.Map(location=[-23.42, -51.93], zoom_start=12)

    # Filtrar imóveis
    if tipo != "Todos":
        dados = df_imoveis[df_imoveis["Tipo"] == tipo]
    else:
        dados = df_imoveis

    # Estatísticas filtradas
    stats = calcular_stats(dados)
    gdf_stats = gdf_bairros.merge(stats, on="Bairro", how="left")

    # Coroplético
    if estilo == "coropletico":
        folium.Choropleth(
            geo_data=gdf_stats,
            data=gdf_stats,
            columns=["Bairro", "preco_medio"],
            key_on="feature.properties.Bairro",
            fill_color="YlOrRd",
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name="Preço médio dos imóveis"
        ).add_to(mapa)

        # Tooltips
        for _, row in gdf_stats.iterrows():
            tooltip = folium.Tooltip(
                f"<b>{row['Bairro']}</b><br>"
                f"Médio: R$ {row['preco_medio']:.0f}<br>"
                f"Máx: R$ {row['preco_max']:.0f}<br>"
                f"Mín: R$ {row['preco_min']:.0f}<br>"
                f"Var vs município: {row['variacao_vs_municipio']:.1f}%<br>"
                f"M² médio: R$ {row['preco_m2_medio']:.0f}"
            )
            folium.GeoJson(row["geometry"], tooltip=tooltip).add_to(mapa)

    # Pontos
    elif estilo == "pontos":
        for _, row in dados.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=4,
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
        HeatMap(
            data=dados[["latitude", "longitude"]].values.tolist(),
            radius=10, blur=15, max_zoom=12
        ).add_to(mapa)

    return mapa._repr_html_()
# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H1("Análise Econômica Territorial"),

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
            {"label": "Coroplético", "value": "coropletico"},
            {"label": "Pontos", "value": "pontos"},
            {"label": "Cluster", "value": "cluster"},
            {"label": "Calor", "value": "calor"}
        ],
        value="coropletico"
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
