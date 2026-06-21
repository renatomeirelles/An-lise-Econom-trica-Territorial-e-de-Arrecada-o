import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap, MarkerCluster
import warnings
from statsmodels.tsa.arima.model import ARIMA
import locale

# Configuração de locale para números brasileiros
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

warnings.filterwarnings("ignore")

app = dash.Dash(__name__)
server = app.server

# =========================
# Configuração Jawg
# =========================
JAWG_TOKEN = "ZK6EgfhFT6px8F8MsRfOp2S5aUMPOvNr5CEEtLmjOYjHDC2MzgI0ZJ1cJjj0C98Y"
CENTRO_MARINGA = [-23.4205, -51.9331]

def _tiles_url(estilo_jawg="jawg-dark"):
    return f"https://tile.jawg.io/{estilo_jawg}/{{z}}/{{x}}/{{y}}{{r}}.png?access-token={JAWG_TOKEN}"

# =========================
# Carregar dados
# =========================
df_imoveis = pd.read_excel("data/imoveis_georreferenciados_novembro.xlsx")
df_series = pd.read_excel("data/serie historica iptu itbi.xlsx")
gdf_bairros = gpd.read_file("data/municipio_completo.shp")
# =========================
# Ajustes nos imóveis
# =========================
df_imoveis["Preço"] = pd.to_numeric(df_imoveis["Preço"], errors="coerce")
df_imoveis["Preço por m²"] = pd.to_numeric(df_imoveis["Preço por m²"], errors="coerce")

# Remove imóveis sem preço ou coordenadas válidas
df_imoveis = df_imoveis.dropna(subset=["Preço", "latitude", "longitude"])
df_imoveis = df_imoveis[(df_imoveis["latitude"].between(-90,90)) & (df_imoveis["longitude"].between(-180,180))]

def calcular_stats(dados):
    stats = dados.groupby("Bairro").agg(
        preco_medio=("Preço", "mean"),
        preco_max=("Preço", "max"),
        preco_min=("Preço", "min"),
        preco_m2_medio=("Preço por m²", "mean"),
        preco_m2_max=("Preço por m²", "max"),
        preco_m2_min=("Preço por m²", "min")
    ).reset_index()
    media_municipio = dados["Preço"].mean()
    stats["variacao_vs_municipio"] = ((stats["preco_medio"] - media_municipio) / media_municipio) * 100
    return stats

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
# ARIMA previsões IPTU e ITBI (com reajuste de 20%)
# =========================
df_final = df_series.pivot(index="Ano", columns="Indicador", values="Valor").dropna()

# IPTU
iptu_series = df_final["IPTU"]
model_iptu = ARIMA(iptu_series, order=(1,1,1)).fit()
forecast_iptu = model_iptu.forecast(steps=2)
forecast_iptu = forecast_iptu * 1.2  # reajuste 20%

# ITBI
itbi_series = df_final["ITBI"]
model_itbi = ARIMA(itbi_series, order=(1,1,1)).fit()
forecast_itbi = model_itbi.forecast(steps=2)
# =========================
# Gráfico IPTU+ITBI com previsões (sem gap)
# =========================
df_plot = df_final.reset_index()
df_plot = df_plot.melt(id_vars="Ano", var_name="Indicador", value_name="Valor")
df_plot["Tipo"] = "Histórico"

# Previsões — incluindo 2025 para continuidade
df_forecast = pd.DataFrame({
    "Ano": [2025, 2026, 2027, 2025, 2026, 2027],
    "Indicador": ["IPTU","IPTU","IPTU","ITBI","ITBI","ITBI"],
    "Valor": [iptu_series.iloc[-1], forecast_iptu.iloc[0], forecast_iptu.iloc[1],
              itbi_series.iloc[-1], forecast_itbi.iloc[0], forecast_itbi.iloc[1]],
    "Tipo": ["Histórico","Previsão","Previsão","Histórico","Previsão","Previsão"]
})
df_plot = pd.concat([df_plot, df_forecast])

fig_iptu_itbi = px.line(
    df_plot, x="Ano", y="Valor", color="Indicador",
    line_dash="Tipo", markers=True,
    title="Evolução Histórica e Previsões IPTU e ITBI"
)

# =========================
# Paleta e faixas para coroplético
# =========================
cores = ['#FF0000','#FFA500','#FFFF00','#00FF00','#00CED1','#0000FF','#8A2BE2','#FF69B4']
faixas_preco = [120000,300000,500000,800000,1000000,1500000,2500000,5000000,10500000]

# =========================
# Funções de mapa
# =========================
def gerar_mapa_coropletico(estilo_jawg="jawg-dark"):
    stats = calcular_stats(df_imoveis)
    gdf_stats = gdf_bairros.merge(stats, left_on="NOME", right_on="Bairro", how="left")
    mapa = folium.Map(location=CENTRO_MARINGA, zoom_start=13,
                      tiles=_tiles_url(estilo_jawg), attr="Jawg Maps")

    for _, row in gdf_stats.iterrows():
        valor = row["preco_medio"]
        cor = "#D3D3D3"
        if pd.notnull(valor):
            for i in range(len(faixas_preco)-1):
                if faixas_preco[i] <= valor <= faixas_preco[i+1]:
                    cor = cores[i]
                    break
        tooltip = folium.Tooltip(
            f"<b>{row['NOME']}</b><br>"
            f"Médio: R$ {locale.format_string('%.0f', row['preco_medio'], grouping=True)}<br>"
            f"Máx: R$ {locale.format_string('%.0f', row['preco_max'], grouping=True)}<br>"
            f"Mín: R$ {locale.format_string('%.0f', row['preco_min'], grouping=True)}<br>"
            f"Var vs município: {row['variacao_vs_municipio']:.1f}%<br>"
            f"M² médio: R$ {locale.format_string('%.0f', row['preco_m2_medio'], grouping=True)}"
        )
        folium.GeoJson(row["geometry"],
            style_function=lambda feature, color=cor: {
                'fillColor': color, 'color': 'white', 'weight': 1, 'fillOpacity': 0.6
            },
            tooltip=tooltip).add_to(mapa)

    return mapa._repr_html_()

