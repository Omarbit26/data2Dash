import streamlit as st
import json
from firebase_service import FirebaseService
from ai_service import AIService

# Configuración de la página
st.set_page_config(page_title="Pipeline Ingesta & IA", layout="centered")

st.title("💼 Pipeline de Empleos Tech")
st.subheader("Carga y Análisis con IA")


# Inicializar servicios
@st.cache_resource
def iniciar_servicios():
    db_service = FirebaseService()
    ai_service = AIService(db_service)
    return db_service, ai_service


try:
    db_service, ai_service = iniciar_servicios()
except Exception as e:
    st.error(f"Error de inicialización: {e}")
    st.stop()

# Crear Pestañas en la UI
tab_ingesta, tab_chat = st.tabs(["📥 Ingesta de Datos", "🤖 Chat con IA"])

# --- PESTAÑA 1: INGESTA ---
with tab_ingesta:
    json_input = st.text_area(
        "Pega aquí el JSON de ChatGPT:",
        height=250,
        placeholder="[\n  {\n    \"empresa\": \"Globant\",\n    ...\n  }\n]"
    )

    if st.button("Enviar Batch a Firebase", type="primary"):
        if not json_input.strip():
            st.warning("⚠️ El cuadro de texto está vacío.")
        else:
            try:
                lote_datos = json.loads(json_input)
                if not isinstance(lote_datos, list):
                    st.error("❌ El formato debe ser una lista JSON (comenzar con '[' y terminar con ']')")
                    st.stop()

                # PASAMOS ai_service PARA QUE CALCULE LOS EMBEDDINGS AL INSERTAR
                cantidad_subida, lista_logs = db_service.cargar_lote_ofertas(lote_datos, ai_service=ai_service)
                st.success(f"🎉 ¡Proceso Terminado! Se cargaron/actualizaron {cantidad_subida} ofertas con sus vectores.")

                with st.expander("Ver detalle del proceso"):
                    for log in lista_logs:
                        st.write(log)

            except json.JSONDecodeError:
                st.error("❌ Error de sintaxis: El texto ingresado no es un JSON válido. Revisa comillas o llaves.")
            except Exception as e:
                st.error(f"❌ Error crítico: {e}")

# --- PESTAÑA 2: CHAT CON IA ---
with tab_chat:
    st.markdown("### Pregúntale a tu Base de Datos de Empleos")
    pregunta = st.text_input("Ejemplo: ¿Qué empresas buscan Data Engineers y qué salario ofrecen?")

    if st.button("Consultar a Gemini"):
        if not pregunta.strip():
            st.warning("Por favor escribe una pregunta.")
        else:
            with st.spinner("Gemini analizando ofertas en Firestore..."):
                try:
                    respuesta = ai_service.responder_pregunta(pregunta)
                    st.markdown("### Respuesta:")
                    st.write(respuesta)
                except Exception as e:
                    st.error(f"Error al consultar la IA: {e}")