import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests # <--- Nueva herramienta para hablar con ImgBB
import os
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inventario ZAP", layout="wide", page_icon="🏗️")

# --- SEGURIDAD ---
def check_password():
    if st.session_state.get('password_correct', False):
        return True
    
    st.header("🔒 Acceso Distribuidora")
    password_input = st.text_input("Contraseña:", type="password")
    
    if st.button("Ingresar"):
        try:
            if password_input == st.secrets["general"]["password"]:
                st.session_state['password_correct'] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        except:
            st.error("Falta configurar secrets.toml")
    return False

# --- CONEXIÓN GOOGLE SHEETS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("inventario_db").sheet1
    except Exception as e:
        st.error(f"Error Sheets: {e}")
        return None

# --- FUNCIÓN IMGBB (NUEVO MOTOR DE IMÁGENES) ---
def subir_a_imgbb(archivo_bytes, nombre):
    """Sube imagen a ImgBB y retorna la URL pública."""
    api_key = st.secrets["imgbb"]["key"]
    url = "https://api.imgbb.com/1/upload"
    
    payload = {
        "key": api_key,
        "name": nombre
    }
    files = {
        "image": archivo_bytes
    }
    
    try:
        response = requests.post(url, data=payload, files=files)
        if response.status_code == 200:
            data = response.json()
            return data['data']['url'] # Retorna el link directo
        else:
            st.error(f"Error ImgBB: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_datos():
    hoja = conectar_google_sheets()
    if hoja:
        datos = hoja.get_all_values()
        if not datos: return pd.DataFrame(), hoja
        headers = datos.pop(0)
        return pd.DataFrame(datos, columns=headers), hoja
    return pd.DataFrame(), None

# --- FRONTEND ---
def main():
    if not check_password(): st.stop()

    st.title("🏭 Gestión ZAP: Celima & Trebol")
    
    menu = ["Ver Inventario", "Registrar Nuevo", "Actualizar Stock"]
    choice = st.sidebar.selectbox("Menú", menu)
    df, hoja = obtener_datos()

    # --- 1. VER INVENTARIO ---
    if choice == "Ver Inventario":
        col1, col2 = st.columns([3,1])
        with col1: st.subheader("📦 Stock Visual")
        with col2: 
            if st.button("🔄 Recargar"): st.rerun()

        busqueda = st.text_input("🔍 Buscar SKU:")
        
        if not df.empty:
            if busqueda:
                mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
                df_filtered = df[mask]
            else:
                df_filtered = df
            
            st.info(f"Mostrando {len(df_filtered)} productos")
            
            # Galería de Tarjetas
            cols = st.columns(3)
            for idx, row in df_filtered.iterrows():
                with cols[idx % 3]:
                    st.markdown(f"**{row['nombre']}**")
                    st.caption(f"ZAP: {row['id']} | {row['marca']}")
                    
                    # MOSTRAR IMAGEN DESDE URL
                    img_url = row['imagen']
                    if img_url and img_url.startswith("http"):
                        st.image(img_url, use_container_width=True)
                    else:
                        st.warning("Sin foto / Foto local antigua")
                        
                    st.metric("Stock", row['stock'], f"S/. {row['precio']}")
                    st.caption(f"Calidad: {row['calidad']} - {row['formato']}")
                    st.divider()

        else:
            st.warning("Inventario vacío.")

    # --- 2. REGISTRAR ---
    elif choice == "Registrar Nuevo":
        st.subheader("📝 Nuevo Ingreso")
        
        with st.form("form_registro", clear_on_submit=True):
            c1, c2 = st.columns(2)
            id_zap = c1.text_input("Código ZAP")
            marca = c2.selectbox("Marca", ["Celima", "Trebol", "Generico", "Otro"])
            
            c3, c4 = st.columns(2)
            nombre = c3.text_input("Descripción")
            categoria = c4.selectbox("Categoría", ["Mayólica", "Sanitario", "Grifería", "Pegamento", "Fragua"])
            
            c5, c6 = st.columns(2)
            formato = c5.text_input("Formato (Ej. 60x60)")
            calidad = c6.selectbox("Calidad", ["Comercial", "Extra", "Única", "Estándar"])
            
            c7, c8 = st.columns(2)
            stock = c7.number_input("Stock", min_value=0)
            precio = c8.number_input("Precio", min_value=0.0)
            
            foto = st.file_uploader("Foto", type=['jpg','png'])
            
            if st.form_submit_button("Guardar"):
                if nombre and hoja:
                    # 1. Subir foto a ImgBB
                    url_final = ""
                    if foto:
                        with st.spinner("Subiendo imagen a la nube..."):
                            url_final = subir_a_imgbb(foto.getvalue(), nombre)
                    
                    if url_final is None and foto:
                         st.error("Falló la subida de imagen. Intenta de nuevo.")
                         st.stop()

                    # 2. Guardar en Excel
                    final_id = id_zap.strip() if id_zap else f"INT-{pd.Timestamp.now().strftime('%M%S')}"
                    
                    # Orden exacto: id, nombre, categoria, marca, formato, calidad, stock, precio, IMAGEN (URL)
                    fila = [str(final_id), nombre, categoria, marca, formato, calidad, stock, precio, url_final]
                    
                    try:
                        hoja.append_row(fila)
                        st.success("✅ Guardado Exitoso!")
                    except Exception as e:
                        st.error(f"Error Excel: {e}")
                else:
                    st.error("Datos incompletos")

    # --- 3. ACTUALIZAR STOCK ---
    elif choice == "Actualizar Stock":
        st.subheader("🔄 Ajuste Rápido")
        if not df.empty:
            opciones = df.apply(lambda x: f"{x['id']} | {x['nombre']}", axis=1)
            seleccion = st.selectbox("Producto:", opciones)
            id_sel = seleccion.split(" | ")[0]
            
            # Buscar fila (usando logica de texto para evitar errores de tipo)
            idx = df.index[df['id'].astype(str) == id_sel].tolist()[0]
            fila_sheet = idx + 2
            
            item = df.iloc[idx]
            
            c1, c2 = st.columns([1,2])
            with c1:
                if item['imagen'].startswith("http"):
                    st.image(item['imagen'])
            
            with c2:
                st.metric("Stock Actual", item['stock'])
                cambio = st.number_input("Ajuste", step=1)
                if st.button("Aplicar"):
                    nuevo = int(int(item['stock']) + cambio)
                    hoja.update_cell(fila_sheet, 7, nuevo)
                    st.success("Hecho")
                    st.rerun()

if __name__ == "__main__":
    main()