import streamlit as st
import pandas as pd
import pydeck as pdk
import os
import base64

st.set_page_config(layout="wide", page_title="Mapa de Tiendas")

# --- 1. CARGA Y LIMPIEZA PROFUNDA ---
@st.cache_data
def cargar_y_limpiar_datos():
    # Asegúrate de que el nombre del archivo coincida con el de GitHub
    df = pd.read_excel("CLIENTES COMPLETOS.xlsm") 
    
    # Limpieza inicial
    df['Latitud'] = pd.to_numeric(df['Latitud'], errors='coerce')
    df['Longitud'] = pd.to_numeric(df['Longitud'], errors='coerce')
    
    # Validación de rangos reales (Lat -90 a 90 y Lon -180 a 180)
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
    # Intentamos con varias extensiones para evitar errores de mayúsculas/minúsculas
    for ext in [".png", ".PNG", ".jpg", ".JPG", ".jpeg"]:
        ruta = f"logos/{nombre_cliente}{ext}" 
        if os.path.exists(ruta):
            with open(ruta, "rb") as f:
                img_str = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{img_str}"
    
    # Icono por defecto si no encuentra el logo
    return "https://cdn-icons-png.flaticon.com/512/684/684908.png"

# --- 2. EJECUCIÓN ---
try:
    # Carga de datos
    df, tiendas_fuera_rango = cargar_y_limpiar_datos()
    
    # Barra lateral - Filtros
    st.sidebar.header("📍 Filtros")
    
    if not tiendas_fuera_rango.empty:
        st.sidebar.warning(f"⚠️ {len(tiendas_fuera_rango)} tiendas con coordenadas inválidas ocultadas.")

    # Filtros dinámicos
    estados = sorted(df['Estado'].unique())
    sel_estados = st.sidebar.multiselect("Estados", estados)
    df_temp = df[df['Estado'].isin(sel_estados)] if sel_estados else df.copy()

    clientes = sorted(df_temp['CLIENTE'].unique())
    sel_clientes = st.sidebar.multiselect("Clientes", clientes)
    df_final = df_temp[df_temp['CLIENTE'].isin(sel_clientes)] if sel_clientes else df_temp.copy()

    # Resumen lateral
    resumen = df_final['CLIENTE'].value_counts().reset_index()
    resumen.columns = ['Cliente', 'Total']
    st.sidebar.write("### Resumen por Cliente")
    st.sidebar.dataframe(resumen, hide_index=True)

    # --- 3. LÓGICA DE CAPAS DINÁMICAS ---
    st.title(f"Tiendas visibles: {len(df_final)}")
    
    LIMITE_MEMORIA_LOGOS = 2000 # Límite para no saturar RAM en Streamlit Cloud

    if len(df_final) == 0:
        st.warning("No hay datos que coincidan con los filtros seleccionados.")
        capa_mapa = None
    elif len(df_final) <= LIMITE_MEMORIA_LOGOS:
        # MODO ICONOS: Solo convertimos a base64 lo necesario
        df_final['icon_data'] = df_final['CLIENTE'].apply(lambda x: {
            "url": obtener_ruta_logo(x),
            "width": 128, "height": 128, "anchorY": 128
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
        st.success(f"Mostrando logos para {len(df_final)} tiendas.")
    else:
        # MODO PUNTOS: Para grandes volúmenes de datos
        capa_mapa = pdk.Layer(
            "ScatterplotLayer",
            data=df_final,
            get_position=["Longitud", "Latitud"],
            get_color=[200, 30, 0, 160],
            get_radius=300,
            pickable=True,
        )
        st.info(f"💡 Mostrando puntos simples por rendimiento. Filtra más para ver logos.")

    # --- 4. RENDERIZADO DEL MAPA ---
    if capa_mapa:
        lat_centro = df_final['Latitud'].mean() if not df_final.empty else 4.57
        lon_centro = df_final['Longitud'].mean() if not df_final.empty else -74.29
        
        view_state = pdk.ViewState(
            latitude=lat_centro,
            longitude=lon_centro,
            zoom=5,
            pitch=0
        )

        st.pydeck_chart(pdk.Deck(
            layers=[capa_mapa],
            initial_view_state=view_state,
            map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
            tooltip={
                "text": "Tienda: {NOMBRE TIENDA}\nCliente: {CLIENTE}\nEstado: {Estado}"
            }
        ))

except Exception as e:
    st.error(f"Error crítico en la aplicación: {e}")
