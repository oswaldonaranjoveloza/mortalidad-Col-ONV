# =========================================================================
# PROGRAMA COMPLETO: Análisis de Mortalidad en Colombia (2019)
# =========================================================================

import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html
import json

# =========================================================================
# === 1. CARGA DE DATOS ===
# =========================================================================
try:
    df_mortalidad = pd.read_excel('data/Mortalidad.xlsx', sheet_name='No_Fetales_2019')
    df_divipola = pd.read_excel('data/Divipola.xlsx', sheet_name='Hoja1')
    df_codigos = pd.read_excel('data/CIE10.xlsx', sheet_name='Final')
    print(" Archivos cargados correctamente.")
except FileNotFoundError:
    print(" ERROR: faltan archivos .xlsx")
    exit()

# =========================================================================
# === 2. LIMPIEZA Y FORMATEO DE DATOS ===
# =========================================================================
# Formato COD_DANE y COD_DEPARTAMENTO
df_mortalidad['COD_DANE'] = df_mortalidad['COD_DANE'].astype(str).str.zfill(5)
df_mortalidad['COD_DEPARTAMENTO'] = df_mortalidad['COD_DEPARTAMENTO'].astype(str).str.zfill(2)

# Divipola
df_divipola.columns = ['COD_DANE', 'COD_DEPARTAMENTO', 'DEPARTAMENTO', 'COD_MUNICIPIO', 'MUNICIPIO', 'FECHA1erFIS']
df_divipola['COD_DANE'] = df_divipola['COD_DANE'].astype(str).str.zfill(5)
df_divipola = df_divipola[['COD_DANE', 'DEPARTAMENTO', 'MUNICIPIO']].drop_duplicates()

# Merge mortalidad con nombres de departamentos
df_final = pd.merge(df_mortalidad, df_divipola, on='COD_DANE', how='left')

# Seleccionar códigos de muerte
df_codigos = df_codigos[['CodigoMuerte', 'DescripcionCodigoMuerte']].copy()

# Merge con descripción de códigos
df_final = pd.merge(df_final, df_codigos, left_on='COD_MUERTE', right_on='CodigoMuerte', how='left')

# =========================================================================
# === 3. MAPA: Total de muertes por departamento ===
# =========================================================================
df_mapa = df_final.groupby('DEPARTAMENTO', as_index=False).agg(Total_Muertes_Dpto=('AÑO', 'size'))

# Equivalencias para nombres del GeoJSON
dic_equivalencias = {
    "Amazonas": "Amazonas",
    "Antioquia": "Antioquia",
    "Arauca": "Arauca",
    "Atlántico": "Atlantico",
    "Bolívar": "Bolivar",
    "Boyacá": "Boyaca",
    "Caldas": "Caldas",
    "Caquetá": "Caqueta",
    "Casanare": "Casanare",
    "Cauca": "Cauca",
    "Cesar": "Cesar",
    "Chocó": "Choco",
    "Córdoba": "Cordoba",
    "Cundinamarca": "Cundinamarca",
    "Guainía": "Guainia",
    "Guaviare": "Guaviare",
    "Huila": "Huila",
    "La Guajira": "La Guajira",
    "Magdalena": "Magdalena",
    "Meta": "Meta",
    "Nariño": "Narino",
    "Norte De Santander": "Norte de Santander",
    "Putumayo": "Putumayo",
    "Quindío": "Quindio",
    "Risaralda": "Risaralda",
    "Archipiélago De San Andrés, Providencia Y Santa Catalina": "San Andres, Providencia y Santa Catalina",
    "Santander": "Santander",
    "Sucre": "Sucre",
    "Tolima": "Tolima",
    "Valle Del Cauca": "Valle del Cauca",
    "Vaupés": "Vaupes",
    "Vichada": "Vichada",
    "Bogotá, D.C.": "Bogota D.C."
}

df_mapa['DEPARTAMENTO'] = df_mapa['DEPARTAMENTO'].astype(str).str.title().str.strip()
df_mapa['shapeName'] = df_mapa['DEPARTAMENTO'].map(dic_equivalencias)

