from dash import Output, Input
import plotly.graph_objects as go
from plotly.graph_objects import Figure

def empty_fig(title: str, msg: str) -> Figure:
    fig = Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False, font=dict(size=16))
    fig.update_layout(title=title, xaxis_visible=False, yaxis_visible=False, template="plotly_white")
    return fig

def tpl(theme): 
    return "plotly_white" if theme == "light" else "plotly_dark"


def register_callbacks(app, svc):

    # ---------- Tema ----------
    @app.callback(Output("theme-store", "data"),
                  Input("theme-toggle", "value"))
    def toggle_theme(values):
        return "light" if "light" in (values or []) else "dark"


    # ---------- Mapa geográfico ----------
    @app.callback(Output("fig-mapa", "figure"),
                  Input("flt-year", "value"),
                  Input("flt-sexo", "value"),
                  Input("theme-store", "data"))
    def mapa(year, sexo, theme):
        df = svc.muertes_por_depto(year, sexo)
        if df.empty:
            return empty_fig("Muertes por departamento", "Sin datos disponibles")
        color = "#4cc9f0" if theme == "dark" else "#1f6feb"
        fig = go.Figure(go.Bar(x=df["nom_dpto"], y=df["muertes"], marker_color=color))
        fig.update_layout(title="Total de muertes por departamento",
                          xaxis_title="Departamento", yaxis_title="Muertes",
                          template=tpl(theme))
        return fig


    # ---------- Tendencia mensual ----------
    @app.callback(Output("fig-tendencia", "figure"),
                  Input("flt-year", "value"),
                  Input("flt-sexo", "value"),
                  Input("theme-store", "data"))
    def tendencia(year, sexo, theme):
        df = svc.muertes_por_mes(year, sexo)
        if df.empty:
            return empty_fig("Tendencia mensual", "Sin datos disponibles")
        fig = go.Figure(go.Scatter(x=df["mes"], y=df["muertes"], mode="lines+markers",
                                   line=dict(color="#1f77b4", width=2)))
        fig.update_layout(title="Tendencia mensual de muertes",
                          xaxis_title="Mes", yaxis_title="Muertes",
                          template=tpl(theme))
        return fig


    # ---------- Causas principales ----------
    @app.callback(Output("fig-causas", "figure"),
                  Input("flt-year", "value"),
                  Input("flt-sexo", "value"),
                  Input("theme-store", "data"))
    def causas(year, sexo, theme):
        df = svc.causas_principales(year, sexo)
        if df.empty:
            return empty_fig("Causas principales", "Sin datos disponibles")
        fig = go.Figure(go.Bar(x=df["nombre_causa"], y=df["muertes"],
                               marker_color="#9467bd"))
        fig.update_layout(title="Principales causas de muerte",
                          xaxis_title="Causa", yaxis_title="Muertes",
                          template=tpl(theme))
        return fig


    # ---------- Ciudades violentas y pacíficas ----------
    @app.callback(Output("fig-top-violentas", "figure"),
                  Output("fig-bottom-pacificas", "figure"),
                  Input("flt-year", "value"),
                  Input("flt-sexo", "value"),
                  Input("theme-store", "data"))
    def ciudades(year, sexo, theme):
        top, bottom = svc.top_ciudades(year, sexo)
        if top.empty:
            return empty_fig("Ciudades con más muertes", "Sin datos"), empty_fig("Ciudades con menos muertes", "Sin datos")

        f1 = go.Figure(go.Bar(x=top["nom_mpio"], y=top["muertes"], marker_color="#d62728"))
        f1.update_layout(title="Ciudades con más muertes",
                         xaxis_title="Ciudad", yaxis_title="Muertes",
                         template=tpl(theme))

        f2 = go.Figure(go.Bar(x=bottom["nom_mpio"], y=bottom["muertes"], marker_color="#2ca02c"))
        f2.update_layout(title="Ciudades con menos muertes",
                         xaxis_title="Ciudad", yaxis_title="Muertes",
                         template=tpl(theme))
        return f1, f2


    # ---------- Distribución por sexo y edad ----------
    @app.callback(Output("fig-sexo-depto", "figure"),
                  Output("fig-histo-edad", "figure"),
                  Input("flt-year", "value"),
                  Input("flt-sexo", "value"),
                  Input("theme-store", "data"))
    def sexo_edad(year, sexo, theme):
        df1 = svc.sexo_por_depto(year)
        df2 = svc.histo_edades(year, sexo)

        f1 = go.Figure()
        for s in df1["sexo_std"].unique():
            sub = df1[df1["sexo_std"] == s]
            f1.add_trace(go.Bar(x=sub["nom_dpto"], y=sub["muertes"], name=s))
        f1.update_layout(title="Muertes por sexo y departamento",
                         barmode="group",
                         xaxis_title="Departamento", yaxis_title="Muertes",
                         template=tpl(theme))

        f2 = go.Figure(go.Bar(x=df2["grupo_edad1"], y=df2["muertes"], marker_color="#17becf"))
        f2.update_layout(title="Distribución por grupos de edad",
                         xaxis_title="Grupo de edad", yaxis_title="Muertes",
                         template=tpl(theme))
        return f1, f2