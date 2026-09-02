import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests

# Configura el título de la pestaña del navegador y el icono
st.set_page_config(
    page_title="Buscador Avanzado de Hospitales - CyL",  # <--- Esto solo va a la pestaña
    page_icon="🏥",
    layout="wide"
)

# TÍTULO VISIBLE DENTRO DE LA PÁGINA WEB
st.title("🏥 ¿Qué hospital me pilla más cerca?")
st.markdown("### Encuentra el hospital más cercano a tu municipio de Castilla y León")
#st.caption("Localiza centros sanitarios por especialidad médica, distancia por carretera y tiempo de viaje estimado.")
st.info("💡 **Indicaciones:** Localiza los centros sanitarios más cercanos según la especialidad médica seleccionada. Las distancias y tiempos de viaje mostrados son **reales por carretera**.")

# 1. CABECERA
# st.title("🏥 Buscador Avanzado de Hospitales - Castilla y León")

# 2. CAJA DE METODOLOGÍA (Usamos st.expander para que no ocupe espacio si el usuario no la abre)
with st.expander("ℹ️ Ver metodología y fuente de datos"):
    st.markdown("""
    **¿Cómo funciona este buscador?**
    
    1. **Geolocalización y Origen:** Se toma como punto de partida la ubicación del municipio seleccionado de Castilla y León a partir del [listado oficial de municipios](https://datosabiertos.jcyl.es/web/jcyl/set/es/sector-publico/municipios/1284278782067) de la Junta de Castilla y León.
    2. **Cálculo de Rutas Reales:** Las distancias y tiempos de desplazamiento se calculan consultando la API pública de **OSRM (Open Source Routing Machine)** para obtener trayectos y tiempos reales por carretera.
    3. **Filtrado por Especialidades:** Los datos de especialidades de los centros sanitarios proceden del [Catálogo Oficial de Hospitales del Ministerio de Sanidad](https://www.sanidad.gob.es/ciudadanos/centrosCA.do), que han sido geolocalizado usando la librería Geopy.
    4. El sitio web se ha generado mediante Python, y se ha programado con la ayuda de Gemini.
    """)
 