# GeoJSON
try:
    gdf = gpd.read_file('colombia_departamentos.geojson')
except:
    gdf = gpd.read_file('data/geoBoundaries-COL-ADM1_simplified.geojson')
gdf = gdf.to_crs(epsg=4326)
geo_json = json.loads(gdf.to_json())

fig_mapa = px.choropleth_map(
    df_mapa,
    geojson=geo_json,
    locations='shapeName',
    featureidkey='properties.shapeName',
    color='Total_Muertes_Dpto',
    hover_name='shapeName',
    hover_data={'Total_Muertes_Dpto': True},
    color_continuous_scale='Reds',
    title="Distribución Total de Muertes por Departamento (2019)",
    center={"lat": 4.6, "lon": -74.1},
    zoom=5,
    opacity=0.8,
    map_style="carto-positron"
)
fig_mapa.update_traces(marker_line_width=0.8, marker_line_color="black")
fig_mapa.update_layout(height=900, margin=dict(l=0,r=0,t=70,b=20), coloraxis_colorbar=dict(title="Total de muertes"))

# =========================================================================
# === 4. Gráfico de líneas: total de muertes por MES ===
# =========================================================================
df_meses = df_final.groupby('MES', as_index=False).size().rename(columns={'size':'Total_Muertes'})
fig_lineas = px.line(df_meses, x='MES', y='Total_Muertes', markers=True,
                     title='Total de Muertes por Mes (2019)', labels={'MES':'Mes', 'Total_Muertes':'Total de Muertes'})

# =========================================================================
# === 5. Top 5 ciudades más violentas (códigos X9) ===
# =========================================================================
df_violencia = df_final[df_final['COD_MUERTE'].str.startswith('X9')]
df_ciudades_violentas = df_violencia.groupby('MUNICIPIO', as_index=False).size().rename(columns={'size':'Total_Homicidios'})
df_ciudades_violentas = df_ciudades_violentas.sort_values('Total_Homicidios', ascending=False).head(5)
fig_barras_violencia = px.bar(df_ciudades_violentas, x='MUNICIPIO', y='Total_Homicidios',
                              title='Top 5 Ciudades más Violentas (Homicidios X9)', color='Total_Homicidios')

# =========================================================================
# === 6. Top 10 ciudades con menor mortalidad (porcentaje preciso) ===
# =========================================================================
#df_ciudades_total = df_final.groupby('MUNICIPIO', as_index=False).size().rename(columns={'size':'Total_Muertes'})
#df_ciudades_total['Porcentaje'] = df_ciudades_total['Total_Muertes'].values/df_ciudades_total['Total_Muertes'].sum()*100
#df_ciudades_menor = df_ciudades_total.sort_values('Total_Muertes').head(10)
#fig_pie_menor = px.pie(df_ciudades_menor, names='MUNICIPIO', values='Porcentaje',
#                       title='Top 10 Ciudades con Menor Mortalidad (%)')

df_ciudades_total = (df_final.groupby('MUNICIPIO', as_index=False).size().rename(columns={'size': 'Total_Muertes'}))

# Calcular porcentaje con más precisión
total_general = df_ciudades_total['Total_Muertes'].sum()
df_ciudades_total['Porcentaje'] = (df_ciudades_total['Total_Muertes'] / total_general) * 100

# Seleccionar las 10 ciudades con menor mortalidad
df_ciudades_menor = df_ciudades_total.sort_values('Total_Muertes').head(10)

# Crear gráfico de torta mostrando cantidad y porcentaje con dos decimales
fig_pie_menor = px.pie(
    df_ciudades_menor,
    names='MUNICIPIO',
    values='Total_Muertes',
    title='Top 10 Ciudades con Menor Mortalidad (Cantidad y Porcentaje)',
    hole=0,  # puedes cambiar a 0.3 si prefieres estilo "donut"
)

