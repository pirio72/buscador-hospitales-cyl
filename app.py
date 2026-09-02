import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA (Pestaña del navegador)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Buscador Avanzado de Hospitales - Castilla y León",
    page_icon="🏥",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. CABECERA Y METODOLOGÍA
# -----------------------------------------------------------------------------
st.title("🏥 Buscador Avanzado de Hospitales - Castilla y León")
st.markdown("##### Localiza centros sanitarios por especialidad médica, distancia por carretera y tiempo de viaje estimado.")

with st.expander("ℹ️ Ver metodología y fuente de datos"):
    st.markdown("""
    **¿Cómo funciona este buscador?**
    
    1. **Geolocalización y Origen:** Se toma como punto de partida la ubicación del municipio seleccionado de Castilla y León a partir del listado oficial.
    2. **Cálculo de Rutas Reales:** Las distancias y tiempos de desplazamiento no se calculan "en línea recta", sino consultando la API pública de **OSRM (Open Source Routing Machine)** para obtener trayectos y tiempos reales por carretera.
    3. **Filtrado por Especialidades:** Los datos de especialidades de los centros sanitarios proceden del Catálogo Oficial de Hospitales geolocalizados.
    """)

# -----------------------------------------------------------------------------
# 3. CARGA Y LIMPIEZA DE DATOS (CON CACHÉ)
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    # Cargar municipios
    try:
        df_mun = pd.read_csv("MunicipiosJCyL_utf8.csv", encoding="utf-8")
    except UnicodeDecodeError:
        df_mun = pd.read_csv("MunicipiosJCyL_utf8.csv", encoding="latin1")

    # Cargar hospitales
    try:
        df_hosp = pd.read_csv("Catalogo_Hospitales_Geolocalizados.csv", encoding="utf-8")
    except UnicodeDecodeError:
        df_hosp = pd.read_csv("Catalogo_Hospitales_Geolocalizados.csv", encoding="latin1")

    # Limpieza de espacios en blanco invisibles
    df_mun["provincia"] = df_mun["provincia"].astype(str).str.strip()
    df_mun["nombre"] = df_mun["nombre"].astype(str).str.strip()
    
    # Asegurar conversión numérica de coordenadas en municipios
    df_mun["latitud"] = pd.to_numeric(df_mun["latitud"].astype(str).str.replace(',', '.'), errors='coerce')
    df_mun["longitud"] = pd.to_numeric(df_mun["longitud"].astype(str).str.replace(',', '.'), errors='coerce')

    # Limpieza de datos en hospitales
    df_hosp["LATITUD"] = pd.to_numeric(df_hosp["LATITUD"].astype(str).str.replace(',', '.'), errors='coerce')
    df_hosp["LONGITUD"] = pd.to_numeric(df_hosp["LONGITUD"].astype(str).str.replace(',', '.'), errors='coerce')
    df_hosp["OFERTA_DOC"] = df_hosp["OFERTA_DOC"].fillna("Sin especificar").astype(str)

    return df_mun, df_hosp

df_municipios, df_hospitales = cargar_datos()

# -----------------------------------------------------------------------------
# 4. FUNCIÓN PARA CÁLCULO DE RUTAS VÍA OSRM
# -----------------------------------------------------------------------------
def obtener_ruta_osrm(lat_origen, lon_origen, lat_destino, lon_destino):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon_origen},{lat_origen};{lon_destino},{lat_destino}?overview=false"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "routes" in data and len(data["routes"]) > 0:
                distancia_km = data["routes"][0]["distance"] / 1000.0
                tiempo_min = data["routes"][0]["duration"] / 60.0
                return round(distancia_km, 1), round(tiempo_min, 0)
    except Exception:
        pass
    return None, None

# -----------------------------------------------------------------------------
# 5. BARRA LATERAL (SIDEBAR) - FILTROS
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 Filtros de Búsqueda")

# Selección de Provincia
provincias_disponibles = sorted(df_municipios["provincia"].dropna().unique())
provincia_sel = st.sidebar.selectbox("1. Selecciona Provincia:", provincias_disponibles)

# Filtrar municipios según la provincia elegida
municipios_prov = df_municipios[df_municipios["provincia"] == provincia_sel]
municipios_disponibles = sorted(municipios_prov["nombre"].dropna().unique())

