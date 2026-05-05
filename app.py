import streamlit as st
import pandas as pd
import pydeck as pdk
import os
import base64

st.set_page_config(layout="wide", page_title="Mapa de Tiendas")

# --- 1. CARGA Y LIMPIEZA PROFUNDA ---
@st.cache_data
def cargar_y_limpiar_datos():
    df = pd.read_excel("Clientes Completos.xlsx")
    df['Latitud'] = pd.to_numeric(df['Latitud'], errors='coerce')
    df['Longitud'] = pd.to_numeric(df['Longitud'], errors='coerce')
    df = df.dropna(subset=['Latitud', 'Longitud'])
    # Filtro de seguridad para que el mapa no salga negro
    df = df[(df['Latitud'] >= -90) & (df['Latitud'] <= 90)]
    return df
    # FILTRO INTELIGENTE: 
    # Para evitar que el mapa salga negro, 
    # validamos rangos reales: Lat (-90 a 90) y Lon (-180 a 180).
    mask_validos = (
        (df['Latitud'] >= -90) & (df['Latitud'] <= 90) &
        (df['Longitud'] >= -180) & (df['Longitud'] <= 180)
    )
    
    df_final = df[mask_validos].copy()
    df_errores = df[~mask_validos].copy()
    
    # Limpieza de nombres para filtros
    df_final['Estado'] = df_final['Estado'].fillna('Desconocido').astype(str)
    df_final['CLIENTE'] = df_final['CLIENTE'].fillna('Sin Cliente').astype(str)
    
    return df_final, df_errores

def obtener_ruta_logo(nombre_cliente):
    ruta = f"Logos/{nombre_cliente}.png" 
    if os.path.exists(ruta):
        with open(ruta, "rb") as f:
            return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
    return "https://cdn-icons-png.flaticon.com/512/684/684908.png"

# --- 2. EJECUCIÓN ---
try:
    # Obtenemos los datos (Soluciona el error de "df no definido")
    df, tiendas_fuera_rango = cargar_y_limpiar_datos()
    
    st.sidebar.header("📍 Filtros")
    
    # Aviso de tiendas omitidas
    if not tiendas_fuera_rango.empty:
        st.sidebar.warning(f"⚠️ {len(tiendas_fuera_rango)} tiendas tienen coordenadas imposibles y fueron ocultadas.")
        if st.sidebar.checkbox("Ver tiendas con error"):
            st.sidebar.write(tiendas_fuera_rango[['NOMBRE TIENDA', 'Latitud', 'Longitud']])

    # Filtros dinámicos
    estados = sorted(df['Estado'].unique())
    sel_estados = st.sidebar.multiselect("Estados", estados)
    df_temp = df[df['Estado'].isin(sel_estados)] if sel_estados else df.copy()

    clientes = sorted(df_temp['CLIENTE'].unique())
    sel_clientes = st.sidebar.multiselect("Clientes", clientes)
    df_final = df_temp[df_temp['CLIENTE'].isin(sel_clientes)] if sel_clientes else df_temp.copy()

    # Título y Resumen
    st.title(f"Tiendas visibles: {len(df_final)}")
    
    # Resumen lateral
    resumen = df_final['CLIENTE'].value_counts().reset_index()
    resumen.columns = ['Cliente', 'Total']
    st.sidebar.dataframe(resumen, hide_index=True)

if len(df_filtrado) <= limite_logos:
    # Solo aquí convertimos a base64 para ahorrar RAM
    df_filtrado['icon_data'] = df_filtrado['CLIENTE'].apply(lambda x: {
        "url": obtener_ruta_logo(x),
        "width": 128, "height": 128, "anchorY": 128
    })
    tipo_capa = "IconLayer"
else:
    # Si son muchas, usamos círculos de colores para que la app no explote
    st.info(f"💡 Mostrando puntos simples para mejorar velocidad ({len(df_filtrado)} tiendas). Filtra más para ver logos.")
    tipo_capa = "ScatterplotLayer"

   # --- 3. LÓGICA DE CAPAS DINÁMICAS ---
# Definimos un límite de seguridad para no saturar la RAM del servidor
LIMITE_MEMORIA_LOGOS = 2000
 
if len(df_final) == 0:
    st.warning("No hay datos que coincidan con los filtros seleccionados.")
elif len(df_final) <= LIMITE_MEMORIA_LOGOS:
    # --- MODO ICONOS (LOGOS) ---
    # Solo procesamos imágenes cuando el volumen de datos es seguro
    df_final['icon_data'] = df_final['CLIENTE'].apply(lambda x: {
        "url": obtener_ruta_logo(x),
        "width": 128,
        "height": 128,
        "anchorY": 128
    })
    
    capa_mapa = pdk.Layer(
        "IconLayer",
        data=df_final,
        get_icon="icon_data",
        get_size=4,
        size_scale=12,
        get_position=["Longitud", "Latitud"],
        pickable=True,
    )
    st.success(f"Mostrando {len(df_final)} tiendas con sus respectivos logos.")
else:
    # --- MODO PUNTOS (SCATTERPLOT) ---
    # Si hay demasiados datos, usamos círculos para evitar que la app se caiga
    capa_mapa = pdk.Layer(
        "ScatterplotLayer",
        data=df_final,
        get_position=["Longitud", "Latitud"],
        get_color=[200, 30, 0, 160], # Color rojizo transparente
        get_radius=300,
        pickable=True,
    )
    st.info(f"💡 Mostrando {len(df_final)} tiendas como puntos. Filtra por Estado para ver los logos individuales.")
 
# --- 4. RENDERIZADO DEL MAPA ---
# Calculamos el centro del mapa basado en los datos visibles
if not df_final.empty:
    lat_centro = df_final['Latitud'].mean()
    lon_centro = df_final['Longitud'].mean()
    zoom_inicial = 5
else:
    lat_centro, lon_centro, zoom_inicial = 4.57, -74.29, 4 # Coordenadas por defecto (ej. Colombia)
 
view_state = pdk.ViewState(
    latitude=lat_centro,
    longitude=lon_centro,
    zoom=zoom_inicial,
    pitch=0
)
 
# Renderizado final
st.pydeck_chart(pdk.Deck(
    layers=[capa_mapa],
    initial_view_state=view_state,
    # Estilo de mapa más liviano para el navegador
    map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
    tooltip={
        "text": "Tienda: {NOMBRE TIENDA}\nCliente: {CLIENTE}\nEstado: {Estado}"
    }
))
except Exception as e:
    st.error(f"Error crítico: {e}")
