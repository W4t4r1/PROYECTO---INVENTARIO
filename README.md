# 🏭 Sistema de Gestión de Inventarios - Mayólicas y Sanitarios

Aplicación web interactiva para el control de stock, gestión de productos y generación de reportes en tiempo real para un negocio de materiales de construcción.

## 🚀 Características Principales

* **Gestión CRUD Completa:** Registro, lectura, actualización y control de productos.
* **Inventario Visual:** Carga y visualización de imágenes reales de los productos (Mayólicas, Sanitarios, Grifería).
* **Alertas Inteligentes:** Indicadores visuales y métricas automáticas para stock crítico.
* **Reportes Ejecutivos:** Exportación de inventario a Excel (.xlsx) con formato profesional e imágenes incrustadas.
* **Base de Datos Relacional:** Persistencia de datos mediante SQLite.

## 🛠️ Tecnologías Utilizadas

Este proyecto fue construido utilizando un stack tecnológico eficiente y escalable basado en Python:

* **Python 3.12+**: Lógica de negocio.
* **Streamlit**: Framework para la interfaz web interactiva.
* **Pandas**: Manipulación y análisis de datos.
* **SQLite3**: Base de datos ligera y serverless.
* **OpenPyXL**: Motor de generación de reportes Excel avanzados.

## ⚙️ Instalación y Uso Local

Si deseas ejecutar este proyecto en tu máquina local:

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/TU_USUARIO/sistema-inventario-mayolicas.git](https://github.com/TU_USUARIO/sistema-inventario-mayolicas.git)
    cd sistema-inventario-mayolicas
    ```

2.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecutar la aplicación:**
    ```bash
    python -m streamlit run app_inventario.py
    ```

## 📂 Estructura del Proyecto

* `app_inventario.py`: Código fuente principal (Frontend + Backend).
* `mi_inventario.db`: Base de datos SQLite (se genera automáticamente si no existe).
* `imagenes/`: Carpeta de almacenamiento para las fotos de los productos.
* `requirements.txt`: Lista de dependencias del proyecto.

---
**Desarrollado por:** Huanca Achahui, Marco Antonio - Estudiante de Ingeniería de Sistemas (UNI - FIIS)