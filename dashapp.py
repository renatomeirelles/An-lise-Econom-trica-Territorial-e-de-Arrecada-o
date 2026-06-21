import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap, MarkerCluster
import warnings
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")

# Tema escuro profissional (Bootswatch Darkly)
external_stylesheets = ["https://cdnjs.cloudflare.com/ajax/libs/bootswatch/5.3.0/darkly/bootstrap.min.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = "Inteligência Fiscal e Territorial - Modelagem Econométrica — Maringá"

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
# ARIMA previsões IPTU e ITBI (treino até 2025, previsão 2026–2027)
# =========================
df_final = df_series.pivot(index="Ano", columns="Indicador", values="Valor").dropna()
df_treino = df_final[df_final.index <= 2025]  # treino até 2025

# IPTU
iptu_series = df_treino["IPTU"]
model_iptu = ARIMA(iptu_series, order=(1,1,1)).fit()
forecast_iptu = model_iptu.forecast(steps=2)  # apenas 2026 e 2027
forecast_iptu = forecast_iptu * 1.2           # reajuste 20% em cada ano

# ITBI
itbi_series = df_treino["ITBI"]
model_itbi = ARIMA(itbi_series, order=(1,1,1)).fit()
forecast_itbi = model_itbi.forecast(steps=2)  # apenas 2026 e 2027

# =========================
# Séries históricas formatadas (para uso no gráfico)
# =========================
iptu_hist = iptu_series.reset_index()
iptu_hist.columns = ["Ano", "Valor"]
iptu_hist["Indicador"] = "IPTU"

itbi_hist = itbi_series.reset_index()
itbi_hist.columns = ["Ano", "Valor"]
itbi_hist["Indicador"] = "ITBI"

# =========================
# Previsões formatadas (corrigido)
# =========================
iptu_forecast = pd.DataFrame({
    "Ano": [2026, 2027],
    "Valor": forecast_iptu.values,
    "Indicador": "IPTU"
})

itbi_forecast = pd.DataFrame({
    "Ano": [2026, 2027],
    "Valor": forecast_itbi.values,
    "Indicador": "ITBI"
})
# =========================
# Gráfico IPTU+ITBI contínuo (sem gap)
# =========================

# Concatenar histórico + previsão em uma única série para cada indicador
iptu_full = pd.concat([iptu_hist, iptu_forecast], ignore_index=True)
itbi_full = pd.concat([itbi_hist, itbi_forecast], ignore_index=True)

# Juntar tudo em um único DataFrame
df_full = pd.concat([iptu_full, itbi_full], ignore_index=True)

fig_iptu_itbi = px.line(
    df_full,
    x="Ano",
    y="Valor",
    color="Indicador",
    markers=True,
    title="Evolução Histórica e Previsões IPTU e ITBI (2026–2027)"
)

# Estilo das linhas: sólido até 2025, pontilhado a partir de 2026
for indicador in ["IPTU", "ITBI"]:
    fig_iptu_itbi.add_scatter(
        x=df_full[df_full["Ano"] >= 2026]["Ano"],
        y=df_full[(df_full["Ano"] >= 2026) & (df_full["Indicador"] == indicador)]["Valor"],
        mode="lines+markers",
        name=f"{indicador} Previsão",
        line=dict(dash="dash")
    )

fig_iptu_itbi.update_xaxes(dtick=1)
fig_iptu_itbi.update_layout(plot_bgcolor="#222", paper_bgcolor="#222", font_color="#eee")

# =========================
# Paleta e faixas para coroplético
# =========================
cores = ['#FF0000','#FFA500','#FFFF00','#00FF00','#00CED1','#0000FF','#8A2BE2','#FF69B4']
faixas_preco = [120000,300000,500000,800000,1000000,1500000,2500000,5000000,10500000]

# =========================
# Funções de mapa (com fundo escuro reforçado)
# =========================
def _map_base(estilo_jawg="jawg-dark"):
    mapa = folium.Map(location=CENTRO_MARINGA, zoom_start=13,
                      tiles=_tiles_url(estilo_jawg), attr="Jawg Maps",
                      control_scale=False, prefer_canvas=True)
    # Forçar fundo escuro no HTML do mapa
    mapa.get_root().html.add_child(folium.Element(
        "<style>html, body {background-color:#222 !important;}</style>"
    ))
    return mapa

def gerar_mapa_coropletico(dados, estilo_jawg="jawg-dark"):
    stats = calcular_stats(dados)
    gdf_stats = gdf_bairros.merge(stats, left_on="NOME", right_on="Bairro", how="left")
    mapa = _map_base(estilo_jawg)

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
            f"Médio: R$ {row['preco_medio']:,.0f}".replace(",", ".") + "<br>"
            f"Máx: R$ {row['preco_max']:,.0f}".replace(",", ".") + "<br>"
            f"Mín: R$ {row['preco_min']:,.0f}".replace(",", ".") + "<br>"
            f"Var vs município: {row['variacao_vs_municipio']:.1f}%<br>"
            f"M² médio: R$ {row['preco_m2_medio']:,.0f}".replace(",", ".")
        )
        folium.GeoJson(row["geometry"],
            style_function=lambda feature, color=cor: {
                'fillColor': color, 'color': 'white', 'weight': 1, 'fillOpacity': 0.6
            },
            tooltip=tooltip).add_to(mapa)

    return mapa._repr_html_()

