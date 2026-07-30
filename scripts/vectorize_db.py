import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.vector import Vector
import google.generativeai as genai
import streamlit as st

# ---------------------------------------------------------
# 1. Configuración de Credenciales
# ---------------------------------------------------------
RUTA_JSON_FIREBASE = "credenciales_firebase.json"
COLECCION = "ofertas_tech"  # Nombre exacto de tu colección en Firestore

EMBEDDING_MODEL = "models/gemini-embedding-001"

# Leer API Key con Streamlit
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# Inicializar Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(RUTA_JSON_FIREBASE)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ---------------------------------------------------------
# 2. Funciones Auxiliares
# ---------------------------------------------------------
def construir_texto_para_embedding(oferta: dict) -> str:
    """Junta los campos clave en un solo texto para vectorizar."""
    titulo = oferta.get("titulo", "")
    empresa = oferta.get("empresa", "")
    descripcion = oferta.get("descripcion", "")
    tecnologias = oferta.get("tecnologias", "")
    modalidad = oferta.get("modalidad", "")

    if isinstance(tecnologias, list):
        tecnologias = ", ".join(tecnologias)

    return f"""
    Título del puesto: {titulo}
    Empresa: {empresa}
    Modalidad: {modalidad}
    Tecnologías/Requisitos: {tecnologias}
    Descripción: {descripcion}
    """.strip()


def generar_embedding(texto: str) -> list[float]:
    """Genera el vector numérico recortado a 768 dimensiones para Firestore."""
    response = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=texto,
        task_type="retrieval_document",
        output_dimensionality=768,  # Forzamos las 768 dimensiones soportadas por tu índice
    )
    raw = response["embedding"]

    if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list):
        raw = raw[0]

    return [float(x) for x in raw]


# ---------------------------------------------------------
# 3. Proceso de Vectorización
# ---------------------------------------------------------
def vectorizar_coleccion():
    print(
        f"🚀 Conectando a Firestore y guardando vectores nativos en '{COLECCION}' (768d)...\n"
    )

    docs = db.collection(COLECCION).stream()
    total_procesados = 0

    for doc in docs:
        oferta_data = doc.to_dict()
        titulo_doc = oferta_data.get("titulo", doc.id)

        print(f"⚡ Generando vector (768d) para: '{titulo_doc}'...")

        try:
            texto_doc = construir_texto_para_embedding(oferta_data)
            vector_lista = generar_embedding(texto_doc)

            # Envolver la lista con Vector() para que Firestore lo reconozca como índice vectorial
            db.collection(COLECCION).document(doc.id).update(
                {"embedding": Vector(vector_lista)}
            )

            total_procesados += 1
            print(f"✅ [Doc ID: {doc.id}] Vector correcto asignado.")

        except Exception as e:
            print(f"❌ Error en Doc ID {doc.id}: {e}")

    print("\n" + "=" * 50)
    print(f"🎉 Migración a Vector nativo finalizada | Procesados: {total_procesados}")
    print("=" * 50)


if __name__ == "__main__":
    vectorizar_coleccion()