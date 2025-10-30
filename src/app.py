# src/app.py — versión final lista para despliegue en Render
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, List

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table

from src.callbacks import register_callbacks

# ========================== UTILIDADES ==========================

def _to_lower(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def _find_col(columns: List[str], must_include: List[str]) -> Optional[str]:
    for c in columns:
        cc = c.casefold()
        if all(fragment.casefold() in cc for fragment in must_include):
            return c
    return None


# ========================== DATA LOADER (OPTIMIZADO) ==========================

@dataclass
class DataLoader:
    base_dir: Path

    def load_divipola(self) -> pd.DataFrame:
        return _cached_load_divipola(self.base_dir)

    def load_causas(self) -> Optional[pd.DataFrame]:
        return _cached_load_causas(self.base_dir)

    def load_mortalidad(self) -> pd.DataFrame:
        return _cached_load_mortalidad(self.base_dir)


# === Funciones caché seguras (hashable por Path) ===

@lru_cache(maxsize=3)
def _cached_load_divipola(base_dir: Path) -> pd.DataFrame:
    path = base_dir / "Divipola_CE_.csv"
    if not path.exists():
        raise FileNotFoundError(f"No se encontró: {path}")
    df = pd.read_csv(path, encoding="latin1")
    df = _to_lower(df)
    rename = {
        "cod_departamento": "cod_dpto",
        "departamento": "nom_dpto",
        "cod_municipio": "cod_mpio",
        "municipio": "nom_mpio"
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df["cod_dpto_int"] = pd.to_numeric(df.get("cod_dpto"), errors="coerce").astype("Int64")
    df["cod_mpio_int"] = pd.to_numeric(df.get("cod_mpio"), errors="coerce").astype("Int64")
    keep = [c for c in ["cod_dpto_int", "nom_dpto", "cod_mpio_int", "nom_mpio"] if c in df.columns]
    return df[keep].drop_duplicates()


@lru_cache(maxsize=3)
def _cached_load_causas(base_dir: Path) -> Optional[pd.DataFrame]:
    path = base_dir / "Anexo2.CodigosDeMuerte_CE_15-03-23.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, encoding="latin1")
    df = _to_lower(df)
    codigo_causa = _find_col(df.columns, ["cie-10"]) or _find_col(df.columns, ["codigo"]) or _find_col(df.columns, ["código"])
    nombre_causa = _find_col(df.columns, ["descripcion"]) or _find_col(df.columns, ["descripción"])
    if not codigo_causa or not nombre_causa:
        return None
    out = df[[codigo_causa, nombre_causa]].dropna().copy()
    out = out.rename(columns={codigo_causa: "codigo_causa", nombre_causa: "nombre_causa"})
    out["codigo_causa"] = out["codigo_causa"].astype(str).str.upper().str.strip()
    out["nombre_causa"] = out["nombre_causa"].astype(str).str.strip()
    return out.drop_duplicates()


@lru_cache(maxsize=3)
def _cached_load_mortalidad(base_dir: Path) -> pd.DataFrame:
    path = base_dir / "Anexo1.Muerte2019_CE_15-03-23.csv"
    if not path.exists():
        raise FileNotFoundError(f"No se encontró: {path}")
    df = pd.read_csv(path, encoding="latin1", low_memory=False)
    df = _to_lower(df)
    rename = {
        "cod_departamento": "cod_dpto",
        "cod_municipio": "cod_mpio",
        "cod_muerte": "codigo_causa",
        "año": "anio",
        "mes": "mes",
        "sexo": "sexo",
        "grupo_edad1": "grupo_edad1"
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df["cod_dpto_int"] = pd.to_numeric(df.get("cod_dpto"), errors="coerce").astype("Int64")
    df["cod_mpio_int"] = pd.to_numeric(df.get("cod_mpio"), errors="coerce").astype("Int64")
    df["sexo_std"] = (
        df["sexo"].astype(str)
        .str.strip()
        .str.upper()
        .map({"1": "Masculino", "2": "Femenino", "M": "Masculino", "F": "Femenino"})
        .fillna("Sin dato")
    )
    return df

# ========================== SERVICIO ==========================

class MortalityService:
    def __init__(self, loader: DataLoader):
        self.loader = loader

    @property
    def mort(self): return self.loader.load_mortalidad()
    @property
    def divi(self): return self.loader.load_divipola()
    @property
    def causas(self): return self.loader.load_causas()

    def years(self): return sorted(self.mort["anio"].dropna().unique().astype(int))
    def sexos(self): return ["Masculino", "Femenino", "Sin dato"]

    def muertes_por_depto(self, year: int | None, sexo: str | None):
        df = self.mort
        if year: df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos":
            df = df[df["sexo_std"].str.lower() == sexo.lower()]
        resumen = (
            df.groupby("cod_dpto", as_index=False)
              .size().rename(columns={"size": "muertes"})
        )
        resumen = resumen.merge(self.divi, left_on="cod_dpto", right_on="cod_dpto_int", how="left")
        return resumen[["nom_dpto", "muertes"]].sort_values("muertes", ascending=False)

    def muertes_por_mes(self, year: int | None, sexo: str | None):
        df = self.mort
        if year: df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos": df = df[df["sexo_std"].str.lower() == sexo.lower()]
        return (df.groupby("mes", as_index=False)
                  .size().rename(columns={"size": "muertes"})
                  .sort_values("mes"))

    def causas_principales(self, year: int | None, sexo: str | None, top_n: int = 10):
        df = self.mort
        if year: df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos": df = df[df["sexo_std"].str.lower() == sexo.lower()]
        resumen = (df.groupby("codigo_causa", as_index=False)
                     .size().rename(columns={"size": "muertes"})
                     .sort_values("muertes", ascending=False)
                     .head(top_n))
        causas = self.causas
        if causas is not None:
            resumen = resumen.merge(causas, on="codigo_causa", how="left")
        return resumen

    def top_ciudades(self, year: int | None, sexo: str | None, top_n: int = 10):
        df = self.mort
        if year: df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos": df = df[df["sexo_std"].str.lower() == sexo.lower()]
        resumen = (df.groupby("nom_mpio", as_index=False)
                     .size().rename(columns={"size": "muertes"})
                     .sort_values("muertes", ascending=False))
        return resumen.head(top_n), resumen.tail(top_n)

    def sexo_por_depto(self, year: int | None):
        df = self.mort
        if year: df = df[df["anio"] == int(year)]
        resumen = (df.groupby(["nom_dpto", "sexo_std"], as_index=False)
                     .size().rename(columns={"size": "muertes"}))
        return resumen

    def histo_edades(self, year: int | None, sexo: str | None):
        df = self.mort
        if year: df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos": df = df[df["sexo_std"].str.lower() == sexo.lower()]
        return (df.groupby("grupo_edad1", as_index=False)
                  .size().rename(columns={"size": "muertes"})
                  .sort_values("grupo_edad1"))


# ========================== DASH APP ==========================

def create_app() -> Dash:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    svc = MortalityService(DataLoader(data_dir))

    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "Mortalidad en Colombia — 2019"

    years = svc.years()
    sexos = svc.sexos()

    app.layout = html.Div([
        html.H2("Mortalidad en Colombia — Explorador interactivo (2019)"),
        html.P("Fuente: Registros de mortalidad, CIE-10 y DIVIPOLA."),

        html.Div([
            html.Div([
                html.Label("Año"),
                dcc.Dropdown(
                    id="flt-year",
                    options=[{"label": str(y), "value": int(y)} for y in years],
                    value=int(years[0]) if years else None,
                    clearable=False,
                    style={"width": "120px"}
                )
            ]),
            html.Div([
                html.Label("Sexo"),
                dcc.Dropdown(
                    id="flt-sexo",
                    options=([{"label": "Todos", "value": "Todos"}] +
                             [{"label": s, "value": s} for s in sexos]),
                    value="Todos",
                    clearable=False,
                    style={"width": "180px"}
                )
            ]),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "10px"}),

        dcc.Tabs(id="tabs", value="mapa", children=[
            dcc.Tab(label="Mapa geográfico", value="mapa", children=[
                dcc.Graph(id="fig-mapa", config={"displaylogo": False})
            ]),
            dcc.Tab(label="Tendencia mensual", value="tendencia", children=[
                dcc.Graph(id="fig-tendencia", config={"displaylogo": False})
            ]),
            dcc.Tab(label="Causas principales", value="causas", children=[
                dcc.Graph(id="fig-causas", config={"displaylogo": False}),
                dash_table.DataTable(
                    id="tbl-causas",
                    columns=[
                        {"name": "Código", "id": "codigo_causa"},
                        {"name": "Causa", "id": "nombre_causa"},
                        {"name": "Muertes", "id": "muertes"},
                    ],
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "left", "padding": "6px"},
                    sort_action="native",
                ),
            ]),
        ])
    ])

    register_callbacks(app, svc)
    return app


app = create_app()
server = app.server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)