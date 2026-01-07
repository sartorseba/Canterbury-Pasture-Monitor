import streamlit as st
import ee
import pandas as pd
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
import folium
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="NZ Pasture Monitor", layout="wide")

# Forzamos los sliders a color rojo
st.markdown("""
    <style>
    .stSlider > div [data-baseweb="slider"] > div { background: linear-gradient(to right, #ff4b4b 0%, #ff4b4b var(--slider-value), #d3d3d3 var(--slider-value), #d3d3d3 100%); }
    div[data-testid="stThumbValue"] { color: #ff4b4b; }
    div[role="slider"] { background-color: #ff4b4b !important; border-color: #ff4b4b !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DICCIONARIO BILINGÜE ---
tr = {
    "es": {
        "title": "🇳🇿 Monitor de Biomasa Satelital",
        "map_sub": "🗺️ Selección de Lote (Vista Híbrida Google)",
        "map_info": "Haga clic en el mapa para actualizar automáticamente el lote.",
        "side_loc": "📍 Ubicación Seleccionada",
        "side_agron": "🌱 Configuración de Pastura",
        "formula_title": "Fórmula de Biomasa:",
        "period": "Período de Análisis",
        "specie": "Especie Forrajera",
        "slope_label": "Pendiente (m)",
        "intercept_label": "Intercepto (b)",
        "cons_vaca": "Consumo (kg MS/vaca/día)",
        "rotacion": "Días de Rotación (Descanso)",
        "radio_label": "Radio de Análisis (m)",
        "zoom": "Zoom de Contexto Visual",
        "graph_title": "📈 Dinámica de Biomasa",
        "audit": "📅 Auditoría de Captura",
        "vigor": "Modo Salud Vegetal (NDVI)",
        "sem_title": "🚦 Carga Animal Sustentable",
        "sem_formula": "Fórmula de Carga Soportable:",
        "sem_green": "SUPERÁVIT: El forraje disponible supera la demanda.",
        "sem_yellow": "EQUILIBRIO: Carga ajustada al stock.",
        "sem_red": "DÉFICIT: Forraje insuficiente.",
        "metric_bio_last": "Última Biomasa Detectada",
        "metric_bio_sel": "Biomasa en Fecha Seleccionada",
        "metric_tasa": "Tasa de Crecimiento",
        "metric_avg": "Promedio del Período",
        "quality_low": "⚠️ CALIDAD BAJA: Se utiliza valor de tendencia por nubes.",
        "legend_btn": "❓ Explicación de las Variables",
        "download": "📥 Descargar Reporte CSV"
    },
    "en": {
        "title": "🇳🇿 Satellite Biomass Monitor",
        "map_sub": "🗺️ Paddock Selection (Google Hybrid View)",
        "map_info": "Click on the map to automatically update the paddock.",
        "side_loc": "📍 Selected Location",
        "side_agron": "🌱 Pasture Configuration",
        "formula_title": "Biomass Formula:",
        "period": "Analysis Period",
        "specie": "Forage Species",
        "slope_label": "Slope (m)",
        "intercept_label": "Intercept (b)",
        "cons_vaca": "Intake (kg DM/cow/day)",
        "rotacion": "Rotation Days (Rest)",
        "radio_label": "Analysis Radius (m)",
        "zoom": "Visual Context Zoom",
        "graph_title": "📈 Biomass Dynamics",
        "audit": "📅 Capture Audit",
        "vigor": "Vegetation Health Mode (NDVI)",
        "sem_title": "🚦 Sustainable Stocking Rate",
        "sem_formula": "Carrying Capacity Formula:",
        "sem_green": "SURPLUS: Available forage exceeds demand.",
        "sem_yellow": "EQUILIBRIUM: Stocking rate matches stock.",
        "sem_red": "DEFICIT: Insufficient forage.",
        "metric_bio_last": "Last Detected Biomass",
        "metric_bio_sel": "Biomass on Selected Date",
        "metric_tasa": "Growth Rate",
        "metric_avg": "Period Average",
        "quality_low": "⚠️ LOW QUALITY: Trend value used due to clouds.",
        "legend_btn": "❓ Variable Explanation",
        "download": "📥 Download CSV Report"
    }
}

idioma_opt = st.sidebar.selectbox("🌐 Idioma / Language", ["Español", "English"])
l = tr["es"] if idioma_opt == "Español" else tr["en"]

st.title(l["title"])

try:
    ee.Initialize(project='nz-biomass')
except:
    st.error("Error de conexión con Google Earth Engine.")

# --- 3. MAPA HÍBRIDO REACTIVO ---
st.subheader(l["map_sub"])
m = folium.Map(location=[-43.5320, 172.6306], zoom_start=12)
# Usamos Google Hybrid para etiquetas correctas
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google Hybrid', name='Google Satellite', overlay=False
).add_to(m)
m.add_child(folium.LatLngPopup())
map_data = st_folium(m, height=300, width=1200)

lat_act, lon_act = (map_data['last_clicked']['lat'], map_data['last_clicked']['lng']) if map_data and map_data['last_clicked'] else (-43.5320, 172.6306)

# --- 4. SIDEBAR ---
st.sidebar.header(l["side_loc"])
lat = st.sidebar.number_input("Lat", value=lat_act, format="%.4f")
lon = st.sidebar.number_input("Lon", value=lon_act, format="%.4f")
rango = st.sidebar.date_input(l["period"], value=(datetime(2025,1,1), datetime(2025,12,31)))

st.sidebar.markdown("---")
st.sidebar.header(l["side_agron"])
st.sidebar.latex(r"kg\;MS/ha = (NDVI \cdot m) - b")

especies = {
    "Raigrás Perenne (NZ)": {"s": 5800, "i": 1200, "c": 18, "r": 21},
    "Alfalfa (Lucerne)": {"s": 6157, "i": 1346, "c": 16, "r": 35}
}
esp_n = st.sidebar.selectbox(l["specie"], list(especies.keys()))
slope = st.sidebar.slider(l["slope_label"], 3000, 7500, especies[esp_n]["s"])
intercept = st.sidebar.slider(l["intercept_label"], 500, 2000, especies[esp_n]["i"])
cons_v = st.sidebar.slider(l["cons_vaca"], 10, 25, especies[esp_n]["c"])
dias_rot = st.sidebar.slider(l["rotacion"], 1, 100, especies[esp_n]["r"])
radio = st.sidebar.slider(l["radio_label"], 10, 500, 100)
zoom_v = st.sidebar.slider(l["zoom"], 2, 15, 8)

# --- 5. FUNCIÓN CACHEADA PARA GOOGLE EARTH ENGINE ---
@st.cache_data(show_spinner=False)
def get_ndvi_data(lat, lon, start, end, radio):
    punto = ee.Geometry.Point([lon, lat])
    roi = punto.buffer(radio)
    coleccion = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                 .filterBounds(roi)
                 .filterDate(start, end)
                 .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                 .map(lambda img: img.addBands(img.normalizedDifference(['B8', 'B4']).rename('NDVI'))))
    
    res = coleccion.map(lambda img: ee.Feature(None, {
        'fecha': img.date().format('YYYY-MM-dd'), 
        'ndvi': img.reduceRegion(ee.Reducer.mean(), roi, 10).get('NDVI')
    })).getInfo()
    
    return pd.DataFrame([f['properties'] for f in res['features']]).dropna(), coleccion, punto

# EJECUCIÓN AUTOMÁTICA
with st.spinner("Actualizando datos desde Sentinel-2..."):
    ndvi_df, coleccion_global, punto_ee = get_ndvi_data(
        lat, lon, rango[0].strftime('%Y-%m-%d'), rango[1].strftime('%Y-%m-%d'), radio
    )

# --- 6. DASHBOARD REACTIVO ---
if not ndvi_df.empty:
    df = ndvi_df.copy()
    df['fecha'] = pd.to_datetime(df['fecha'])
    df = df.sort_values('fecha')
    
    # Cálculos dinámicos inmediatos
    df['kg_dm_ha'] = (df['ndvi'] * slope) - intercept
    df['kg_dm_ha'] = df['kg_dm_ha'].clip(lower=0)
    df['tendencia'] = df['kg_dm_ha'].rolling(window=3, center=True).mean()
    df['tasa'] = df['kg_dm_ha'].diff() / df['fecha'].diff().dt.days
    df['nube'] = df['kg_dm_ha'] < (df['tendencia'].shift(1) * 0.6)

    avg_p = df['kg_dm_ha'].mean()
    ultima_biomasa = df['kg_dm_ha'].iloc[-1]
    
    st.subheader(f"{l['graph_title']}: {esp_n}")
    col_g1, col_g2 = st.columns([3, 1])
    with col_g1:
        fig, ax = plt.subplots(figsize=(12, 3.5))
        ax.plot(df['fecha'], df['kg_dm_ha'], 'o--', alpha=0.2, color='gray')
        ax.plot(df['fecha'], df['tendencia'], '-', linewidth=3, color='forestgreen')
        ax.scatter(df[df['nube']]['fecha'], df[df['nube']]['kg_dm_ha'], color='red', s=80)
        ax.axhline(avg_p, color='red', linestyle=':', alpha=0.3) # Línea sutil promedio
        ax.set_ylim(-100, max(5000, df['kg_dm_ha'].max() * 1.1))
        st.pyplot(fig)
    with col_g2:
        st.metric(l["metric_avg"], f"{int(avg_p)} kg MS/ha")
        st.metric(l["metric_bio_last"], f"{int(ultima_biomasa)} kg MS/ha", f"{((ultima_biomasa-avg_p)/avg_p)*100:.1f}%")

    st.markdown("---")
    fecha_sel = st.select_slider(l["audit"], options=df['fecha'].dt.strftime('%Y-%m-%d').tolist())
    ver_v = st.toggle(l["vigor"])
    dato = df[df['fecha'].dt.strftime('%Y-%m-%d') == fecha_sel].iloc[0]

    c_img, c_met = st.columns([1.6, 1])
    with c_img:
        # Visor reactivo
        img_ee = coleccion_global.filterDate(fecha_sel, (pd.to_datetime(fecha_sel) + timedelta(days=1)).strftime('%Y-%m-%d')).first()
        viz = img_ee.normalizedDifference(['B8', 'B4']).visualize(min=0.2, max=0.8, palette=['red', 'yellow', 'green']) if ver_v else img_ee.select(['B4','B3','B2']).visualize(min=0, max=3000, gamma=1.4)
        roi_act = punto_ee.buffer(radio)
        url_t = viz.blend(ee.Image().byte().paint(ee.FeatureCollection(roi_act), 1, 2).visualize(palette=['#FF0000'])).getThumbURL({'dimensions': 800, 'region': punto_ee.buffer(radio * zoom_v).bounds(), 'format': 'png'})
        st.image(url_t, width="stretch")

    with c_met:
        st.subheader(l["sem_title"])
        es_nube = dato['nube']
        bio_calc = dato['tendencia'] if es_nube else dato['kg_dm_ha']
        tasa_calc = dato['tasa'] if not es_nube else 0
        remanente_obj = 1500
        carga = (tasa_calc + ((bio_calc - remanente_obj) / dias_rot)) / cons_v if cons_v > 0 else 0
        
        if es_nube: st.warning(l["quality_low"])
        if carga > 3.5: st.success(f"{l['sem_green']} ({carga:.1f} vacas/ha)")
        elif carga > 1.5: st.warning(f"{l['sem_yellow']} ({carga:.1f} vacas/ha)")
        else: st.error(f"{l['sem_red']} ({carga:.1f} vacas/ha)")

        with st.expander(f"📌 {l['sem_formula']}"):
            st.latex(r"Carga = \frac{Tasa + \frac{Biomasa - 1500}{Rotación}}{Consumo}")

        st.divider()
        st.metric(l["metric_bio_sel"], f"{int(bio_calc)} kg MS/ha", delta="Trend" if es_nube else None)
        st.metric(l["metric_tasa"], f"{tasa_calc:.1f} kg/día")

    st.sidebar.download_button(l["download"], df.to_csv(index=False).encode('utf-8'), "agtech_report.csv", "text/csv")