def gerar_mapa_pontos(dados, estilo_jawg="jawg-dark"):
    dados = dados.sample(min(len(dados), 2000))  # limita para performance
    mapa = _map_base(estilo_jawg)
    for _, row in dados.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=2,
            color="#00aa55",
            fill=True,
            fill_color="#00aa55",
            fill_opacity=0.7,
            popup=f"{row['Tipo']} — R$ {row['Preço']:,.0f}".replace(",", ".")
        ).add_to(mapa)
    return mapa._repr_html_()

def gerar_mapa_cluster(dados, estilo_jawg="jawg-dark"):
    dados = dados.sample(min(len(dados), 2000))
    mapa = _map_base(estilo_jawg)
    cluster = MarkerCluster(disableClusteringAtZoom=17).add_to(mapa)
    for _, row in dados.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=f"{row['Tipo']} — R$ {row['Preço']:,.0f}".replace(",", ".")
        ).add_to(cluster)
    return mapa._repr_html_()

def gerar_mapa_calor(dados, estilo_jawg="jawg-dark"):
    heat_data = dados[['latitude', 'longitude']].values.tolist()
    mapa = _map_base(estilo_jawg)
    HeatMap(heat_data, radius=10, blur=12, max_zoom=18).add_to(mapa)
    return mapa._repr_html_()
# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H1("Inteligência Fiscal e Territorial - Modelagem Econométrica — Maringá",
            style={"textAlign": "center", "marginBottom": "30px", "color": "#eee"}),

    # Filtros
    html.Div([
        html.Div([
            html.Label("Tipo de imóvel:", style={"color": "#eee"}),
            dcc.Dropdown(
                id="filtro-tipo",
                options=[{"label": "Todos", "value": "Todos"}] +
                        [{"label": t, "value": t} for t in df_imoveis["Tipo"].unique()],
                value="Todos",
                clearable=False,
                style={"color": "#000"}
            )
        ], style={"flex": "1"}),

        html.Div([
            html.Label("Estilo do mapa:", style={"color": "#eee"}),
            dcc.Dropdown(
                id="filtro-estilo",
                options=[
                    {"label": "Coroplético", "value": "coropletico"},
                    {"label": "Pontos", "value": "pontos"},
                    {"label": "Cluster", "value": "cluster"},
                    {"label": "Calor", "value": "calor"}
                ],
                value="coropletico",
                clearable=False,
                style={"color": "#000"}
            )
        ], style={"flex": "1"})
    ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),

    # Linha de cards resumo (callback vai preencher aqui)
    html.Div(id="cards", style={"display":"flex","gap":"20px","margin":"20px 0"}),

    # Mapa + gráfico de distribuição lado a lado
    html.Div([
        html.Div([
            html.Iframe(id="mapa", width="100%", height="600",
                        style={"border":"none","backgroundColor":"#222"})
        ], style={"flex":"2"}),

        html.Div([
            dcc.Graph(id="grafico-precos",
                      style={"height":"600px","backgroundColor":"#222"})
        ], style={"flex":"1","backgroundColor":"#222","padding":"10px","border":"1px solid #444"})
    ], style={"display":"flex","gap":"20px"}),

    # Gráfico IPTU+ITBI
    html.Div([
        dcc.Graph(figure=fig_iptu_itbi,
                  style={"marginTop":"30px","backgroundColor":"#222"})
    ], style={"backgroundColor":"#222","padding":"10px","marginTop":"20px","border":"1px solid #444"})
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
    try:
        dados = df_imoveis if tipo == "Todos" else df_imoveis[df_imoveis["Tipo"] == tipo]

        # Escolher mapa
        if estilo == "coropletico":
            mapa_html = gerar_mapa_coropletico(dados)
        elif estilo == "pontos":
            mapa_html = gerar_mapa_pontos(dados)
        elif estilo == "cluster":
            mapa_html = gerar_mapa_cluster(dados)
        elif estilo == "calor":
            mapa_html = gerar_mapa_calor(dados)
        else:
            mapa_html = gerar_mapa_coropletico(dados)

        # Histograma
        if len(dados) > 0:
            fig_hist = px.histogram(dados, x="Preço", nbins=30,
                                    title=f"Distribuição de Vendas - {tipo}")
        else:
            fig_hist = px.histogram(title="Sem dados para este filtro")
        fig_hist.update_layout(plot_bgcolor="#222", paper_bgcolor="#222", font_color="#eee")

        # Cards horizontais
        card1 = html.Div([
            html.H4("Imóveis filtrados", style={"color": "#eee"}),
            html.P(f"Total: {len(dados)}", style={"color": "#eee"}),
            html.P(f"Média preço: R$ {dados['Preço'].mean():,.0f}".replace(",", ".") if len(dados) > 0 else "Sem dados", style={"color": "#eee"}),
            html.P(f"Média preço/m²: R$ {dados['Preço por m²'].mean():,.0f}".replace(",", ".") if len(dados) > 0 else "Sem dados", style={"color": "#eee"})
        ], style={"border":"1px solid #444","padding":"15px","flex":"1","backgroundColor":"#222"}),

        card2 = html.Div([
            html.H4("Previsão IPTU", style={"color": "#eee"}),
            html.P(f"2026: R$ {forecast_iptu.iloc[0]:,.0f}".replace(",", "."), style={"color": "#eee"}),
            html.P(f"2027: R$ {forecast_iptu.iloc[1]:,.0f}".replace(",", "."), style={"color": "#eee"})
        ], style={"border":"1px solid #444","padding":"15px","flex":"1","backgroundColor":"#222"}),

        card3 = html.Div([
            html.H4("Previsão ITBI", style={"color": "#eee"}),
            html.P(f"2026: R$ {forecast_itbi.iloc[0]:,.0f}".replace(",", "."), style={"color": "#eee"}),
            html.P(f"2027: R$ {forecast_itbi.iloc[1]:,.0f}".replace(",", "."), style={"color": "#eee"})
        ], style={"border":"1px solid #444","padding":"15px","flex":"1","backgroundColor":"#222"})

        cards = [card1, card2, card3]

        return mapa_html, fig_hist, cards

    except Exception as e:
        fallback_card = html.Div([
            html.H4("Erro ao gerar resumo", style={"color":"#fff"}),
            html.P(str(e), style={"color":"#fff"})
        ], style={"backgroundColor":"#900","padding":"20px"})
        return "", px.histogram(title="Erro"), [fallback_card]

if __name__ == "__main__":
    app.run_server(debug=True)


