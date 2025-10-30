from dash import html, dcc
from components.filters import build_filters_bar


def layout(svc):
    return html.Div([
        dcc.Store(id="theme-store", data="dark"),
        html.Div([
            html.H2("Mortalidad en Colombia — Explorador interactivo (2019)"),
            html.P("Fuente: Registros de mortalidad, CIE-10 y DIVIPOLA.", className="sub"),
            build_filters_bar(svc),
            dcc.Tabs(id="tabs", value="mapa", className="tabs", children=[
                dcc.Tab(label="Mapa geográfico", value="mapa", children=[dcc.Graph(id="fig-mapa")]),
                dcc.Tab(label="Tendencia mensual", value="tendencia", children=[dcc.Graph(id="fig-tendencia")]),
                dcc.Tab(label="Causas principales", value="causas", children=[dcc.Graph(id="fig-causas")]),
                dcc.Tab(label="Ciudades violentas y pacíficas", value="ciudades",
                        children=[dcc.Graph(id="fig-top-violentas"), dcc.Graph(id="fig-bottom-pacificas")]),
                dcc.Tab(label="Distribución por sexo y edad", value="sexo_edad",
                        children=[dcc.Graph(id="fig-sexo-depto"), dcc.Graph(id="fig-histo-edad")])
            ])
        ])
    ])