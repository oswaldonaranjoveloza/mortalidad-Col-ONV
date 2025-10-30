from dash import html, dcc


def build_filters_bar(svc):
    years = svc.years()
    dptos = svc.departamentos()
    sexos = svc.sexos()

    return html.Div([
        html.Div([
            html.Label("Año"),
            dcc.Dropdown(
                id="flt-year",
                options=[{"label": str(y), "value": y} for y in years],
                value=years[0] if years else None,
                clearable=False,
                style={"width": "120px"}
            )
        ], className="dd-wrap"),

        html.Div([
            html.Label("Departamento"),
            dcc.Dropdown(
                id="flt-depto",
                options=[{"label": "Todos", "value": "Todos"}] +
                        [{"label": d, "value": d} for d in dptos],
                value="Todos",
                clearable=False,
                style={"width": "280px"}
            )
        ], className="dd-wrap"),

        html.Div([
            html.Label("Sexo"),
            dcc.Dropdown(
                id="flt-sexo",
                options=[{"label": "Todos", "value": "Todos"}] +
                        [{"label": s, "value": s} for s in sexos],
                value="Todos",
                clearable=False,
                style={"width": "180px"}
            )
        ], className="dd-wrap"),

        html.Div([
            dcc.Checklist(
                id="theme-toggle",
                options=[{"label": "🌓 Tema claro", "value": "light"}],
                value=[],
                inputStyle={"marginRight": "6px"},
                style={"marginBottom": "8px"}
            ),
            html.Button("📒 Dataset completo (Excel)", id="btn-raw",
                        n_clicks=0, className="btn-primary"),
            dcc.Download(id="dwn-raw")
        ], style={"textAlign": "right"}),
    ], className="filters")