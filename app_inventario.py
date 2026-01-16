import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import os
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inventario Ledisa", layout="wide", page_icon="🏗️")

# --- CONEXIÓN GOOGLE SHEETS ---
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Usamos secrets sin try/except agresivo para ver el error real si falla
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("inventario_db").sheet1
    except Exception as e:
        # Solo mostramos error si realmente falla la conexión, no el login
        st.error(f"⚠️ Error conectando a Google Sheets: {e}")
        return None

# --- FUNCIÓN IMGBB ---
def subir_a_imgbb(archivo_bytes, nombre):
    try:
        api_key = st.secrets["imgbb"]["key"]
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": api_key, "name": nombre}
        files = {"image": archivo_bytes}
        response = requests.post(url, data=payload, files=files)
        if response.status_code == 200:
            return response.json()['data']['url']
        else:
            st.error(f"Error ImgBB: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error subiendo imagen: {e}")
        return None

def obtener_datos():
    hoja = conectar_google_sheets()
    if hoja:
        try:
            datos = hoja.get_all_values()
            if not datos: return pd.DataFrame(), hoja
            headers = datos.pop(0)
            return pd.DataFrame(datos, columns=headers), hoja
        except Exception:
            return pd.DataFrame(), hoja
    return pd.DataFrame(), None

# --- BARRA LATERAL DE LOGIN (SOLUCIÓN A TUS DOS DUDAS) ---
def sidebar_login():
    st.sidebar.title("🔐 Acceso")
    
    # Si ya está logueado, mostrar botón de salir
    if st.session_state.get('password_correct', False):
        st.sidebar.success("Modo: ADMINISTRADOR")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state['password_correct'] = False
            st.rerun()
        return True
    
    # Si no está logueado, mostrar formulario de login
    else:
        st.sidebar.info("Modo: VISITANTE (Solo lectura)")
        st.sidebar.markdown("---")
        st.sidebar.subheader("Ingreso Administrativo")
        
        # Usamos st.form para evitar el error de "doble enter"
        with st.sidebar.form("login_form"):
            password_input = st.text_input("Contraseña:", type="password")
            submit_button = st.form_submit_button("Ingresar")
            
            if submit_button:
                try:
                    # Verificación directa
                    if password_input == st.secrets["general"]["password"]:
                        st.session_state['password_correct'] = True
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta")
                except KeyError:
                    st.error("⚠️ Error: No encuentro [general] password en secrets.toml")
        
        return False

# --- FRONTEND PRINCIPAL ---
def main():
    # 1. Gestionamos el Login en la barra lateral
    es_admin = sidebar_login()

    st.title("🏭 Inventario: Celima & Trebol")
    
    # 2. Menú Dinámico según si es Admin o no
    if es_admin:
        menu = ["Ver Inventario", "Registrar Nuevo", "Actualizar Stock"]
    else:
        menu = ["Ver Inventario"] # Visitantes solo ven esto

    choice = st.sidebar.selectbox("Navegación", menu)
    df, hoja = obtener_datos()

    # --- OPCIÓN 1: VER INVENTARIO (PÚBLICO) ---
    if choice == "Ver Inventario":
        col1, col2 = st.columns([3,1])
        with col1: st.subheader("📦 Stock Disponible")
        with col2: 
            if st.button("🔄 Actualizar Tabla"): st.rerun()

        busqueda = st.text_input("🔍 Buscar producto:")
        
        if not df.empty:
            if busqueda:
                mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
                df_filtered = df[mask]
            else:
                df_filtered = df
            
            # Solo mostramos KPIs básicos
            st.caption(f"Mostrando {len(df_filtered)} productos encontrados.")
            
            # Galería visual
            cols = st.columns(3)
            for idx, row in df_filtered.iterrows():
                with cols[idx % 3]:
                    st.markdown(f"**{row['nombre']}**")
                    st.caption(f"Marca: {row['marca']} | Formato: {row['formato']}")
                    
                    img_url = row['imagen']
                    if img_url and img_url.startswith("http"):
                        st.image(img_url, use_container_width=True)
                    else:
                        st.warning("Sin foto")
                        
                    # Precios y Stock visibles para todos
                    st.metric("Stock", row['stock'], f"S/. {row['precio']}")
                    st.divider()
        else:
            st.warning("No se pudo cargar el inventario o está vacío.")

    # --- OPCIÓN 2: REGISTRAR (SOLO ADMIN) ---
    elif choice == "Registrar Nuevo":
        # Doble chequeo de seguridad por si acaso
        if not es_admin: st.stop()
        
        st.subheader("📝 Nuevo Ingreso (Privado)")
        with st.form("form_registro", clear_on_submit=True):
            c1, c2 = st.columns(2)
            id_zap = c1.text_input("Código ZAP")
            marca = c2.selectbox("Marca", ["Celima", "Trebol", "Generico", "Otro"])
            
            c3, c4 = st.columns(2)
            nombre = c3.text_input("Descripción")
            categoria = c4.selectbox("Categoría", ["Mayólica", "Sanitario", "Grifería", "Pegamento", "Fragua"])
            
            c5, c6 = st.columns(2)
            formato = c5.text_input("Formato")
            calidad = c6.selectbox("Calidad", ["Comercial", "Extra", "Única", "Estándar"])
            
            c7, c8 = st.columns(2)
            stock = c7.number_input("Stock", min_value=0)
            precio = c8.number_input("Precio", min_value=0.0)
            
            foto = st.file_uploader("Foto", type=['jpg','png'])
            
            if st.form_submit_button("Guardar en Nube"):
                if nombre and hoja:
                    url_final = ""
                    if foto:
                        with st.spinner("Subiendo foto..."):
                            url_final = subir_a_imgbb(foto.getvalue(), nombre)
                            if not url_final: st.error("Error subiendo foto"); st.stop()

                    final_id = id_zap.strip() if id_zap else f"INT-{pd.Timestamp.now().strftime('%M%S')}"
                    # id, nombre, categoria, marca, formato, calidad, stock, precio, IMAGEN
                    fila = [str(final_id), nombre, categoria, marca, formato, calidad, stock, precio, url_final]
                    
                    try:
                        hoja.append_row(fila)
                        st.success(f"✅ Registrado: {nombre}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Falta nombre")

    # --- OPCIÓN 3: ACTUALIZAR (SOLO ADMIN) ---
    elif choice == "Actualizar Stock":
        if not es_admin: st.stop()
        
        st.subheader("🔄 Ajuste de Inventario")
        if not df.empty:
            opciones = df.apply(lambda x: f"{x['id']} | {x['nombre']}", axis=1)
            seleccion = st.selectbox("Seleccionar Producto:", opciones)
            id_sel = seleccion.split(" | ")[0]
            
            idx = df.index[df['id'].astype(str) == id_sel].tolist()[0]
            fila_sheet = idx + 2
            item = df.iloc[idx]
            
            c1, c2 = st.columns([1,2])
            with c1:
                if item['imagen'].startswith("http"): st.image(item['imagen'])
            with c2:
                st.metric("Stock Actual", item['stock'])
                cambio = st.number_input("Ajuste (+/-)", step=1)
                
                if st.button("Aplicar Cambio"):
                    nuevo = int(int(item['stock']) + cambio)
                    hoja.update_cell(fila_sheet, 7, nuevo)
                    st.success("✅ Stock actualizado")
                    st.rerun()

if __name__ == "__main__":
    main()