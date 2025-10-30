# src/app.py — versión final lista para despliegue en Render

from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import numpy as np
import pandas as pd
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

# ========================== DATA LOADER ==========================

@dataclass
class DataLoader:
    base_dir: Path

    def load_divipola(self) -> pd.DataFrame:
        path = self.base_dir / "Divipola_CE_.xlsx"
        df = pd.read_excel(path)
        df = _to_lower(df)
        rename = {"cod_departamento":"cod_dpto","departamento":"nom_dpto","cod_municipio":"cod_mpio","municipio":"nom_mpio"}
        for k,v in rename.items():
            if k in df.columns: df = df.rename(columns={k:v})
        df["cod_dpto_int"] = pd.to_numeric(df.get("cod_dpto"), errors="coerce").astype("Int64")
        df["cod_mpio_int"] = pd.to_numeric(df.get("cod_mpio"), errors="coerce").astype("Int64")
        keep = [c for c in ["cod_dpto_int","nom_dpto","cod_mpio_int","nom_mpio"] if c in df.columns]
        return df[keep].drop_duplicates()

    def load_causas(self) -> Optional[pd.DataFrame]:
        path = self.base_dir / "Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx"
        if not path.exists():
            return None
        df = pd.read_excel(path)
        df = _to_lower(df)
        codigo_causa = _find_col(df.columns, ["cie-10"]) or _find_col(df.columns, ["codigo"]) or _find_col(df.columns, ["código"])
        nombre_causa = _find_col(df.columns, ["descripcion"]) or _find_col(df.columns, ["descripción"])
        if not codigo_causa or not nombre_causa:
            return None
        out = df[[codigo_causa, nombre_causa]].dropna().copy()
        out = out.rename(columns={codigo_causa:"codigo_causa", nombre_causa:"nombre_causa"})
        out["codigo_causa"] = out["codigo_causa"].astype(str).str.upper().str.strip()
        out["nombre_causa"] = out["nombre_causa"].astype(str).str.strip()
        return out.drop_duplicates()

    def load_mortalidad(self) -> pd.DataFrame:
        path = self.base_dir / "Anexo1.Muerte2019_CE_15-03-23.xlsx"
        df = pd.read_excel(path)
        df = _to_lower(df)
        rename = {"cod_departamento":"cod_dpto","cod_municipio":"cod_mpio","cod_muerte":"codigo_causa","año":"anio","mes":"mes","sexo":"sexo","grupo_edad1":"grupo_edad1"}
        for k,v in rename.items():
            if k in df.columns and v not in df.columns:
                df = df.rename(columns={k:v})
        df["cod_dpto_int"] = pd.to_numeric(df.get("cod_dpto"), errors="coerce").astype("Int64")
        df["cod_mpio_int"] = pd.to_numeric(df.get("cod_mpio"), errors="coerce").astype("Int64")
        df["sexo_std"] = df["sexo"].astype(str).str.strip().str.upper().map({"1":"Masculino","2":"Femenino","M":"Masculino","F":"Femenino"}).fillna("Sin dato")
        return df

# ========================== SERVICIO ==========================

