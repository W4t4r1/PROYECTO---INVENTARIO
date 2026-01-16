import streamlit as st
import sqlite3
import pandas as pd
import os
from PIL import Image
import io
from openpyxl.drawing.image import Image as ExcelImage # <--- NUEVO IMPORT NECESARIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inventario UNI", layout="wide", page_icon="🏗️")

if not os.path.exists("imagenes"):
    os.makedirs("imagenes")

def conectar():
    return sqlite3.connect("mi_inventario.db")

def crear_tabla():
    conn = conectar()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE productos ADD COLUMN imagen TEXT")
    except sqlite3.OperationalError:
        pass 
    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT,
            formato TEXT,
            stock INTEGER DEFAULT 0,
            precio REAL,
            imagen TEXT
        )
    """)
    conn.commit()
    conn.close()

def main():
    crear_tabla()
    
    st.title("🏗️ Sistema de Control: Mayólicas y Sanitarios")

    menu = ["Ver Inventario", "Registrar Nuevo", "Actualizar Stock"]
    choice = st.sidebar.selectbox("Menú Principal", menu)

    # ==========================
    # 1. VER INVENTARIO
    # ==========================
    if choice == "Ver Inventario":
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("📦 Inventario Visual")
        with col2:
            if st.button("🔄 Actualizar Datos"):
                st.rerun()

        busqueda = st.text_input("🔍 Buscar producto:")
        
        conn = conectar()
        if busqueda:
            query = f"SELECT * FROM productos WHERE nombre LIKE '%{busqueda}%' OR categoria LIKE '%{busqueda}%'"
        else:
            query = "SELECT * FROM productos"
        
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            df['stock'] = pd.to_numeric(df['stock'], errors='coerce').fillna(0).astype(int)
            df['precio'] = pd.to_numeric(df['precio'], errors='coerce').fillna(0.0)

            # --- GENERACIÓN DE EXCEL CON IMÁGENES INCRUSTADAS ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Inventario')
                workbook = writer.book
                worksheet = writer.sheets['Inventario']
                
                # Ajustamos ancho de columnas
                for idx, col in enumerate(df.columns):
                    letra = chr(65 + idx)
                    worksheet.column_dimensions[letra].width = 20
                
                # Columna de imágenes (Asumimos que es la última, columna 'G' o índice 6)
                col_img_idx = df.columns.get_loc("imagen") + 1 # +1 porque Excel empieza en 1
                letra_col_img = chr(64 + col_img_idx) 
                worksheet.column_dimensions[letra_col_img].width = 15 # Ancho para la foto

                # ITERAMOS PARA PEGAR LAS FOTOS
                for index, row in df.iterrows():
                    ruta_img = row['imagen']
                    fila_excel = index + 2 # +2 porque hay encabezado y Excel empieza en 1
                    
                    if ruta_img and os.path.exists(ruta_img):
                        try:
                            # Cargamos y redimensionamos la imagen para Excel
                            img = ExcelImage(ruta_img)
                            img.height = 50 
                            img.width = 50
                            
                            # La pegamos en la celda correcta
                            celda = f"{letra_col_img}{fila_excel}"
                            worksheet.add_image(img, celda)
                            
                            # Aumentamos la altura de la fila para que quepa la foto
                            worksheet.row_dimensions[fila_excel].height = 40
                            
                            # Borramos el texto de la ruta para que no estorbe (opcional)
                            worksheet[celda] = "" 
                        except Exception:
                            pass # Si falla la imagen, dejamos el texto

            buffer.seek(0)
            # ----------------------------------------------------

            col_kpi1, col_kpi2, col_descarga = st.columns(3)
            col_kpi1.metric("Total Unidades", df['stock'].sum())
            col_kpi2.metric("Valor Total", f"S/. {(df['stock'] * df['precio']).sum():,.2f}")
            
            with col_descarga:
                st.download_button(
                    label="📥 Descargar Excel con Fotos",
                    data=buffer,
                    file_name='inventario_con_fotos.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )

            # Vistas en pantalla
            vista = st.radio("Vista:", ["Tabla Detallada", "Galería de Fotos"], horizontal=True)
            
            if vista == "Tabla Detallada":
                def resaltar_stock(val):
                    color = '#ffcccc' if val < 10 else ''
                    return f'background-color: {color}'
                
                st.dataframe(
                    df.style.format({"precio": "S/. {:.2f}"}).applymap(resaltar_stock, subset=['stock']),
                    use_container_width=True
                )
            
            else: 
                cols = st.columns(4)
                for index, row in df.iterrows():
                    with cols[index % 4]:
                        st.markdown(f"**{row['nombre']}**")
                        img_path = row['imagen']
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                        else:
                            st.info("Sin imagen")
                        st.caption(f"Stock: {row['stock']} | Precio: S/.{row['precio']}")
                        st.divider()

    # ==========================
    # 2. REGISTRAR
    # ==========================
    elif choice == "Registrar Nuevo":
        st.subheader("📝 Nuevo Producto con Foto")
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre del Producto")
            categoria = col2.selectbox("Categoría", ["Mayólica", "Porcelanato", "Sanitario", "Grifería", "Pegamento"])
            col3, col4, col5 = st.columns(3)
            formato = col3.text_input("Formato")
            stock = col4.number_input("Stock Inicial", min_value=0)
            precio = col5.number_input("Precio", min_value=0.0, step=0.1)
            imagen_archivo = st.file_uploader("Subir Foto", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("Guardar Producto"):
                if nombre:
                    ruta_final = None
                    if imagen_archivo is not None:
                        ruta_final = os.path.join("imagenes", imagen_archivo.name)
                        with open(ruta_final, "wb") as f:
                            f.write(imagen_archivo.getbuffer())
                    
                    conn = conectar()
                    c = conn.cursor()
                    c.execute("INSERT INTO productos (nombre, categoria, formato, stock, precio, imagen) VALUES (?, ?, ?, ?, ?, ?)", 
                             (nombre, categoria, formato, stock, precio, ruta_final))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {nombre} registrado correctamente!")
                else:
                    st.error("❌ Nombre obligatorio")

    # ==========================
    # 3. ACTUALIZAR STOCK
    # ==========================
    elif choice == "Actualizar Stock":
        st.subheader("🔄 Movimientos de Almacén")
        conn = conectar()
        df = pd.read_sql("SELECT * FROM productos", conn)
        conn.close()
        
        if not df.empty:
            df['stock'] = pd.to_numeric(df['stock'], errors='coerce').fillna(0).astype(int)
            producto_selec = st.selectbox("Buscar Producto:", df['id'].astype(str) + " - " + df['nombre'])
            id_sel = int(producto_selec.split(" - ")[0])
            prod_data = df[df['id'] == id_sel].iloc[0]
            
            c1, c2 = st.columns([1, 3])
            with c1:
                if prod_data['imagen'] and os.path.exists(prod_data['imagen']):
                    st.image(prod_data['imagen'], width=150)
                else:
                    st.warning("Sin foto")
            with c2:
                st.metric("Stock Actual", prod_data['stock'])
                cantidad = st.number_input("Cantidad a sumar/restar:", step=1)
                if st.button("Aplicar Cambio"):
                    nuevo_stock = int(prod_data['stock'] + cantidad)
                    if nuevo_stock < 0:
                        st.error("❌ Stock insuficiente.")
                    else:
                        conn = conectar()
                        conn.cursor().execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, id_sel))
                        conn.commit()
                        conn.close()
                        st.success("✅ Stock actualizado")
                        st.rerun()

if __name__ == "__main__":
    main()