def gerar_mapa_pontos(estilo_jawg="jawg-dark"):
    dados = df_imoveis.dropna(subset=["latitude","longitude"])
    dados = dados[(dados["latitude"].between(-90,90)) & (dados["longitude"].between(-180,180))]
    # limitar para performance
    dados = dados.sample(min(len(dados), 2000))
    mapa = folium.Map(location=CENTRO_MARINGA, zoom_start=13,
                      tiles=_tiles_url(estilo_jawg), attr="Jawg Maps")
    for _, row in dados.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=2,
            color="#00aa55",
            fill=True,
            fill_color="#00aa55",
            fill_opacity=0.7,
            popup=f"{row['Tipo']} — R$ {locale.format_string('%.0f', row['Preço'], grouping=True)}"
        ).add_to(mapa)
    return mapa._repr_html_()

def gerar_mapa_cluster(estilo_jawg="jawg-dark"):
    dados = df_imoveis.dropna(subset=["latitude","longitude"])
    dados = dados[(dados["latitude"].between(-90,90)) & (dados["longitude"].between(-180,180))]
    dados = dados.sample(min(len(dados), 2000))
    mapa = folium.Map(location=CENTRO_MARINGA, zoom_start=13,
                      tiles=_tiles_url(estilo_jawg), attr="Jawg Maps")
    cluster = MarkerCluster(disableClusteringAtZoom=17).add_to(mapa)
    for _, row in dados.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=f"{row['Tipo']} — R$ {locale.format_string('%.0f', row['Preço'], grouping=True)}"
        ).add_to(cluster)
    return mapa._repr_html_()

def gerar_mapa_calor(estilo_jawg="jawg-dark"):
    dados = df_imoveis.dropna(subset=["latitude","longitude"])
    heat_data = dados[['latitude', 'longitude']].values.tolist()
    mapa = folium.Map(location=CENTRO_MARINGA, zoom_start=13,
                      tiles=_tiles_url(estilo_jawg), attr="Jawg Maps")
    HeatMap(heat_data, radius=10, blur=12, max_zoom=18).add_to(mapa)
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

    # Cards resumo
    html.Div(id="cards", style={"display": "flex", "gap": "20px", "margin": "20px 0"}),

    # Mapa
    html.Iframe(id="mapa", width="100%", height="600"),

    # Histograma dinâmico
    dcc.Graph(id="grafico-precos"),

    # Gráfico IPTU+ITBI
    dcc.Graph(figure=fig_iptu_itbi)
])

# =========================
# Callback
# =========================
@app.callback(
    Output("mapa", "srcDoc"),
    Output("grafico-precos", "figure"),
    Output("cards", "children"),
    Input("filtro-tipo", "value"),
    Input("filtro-estilo", "value")
)
def atualizar_mapa(tipo, estilo):
    # Escolher mapa
    if estilo == "coropletico":
        mapa_html = gerar_mapa_coropletico()
    elif estilo == "pontos":
        mapa_html = gerar_mapa_pontos()
    elif estilo == "cluster":
        mapa_html = gerar_mapa_cluster()
    elif estilo == "calor":
        mapa_html = gerar_mapa_calor()
    else:
        mapa_html = gerar_mapa_coropletico()

    # Filtrar dados para histograma
    dados = df_imoveis if tipo == "Todos" else df_imoveis[df_imoveis["Tipo"] == tipo]

    if len(dados) > 0:
        fig_hist = px.histogram(dados, x="Preço", nbins=30, title=f"Distribuição de Preços - {tipo}")
    else:
        fig_hist = px.histogram(title="Sem dados para este filtro")

    # Cards
    card1 = html.Div([
        html.H4("Imóveis filtrados"),
        html.P(f"Total: {len(dados)}"),
        html.P(f"Média preço: R$ {locale.format_string('%.0f', dados['Preço'].mean(), grouping=True)}" if len(dados) > 0 else "Sem dados")
    ], style={"border": "1px solid #ccc", "padding": "10px", "flex": "1"})

    card2 = html.Div([
        html.H4("Previsão IPTU"),
        html.P(f"2026: R$ {locale.format_string('%.0f', forecast_iptu.iloc[0], grouping=True)}"),
        html.P(f"2027: R$ {locale.format_string('%.0f', forecast_iptu.iloc[1], grouping=True)}")
    ], style={"border": "1px solid #ccc", "padding": "10px", "flex": "1"})

    card3 = html.Div([
        html.H4("Previsão ITBI"),
        html.P(f"2026: R$ {locale.format_string('%.0f', forecast_itbi.iloc[0], grouping=True)}"),
        html.P(f"2027: R$ {locale.format_string('%.0f', forecast_itbi.iloc[1], grouping=True)}")
    ], style={"border": "1px solid #ccc", "padding": "10px", "flex": "1"})

    cards = [card1, card2, card3]

    return mapa_html, fig_hist, cards

if __name__ == "__main__":
    app.run_server(debug=True)
