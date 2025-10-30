# src/app.py — versión final lista para despliegue en Render
import pandas as pd
from dash import Dash
from dash import html
from dash import dcc
from dash_bootstrap_components.themes import FLATLY
from pathlib import Path
from functools import lru_cache
import dash_bootstrap_components as dbc

from layout import build_layout
from callbacks import register_callbacks


# ==========================================================
# 1. Carga de datos base
# ==========================================================
class DataLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    @lru_cache(maxsize=None)
    def load_mortalidad(self):
        file = self.base_dir / "data" / "Anexo1.Muerte2019_CE_15-03-23.csv"
        df = pd.read_csv(file, encoding="utf-8")
        print("\n=== CARGANDO ARCHIVO DE MORTALIDAD ===")
        print(f"Ruta: {file}")
        print("Columnas detectadas:", list(df.columns))
        print("Primeras filas:")
        print(df.head(5))
        print("======================================\n")
        df.columns = [c.strip().lower() for c in df.columns]  # ← normaliza nombres

        # Normaliza nombres esperados
        rename_map = {
            "anio": "anio",
            "año": "anio",
            "ano": "anio",
            "cod_departamento": "cod_departamento",
            "cod_dane": "cod_dane",
            "cod_muerte": "cod_muerte",
            "sexo": "sexo",
            "mes": "mes",
            "manera_muerte": "manera_muerte",
        }
        df.rename(columns=rename_map, inplace=True)

        # Convierte tipos
        df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
        df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
        df["sexo"] = df["sexo"].map({1: "Masculino", 2: "Femenino"}).fillna("Todos")

        return df

    @lru_cache(maxsize=None)
    def load_codigos(self):
        file = self.base_dir / "data" / "Anexo2.CodigosDeMuerte_CE_15-03-23.csv"
        df = pd.read_csv(file, encoding="utf-8")
        print("\n=== CARGANDO CÓDIGOS DE MUERTE ===")
        print(df.head(5))
        print("===================================\n")
        return df
        df.columns = [c.strip().lower() for c in df.columns]
        rename_map = {"codigo": "codigo_causa", "nombre": "nombre_causa"}
        df.rename(columns=rename_map, inplace=True)
        return df

    @lru_cache(maxsize=None)
    def load_divipola(self):
        file = self.base_dir / "data" / "Divipola_CE_.csv"
        df = pd.read_csv(file, encoding="utf-8")
        print("\n=== CARGANDO DIVIPOLA ===")
        print(df.head(5))
        print("===================================\n")
        return df
        df.columns = [c.strip().lower() for c in df.columns]
        rename_map = {
            "cod_departamento": "cod_departamento",
            "nom_dpto": "nom_dpto",
        }
        df.rename(columns=rename_map, inplace=True)
        return df


# ==========================================================
# 2. Servicio de consulta
# ==========================================================
class MortalityService:
    def __init__(self, loader: DataLoader):
        self.loader = loader

    @property
    @lru_cache(maxsize=None)
    def mort(self):
        return self.loader.load_mortalidad()

    def years(self):
        return sorted(self.mort["anio"].dropna().unique().astype(int))

    def muertes_por_depto(self, anio, sexo):
        df = self.mort.copy()
        if anio:
            df = df[df["anio"] == anio]
        if sexo != "Todos":
            df = df[df["sexo"] == sexo]

        div = self.loader.load_divipola()
        df = (
            df.groupby("cod_departamento", as_index=False)
            .size()
            .rename(columns={"size": "muertes"})
        )
        df = df.merge(div, on="cod_departamento", how="left")
        return df[["cod_departamento", "nom_dpto", "muertes"]]

    def tendencia_mensual(self, anio, sexo):
        df = self.mort.copy()
        if anio:
            df = df[df["anio"] == anio]
        if sexo != "Todos":
            df = df[df["sexo"] == sexo]
        df = (
            df.groupby("mes", as_index=False)
            .size()
            .rename(columns={"size": "muertes"})
            .sort_values("mes")
        )
        return df

    def causas_principales(self, anio, sexo, top=10):
        df = self.mort.copy()
        if anio:
            df = df[df["anio"] == anio]
        if sexo != "Todos":
            df = df[df["sexo"] == sexo]

        cod = self.loader.load_codigos()
        df = (
            df.groupby("cod_muerte", as_index=False)
            .size()
            .rename(columns={"size": "muertes"})
        )
        df = df.merge(cod, left_on="cod_muerte", right_on="codigo_causa", how="left")
        return df.nlargest(top, "muertes")[["codigo_causa", "nombre_causa", "muertes"]]


# ==========================================================
# 3. Crear app
# ==========================================================
def create_app():
    base_dir = Path(__file__).resolve().parent.parent
    loader = DataLoader(base_dir)
    svc = MortalityService(loader)

    app = Dash(
        __name__,
        external_stylesheets=[FLATLY],
        suppress_callback_exceptions=True,
    )
    app.title = "Mortalidad en Colombia"

    years = svc.years()
    app.layout = build_layout(app, years)

    register_callbacks(app, svc)

    server = app.server
    return app, server


app, server = create_app()

if __name__ == "__main__":
    app.run_server(debug=True)