# Mostrar etiquetas con nombre + cantidad + porcentaje exacto
fig_pie_menor.update_traces(
    textinfo='label+value+percent',
    #texttemplate='%{label}<br>%{value} muertes<br>(%{percent:.2%})',
    texttemplate=f'%{{label}}<br>%{value} / int(total_general) muertes<br>({{percent:.2%}})',
    hovertemplate='<b>%{label}</b><br>Total: %{value} muertes<br>Porcentaje: %{percent:.2%}',
    textfont_size=13
) 

# =========================================================================
# === 7. Tabla de 10 principales causas de muerte ===
# =========================================================================
df_causas = df_final.groupby(['CodigoMuerte','DescripcionCodigoMuerte'], as_index=False).size().rename(columns={'size':'Total_Casos'})
df_causas = df_causas.sort_values('Total_Casos', ascending=False).head(10)
fig_tabla_causas = go.Figure(data=[go.Table(
    header=dict(values=list(df_causas.columns), fill_color='paleturquoise', align='left'),
    cells=dict(values=[df_causas.CodigoMuerte, df_causas.DescripcionCodigoMuerte, df_causas.Total_Casos],
               fill_color='lavender', align='left'))
])

# =========================================================================
# === 8. Barras apiladas por sexo y departamento ===
# =========================================================================
df_sexo_dpto = df_final.groupby(['DEPARTAMENTO','SEXO'], as_index=False).size().rename(columns={'size':'Total'})
fig_barras_sexo = px.bar(df_sexo_dpto, x='DEPARTAMENTO', y='Total', color='SEXO',
                         title='Comparación de muertes por SEXO y Departamento', barmode='stack')

# =========================================================================
# === 9. Histograma por rango de edad aproximado ===
# =========================================================================
# Rango aproximado según tu tabla
rango_edad = {
    0:'0-4', 5:'1-11 meses', 7:'1-4', 9:'5-14', 11:'15-19', 12:'20-29',
    14:'30-44', 17:'45-59', 20:'60-84', 25:'85-100+', 29:'Sin información'
}

df_final['RangoEdad'] = df_final['GRUPO_EDAD1'].map(rango_edad)
df_hist_edad = df_final.groupby('RangoEdad', as_index=False).size().rename(columns={'size':'Total_Muertes'})
fig_hist_edad = px.bar(df_hist_edad, x='RangoEdad', y='Total_Muertes', title='Distribución de Muertes por Rango de Edad')

# =========================================================================
# === 10. DASH APP ===
# =========================================================================
app = Dash(__name__)
server = app.server

app.layout = html.Div(style={'backgroundColor':'#f8f9fa','padding':'20px'}, children=[
#    html.H1('Análisis de Mortalidad en Colombia (2019) 🇨🇴', style={'textAlign':'center','color':'#343a40','margin-bottom':'30px'}),
    html.H1('Análisis de Mortalidad en Colombia (2019) 🇨🇴', style={'textAlign': 'center', 'color': '#343a40', 'margin-bottom': '10px'}),
    html.H4('Autores: Oswaldo Naranjo Veloza y Manuel Antonio Sanabria Gil', style={'textAlign': 'center', 'color': '#6c757d', 'margin-bottom': '30px'}),
#
    html.Div(style={'backgroundColor':'white','padding':'10px','borderRadius':'8px','boxShadow':'0 4px 6px rgba(0,0,0,0.1)','maxWidth':'95%','margin':'auto'}, children=[
        dcc.Graph(id='mapa-mortalidad', figure=fig_mapa),
        dcc.Graph(id='lineas-mes', figure=fig_lineas),
        dcc.Graph(id='barras-violencia', figure=fig_barras_violencia),
        dcc.Graph(id='pie-menor', figure=fig_pie_menor),
        dcc.Graph(id='tabla-causas', figure=fig_tabla_causas),
        dcc.Graph(id='barras-sexo', figure=fig_barras_sexo),
        dcc.Graph(id='hist-edad', figure=fig_hist_edad)
    ])
])

if __name__ == '__main__':
    print(" Servidor ejecutándose en: http://127.0.0.1:8050/")
    app.run(debug=True)