# -----------------------------------------------------------------------------
# DICCIONARIO CON PALABRAS CLAVE PRECISAS
# -----------------------------------------------------------------------------
DICCIONARIO_ESPECIALIDADES = {
    "🌐 Todas las especialidades y centros": [],
    
    # --- ÁREA MÉDICA Y ÓRGANOS INTERNOS ---
    "🦴 Huesos, Músculos y Traumatología (Cirugía Ortopédica / Reumatología)": [
        "traumatolog", "ortoped", "cirugia ortopedica", "reumatolog", "artrosis", "trauma"
    ],
    "🫁 Aparato Respiratorio y Pulmones (Neumología)": [
        "neumolog", "respiratorio", "pulmon", "cirugia toracica", "asma"
    ],
    "❤️ Corazón y Circulación (Cardiología / Cirugía Cardiovascular)": [
        "cardiolog", "vascular", "circatorio", "corazon", "arritmias", "angiolog"
    ],
    "🩸 Aparato Digestivo y Estómago (Gastroenterología / Hepatología)": [
        "digestivo", "gastroenterolog", "endoscopia", "higado", "hepatolog"
    ],
    "🧠 Cerebro y Sistema Nervioso (Neurología / Neurocirugía)": [
        "neurolog", "cerebro", "sistema nervioso", "ictus", "epilepsia", "neurocirugia"
    ],
    "🧪 Riñón y Vías Urinarias (Nefrología / Urología)": [
        "nefrolog", "urolog", "riñon", "prostata", "vias urinarias"
    ],
    "🩺 Hormonas, Diabetes y Nutrición (Endocrinología)": [
        "endocrinolog", "diabetes", "tiroides", "nutricion", "metabolismo"
    ],
    "🩸 Sangre y Sistema Inmune (Hematología / Alergología)": [
        "hematolog", "alergolog", "anemia", "transfusion"
    ],

    # --- MATERNO-INFANTIL Y EDADES ---
    "👶 Niños y Bebés (Pediatría y Cirugía Pediátrica)": [
        "pediatria", "materno infantil", "neonatolog", "pediatrica"
    ],
    "🤰 Mujer y Embarazo (Obstetricia y Ginecología)": [
        "ginecolog", "obstetricia", "maternidad", "parto", "reproduccion asistida"
    ],
    "🧓 Personas Mayores (Geriatría)": [
        "geriatria", "geriatrico"
    ],

    # --- ÁREA QUIRÚRGICA Y CIRUGÍAS ---
    "✂️ Cirugía General y Digestiva": [
        "cirugia general", "general y digestivo"
    ],
    "✨ Cirugía Plástica, Estética y Reparadora": [
        "cirugia plastica", "estetica", "reparadora", "quemados"
    ],
    "🦷 Boca, Cara y Mandíbula (Cirugía Maxilofacial / Odontología)": [
        "maxilofacial", "odontolog", "estomatolog"
    ],

    # --- CABEZA, SENTIDOS Y PIEL ---
    "👁️ Visión y Ojos (Oftalmología)": [
        "oftalmolog", "ojos", "retina", "cataratas"
    ],
    "👂 Oído, Nariz y Garganta (Otorrinolaringología - ORL)": [
        "otorrinolaringolog", "orl"
    ],
    "🧴 Piel, Dermatología y Venereología": [
        "dermatolog", "piel", "melanoma"
    ],

    # --- ONCOLOGÍA Y TRATAMIENTOS ESPECIALES ---
    "🎗️ Cáncer y Tumores (Oncología Médica / Radioterápica)": [
        "oncolog", "cancer", "tumor", "quimioterapia", "radioterapia"
    ],
    "🧠 Salud Mental y Conducta (Psiquiatría / Psicología)": [
        "psiquiatria", "salud mental", "psicologia clinical"
    ],

    # --- URGENCIAS Y DIAGNÓSTICO ---
    "🚨 Urgencias y Cuidados Intensivos (UCI / Cuidados Críticos)": [
        "urgencias", "uci", "intensivos", "reanimacion"
    ],
    "📸 Radiología e Imagen Diagnóstica (TAC / Resonancia / Ecografía)": [
        "radiodiagnostico", "radiolog", "resonancia magnetica", "tac", "ecografia"
    ]
}

