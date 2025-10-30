# src/layout.py
from dash import html, dcc


def build_layout(app, years):
    """
    Construye el layout principal del dashboard.
    Recibe:
        app: instancia de Dash
        years: lista de años disponibles
    """

    return html.Div(
        [
            # Título principal
            html.H1(
                "Mortalidad en Colombia — Explorador Interactivo",
                style={
                    "textAlign": "center",
                    "color": "#003366",
                    "fontWeight": "bold",
                    "marginBottom": "0.5rem",
                },
            ),

            html.P(
                "Fuente: Registros de mortalidad (DANE). Año base: 2019.",
                style={
                    "textAlign": "center",
                    "color": "#555",
                    "marginBottom": "2rem",
                },
            ),

            # Filtros superiores
            html.Div(
                [
                    html.Div(
                        [
                            html.Label(
                                "Año:",
                                style={"fontWeight": "bold", "color": "#333"},
                            ),
                            dcc.Dropdown(
                                id="ddl-anio",
                                options=[
                                    {"label": str(y), "value": int(y)} for y in years
                                ],
                                value=years[0] if years else None,
                                clearable=False,
                                style={
                                    "width": "150px",
                                    "borderRadius": "8px",
                                    "fontSize": "15px",
                                },
                            ),
                        ],
                        style={"display": "flex", "flexDirection": "column"},
                    ),

                    html.Div(
                        [
                            html.Label(
                                "Sexo:",
                                style={"fontWeight": "bold", "color": "#333"},
                            ),
                            dcc.Dropdown(
                                id="ddl-sexo",
                                options=[
                                    {"label": "Todos", "value": "Todos"},
                                    {"label": "Masculino", "value": "Masculino"},
                                    {"label": "Femenino", "value": "Femenino"},
                                ],
                                value="Todos",
                                clearable=False,
                                style={
                                    "width": "200px",
                                    "borderRadius": "8px",
                                    "fontSize": "15px",
                                },
                            ),
                        ],
                        style={"display": "flex", "flexDirection": "column"},
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "center",
                    "gap": "2rem",
                    "flexWrap": "wrap",
                    "marginBottom": "2rem",
                },
            ),

            # Contenedor de pestañas
            html.Div(
                [
                    dcc.Tabs(
                        id="tabs",
                        value="tab-mapa",
                        children=[
                            dcc.Tab(
                                label="Mapa geográfico",
                                value="tab-mapa",
                                style={
                                    "fontWeight": "bold",
                                    "padding": "10px",
                                    "backgroundColor": "#f2f2f2",
                                    "borderRadius": "8px 8px 0 0",
                                },
                                selected_style={
                                    "backgroundColor": "#007BFF",
                                    "color": "white",
                                    "borderRadius": "8px 8px 0 0",
                                    "fontWeight": "bold",
                                },
                            ),
                            dcc.Tab(
                                label="Tendencia mensual",
                                value="tab-tendencia",
                                style={
                                    "fontWeight": "bold",
                                    "padding": "10px",
                                    "backgroundColor": "#f2f2f2",
                                    "borderRadius": "8px 8px 0 0",
                                },
                                selected_style={
                                    "backgroundColor": "#007BFF",
                                    "color": "white",
                                    "borderRadius": "8px 8px 0 0",
                                    "fontWeight": "bold",
                                },
                            ),
                            dcc.Tab(
                                label="Causas principales",
                                value="tab-causas",
                                style={
                                    "fontWeight": "bold",
                                    "padding": "10px",
                                    "backgroundColor": "#f2f2f2",
                                    "borderRadius": "8px 8px 0 0",
                                },
                                selected_style={
                                    "backgroundColor": "#007BFF",
                                    "color": "white",
                                    "borderRadius": "8px 8px 0 0",
                                    "fontWeight": "bold",
                                },
                            ),
                        ],
                        style={"marginBottom": "1.5rem"},
                    ),
                ],
                style={"maxWidth": "1000px", "margin": "0 auto"},
            ),

            # Gráfico principal
            html.Div(
                [
                    dcc.Graph(
                        id="fig-main",
                        style={
                            "height": "600px",
                            "width": "100%",
                            "backgroundColor": "white",
                            "borderRadius": "12px",
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
                        },
                        config={
                            "displayModeBar": True,
                            "modeBarButtonsToRemove": ["select", "lasso2d"],
                            "displaylogo": False,
                        },
                    )
                ],
                style={"maxWidth": "1000px", "margin": "0 auto"},
            ),

            html.Br(),
            html.Footer(
                "© 2025 | Universidad de La Salle — Aplicaciones I | Desarrollado por Oswaldo Naranjo Veloza",
                style={
                    "textAlign": "center",
                    "color": "#666",
                    "marginTop": "3rem",
                    "fontSize": "13px",
                },
            ),
        ],
        style={
            "fontFamily": "'Segoe UI', sans-serif",
            "backgroundColor": "#fafafa",
            "padding": "20px",
            "minHeight": "100vh",
        },
    )