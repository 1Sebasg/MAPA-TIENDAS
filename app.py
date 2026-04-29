import streamlit as st
import pandas as pd
import pydeck as pdk
import os
import base64

st.set_page_config(layout="wide", page_title="Mapa de Tiendas")

# --- 1. CARGA Y LIMPIEZA PROFUNDA ---
@st.cache_data
def cargar_y_limpiar_datos():
    # Cargamos tu archivo original
    df = pd.read_excel("Clientes Completos.xlsx")
    
    # Aseguramos que Latitud y Longitud sean números
    df['Latitud'] = pd.to_numeric(df['Latitud'], errors='coerce')
    df['Longitud'] = pd.to_numeric(df['Longitud'], errors='coerce')
    
    # Eliminamos solo las que no tienen ningún dato numérico
    df = df.dropna(subset=['Latitud', 'Longitud'])
    
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
    ruta = f"logos/{nombre_cliente}.jpg" 
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

    # --- 3. MAPA ---
    df_final['icon_data'] = df_final['CLIENTE'].apply(lambda x: {
        "url": obtener_ruta_logo(x), "width": 128, "height": 128, "anchorY": 128
    })

    view_state = pdk.ViewState(
        latitude=df_final['Latitud'].mean() if not df_final.empty else 39.82,
        longitude=df_final['Longitud'].mean() if not df_final.empty else -98.57,
        zoom=4
    )

    icon_layer = pdk.Layer(
        "IconLayer",
        data=df_final,
        get_icon="icon_data",
        get_size=3,
        size_scale=7,
        get_position=["Longitud", "Latitud"],
        pickable=True,
    )

    # Usamos el estilo Voyager que es el más resistente al error de "indexOf"
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("IconLayer", data=df_final, get_icon="icon_data", get_size=4, size_scale=10, get_position=["Longitud", "Latitud"], pickable=True)],
        initial_view_state=view_state,
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        tooltip={"text": "Tienda: {NOMBRE TIENDA}\nCliente: {CLIENTE}"}
    ))

except Exception as e:
    st.error(f"Error crítico: {e}")
