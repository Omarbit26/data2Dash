import hashlib
from firebase_admin import credentials, firestore, initialize_app, _apps


class FirebaseService:
    def __init__(self, ruta_credenciales='credenciales_firebase.json'):
        """Inicializa la conexión con Firestore usando el archivo local de credenciales"""
        if not _apps:
            cred = credentials.Certificate(ruta_credenciales)
            initialize_app(cred)
        self.db = firestore.client()
        self.coleccion = 'ofertas_tech'

    def _generar_id_unico(self, oferta):
        """
        Genera la llave lógica compuesta única para evitar duplicados.
        Fórmula: EMPRESA + ROL + SENIORITY + COD_MES + LISTA_DE_TECNOLOGIAS (Ordenadas)
        """
        empresa = str(oferta.get('empresa', 'Anonima')).strip().lower()
        rol = str(oferta.get('tipo_de_rol', 'Otros_Tech')).strip().lower()
        seniority = str(oferta.get('nivel_seniority', 'Null')).strip().lower()

        # Extraer COD_MES desde la fecha_carga (ej: "2026-07-12" -> "202607")
        fecha_carga = oferta.get('fecha_carga', '')
        cod_mes = "".join(fecha_carga.split("-")[:2]) if "-" in fecha_carga else "000000"

        # Estandarizar tecnologías: pasar a minúsculas y ordenar alfabéticamente
        techs = oferta.get('tecnologias_principales', [])
        techs_limpias = sorted([str(t).strip().lower() for t in techs if t])
        techs_string = "_".join(techs_limpias)

        # Concatenar y encriptar en MD5
        clave_negocio = f"{empresa}_{rol}_{seniority}_{cod_mes}_{techs_string}"
        return hashlib.md5(clave_negocio.encode('utf-8')).hexdigest()

    def _limpiar_tipos_datos(self, oferta):
        """Asegura que los campos numéricos vayan como enteros a Firebase"""
        if oferta.get('experiencia_anos') is not None:
            try:
                oferta['experiencia_anos'] = int(oferta['experiencia_anos'])
            except:
                oferta['experiencia_anos'] = None

        if oferta.get('salario_anual_usd') is not None:
            try:
                oferta['salario_anual_usd'] = int(oferta['salario_anual_usd'])
            except:
                oferta['salario_anual_usd'] = None
        return oferta

    def cargar_lote_ofertas(self, lista_ofertas):
        """Recorre el lote de ofertas e inyecta cada una mediante Upsert"""
        exitos = 0
        logs = []

        for oferta in lista_ofertas:
            try:
                # 1. Limpiar tipos de datos
                oferta_limpia = self._limpiar_tipos_datos(oferta)

                # 2. Calcular su ID único basado en negocio
                doc_id = self._generar_id_unico(oferta_limpia)

                # 3. Guardar o sobreescribir en Firestore (Upsert)
                self.db.collection(self.coleccion).document(doc_id).set(oferta_limpia)

                titulo = oferta_limpia.get('puesto_titulo_original', 'Puesto sin título')
                logs.append(f"✅ Cargado: {titulo}")
                exitos += 1
            except Exception as e:
                logs.append(f"❌ Error en oferta: {str(e)}")

        return exitos, logs