# -----------------------------------------------------------------------------
# 1. CARGA Y PREPARACIÓN DE DATOS
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    df_mun = pd.read_csv("MunicipiosJCyL_utf8.csv", encoding="utf-8-sig")
    df_hosp = pd.read_csv("Catalogo_Hospitales_Geolocalizados.csv", encoding="utf-8-sig")
    
    df_mun.columns = df_mun.columns.str.strip().str.lower()
    df_hosp.columns = df_hosp.columns.str.strip().str.lower()

    # Función de reparación de caracteres mal codificados (sin librerías externas)
    def reparar_texto(texto):
        if not isinstance(texto, str):
            return texto
        try:
            return texto.encode('latin1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return texto

    columnas_texto = [
        'nombre', 'municipio', 'provincia', 'comunidad autonoma', 
        'comunidad_autonoma', 'dependencia funcional', 'tipo de centro', 
        'observaciones', 'servicios'
    ]
    
    for col in columnas_texto:
        if col in df_hosp.columns:
            df_hosp[col] = df_hosp[col].apply(reparar_texto)
        if col in df_mun.columns:
            df_mun[col] = df_mun[col].apply(reparar_texto)

    df_mun = df_mun.rename(columns={'municipio': 'nombre', 'lat': 'latitud', 'lon': 'longitud'})

    def limpiar_coordenada(serie):
        if serie.dtype == object:
            serie = serie.astype(str).str.replace(',', '.')
        return pd.to_numeric(serie, errors='coerce')

    df_mun["latitud"] = limpiar_coordenada(df_mun["latitud"])
    df_mun["longitud"] = limpiar_coordenada(df_mun["longitud"])
    df_hosp["latitud"] = limpiar_coordenada(df_hosp["latitud"])
    df_hosp["longitud"] = limpiar_coordenada(df_hosp["longitud"])

    df_mun = df_mun.dropna(subset=["latitud", "longitud"])
    df_hosp = df_hosp.dropna(subset=["latitud", "longitud"])

    def quitar_acentos(texto):
        if not isinstance(texto, str):
            return ""
        trans = str.maketrans("áéíóúÁÉÍÓÚñÑüÜ", "aeiouAEIOUnNuU")
        return texto.translate(trans).lower()

    # CyL vs Otras CCAA
    col_ccaa = next((c for c in ['comunidad autonoma', 'comunidad_autonoma', 'ccaa'] if c in df_hosp.columns), None)
    if col_ccaa:
        df_hosp['es_cyl'] = df_hosp[col_ccaa].astype(str).str.contains('Castilla y Le', case=False, na=False)
    else:
        provincias_cyl = ['ÁVILA', 'AVILA', 'BURGOS', 'LEÓN', 'LEON', 'PALENCIA', 'SALAMANCA', 'SEGOVIA', 'SORIA', 'VALLADOLID', 'ZAMORA']
        col_prov = next((c for c in ['provincia', 'cod_provincia'] if c in df_hosp.columns), 'provincia')
        if col_prov in df_hosp.columns:
            df_hosp['es_cyl'] = df_hosp[col_prov].astype(str).str.upper().isin(provincias_cyl)
        else:
            df_hosp['es_cyl'] = True

    df_hosp['origen_ccaa'] = df_hosp['es_cyl'].map({True: '🟢 Castilla y León', False: '🔵 Otra CCAA'})

    # Titularidad
    col_dep = next((c for c in ['dependencia funcional', 'dependencia_funcional', 'dependencia'] if c in df_hosp.columns), None)
    col_concierto = next((c for c in ['concierto'] if c in df_hosp.columns), None)

    def clasificar_titularidad(row):
        dep = str(row[col_dep]).lower() if (col_dep and pd.notna(row[col_dep])) else ""
        conc = str(row[col_concierto]).lower() if (col_concierto and pd.notna(row[col_concierto])) else ""

        publico_keywords = ['servicio autonomico', 'sacyl', 'seguridad social', 'defensa', 'militar', 'diputacion', 'ayuntamiento', 'publico']
        
        if any(kw in quitar_acentos(dep) for kw in publico_keywords):
            return "Público"
        elif "concierto" in conc or "si" in conc:
            return "Privado Concertado"
        else:
            return "Privado"

    df_hosp['titularidad'] = df_hosp.apply(clasificar_titularidad, axis=1)

    # Tipo de centro
    col_tipo = next((c for c in ['tipo de centro', 'tipo_centro', 'especialidad', 'oferta asistencial'] if c in df_hosp.columns), None)
    if col_tipo:
        df_hosp['tipo_centro_clean'] = df_hosp[col_tipo].fillna('General / Sin especificar')
    else:
        df_hosp['tipo_centro_clean'] = 'General'

    # Texto indexado
    obs_text = df_hosp['observaciones'].astype(str) if 'observaciones' in df_hosp.columns else ""
    serv_text = df_hosp['servicios'].astype(str) if 'servicios' in df_hosp.columns else ""

    df_hosp['texto_index'] = (
        df_hosp['nombre'].astype(str) + " " +
        df_hosp['tipo_centro_clean'].astype(str) + " " +
        obs_text + " " + serv_text
    ).apply(quitar_acentos)

    return df_mun, df_hosp

# LLAMADA OBLIGATORIA A LA CARGA DE DATOS
try:
    df_municipios, df_hospitales = cargar_datos()
    st.sidebar.success("✅ Datos cargados correctamente")
except Exception as e:
    st.error(f"Error al cargar los archivos CSV: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 2. FUNCIONES DE DISTANCIA (HAVERSINE Y OSRM)
# -----------------------------------------------------------------------------
def haversine_vectorized(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

@st.cache_data(show_spinner=False)
def obtener_ruta_osrm(lat1, lon1, lat2, lon2):
    """Consulta la API de OSRM para obtener la distancia real por carretera y tiempo de viaje."""
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            datos = r.json()
            if datos.get("code") == "Ok":
                dist_km = datos["routes"][0]["distance"] / 1000.0
                duracion_min = datos["routes"][0]["duration"] / 60.0
                return round(dist_km, 1), round(duracion_min)
    except Exception:
        pass
    
    # Estimación fallback
    dist_haversine = haversine_vectorized(lat1, lon1, lat2, lon2)
    dist_estimada = dist_haversine * 1.3
    tiempo_estimado = (dist_estimada / 80.0) * 60
    return round(dist_estimada, 1), round(tiempo_estimado)

# -----------------------------------------------------------------------------
# 3. FILTROS EN BARRA LATERAL
# -----------------------------------------------------------------------------
st.sidebar.header("📍 1. Ubicación de Origen")
provincias = sorted(df_municipios["provincia"].dropna().unique())
provincia_sel = st.sidebar.selectbox("Provincia de CyL:", provincias)

municipios_prov = df_municipios[df_municipios["provincia"] == provincia_sel]
municipio_sel = st.sidebar.selectbox("Municipio:", sorted(municipios_prov["nombre"].unique()))

datos_mun = municipios_prov[municipios_prov["nombre"] == municipio_sel].iloc[0]
lat_mun = float(datos_mun["latitud"])
lon_mun = float(datos_mun["longitud"])

st.sidebar.header("🩺 2. Especialidad Médica")
especialidad_elegida = st.sidebar.selectbox(
    "Selecciona Especialidad o Área Médica:",
    options=list(DICCIONARIO_ESPECIALIDADES.keys())
)

st.sidebar.header("⚙️ 3. Filtros del Centro")
filtro_ccaa = st.sidebar.radio("Ámbito Territorial:", ["Todos (Incluir provincias limítrofes)", "Solo Castilla y León"])

filtro_titularidad = st.sidebar.multiselect(
    "Titularidad:",
    ["Público", "Privado Concertado", "Privado"],
    default=["Público", "Privado Concertado", "Privado"]
)

radio_max_km = st.sidebar.slider("Distancia máxima de búsqueda (km):", 10, 300, 150)
num_resultados = st.sidebar.slider("Mostrar X hospitales más cercanos:", 1, 20, 5)

# -----------------------------------------------------------------------------
# 4. FILTRADO Y CÁLCULO POR CARRETERA
# -----------------------------------------------------------------------------
df_filtrado = df_hospitales.copy()

df_filtrado["dist_recta_km"] = haversine_vectorized(
    lat_mun, lon_mun, 
    df_filtrado["latitud"].values, df_filtrado["longitud"].values
)

df_filtrado = df_filtrado[df_filtrado["dist_recta_km"] <= radio_max_km]

if filtro_ccaa == "Solo Castilla y León":
    df_filtrado = df_filtrado[df_filtrado["es_cyl"] == True]

if filtro_titularidad:
    df_filtrado = df_filtrado[df_filtrado["titularidad"].isin(filtro_titularidad)]

palabras_clave = DICCIONARIO_ESPECIALIDADES[especialidad_elegida]

if palabras_clave:
    terminos_hospital_general = "general|complejo asistencial|hospital universitario|clinico|comarcal"
    pattern_especialidad = '|'.join(palabras_clave)
    
    condicion_especialidad = df_filtrado["texto_index"].str.contains(pattern_especialidad, na=False, regex=True)
    condicion_general = df_filtrado["texto_index"].str.contains(terminos_hospital_general, na=False, regex=True)
    
    df_filtrado = df_filtrado[condicion_especialidad | condicion_general]

if df_filtrado.empty:
    st.warning("⚠️ No se encontraron hospitales en ese radio con los criterios seleccionados. Amplía el deslizador de 'Distancia máxima de búsqueda' en la barra lateral.")
    st.stop()

candidatos = df_filtrado.sort_values(by="dist_recta_km").head(num_resultados * 2).copy()

with st.spinner("🚗 Calculando rutas y tiempos de viaje por carretera..."):
    distancias_carretera = []
    tiempos_minutos = []
    
    for _, row in candidatos.iterrows():
        d_carretera, t_min = obtener_ruta_osrm(lat_mun, lon_mun, row["latitud"], row["longitud"])
        distancias_carretera.append(d_carretera)
        tiempos_minutos.append(t_min)
        
    candidatos["distancia_carretera_km"] = distancias_carretera
    candidatos["tiempo_min"] = tiempos_minutos

cercanos = candidatos.sort_values(by="tiempo_min").head(num_resultados)

# -----------------------------------------------------------------------------
# 5. VISUALIZACIÓN DE RESULTADOS
# -----------------------------------------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Mapa desde {municipio_sel} ({provincia_sel})")
    
    m = folium.Map(location=[lat_mun, lon_mun], zoom_start=9)
    
    folium.Marker(
        [lat_mun, lon_mun],
        popup=f"<b>{municipio_sel}</b>",
        tooltip="Origen",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)
    
    color_map = {"Público": "blue", "Privado Concertado": "orange", "Privado": "gray"}
    for _, h in cercanos.iterrows():
        icon_color = color_map.get(h["titularidad"], "blue")
        
        popup_html = f"""
        <b>{h['nombre']}</b><br>
        <b>Ámbito:</b> {h['origen_ccaa']}<br>
        <b>Titularidad:</b> {h['titularidad']}<br>
        <b>Tipo:</b> {h['tipo_centro_clean']}<br>
        <b>🚗 Carretera:</b> {h['distancia_carretera_km']} km<br>
        <b>⏱️ Tiempo estimado:</b> {h['tiempo_min']} min
        """
        
        folium.Marker(
            [h["latitud"], h["longitud"]],
            popup=popup_html,
            tooltip=f"{h['nombre']} ({h['distancia_carretera_km']} km | {h['tiempo_min']} min)",
            icon=folium.Icon(color=icon_color, icon="plus")
        ).add_to(m)
    
    st_folium(m, width=800, height=520)

with col2:
    st.subheader("Hospitales Más Cercanos")
    st.caption(f"Filtro aplicado: **{especialidad_elegida}**")
    
    for idx, row in cercanos.iterrows():
        st.markdown(f"### {row['nombre']}")
        
        badge_ccaa = "🟢 CyL" if row["es_cyl"] else "🔵 Fuera de CyL"
        st.write(f"**{badge_ccaa}** | **Titularidad:** {row['titularidad']}")
        st.caption(f"🏥 **Clasificación:** {row['tipo_centro_clean']}")
        st.caption(f"🚗 **{row['distancia_carretera_km']} km por carretera** | ⏱️ **~{row['tiempo_min']} min en coche**")
        st.caption(f"📍 {row.get('municipio', '')} ({row.get('provincia', '')})")
        st.divider()

st.subheader("📊 Lista Detallada de Tiempos y Distancias")
cols_tabla = [c for c in ["nombre", "origen_ccaa", "titularidad", "tipo_centro_clean", "provincia", "distancia_carretera_km", "tiempo_min"] if c in cercanos.columns]
st.dataframe(cercanos[cols_tabla].rename(columns={
    'nombre': 'Hospital',
    'origen_ccaa': 'Comunidad Aut.',
    'titularidad': 'Titularidad',
    'tipo_centro_clean': 'Tipo de Centro / Especialidad',
    'provincia': 'Provincia',
    'distancia_carretera_km': 'Distancia Carretera (km)',
    'tiempo_min': 'Tiempo estimado (min)'
}), use_container_width=True)

# 3. PIE DE PÁGINA / AUTORÍA (Colócalo al final de todo tu script app5.py)
st.divider()  # Línea separadora visual

st.markdown(
    """
    <div style="text-align: center; color: #666666; font-size: 1.3em; padding: 10px 0;">
        Creado por <strong>DATABIERTO</strong> (Open Science Lab - UC3M)
    </div>
    """,
    unsafe_allow_html=True
)