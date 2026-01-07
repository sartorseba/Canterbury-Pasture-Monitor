import streamlit as st
import ee
import pandas as pd
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
import folium
import json
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="NZ Pasture Monitor", layout="wide")

st.markdown("""
    <style>
    .stSlider > div [data-baseweb="slider"] > div { background: linear-gradient(to right, #ff4b4b 0%, #ff4b4b var(--slider-value), #d3d3d3 var(--slider-value), #d3d3d3 100%); }
    div[data-testid="stThumbValue"] { color: #ff4b4b; }
    div[role="slider"] { background-color: #ff4b4b !important; border-color: #ff4b4b !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MEMORIA DE SESIÓN ---
if 'lat' not in st.session_state: st.session_state.lat = -43.5320
if 'lon' not in st.session_state: st.session_state.lon = 172.6306
# El centro del mapa inicia donde el usuario mira
if 'map_center' not in st.session_state: st.session_state.map_center = [-43.5320, 172.6306]
if 'zoom' not in st.session_state: st.session_state.zoom = 12
if 'analysis_results' not in st.session_state: st.session_state.analysis_results = None
if 'url_cache' not in st.session_state: st.session_state.url_cache = {}

# --- 3. CONEXIÓN ---
@st.cache_resource
def iniciar_conexion_gee():
    try:
        if "GEE_JSON" in st.secrets:
            info = json.loads(st.secrets["GEE_JSON"])
            credentials = ee.ServiceAccountCredentials(info['client_email'], key_data=st.secrets["GEE_JSON"])
            ee.Initialize(credentials, project=info['project_id'])
        else:
            ee.Initialize(project='nz-biomass')
        return True
    except Exception as e:
        return str(e)

gee_status = iniciar_conexion_gee()
if gee_status is not True:
    st.error(f"❌ Connection Failed: {gee_status}")
    st.stop()

# --- 4. DICCIONARIO ---
tr = {
    "en": {"title": "🇳🇿 Satellite Biomass Monitor - Canterbury", "map_sub": "🗺️ Click on the map to select your paddock", "side_agron": "🌱 Pasture Configuration", "period": "Analysis Period", "specie": "Forage Species", "slope_label": "Slope (m)", "intercept_label": "Intercept (b)", "cons_vaca": "Intake (kg DM/cow/day)", "rotacion": "Rotation Days (Rest)", "audit": "📅 Capture Audit", "switch_label": "View NDVI Layer (On) / Visible RGB (Off)", "city_warn": "⚠️ Urban area detected. Production set to 0 for accuracy.", "sem_title": "🚦 Sustainable Stocking Rate", "sem_formula": "Carrying Capacity Formula:", "metric_bio_last": "Last Detected Biomass", "metric_bio_sel": "Biomass on Selected Date", "metric_tasa": "Growth Rate", "metric_avg": "Period Average", "btn_run": "🚀 Run Analysis", "download": "📥 Download CSV Report"},
    "es": {"title": "🇳🇿 Monitor de Biomasa Satelital - Canterbury", "map_sub": "🗺️ Haz clic en el mapa para seleccionar tu lote", "side_agron": "🌱 Configuración de Pastura", "period": "Período de Análisis", "specie": "Especie Forrajera", "slope_label": "Pendiente (m)", "intercept_label": "Intercepto (b)", "cons_vaca": "Consumo (kg MS/vaca/día)", "rotacion": "Días de Rotación (Descanso)", "audit": "📅 Auditoría de Captura", "switch_label": "Ver Capa NDVI (Encendido) / Satélite Real (Apagado)", "city_warn": "⚠️ Zona urbana detectada. Producción seteada en cero por precisión.", "sem_title": "🚦 Carga Animal Sustentable", "sem_formula": "Fórmula de Carga Soportable:", "metric_bio_last": "Última Biomasa Detectada", "metric_bio_sel": "Biomasa en Fecha Seleccionada", "metric_tasa": "Tasa de Crecimiento", "metric_avg": "Promedio del Período", "btn_run": "🚀 Ejecutar Análisis", "download": "📥 Descargar Reporte CSV"}
}

idioma_opt = st.sidebar.selectbox("🌐 Language / Idioma", ["English", "Español"], index=0)
l = tr["en"] if idioma_opt == "English" else tr["es"]
st.title(l["title"])

# --- 5. MAPA INTERACTIVO PRO (Optimizado) ---
st.subheader(l["map_sub"])

m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.zoom)
folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Hybrid', overlay=False).add_to(m)

# El Pin sigue la lógica de datos
folium.Marker(
    [st.session_state.lat, st.session_state.lon], 
    popup="Selected Paddock", 
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(m)

# FIX DINÁMICA NATURAL: "returned_objects" evita la carga pesada al hacer zoom
map_data = st_folium(
    m, 
    height=350, 
    width="stretch", 
    key="mapa_canterbury", 
    returned_objects=["last_clicked", "center", "zoom"]
)

# Lógica de Actualización Silenciosa
if map_data:
    changed = False
    
    # Actualizamos donde mira el usuario (Zoom/Pan)
    if map_data.get('zoom') and map_data['zoom'] != st.session_state.zoom:
        st.session_state.zoom = map_data['zoom']
        # No hacemos rerun aquí, dejamos que fluya natural
        
    if map_data.get('center'):
        st.session_state.map_center = [map_data['center']['lat'], map_data['center']['lng']]

    # Solo hacemos RERUN si cambia el PIN (Clic explícito)
    if map_data.get('last_clicked'):
        new_lat = map_data['last_clicked']['lat']
        new_lon = map_data['last_clicked']['lng']
        if new_lat != st.session_state.lat or new_lon != st.session_state.lon:
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            st.rerun()

# --- 6. SIDEBAR ---
st.sidebar.header(l["side_agron"])
lat_in = st.sidebar.number_input("Lat", value=st.session_state.lat, format="%.4f")
lon_in = st.sidebar.number_input("Lon", value=st.session_state.lon, format="%.4f")

# Sincronización manual forzada
if lat_in != st.session_state.lat or lon_in != st.session_state.lon:
    st.session_state.lat = lat_in
    st.session_state.lon = lon_in
    st.session_state.map_center = [lat_in, lon_in]
    st.rerun()

# FECHA AUTOMÁTICA (1 Año atrás)
hoy = datetime.now().date()
un_anio_atras = hoy - timedelta(days=365)
rango = st.sidebar.date_input(l["period"], value=(un_anio_atras, hoy))

especies = {"Raigrás Perenne (NZ)": {"s": 5800, "i": 1200, "c": 18, "r": 21}, "Alfalfa (Lucerne)": {"s": 6157, "i": 1346, "c": 16, "r": 35}}
esp_n = st.sidebar.selectbox(l["specie"], list(especies.keys()))
slope = st.sidebar.slider(l["slope_label"], 3000, 7500, especies[esp_n]["s"])
intercept = st.sidebar.slider(l["intercept_label"], 500, 2000, especies[esp_n]["i"])
cons_v = st.sidebar.slider(l["cons_vaca"], 10, 25, especies[esp_n]["c"])
dias_rot = st.sidebar.slider(l["rotacion"], 1, 100, especies[esp_n]["r"])
radio = st.sidebar.slider("Radius (m)", 10, 500, 100)

btn_run = st.sidebar.button(l["btn_run"], type="primary", use_container_width=True)

# --- 7. PROCESAMIENTO ---
@st.cache_data(show_spinner=False)
def get_agronomic_data(lat, lon, start, end, rad):
    p = ee.Geometry.Point([lon, lat])
    roi = p.buffer(rad)
    lc = ee.Image("ESA/WorldCover/v200/2021").clip(roi)
    is_urban = ee.Number(lc.eq(50).reduceRegion(ee.Reducer.mean(), roi, 20).get('Map')).gt(0.35).getInfo()

    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi)
           .filterDate(start, end).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
           .map(lambda img: img.addBands(img.normalizedDifference(['B8', 'B4']).rename('NDVI'))))
    
    res = col.map(lambda img: ee.Feature(None, {
        'fecha': img.date().format('YYYY-MM-dd'), 
        'ndvi': img.reduceRegion(ee.Reducer.mean(), roi, 20).get('NDVI')
    })).getInfo()
    
    df = pd.DataFrame([f['properties'] for f in res['features']]).dropna()
    return df, col, p, is_urban

# --- 8. DASHBOARD ---
if btn_run:
    st.session_state.url_cache = {} 
    with st.spinner("🛰️ Synchronizing..."):
        st.session_state.analysis_results = get_agronomic_data(st.session_state.lat, st.session_state.lon, rango[0].strftime('%Y-%m-%d'), rango[1].strftime('%Y-%m-%d'), radio)

if st.session_state.analysis_results is not None:
    df_raw, col_global, p_ee, urban_flag = st.session_state.analysis_results
    
    if urban_flag: st.warning(l["city_warn"])
    
    if not df_raw.empty:
        df = df_raw.copy()
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.sort_values('fecha')
        mult = 0 if urban_flag else 1
        df['kg_dm_ha'] = (((df['ndvi'] * slope) - intercept) * mult).clip(lower=0)
        
        df['clean'] = df['kg_dm_ha']
        df.loc[df['kg_dm_ha'] < (df['kg_dm_ha'].rolling(3).mean() * 0.6), 'clean'] = None
        df['tendencia'] = df['clean'].interpolate().rolling(window=7, center=True, min_periods=1).mean()
        df['tasa'] = df['tendencia'].diff() / df['fecha'].diff().dt.days

        avg_p = df['tendencia'].mean()
        col_g1, col_g2 = st.columns([3, 1])
        with col_g1:
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(df['fecha'], df['kg_dm_ha'], 'o', alpha=0.1, color='gray')
            ax.plot(df['fecha'], df['tendencia'], '-', linewidth=4, color='forestgreen')
            ax.fill_between(df['fecha'], df['tendencia'], color='forestgreen', alpha=0.1)
            st.pyplot(fig)
        with col_g2:
            st.metric(l["metric_avg"], f"{int(avg_p)} kg MS/ha")
            st.metric(l["metric_bio_last"], f"{int(df['tendencia'].iloc[-1])} kg")

        st.divider()
        
        c_sel, c_tog = st.columns([3, 1])
        with c_sel: fecha_sel = st.select_slider(l["audit"], options=df['fecha'].dt.strftime('%Y-%m-%d').tolist())
        with c_tog: modo_ndvi = st.toggle(l["switch_label"], value=False)
            
        dato = df[df['fecha'].dt.strftime('%Y-%m-%d') == fecha_sel].iloc[0]

        c_img, c_met = st.columns([1.6, 1])
        with c_img:
            cache_key = f"{fecha_sel}_{modo_ndvi}"
            if cache_key in st.session_state.url_cache:
                url_t = st.session_state.url_cache[cache_key]
                st.image(url_t, width="stretch")
            else:
                img_ee = col_global.filterDate(fecha_sel, (pd.to_datetime(fecha_sel) + timedelta(days=1)).strftime('%Y-%m-%d')).first()
                if img_ee:
                    viz = img_ee.normalizedDifference(['B8', 'B4']).visualize(min=0.2, max=0.8, palette=['red', 'yellow', 'green']) if modo_ndvi else img_ee.select(['B4','B3','B2']).visualize(min=0, max=3000, gamma=1.4)
                    url_t = viz.blend(ee.Image().byte().paint(ee.FeatureCollection(p_ee.buffer(radio)), 1, 2).visualize(palette=['#FF0000'])).getThumbURL({'dimensions': 800, 'region': p_ee.buffer(radio * 8).bounds(), 'format': 'png'})
                    st.session_state.url_cache[cache_key] = url_t
                    st.image(url_t, width="stretch")

        with c_met:
            st.subheader(l["sem_title"])
            bio_c = dato['tendencia']
            tasa_c = dato['tasa'] if not pd.isna(dato['tasa']) else 0
            carga = (tasa_c + ((bio_c - 1500) / dias_rot)) / cons_v if cons_v > 0 else 0
            
            if carga > 3.5: st.success(f"SURPLUS ({carga:.1f} cows/ha)")
            elif carga > 1.5: st.warning(f"EQUILIBRIUM ({carga:.1f} cows/ha)")
            else: st.error(f"DEFICIT ({carga:.1f} cows/ha)")

            with st.expander(f"📌 {l['sem_formula']}"): 
                st.latex(r"Stocking = \frac{Growth + \frac{Biomass - 1500}{Rotation}}{Intake}")
            
            st.metric(l["metric_bio_sel"], f"{int(bio_c)} kg MS/ha")
            st.metric(l["metric_tasa"], f"{tasa_c:.1f} kg/day")

        st.sidebar.download_button(l["download"], df.to_csv(index=False).encode('utf-8'), "pasture_report.csv", "text/csv")
