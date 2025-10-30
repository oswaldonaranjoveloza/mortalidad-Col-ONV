# -*- coding: utf-8 -*-
"""
app_final_graph_objects.py — Integración total de Dash + Plotly Graph Objects
Basado en las versiones previas (plus_darkfix y fixed_width).
Mejora visual y control total sobre gráficos.
Autores: Oswaldo Naranjo Veloza y Manuel Antonio Sanabria Gil
Universidad de La Salle - Maestría en Inteligencia Artificial - Aplicaciones I
"""
from dash import Dash
from layout import layout
from callbacks import register_callbacks
from pathlib import Path
from services import MortalityService, DataLoader

def create_app():
    svc = MortalityService(DataLoader(Path("data")))
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "Mortalidad en Colombia — Explorador Interactivo"
    app.layout = layout(svc)
    register_callbacks(app, svc)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8050, debug=True)