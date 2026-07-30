import streamlit as st
import google.generativeai as genai


class AIService:

    def __init__(self, db_service):
        """Recibe la instancia de FirebaseService para consultar Firestore."""
        self.db_service = db_service

        # Configurar la API Key desde los secrets
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)

        # Apuntamos a la versión actual activa: gemini-3.6-flash
        self.model = genai.GenerativeModel("models/gemini-3.6-flash")

    def _obtener_todas_las_ofertas(self):
        """Obtiene las ofertas desde Firestore para darle contexto a la IA."""
        docs = self.db_service.db.collection(
            self.db_service.coleccion
        ).stream()
        return [doc.to_dict() for doc in docs]

    def responder_pregunta(self, pregunta_usuario):
        """Envía el contexto de la base de datos + la pregunta a Gemini."""
        ofertas = self._obtener_todas_las_ofertas()

        if not ofertas:
            return (
                "⚠️ No hay ofertas registradas en la base de datos para responder."
            )

        prompt = f"""
Eres un asistente experto en análisis de datos del mercado laboral Tech.
Tienes acceso a la siguiente lista de ofertas laborales en formato JSON cargadas en la base de datos de Firestore:

{ofertas}

Pregunta del usuario: "{pregunta_usuario}"

Instrucciones:
1. Responde a la pregunta basándote ÚNICAMENTE en los datos de las ofertas proporcionadas.
2. Sé claro, conciso y estructurado (puedes usar viñetas o tablas markdown si ayuda).
3. Si la pregunta no se puede responder con la información disponible, indícalo amablemente.
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"❌ Error al procesar la consulta con Gemini: {e}"