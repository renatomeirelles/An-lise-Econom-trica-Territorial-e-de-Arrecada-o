import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd

# =========================
# Criar app Dash
# =========================
app = dash.Dash(__name__)
server = app.server  # importante para o Render

# =========================
# Dados de teste
# =========================
df = pd.DataFrame({
    "x": [1, 2, 3, 4, 5],
    "y": [10, 20, 30, 40, 50]
})

# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H1("Teste Dash no Render"),
    dcc.Dropdown(
        options=[{"label": "Opção 1", "value": "1"}],
        value="1"
    ),
    dcc.Graph(figure=px.line(df, x="x", y="y"))
])

# =========================
# Rodar servidor local
# =========================
if __name__ == "__main__":
    app.run_server(debug=True)
