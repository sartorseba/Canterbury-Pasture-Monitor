# 🇳🇿 NZ Pasture Monitor: Satellite Biomass Estimator

### 🛰️ Precision Agriculture Tool for Canterbury & Hawke's Bay
**Live Demo:** [Streamlit App Link] | **Status:** v1.0 Production Ready

---

## 📋 Overview
This project is a **professional-grade AgTech dashboard** designed to estimate pasture biomass (kg DM/ha) using real-time satellite imagery from **Sentinel-2**. 

Built for the New Zealand agricultural context, it allows Farm Managers and Agronomists to make data-driven grazing decisions by monitoring growth trends, analyzing historical performance, and calculating sustainable stocking rates.

## 🚀 Key Features
* **📡 Real-Time Satellite Sync:** Direct integration with **Google Earth Engine (GEE)** API for on-the-fly NDVI processing.
* **🧠 Smart Caching System:** Implements `st.session_state` and custom caching logic to prevent redundant API calls, ensuring instant response times.
* **🗺️ Fluid UX Architecture:** * **Persistence:** Map coordinates and zoom levels remain stable during interaction.
    * **Context Awareness:** Dynamic MiniMap and "Context Zoom" sliders to analyze paddock surroundings without losing focus.
    * **Auto-Execution:** Smart triggers update the analysis automatically when the pin is moved.
* **📊 Agronomic Intelligence:** * Built-in **NZ Perennial Ryegrass** and **Lucerne** calibration curves.
    * **Stocking Rate Calculator:** Real-time computation of surplus/deficit based on cow intake and rotation length.
    * **Urban Filtering:** ESA WorldCover integration to automatically mask non-productive areas (roads, buildings).

## 🛠️ Tech Stack
* **Core:** Python 3.11, Streamlit
* **Geospatial Engine:** Google Earth Engine (Python API)
* **Mapping:** Folium, Streamlit-Folium, Leaflet Plugins
* **Data Processing:** Pandas, NumPy, Matplotlib

## ⚙️ Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/nz-pasture-monitor.git](https://github.com/your-username/nz-pasture-monitor.git)
   cd nz-pasture-monitor
