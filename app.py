import streamlit as st
import json
from firebase_service import FirebaseService

# Configuración de la ventana del navegador
st.set_page_config(page_title="Pipeline Ingesta", layout="centered")

st.title("💼 Pipeline Ingesta de Empleos")
st.subheader("Carga MVP - Local a Cloud Firestore")


# Inicializar nuestro servicio de base de datos de forma segura
@st.cache_resource
def iniciar_servicio():
    return FirebaseService()


try:
    db_service = iniciar_servicio()
except Exception as e:
    st.error(f"Error de conexión con Firestore: {e}")
    st.stop()

# Caja de texto gigante para pegar el JSON
json_input = st.text_area(
    "Pega aquí el JSON de ChatGPT:",
    height=250,
    placeholder="[\n  {\n    \"empresa\": \"Globant\",\n    ...\n  }\n]"
)

# Botón de acción
if st.button("Enviar Batch a Firebase", type="primary"):
    if not json_input.strip():
        st.warning("⚠️ El cuadro de texto está vacío.")
    else:
        try:
            # 1. Validar que el texto sea un JSON real y una lista
            lote_datos = json.loads(json_input)
            if not isinstance(lote_datos, list):
                st.error("❌ El formato debe ser una lista JSON (comenzar con '[' y terminar con ']')")
                st.stop()

            # 2. Ejecutar la carga a través del servicio
            cantidad_subida, lista_logs = db_service.cargar_lote_ofertas(lote_datos)

            # 3. Mostrar resumen de éxito
            st.success(f"🎉 ¡Proceso Terminado! Se cargaron/actualizaron {cantidad_subida} ofertas.")

            # Desplegar el visor de logs por si quieres auditar la carga
            with st.expander("Ver detalle del proceso"):
                for log in lista_logs:
                    st.write(log)

        except json.JSONDecodeError:
            st.error("❌ Error de sintaxis: El texto ingresado no es un JSON válido. Revisa comillas o llaves.")
        except Exception as e:
            st.error(f"❌ Error crítico: {e}")