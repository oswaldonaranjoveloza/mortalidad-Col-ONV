# src/app.py — versión final lista para despliegue en Render
# src/app.py
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from dash import Dash, dcc, html

# --------------------------------------------------------------------------------------
# 1. utilidades de normalización
# --------------------------------------------------------------------------------------

def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    """normaliza nombres de columnas: minúsculas, sin tildes, sin espacios."""
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace("á", "a")
        .str.replace("é", "e")
        .str.replace("í", "i")
        .str.replace("ó", "o")
        .str.replace("ú", "u")
        .str.replace("ñ", "n")
        .str.replace(" ", "_")
    )
    return df

# --------------------------------------------------------------------------------------
# 2. cargador de datos (sin lru_cache problemático)
# --------------------------------------------------------------------------------------


@dataclass
class DataLoader:
    base_dir: Path

    def load_divipola(self) -> pd.DataFrame:
        path = self.base_dir / "Divipola_CE_.csv"
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de divipola: {path}")

        df = pd.read_csv(path, encoding="latin1", low_memory=False)
        df = _norm_cols(df)

        # nombres esperados
        rename = {
            "cod_departamento": "cod_dpto",
            "departamento": "nom_dpto",
            "cod_municipio": "cod_mpio",
            "municipio": "nom_mpio",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        # claves numéricas
        if "cod_dpto" in df.columns:
            df["cod_dpto_int"] = pd.to_numeric(df["cod_dpto"], errors="coerce").astype("Int64")
        else:
            df["cod_dpto_int"] = pd.NA

        if "cod_mpio" in df.columns:
            df["cod_mpio_int"] = pd.to_numeric(df["cod_mpio"], errors="coerce").astype("Int64")
        else:
            df["cod_mpio_int"] = pd.NA

        return df[["cod_dpto_int", "nom_dpto", "cod_mpio_int", "nom_mpio"]].drop_duplicates()

    def load_causas(self) -> Optional[pd.DataFrame]:
        # tu archivo se llama así en el repo
        path = self.base_dir / "Anexo2.CodigosDeMuerte_CE_15-03-23.csv"
        if not path.exists():
            return None

        df = pd.read_csv(path, encoding="latin1", low_memory=False)
        df = _norm_cols(df)

        # encontrar columnas de código y descripción aunque tengan nombres raros
        codigo_col = None
        desc_col = None
        for c in df.columns:
            if "cie" in c or "codigo" in c:
                codigo_col = c
            if "descripcion" in c or "descricion" in c:
                desc_col = c

        if not codigo_col or not desc_col:
            # lo devolvemos igual, pero la app seguirá mostrando solo el código
            return None

        df = df.rename(columns={codigo_col: "codigo_causa", desc_col: "nombre_causa"})
        df["codigo_causa"] = df["codigo_causa"].astype(str).str.upper().str.strip()
        df["nombre_causa"] = df["nombre_causa"].astype(str).str.strip()

        return df[["codigo_causa", "nombre_causa"]].drop_duplicates()

    def load_mortalidad(self) -> pd.DataFrame:
        path = self.base_dir / "Anexo1.Muerte2019_CE_15-03-23.csv"
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de mortalidad: {path}")

        # el archivo viene en latin1
        df = pd.read_csv(path, encoding="latin1", low_memory=False)
        df = _norm_cols(df)

        # en tu archivo real la columna es ANIO (sin tilde) -> tras normalizar queda "anio"
        # pero dejamos detección flexible por si lo cambias mañana
        if "anio" in df.columns:
            anio_col = "anio"
        elif "ano" in df.columns:
            anio_col = "ano"
        elif "año" in df.columns:
            anio_col = "año"
        else:
            raise KeyError(f"No se encontró columna de año en mortalidad. Columnas: {list(df.columns)}")

        rename = {
            anio_col: "anio",
            "cod_departamento": "cod_dpto",
            "cod_municipio": "cod_mpio",
            "cod_muerte": "codigo_causa",
            "mes": "mes",
            "sexo": "sexo",
            "grupo_edad1": "grupo_edad1",
            "manera_muerte": "manera_muerte",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        # tipos
        df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
        if "cod_dpto" in df.columns:
            df["cod_dpto_int"] = pd.to_numeric(df["cod_dpto"], errors="coerce").astype("Int64")
        else:
            df["cod_dpto_int"] = pd.NA

        if "cod_mpio" in df.columns:
            df["cod_mpio_int"] = pd.to_numeric(df["cod_mpio"], errors="coerce").astype("Int64")
        else:
            df["cod_mpio_int"] = pd.NA

        # sexo 1/2 -> etiquetas
        df["sexo_std"] = (
            df["sexo"]
            .astype(str)
            .str.strip()
            .map({"1": "Masculino", "2": "Femenino"})
            .fillna("Sin dato")
        )

        return df


# --------------------------------------------------------------------------------------
# 3. servicio de dominio
# --------------------------------------------------------------------------------------


class MortalityService:
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self._mort = loader.load_mortalidad()
        self._divi = loader.load_divipola()
        self._causas = loader.load_causas()

        # unir nombres de dpto de una vez
        self._mort = self._mort.merge(
            self._divi[["cod_dpto_int", "nom_dpto"]], on="cod_dpto_int", how="left"
        )

    # ---------- helpers ----------
    @property
    def mort(self) -> pd.DataFrame:
        return self._mort

    def years(self) -> list[int]:
        return sorted(self._mort["anio"].dropna().unique().astype(int).tolist())

    def filter_base(self, anio: int, sexo: str) -> pd.DataFrame:
        df = self._mort[self._mort["anio"] == anio].copy()
        if sexo and sexo != "Todos":
            df = df[df["sexo_std"] == sexo]
        return df

    # ---------- consultas para las pestañas ----------
    def muertes_por_depto(self, anio: int, sexo: str) -> pd.DataFrame:
        df = self.filter_base(anio, sexo)
        out = (
            df.groupby("nom_dpto", dropna=False)
            .size()
            .reset_index(name="muertes")
            .sort_values("muertes", ascending=False)
        )
        return out

    def tendencia_mensual(self, anio: int, sexo: str) -> pd.DataFrame:
        df = self.filter_base(anio, sexo)
        if "mes" not in df.columns:
            return pd.DataFrame(columns=["mes", "muertes"])
        out = (
            df.groupby("mes")
            .size()
            .reset_index(name="muertes")
            .sort_values("mes")
        )
        return out

    def causas_principales(self, anio: int, sexo: str, top: int = 10) -> pd.DataFrame:
        df = self.filter_base(anio, sexo)
        if "codigo_causa" not in df.columns:
            return pd.DataFrame(columns=["codigo_causa", "muertes"])

        out = (
            df.groupby("codigo_causa")
            .size()
            .reset_index(name="muertes")
            .sort_values("muertes", ascending=False)
            .head(top)
        )

        # si tenemos el catálogo, lo unimos
        if self._causas is not None:
            out = out.merge(self._causas, on="codigo_causa", how="left")

        return out


# --------------------------------------------------------------------------------------
# 4. layout base (el visual ya lo tienes en layout.py, pero por si se ejecuta solo)
# --------------------------------------------------------------------------------------


def empty_fig():
    """Figura vacía para evitar crashes en el primer render."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[],
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig


def build_layout(app: Dash, years: list[int]):
    # si tienes layout.py puedes importar aquí y devolver eso;
    # pero dejo un layout mínimo para que no truene si lo ejecutas solo.
    return html.Div(
        [
            html.H1("Mortalidad en Colombia — Explorador interactivo (2019)"),
            html.P("Fuente: Registros de mortalidad, CIE-10 y DIVIPOLA."),
            html.Div(
                [
                    dcc.Dropdown(
                        id="ddl-anio",
                        options=[{"label": str(y), "value": int(y)} for y in years],
                        value=years[0] if years else None,
                        style={"width": "150px"},
                    ),
                    dcc.Dropdown(
                        id="ddl-sexo",
                        options=[
                            {"label": "Todos", "value": "Todos"},
                            {"label": "Masculino", "value": "Masculino"},
                            {"label": "Femenino", "value": "Femenino"},
                        ],
                        value="Todos",
                        style={"width": "150px", "marginLeft": "1rem"},
                    ),
                ],
                style={"display": "flex", "gap": "1rem", "marginBottom": "1rem"},
            ),
            dcc.Tabs(
                id="tabs",
                value="tab-mapa",
                children=[
                    dcc.Tab(label="Mapa geográfico", value="tab-mapa"),
                    dcc.Tab(label="Tendencia mensual", value="tab-tendencia"),
                    dcc.Tab(label="Causas principales", value="tab-causas"),
                ],
            ),
            dcc.Graph(id="fig-main", figure=empty_fig()),
        ],
        style={"padding": "1rem"},
    )


# --------------------------------------------------------------------------------------
# 5. crear app y registrar callbacks (tu callbacks.py actual debe tener register_callbacks)
# --------------------------------------------------------------------------------------


def create_app() -> Dash:
    # ruta /src/app.py  -> queremos ../data
    data_dir = Path(__file__).resolve().parent.parent / "data"

    loader = DataLoader(data_dir)
    svc = MortalityService(loader)

    app = Dash(__name__)
    app.title = "Mortalidad en Colombia"
    app.layout = build_layout(app, svc.years())

    # pasar objetos reales a callbacks
    try:
        from callbacks import register_callbacks  # tus callbacks actuales
        register_callbacks(app, svc)
    except ImportError:
        # si no existe callbacks.py o si estás probando local, no se rompe
        pass

    # para Render
    global server
    server = app.server

    return app

app = create_app()

# --------------------------------------------------------------------------------------
# 6. ejecución local
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    # en local
    app.run(host="0.0.0.0", port=8050, debug=True)