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

# --- 2. MOTOR DE CONEXIÓN GEE INTELIGENTE ---
def conectar_gee():
    try:
        if "GEE_JSON" in st.secrets:
            info = json.loads(st.secrets["GEE_JSON"])
            credentials = ee.ServiceAccountCredentials(info['client_email'], key_data=st.secrets["GEE_JSON"])
            ee.Initialize(credentials, project=info['project_id'])
            return
    except Exception:
        pass
    try:
        ee.Initialize(project='nz-biomass') # Tu proyecto local
    except Exception as e:
        st.error(f"GEE Connection Error: {e}. Try 'earthengine authenticate' in terminal.")

conectar_gee()

# --- 3. DICCIONARIO BILINGÜE (Inglés por defecto) ---
tr = {
    "en": {
        "title": "🇳🇿 Satellite Biomass Monitor - Canterbury",
        "map_sub": "🗺️ Paddock Selection (Google Hybrid View)",
        "side_agron": "🌱 Pasture Configuration",
        "period": "Analysis Period",
        "specie": "Forage Species",
        "slope_label": "Slope (m)",
        "intercept_label": "Intercept (b)",
        "cons_vaca": "Intake (kg DM/cow/day)",
        "rotacion": "Rotation Days (Rest)",
        "audit": "📅 Capture Audit",
        "switch_label": "NDVI Mode (Off = Visible RGB)",
        "sem_title": "🚦 Sustainable Stocking Rate",
        "sem_formula": "Carrying Capacity Formula:",
        "metric_bio_last": "Last Detected Biomass",
        "metric_bio_sel": "Biomass on Selected Date",
        "metric_tasa": "Growth Rate",
        "metric_avg": "Period Average",
        "quality_low": "⚠️ LOW QUALITY: Using trend value due to clouds.",
        "download": "📥 Download CSV Report"
    },
    "es": {
        "title": "🇳🇿 Monitor de Biomasa Satelital - Canterbury",
        "map_sub": "🗺️ Selección de Lote (Vista Híbrida)",
        "side_agron": "🌱 Configuración de Pastura",
        "period": "Período de Análisis",
        "specie": "Especie Forrajera",
        "slope_label": "Pendiente (m)",
        "intercept_label": "Intercepto (b)",
        "cons_vaca": "Consumo (kg MS/vaca/día)",
        "rotacion": "Días de Rotación (Descanso)",
        "audit": "📅 Auditoría de Captura",
        "switch_label": "Modo NDVI (Apagado = Visible RGB)",
        "sem_title": "🚦 Carga Animal Sustentable",
        "sem_formula": "Fórmula de Carga Soportable:",
        "metric_bio_last": "Última Biomasa Detectada",
        "metric_bio_sel": "Biomasa en Fecha Seleccionada",
        "metric_tasa": "Tasa de Crecimiento",
        "metric_avg": "Promedio del Período",
        "quality_low": "⚠️ CALIDAD BAJA: Usando tendencia por nubes.",
        "download": "📥 Descargar Reporte CSV"
    }
}

# Selector de idioma: Inglés configurado por defecto (index=0)
idioma_opt = st.sidebar.selectbox("🌐 Language / Idioma", ["English", "Español"], index=0)
l = tr["en"] if idioma_opt == "English" else tr["es"]
st.title(l["title"])

# --- 4. MAPA HÍBRIDO ---
st.subheader(l["map_sub"])
m = folium.Map(location=[-43.5320, 172.6306], zoom_start=12)
folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                 attr='Google', name='Google Hybrid', overlay=False).add_to(m)
m.add_child(folium.LatLngPopup())
map_data = st_folium(m, height=300, width=1200)

lat_act, lon_act = (map_data['last_clicked']['lat'], map_data['last_clicked']['lng']) if map_data and map_data['last_clicked'] else (-43.5320, 172.6306)

# --- 5. SIDEBAR ---
st.sidebar.header(l["side_agron"])
lat = st.sidebar.number_input("Lat", value=lat_act, format="%.4f")
lon = st.sidebar.number_input("Lon", value=lon_act, format="%.4f")
rango = st.sidebar.date_input(l["period"], value=(datetime(2025,1,1), datetime(2025,12,31)))

especies = {
    "Raigrás Perenne (NZ)": {"s": 5800, "i": 1200, "c": 18, "r": 21},
    "Alfalfa (Lucerne)": {"s": 6157, "i": 1346, "c": 16, "r": 35}
}
esp_n = st.sidebar.selectbox(l["specie"], list(especies.keys()))
slope = st.sidebar.slider(l["slope_label"], 3000, 7500, especies[esp_n]["s"])
intercept = st.sidebar.slider(l["intercept_label"], 500, 2000, especies[esp_n]["i"])
cons_v = st.sidebar.slider(l["cons_vaca"], 10, 25, especies[esp_n]["c"])
dias_rot = st.sidebar.slider(l["rotacion"], 1, 100, especies[esp_n]["r"])
radio = st.sidebar.slider("Radio (m)", 10, 500, 100)