class MortalityService:
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self.divi = self.loader.load_divipola()
        self.mort = self.loader.load_mortalidad()
        self.causas = self.loader.load_causas()
        self.mort = self.mort.merge(self.divi, left_on="cod_mpio_int", right_on="cod_mpio_int", how="left")
        if self.causas is not None:
            self.mort = self.mort.merge(self.causas, on="codigo_causa", how="left")

    def years(self): return sorted(self.mort["anio"].dropna().unique().astype(int))
    
    def departamentos(self): return sorted(self.mort["nom_dpto"].dropna().unique())
    
    def sexos(self): return ["Masculino","Femenino","Sin dato"]
    
    def muertes_por_depto(self, year: int | None, sexo: str | None):
        """Agrupa las muertes por departamento, filtrando por año y sexo."""
        df = self.mort.copy()

        if year:
            df = df[df["anio"] == int(year)]

        if sexo and sexo != "Todos":
            df = df[df["sexo_std"].str.lower() == sexo.lower()]

        # Verificar que nom_dpto exista
        if "nom_dpto" not in df.columns:
            return pd.DataFrame(columns=["nom_dpto", "muertes"])

        resumen = (
            df.groupby("nom_dpto", as_index=False)["anio"]
            .count()
            .rename(columns={"anio": "muertes"})
            .sort_values("muertes", ascending=False)
        )
        return resumen

    def muertes_por_mes(self, year: int | None, sexo: str | None):
        df = self.mort.copy()
        if year:
            df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos":
            df = df[df["sexo_std"].str.lower() == sexo.lower()]
        if "mes" not in df.columns:
            return pd.DataFrame(columns=["mes", "muertes"])
        resumen = (
            df.groupby("mes", as_index=False)["anio"]
            .count()
            .rename(columns={"anio": "muertes"})
            .sort_values("mes")
        )
        return resumen

    def causas_principales(self, year: int | None, sexo: str | None, top_n: int = 10):
        df = self.mort.copy()
        if year:
            df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos":
            df = df[df["sexo_std"].str.lower() == sexo.lower()]
        if "nombre_causa" not in df.columns:
            return pd.DataFrame(columns=["nombre_causa", "muertes"])
        resumen = (
            df.groupby("nombre_causa", as_index=False)["anio"]
            .count()
            .rename(columns={"anio": "muertes"})
            .sort_values("muertes", ascending=False)
            .head(top_n)
        )
        return resumen

    def top_ciudades(self, year: int | None, sexo: str | None, top_n: int = 10):
        df = self.mort.copy()
        if year:
            df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos":
            df = df[df["sexo_std"].str.lower() == sexo.lower()]
        if "nom_mpio" not in df.columns:
            return pd.DataFrame(columns=["nom_mpio", "muertes"])
        resumen = (
            df.groupby("nom_mpio", as_index=False)["anio"]
            .count()
            .rename(columns={"anio": "muertes"})
            .sort_values("muertes", ascending=False)
        )
        return resumen.head(top_n), resumen.tail(top_n)

    def sexo_por_depto(self, year: int | None):
        df = self.mort.copy()
        if year:
            df = df[df["anio"] == int(year)]
        if "nom_dpto" not in df.columns or "sexo_std" not in df.columns:
            return pd.DataFrame(columns=["nom_dpto", "sexo_std", "muertes"])
        resumen = (
            df.groupby(["nom_dpto", "sexo_std"], as_index=False)["anio"]
            .count()
            .rename(columns={"anio": "muertes"})
        )
        return resumen

    def histo_edades(self, year: int | None, sexo: str | None):
        df = self.mort.copy()
        if year:
            df = df[df["anio"] == int(year)]
        if sexo and sexo != "Todos":
            df = df[df["sexo_std"].str.lower() == sexo.lower()]
        if "grupo_edad1" not in df.columns:
            return pd.DataFrame(columns=["grupo_edad1", "muertes"])
        resumen = (
            df.groupby("grupo_edad1", as_index=False)["anio"]
            .count()
            .rename(columns={"anio": "muertes"})
            .sort_values("grupo_edad1")
        )
        return resumen

# ========================== APP DASH ==========================

def create_app() -> Dash:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    svc = MortalityService(DataLoader(data_dir))

    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "Mortalidad en Colombia — 2019"
    # --- construir opciones para filtros desde el servicio ---
    years = svc.years()
    sexos = svc.sexos()
    
    def muertes_por_depto(self, year: int | None, sexo: str | None):
        """Agrupa las muertes por departamento, filtrando por año y sexo."""
        df = self.mort.copy()

        if year:
            df = df[df["anio"] == int(year)]

        if sexo and sexo != "Todos":
            df = df[df["sexo_std"].str.lower() == sexo.lower()]

        # Verificar que nom_dpto exista
        if "nom_dpto" not in df.columns:
            return pd.DataFrame(columns=["nom_dpto", "muertes"])

        resumen = (
            df.groupby("nom_dpto", as_index=False)["anio"]
            .count()
            .rename(columns={"anio": "muertes"})
            .sort_values("muertes", ascending=False)
        )
        return resumen

    app.layout = html.Div([
        # Store para tema (lo usa callbacks.py)
        dcc.Store(id="theme-store", data="light"),

        html.H2("Mortalidad en Colombia — Explorador interactivo (2019)"),
        html.P("Fuente: Registros de mortalidad, CIE-10 y DIVIPOLA."),

        # Barra de filtros (IDs según callbacks.py)
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
            ], className="dd-wrap"),

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
            ], className="dd-wrap"),

            html.Div([
                dcc.Checklist(
                    id="theme-toggle",
                    options=[{"label": "🌓 Tema claro", "value": "light"}],
                    value=["light"],
                    inputStyle={"marginRight": "6px"},
                    style={"marginTop": "22px"}
                )
            ], className="dd-wrap"),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "160px 220px 1fr",
            "gap": "12px",
            "alignItems": "end",
            "padding": "12px",
            "background": "#f5f7fb",
            "borderRadius": "12px",
            "border": "1px solid rgba(31,111,235,.20)",
            "marginBottom": "10px"
        }),

        # Pestañas con los Graph que esperan los callbacks
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
            dcc.Tab(label="Ciudades violentas y pacíficas", value="ciudades", children=[
                dcc.Graph(id="fig-top-violentas", config={"displaylogo": False}),
                dcc.Graph(id="fig-bottom-pacificas", config={"displaylogo": False}),
            ]),
            dcc.Tab(label="Distribución por sexo y edad", value="sexo_edad", children=[
                dcc.Graph(id="fig-sexo-depto", config={"displaylogo": False}),
                dcc.Graph(id="fig-histo-edad", config={"displaylogo": False}),
            ]),
        ])
    ])

    register_callbacks(app, svc)
    return app

app = create_app()
server = app.server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
