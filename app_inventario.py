import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import io
from openpyxl.drawing.image import Image as ExcelImage

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Inventario ZAP Celima", layout="wide", page_icon="🏗️")

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

# --- CONEXIÓN ---
def conectar_google_sheets():
    if not os.path.exists("imagenes"): os.makedirs("imagenes")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("inventario_db").sheet1
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_datos():
    hoja = conectar_google_sheets()
    if hoja:
        # Usamos get_all_values en lugar de get_all_records
        # Esto evita el error de "headers duplicados" o celdas vacías
        datos = hoja.get_all_values()
        
        if not datos:
            return pd.DataFrame(), hoja
            
        # La primera fila son los encabezados
        headers = datos.pop(0) 
        
        # Creamos el DataFrame manualmente
        df = pd.DataFrame(datos, columns=headers)
        return df, hoja
        
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
        with col1: st.subheader("📦 Stock Valorizado")
        with col2: 
            if st.button("🔄 Recargar"): st.rerun()

        busqueda = st.text_input("🔍 Buscar (Código ZAP, Nombre, Calidad...):")
        
        if not df.empty:
            if busqueda:
                mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
                df_filtered = df[mask]
            else:
                df_filtered = df

            # Limpieza y KPIs
            df_filtered['stock'] = pd.to_numeric(df_filtered['stock'], errors='coerce').fillna(0).astype(int)
            df_filtered['precio'] = pd.to_numeric(df_filtered['precio'], errors='coerce').fillna(0.0)

            c1, c2, c3 = st.columns(3)
            c1.metric("SKUs Totales", len(df_filtered))
            c2.metric("Unidades Físicas", df_filtered['stock'].sum())
            c3.metric("Valor en Soles", f"S/. {(df_filtered['stock'] * df_filtered['precio']).sum():,.2f}")

            # Exportar Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Stock')
            
            st.download_button("📥 Descargar Excel", data=buffer.getvalue(), file_name='stock_zap.xlsx')
            
            # Tabla Principal
            # Aseguramos que se muestren las columnas clave
            columnas_visibles = ['id', 'marca', 'nombre', 'calidad', 'formato', 'stock', 'precio']
            # Filtramos solo las columnas que existan en el DF para evitar errores si Google Sheets no está actualizado
            cols_finales = [c for c in columnas_visibles if c in df_filtered.columns]
            
            st.dataframe(df_filtered[cols_finales], use_container_width=True)
        else:
            st.warning("No hay datos. Registra productos.")

    # --- 2. REGISTRAR (Con ZAP y Calidad) ---
    elif choice == "Registrar Nuevo":
        st.subheader("📝 Nuevo Ingreso (Código ZAP)")
        
        with st.form("form_registro", clear_on_submit=True):
            # Fila 1: Lo más importante
            c1, c2 = st.columns(2)
            id_zap = c1.text_input("Código ZAP (Ej. 110016549)", help="Código numérico único del sistema SAP/Celima")
            marca = c2.selectbox("Marca", ["Celima", "Trebol", "Generico", "Otro"])
            
            # Fila 2: Definición del producto
            c3, c4 = st.columns(2)
            nombre = c3.text_input("Descripción (Ej. Cayalti Gris)")
            categoria = c4.selectbox("Categoría", ["Mayólica", "Sanitario", "Grifería", "Pegamento", "Fragua", "Otros"])
            
            # Fila 3: Detalles Técnicos
            c5, c6 = st.columns(2)
            # Formatos
            formatos = ["27x45", "30x30", "45x45", "60x60", "30x60", "59x59", "Otro"]
            formato_sel = c5.selectbox("Formato / Medida", formatos)
            if formato_sel == "Otro": formato_sel = st.text_input("Formato Manual:")
            
            # Calidades (Lógica condicional visual)
            calidades = ["Comercial", "Extra", "Única", "Estándar (No aplica)"]
            calidad = c6.selectbox("Calidad / Tipo", calidades, index=0)
            
            # Fila 4: Comercial
            c7, c8 = st.columns(2)
            stock = c7.number_input("Stock Inicial", min_value=0, step=1)
            precio = c8.number_input("Precio Unitario", min_value=0.0)
            
            foto = st.file_uploader("Foto referencial", type=['jpg','png'])
            
            if st.form_submit_button("Guardar en Nube"):
                if nombre and hoja:
                    ruta_img = ""
                    if foto:
                        ruta_img = os.path.join("imagenes", foto.name)
                        with open(ruta_img, "wb") as f: f.write(foto.getbuffer())

                    # ID Logic
                    final_id = id_zap.strip()
                    if not final_id:
                        # Si es un "hueso" sin código ZAP, generamos uno interno
                        import random
                        final_id = f"INT-{random.randint(10000, 99999)}"
                    
                    # Validación de duplicados
                    if str(final_id) in df['id'].astype(str).values:
                        st.error(f"⚠️ El código ZAP {final_id} ya existe en el inventario.")
                        st.stop()
                    
                    # Armamos la fila respetando el orden de Google Sheets
                    # id, nombre, categoria, marca, formato, CALIDAD, stock, precio, imagen
                    fila = [
                        str(final_id), 
                        nombre, 
                        categoria, 
                        marca, 
                        formato_sel, 
                        calidad, # <--- Nueva columna
                        stock, 
                        precio, 
                        ruta_img
                    ]
                    
                    try:
                        hoja.append_row(fila)
                        st.success(f"✅ Registrado: {nombre} ({calidad}) - ZAP: {final_id}")
                    except Exception as e:
                        st.error(f"Error guardando: {e}")
                else:
                    st.error("Nombre obligatorio.")

    # --- 3. ACTUALIZAR STOCK ---
    elif choice == "Actualizar Stock":
        st.subheader("🔄 Entrada/Salida Rápida")
        if not df.empty:
            # Buscador incluye Calidad y ZAP
            def etiqueta(x):
                return f"{x['id']} | {x['nombre']} ({x['calidad']}) - {x['formato']}"
            
            opciones = df.apply(etiqueta, axis=1)
            seleccion = st.selectbox("Buscar SKU:", opciones)
            
            id_sel = seleccion.split(" | ")[0]
            
            # Localizar fila
            idx = df.index[df['id'].astype(str) == id_sel].tolist()[0]
            fila_sheet = idx + 2
            
            # Datos actuales
            item = df.iloc[idx]
            c1, c2 = st.columns([1,3])
            with c1:
                st.info(f"Stock: {item['stock']}")
                st.caption(f"Calidad: {item['calidad']}")
            
            with c2:
                cambio = st.number_input("Ajuste (+/-):", step=1)
                if st.button("Confirmar Ajuste"):
                    nuevo = int(item['stock'] + cambio)
                    if nuevo < 0:
                        st.error("No hay suficiente stock")
                    else:
                        # Columna 7 es Stock ahora (A=1, B=2, C=3, D=4, E=5, F=6(Calidad), G=7(Stock))
                        hoja.update_cell(fila_sheet, 7, nuevo)
                        st.success("✅ Stock actualizado")
                        st.rerun()

if __name__ == "__main__":
    main()