# Selección de Municipio (Protegido)
if municipios_disponibles:
    municipio_sel = st.sidebar.selectbox("2. Selecciona Municipio:", municipios_disponibles)
    datos_mun = municipios_prov[municipios_prov["nombre"] == municipio_sel]
    
    if not datos_mun.empty and not pd.isna(datos_mun["latitud"].iloc[0]):
        lat_mun = float(datos_mun["latitud"].iloc[0])
        lon_mun = float(datos_mun["longitud"].iloc[0])
    else:
        st.error(f"No se encontraron coordenadas válidas para el municipio: {municipio_sel}")
        st.stop()
else:
    st.warning("No hay municipios disponibles para la provincia seleccionada.")
    st.stop()

# Filtro de Especialidades
st.sidebar.subheader("Especialidades y Servicios")
todas_especialidades = set()
for oferta in df_hospitales["OFERTA_DOC"].dropna():
    items = [item.strip() for item in oferta.split(";") if item.strip()]
    todas_especialidades.update(items)

especialidades_ordenadas = sorted(list(todas_especialidades))
especialidad_sel = st.sidebar.multiselect("Filtrar por especialidad:", especialidades_ordenadas)

# -----------------------------------------------------------------------------
# 6. FILTRADO Y CÁLCULO DE DISTANCIAS
# -----------------------------------------------------------------------------
# Filtrar por especialidades seleccionadas
if especialidad_sel:
    def tiene_especialidad(oferta):
        return any(esp in str(oferta) for esp in especialidad_sel)
    
    df_filtrado = df_hospitales[df_hospitales["OFERTA_DOC"].apply(tiene_especialidad)].copy()
else:
    df_filtrado = df_hospitales.copy()

# Botón para ejecutar cálculo de rutas reales por carretera
st.sidebar.markdown("---")
calcular_rutas = st.sidebar.button("🚗 Calcular Distancias Reales", type="primary")

if calcular_rutas:
    with st.spinner("Calculando rutas por carretera desde " + municipio_sel + "..."):
        distancias = []
        tiempos = []
        for _, row in df_filtrado.iterrows():
            if pd.notna(row["LATITUD"]) and pd.notna(row["LONGITUD"]):
                d, t = obtener_ruta_osrm(lat_mun, lon_mun, float(row["LATITUD"]), float(row["LONGITUD"]))
                distancias.append(d)
                tiempos.append(t)
            else:
                distancias.append(None)
                tiempos.append(None)
        
        df_filtrado["Distancia (km)"] = distancias
        df_filtrado["Tiempo (min)"] = tiempos
        df_filtrado = df_filtrado.sort_values(by="Distancia (km)", ascending=True)

# -----------------------------------------------------------------------------
# 7. MAPA INTERACTIVO (FOLIUM) Y TABLA
# -----------------------------------------------------------------------------
m = folium.Map(location=[lat_mun, lon_mun], zoom_start=9)

# Marcador del municipio origen
folium.Marker(
    location=[lat_mun, lon_mun],
    popup=f"<b>Origen:</b> {municipio_sel}",
    icon=folium.Icon(color="green", icon="home", prefix="fa")
).add_to(m)

# Marcadores de los hospitales
for _, row in df_filtrado.iterrows():
    if pd.notna(row["LATITUD"]) and pd.notna(row["LONGITUD"]):
        popup_txt = f"<b>{row['NOMBRE']}</b><br>{row.get('NOMBRE_MUNICIPIO', '')}"
        if "Distancia (km)" in df_filtrado.columns and pd.notna(row["Distancia (km)"]):
            popup_txt += f"<br>🚗 {row['Distancia (km)']} km ({int(row['Tiempo (min)'])} min)"
            
        folium.Marker(
            location=[float(row["LATITUD"]), float(row["LONGITUD"])],
            popup=popup_txt,
            icon=folium.Icon(color="red", icon="plus-square", prefix="fa")
        ).add_to(m)

# Mostrar mapa en la app
st_folium(m, width="100%", height=500)

# Tabla de resultados
st.subheader("🏥 Hospitales Encontrados")
columnas_mostrar = ["NOMBRE", "NOMBRE_MUNICIPIO", "OFERTA_DOC"]
if "Distancia (km)" in df_filtrado.columns:
    columnas_mostrar.extend(["Distancia (km)", "Tiempo (min)"])

st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True)

# -----------------------------------------------------------------------------
# 8. PIE DE PÁGINA (AUTORÍA)
# -----------------------------------------------------------------------------
st.divider()
st.markdown(
    """
    <div style="text-align: center; color: #666666; font-size: 0.9em; padding: 10px 0;">
        <strong>DATABIERTO</strong> (Open Science Lab - UC3M)
    </div>
    """,
    unsafe_allow_html=True
)