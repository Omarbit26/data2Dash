import hashlib
import streamlit as st
from firebase_admin import credentials, firestore, initialize_app, _apps


class FirebaseService:
    def __init__(self, ruta_credenciales='credenciales_firebase.json'):
        """Inicializa la conexión de forma híbrida (Local o Cloud)"""
        if not _apps:
            try:
                cred = credentials.Certificate(ruta_credenciales)
                initialize_app(cred)
            except Exception:
                try:
                    cred_dict = dict(st.secrets["gcp_service_account"])
                    cred = credentials.Certificate(cred_dict)
                    initialize_app(cred)
                except Exception as secret_error:
                    raise RuntimeError(
                        f"Error en la nube: Verifica que pegaste bien los Secrets en Streamlit. Detalle: {secret_error}"
                    )

        self.db = firestore.client()
        self.coleccion = 'ofertas_tech'

    def _generar_id_unico(self, oferta):
        """Genera la llave lógica compuesta única para evitar duplicados."""
        empresa = str(oferta.get('empresa', 'Anonima')).strip().lower()
        rol = str(oferta.get('tipo_de_rol', 'Otros_Tech')).strip().lower()
        seniority = str(oferta.get('nivel_seniority', 'Null')).strip().lower()

        fecha_carga = oferta.get('fecha_carga', '')
        cod_mes = "".join(fecha_carga.split("-")[:2]) if "-" in fecha_carga else "000000"

        techs = oferta.get('tecnologias_principales', [])
        techs_limpias = sorted([str(t).strip().lower() for t in techs if t])
        techs_string = "_".join(techs_limpias)

        clave_negocio = f"{empresa}_{rol}_{seniority}_{cod_mes}_{techs_string}"
        return hashlib.md5(clave_negocio.encode('utf-8')).hexdigest()

    def _limpiar_tipos_datos(self, oferta):
        """Asegura que los campos numéricos vayan como enteros a Firebase"""
        if oferta.get('experiencia_anos') is not None:
            try:
                oferta['experiencia_anos'] = int(oferta['experiencia_anos'])
            except Exception:
                oferta['experiencia_anos'] = None

        if oferta.get('salario_anual_usd') is not None:
            try:
                oferta['salario_anual_usd'] = int(oferta['salario_anual_usd'])
            except Exception:
                oferta['salario_anual_usd'] = None
        return oferta

    def cargar_lote_ofertas(self, lista_ofertas, ai_service=None):
        """Recorre el lote de ofertas e inyecta cada una mediante Upsert, generando su embedding."""
        exitos = 0
        logs = []

        for oferta in lista_ofertas:
            try:
                oferta_limpia = self._limpiar_tipos_datos(oferta)
                doc_id = self._generar_id_unico(oferta_limpia)

                # Generar embedding si el ai_service fue provisto
                if ai_service:
                    oferta_limpia['embedding'] = ai_service.generar_embedding_oferta(oferta_limpia)

                self.db.collection(self.coleccion).document(doc_id).set(oferta_limpia)

                titulo = oferta_limpia.get('puesto_titulo_original', 'Puesto sin título')
                logs.append(f"✅ Cargado con vector: {titulo}")
                exitos += 1
            except Exception as e:
                logs.append(f"❌ Error en oferta: {str(e)}")

        return exitos, logs