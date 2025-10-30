# src/callbacks.py
from dash import Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def register_callbacks(app, svc):
    """
    Registra todos los callbacks del dashboard.
    svc: instancia de MortalityService (ver app.py)
    """

    @app.callback(
        Output("fig-main", "figure"),
        Input("ddl-anio", "value"),
        Input("ddl-sexo", "value"),
        Input("tabs", "value"),
    )
    def actualizar_graficos(anio, sexo, tab):
        if not anio:
            return go.Figure()

        # Tab 1: Muertes por departamento (Mapa o barras)
        if tab == "tab-mapa":
            df = svc.muertes_por_depto(anio, sexo)
            if df.empty:
                fig = go.Figure()
                fig.update_layout(title="Sin datos para el año seleccionado")
                return fig

            # Si tenemos coordenadas, usar mapa choropleth; si no, barras horizontales
            if "nom_dpto" in df.columns:
                fig = px.bar(
                    df,
                    x="muertes",
                    y="nom_dpto",
                    orientation="h",
                    title=f"Muertes por Departamento ({anio}, {sexo})",
                )
                fig.update_layout(
                    yaxis_title="Departamento",
                    xaxis_title="Número de muertes",
                    margin=dict(l=80, r=30, t=80, b=40),
                    height=600,
                )
                fig.update_traces(marker_color="#007BFF")
                return fig

        # Tab 2: Tendencia mensual
        elif tab == "tab-tendencia":
            df = svc.tendencia_mensual(anio, sexo)
            if df.empty:
                fig = go.Figure()
                fig.update_layout(title="No hay datos mensuales disponibles")
                return fig

            df["mes_nombre"] = df["mes"].map({
                1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
                7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
            })

            fig = px.line(
                df,
                x="mes_nombre",
                y="muertes",
                markers=True,
                title=f"Tendencia mensual de muertes ({anio}, {sexo})",
            )
            fig.update_layout(
                xaxis_title="Mes",
                yaxis_title="Número de muertes",
                height=500,
                margin=dict(l=40, r=30, t=80, b=40),
            )
            return fig

        # Tab 3: Causas principales
        elif tab == "tab-causas":
            df = svc.causas_principales(anio, sexo, top=10)
            if df.empty:
                fig = go.Figure()
                fig.update_layout(title="Sin datos de causas disponibles")
                return fig

            df["etiqueta"] = df.apply(
                lambda r: f"{r['nombre_causa']}" if pd.notna(r.get("nombre_causa")) else r["codigo_causa"],
                axis=1,
            )

            fig = px.bar(
                df,
                x="muertes",
                y="etiqueta",
                orientation="h",
                title=f"Principales causas de muerte ({anio}, {sexo})",
            )
            fig.update_layout(
                xaxis_title="Número de muertes",
                yaxis_title="Causa",
                height=600,
                margin=dict(l=200, r=30, t=80, b=40),
            )
            fig.update_traces(marker_color="#FF6B6B")
            return fig

        # fallback
        return go.Figure()