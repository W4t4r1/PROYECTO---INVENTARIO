import sqlite3
import os

# --- NOMBRE DEL ARCHIVO DE BASE DE DATOS ---
DB_NAME = "mi_inventario.db"

def conectar():
    """Crea la conexión a la base de datos."""
    return sqlite3.connect(DB_NAME)

def crear_tablas():
    """Crea la estructura inicial si no existe."""
    conexion = conectar()
    cursor = conexion.cursor()
    
    # Creamos la tabla con ID, Nombre, Categoría, Formato, Stock y Precio
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        categoria TEXT,
        formato TEXT,
        stock INTEGER DEFAULT 0,
        precio REAL
    )
    """)
    conexion.commit()
    conexion.close()

def registrar_producto():
    """Función para CREAR (Create) datos."""
    print("\n--- REGISTRO DE NUEVO PRODUCTO ---")
    
    # 1. Inputs del usuario
    nombre = input("Nombre del producto (ej. Pegamento Gris): ")
    categoria = input("Categoría (ej. Mayólica, Grifería): ")
    formato = input("Formato/Medidas (ej. 60x60): ")
    
    # 2. Validación de números
    try:
        stock = int(input("Stock inicial (cantidad): "))
        precio = float(input("Precio unitario (S/.): "))
    except ValueError:
        print("❌ ERROR: El stock y precio deben ser números válidos.")
        return 

    # 3. Guardado en SQL
    conexion = conectar()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO productos (nombre, categoria, formato, stock, precio)
        VALUES (?, ?, ?, ?, ?)
        """, (nombre, categoria, formato, stock, precio))
        
        conexion.commit()
        print(f"✅ ¡Éxito! Producto '{nombre}' registrado correctamente.")
    except Exception as e:
        print(f"❌ Error crítico al guardar: {e}")
    finally:
        conexion.close()

def ver_inventario():
    """Función para LEER (Read) datos."""
    print("\n--- INVENTARIO ACTUAL ---")
    conexion = conectar()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    
    conexion.close()

    if not productos:
        print("⚠️ El inventario está vacío.")
    else:
        # Encabezados de la tabla (Formato visual)
        print(f"{'ID':<4} | {'NOMBRE':<25} | {'CATEGORIA':<15} | {'STOCK':<6} | {'PRECIO':<8}")
        print("-" * 75)
        
        for p in productos:
            # p[0]=id, p[1]=nombre, p[2]=categoria, p[3]=formato, p[4]=stock, p[5]=precio
            print(f"{p[0]:<4} | {p[1]:<25} | {p[2]:<15} | {p[4]:<6} | S/.{p[5]:<8}")

def actualizar_stock():
    """Función para ACTUALIZAR (Update) datos."""
    ver_inventario() # Mostramos la lista para que el usuario vea el ID
    print("\n--- ACTUALIZAR STOCK (ENTRADA/SALIDA) ---")
    
    try:
        id_producto = int(input("👉 Ingresa el ID del producto a modificar: "))
        cantidad = int(input("👉 Cantidad a sumar (positivo) o restar (negativo ej. -5): "))
    except ValueError:
        print("❌ Error: Debes ingresar números enteros.")
        return

    conexion = conectar()
    cursor = conexion.cursor()

    # 1. Verificar existencia y stock actual
    cursor.execute("SELECT stock, nombre FROM productos WHERE id = ?", (id_producto,))
    resultado = cursor.fetchone()

    if resultado:
        stock_actual = resultado[0]
        nombre_prod = resultado[1]
        nuevo_stock = stock_actual + cantidad
        
        # 2. Lógica de Negocio: No permitir negativos
        if nuevo_stock < 0:
            print(f"⛔ OPERACIÓN DENEGADA: No tienes suficiente stock. Tienes {stock_actual} y quieres restar {abs(cantidad)}.")
        else:
            # 3. Ejecutar el cambio
            cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, id_producto))
            conexion.commit()
            print(f"✅ Stock de '{nombre_prod}' actualizado. Nuevo total: {nuevo_stock}")
    else:
        print("❌ Error: Producto no encontrado.")
    
    conexion.close()

# --- BLOQUE PRINCIPAL (MENÚ) ---
if __name__ == "__main__":
    crear_tablas() # Siempre aseguramos que la tabla exista al iniciar
    
    while True:
        print("\n" + "="*40)
        print(" SISTEMA DE GESTIÓN - MAYÓLICAS Y SANITARIOS")
        print("="*40)
        print("1. 📦 Registrar Producto Nuevo")
        print("2. 📋 Ver Inventario Completo")
        print("3. 🔄 Registrar Entrada/Salida (Ventas/Compras)")
        print("4. 🚪 Salir")
        
        opcion = input("\nElige una opción: ")
        
        if opcion == "1":
            registrar_producto()
        elif opcion == "2":
            ver_inventario()
        elif opcion == "3":
            actualizar_stock()
        elif opcion == "4":
            print("Cerrando sistema. ¡Hasta luego!")
            break
        else:
            print("⚠️ Opción no válida, intenta de nuevo.")