# --- 6. DATOS SATELITALES ---
@st.cache_data(show_spinner=False)
def get_pasture_data(lat, lon, start, end, rad):
    p = ee.Geometry.Point([lon, lat])
    roi = p.buffer(rad)
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi)
           .filterDate(start, end).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
           .map(lambda img: img.addBands(img.normalizedDifference(['B8', 'B4']).rename('NDVI'))))
    res = col.map(lambda img: ee.Feature(None, {'fecha': img.date().format('YYYY-MM-dd'), 
                                               'ndvi': img.reduceRegion(ee.Reducer.mean(), roi, 10).get('NDVI')})).getInfo()
    return pd.DataFrame([f['properties'] for f in res['features']]).dropna(), col, p

with st.spinner("Connecting to Sentinel-2..."):
    df_raw, col_global, p_ee = get_pasture_data(lat, lon, rango[0].strftime('%Y-%m-%d'), rango[1].strftime('%Y-%m-%d'), radio)

# --- 7. DASHBOARD ---
if not df_raw.empty:
    df = df_raw.copy()
    df['fecha'] = pd.to_datetime(df['fecha'])
    df = df.sort_values('fecha')
    df['kg_dm_ha'] = (df['ndvi'] * slope) - intercept
    df['tendencia'] = df['kg_dm_ha'].rolling(window=3, center=True).mean()
    df['tasa'] = df['kg_dm_ha'].diff() / df['fecha'].diff().dt.days
    df['nube'] = df['kg_dm_ha'] < (df['tendencia'].shift(1) * 0.6)

    avg_p = df['kg_dm_ha'].mean()
    
    col_g1, col_g2 = st.columns([3, 1])
    with col_g1:
        fig, ax = plt.subplots(figsize=(12, 3.5))
        ax.plot(df['fecha'], df['kg_dm_ha'], 'o--', alpha=0.2, color='gray')
        ax.plot(df['fecha'], df['tendencia'], '-', linewidth=3, color='forestgreen')
        ax.scatter(df[df['nube']]['fecha'], df[df['nube']]['kg_dm_ha'], color='red', s=80)
        ax.axhline(avg_p, color='red', linestyle=':', alpha=0.3)
        st.pyplot(fig)
    with col_g2:
        st.metric(l["metric_avg"], f"{int(avg_p)} kg MS/ha")
        ultima = df['kg_dm_ha'].iloc[-1]
        st.metric(l["metric_bio_last"], f"{int(ultima)} kg", f"{((ultima-avg_p)/avg_p)*100:.1f}%")

    st.divider()
    fecha_sel = st.select_slider(l["audit"], options=df['fecha'].dt.strftime('%Y-%m-%d').tolist())
    
    # INTERRUPTOR CORREGIDO: Por defecto en TRUE (NDVI)
    modo_ndvi = st.toggle(l["switch_label"], value=True)
    
    dato = df[df['fecha'].dt.strftime('%Y-%m-%d') == fecha_sel].iloc[0]

    c_img, c_met = st.columns([1.6, 1])
    with c_img:
        img_ee = col_global.filterDate(fecha_sel, (pd.to_datetime(fecha_sel) + timedelta(days=1)).strftime('%Y-%m-%d')).first()
        
        # Lógica Invertida: TRUE = NDVI, FALSE = RGB
        if modo_ndvi:
            viz = img_ee.normalizedDifference(['B8', 'B4']).visualize(min=0.2, max=0.8, palette=['red', 'yellow', 'green'])
        else:
            viz = img_ee.select(['B4','B3','B2']).visualize(min=0, max=3000, gamma=1.4)
            
        url_t = viz.blend(ee.Image().byte().paint(ee.FeatureCollection(p_ee.buffer(radio)), 1, 2).visualize(palette=['#FF0000'])).getThumbURL({'dimensions': 800, 'region': p_ee.buffer(radio * 8).bounds(), 'format': 'png'})
        st.image(url_t, width="stretch")

    with c_met:
        st.subheader(l["sem_title"])
        bio_c = dato['tendencia'] if dato['nube'] else dato['kg_dm_ha']
        tasa_c = dato['tasa'] if not dato['nube'] else 0
        carga = (tasa_c + ((bio_c - 1500) / dias_rot)) / cons_v if cons_v > 0 else 0
        
        if dato['nube']: st.warning(l["quality_low"])
        if carga > 3.5: st.success(f"{'SURPLUS' if idioma_opt=='English' else 'SUPERÁVIT'} ({carga:.1f} {'cows' if idioma_opt=='English' else 'vacas'}/ha)")
        elif carga > 1.5: st.warning(f"{'EQUILIBRIUM' if idioma_opt=='English' else 'EQUILIBRIO'} ({carga:.1f} {'cows' if idioma_opt=='English' else 'vacas'}/ha)")
        else: st.error(f"{'DEFICIT' if idioma_opt=='English' else 'DÉFICIT'} ({carga:.1f} {'cows' if idioma_opt=='English' else 'vacas'}/ha)")

        with st.expander(f"📌 {l['sem_formula']}"):
            st.latex(r"Stocking = \frac{Growth + \frac{Biomass - 1500}{Rotation}}{Intake}")

        st.metric(l["metric_bio_sel"], f"{int(bio_c)} kg MS/ha")
        st.metric(l["metric_tasa"], f"{tasa_c:.1f} kg/day" if idioma_opt=='English' else f"{tasa_c:.1f} kg/día")

    st.sidebar.download_button(l["download"], df.to_csv(index=False).encode('utf-8'), "pasture_report.csv", "text/csv")