import google.generativeai as genai
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
import streamlit as st


class AIService:

    def __init__(self, db_service):
        """Inicializa los servicios de Gemini y la conexión con Firestore."""
        self.db_service = db_service

        # 1. Configurar la API Key desde los secrets de Streamlit
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)

        # 2. Definir los modelos
        self.generation_model = genai.GenerativeModel("models/gemini-3.6-flash")
        self.embedding_model = "models/gemini-embedding-001"

    def generar_embedding_oferta(self, oferta: dict) -> Vector:
        # 1. Extraemos la fecha de carga
        fecha_carga = oferta.get("fecha_carga", "")
        titulo = oferta.get("puesto_titulo_original", oferta.get("titulo", ""))
        empresa = oferta.get("empresa", "")
        descripcion = oferta.get("descripcion", "")
        tecnologias = oferta.get(
            "tecnologias_principales", oferta.get("tecnologias", "")
        )
        modalidad = oferta.get("modalidad", "")

        if isinstance(tecnologias, list):
            tecnologias = ", ".join(tecnologias)

        # 2. Destacamos la fecha explícitamente en el texto del vector
        texto_doc = f"""
        Fecha de publicación / registro: {fecha_carga}
        Título del puesto: {titulo}
        Empresa: {empresa}
        Modalidad: {modalidad}
        Tecnologías/Requisitos: {tecnologias}
        Descripción: {descripcion}
        """.strip()

        response = genai.embed_content(
            model=self.embedding_model,
            content=texto_doc,
            task_type="retrieval_document",
            output_dimensionality=768,
        )
        raw = response["embedding"]

        if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list):
            raw = raw[0]

        vector_puro = [float(x) for x in raw]
        return Vector(vector_puro)

    def _generar_embedding_pregunta(self, pregunta: str) -> list[float]:
        """Convierte la consulta del usuario en un vector numérico de 768 dimensiones."""
        response = genai.embed_content(
            model=self.embedding_model,
            content=pregunta,
            task_type="retrieval_query",
            output_dimensionality=768,
        )
        raw = response["embedding"]

        if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list):
            raw = raw[0]

        return [float(x) for x in raw]

    def _buscar_ofertas_relevantes(self, pregunta: str, top_k: int = 5) -> list[dict]:
        """Consulta el índice vectorial de Firestore y devuelve las 'top_k' ofertas más parecidas."""
        vector_query = self._generar_embedding_pregunta(pregunta)
        v_obj = Vector(vector_query)

        coleccion_ref = self.db_service.db.collection(self.db_service.coleccion)

        vector_search = coleccion_ref.find_nearest(
            vector_field="embedding",
            query_vector=v_obj,
            distance_measure=DistanceMeasure.COSINE,
            limit=top_k,
        )

        results = vector_search.get()

        ofertas_relevantes = []
        for doc in results:
            data = doc.to_dict()
            data.pop("embedding", None)
            ofertas_relevantes.append(data)

        print(f"🔎 DOCUMENTOS ENCONTRADOS POR FIRESTORE: {len(ofertas_relevantes)}")
        return ofertas_relevantes

    def responder_pregunta(self, pregunta_usuario: str) -> str:
        """Flujo RAG completo: Búsqueda vectorial + Generación con Gemini."""
        try:
            ofertas_contexto = self._buscar_ofertas_relevantes(
                pregunta_usuario, top_k=5
            )

            if not ofertas_contexto:
                return "⚠️ No encontré ofertas en la base de datos que coincidan con tu búsqueda."

            prompt = f"""
Eres un asistente experto en el mercado laboral Tech.
Se han extraído las {len(ofertas_contexto)} ofertas más relevantes de la base de datos para responder a la consulta del usuario:

--- OFERTAS RECUPERADAS ---
{ofertas_contexto}
---------------------------

Pregunta del usuario: "{pregunta_usuario}"

Instrucciones:
1. Responde a la pregunta basándote ÚNICAMENTE en la lista de ofertas proporcionadas arriba.
2. Sé claro, directo y usa formato Markdown (negritas, listas, etc.) para que la respuesta sea fácil de leer.
3. Si la información proporcionada no responde completamente a lo que pide el usuario, indícalo de forma amable.
"""

            response = self.generation_model.generate_content(prompt)
            return response.text

        except Exception as e:
            return f"❌ Ocurrió un error al procesar la búsqueda vectorial: {e}"