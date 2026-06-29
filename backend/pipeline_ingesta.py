"""
pipeline_ingesta.py
===================
Pipeline de ingesta, deduplicación, respaldo en Google Drive e indexación
en Elasticsearch para documentos locales.

Extensiones soportadas: .txt, .md, .pdf, .docx

Uso:
    python pipeline_ingesta.py --directorio ./mis_documentos \
                               --credentials credentials.json \
                               --folder-id <GOOGLE_DRIVE_FOLDER_ID> \
                               --es-host http://localhost:9200 \
                               --es-index documentos_busqueda

Ejemplo: 
    python pipeline_ingesta.py --directorio ./Documentos --credentials credentials.json --folder-id 1fT3PKeERCtWcEYh1LO7nYcT3_USX9wsj --es-host http://192.168.1.15:9200 --es-index documentos_busqueda
    

Requisitos (instalar antes de ejecutar):
    pip install google-api-python-client google-auth \
                elasticsearch pypdf python-docx
"""

import argparse
import hashlib
import logging
import os
import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Google Drive ──────────────────────────────────────────────────────────────
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ── Elasticsearch ─────────────────────────────────────────────────────────────
from elasticsearch import Elasticsearch, ConnectionError as ESConnectionError
from elasticsearch.helpers import bulk

# ── Extracción de texto ───────────────────────────────────────────────────────
import pypdf                          # PDFs
from docx import Document as DocxDoc  # DOCX

ELASTICSEARCH_ACTIVO = True

NUMERO_SHARDS = int(os.getenv("ELASTIC_PRIMARY_SHARDS", "2"))
NUMERO_REPLICAS = int(os.getenv("ELASTIC_REPLICAS", "2"))

SALIDA_JSON_DIR = Path("./documentos_indexados")
SCOPES = ["https://www.googleapis.com/auth/drive"]


# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline_ingesta.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# =============================================================================
# EXTENSIONES SOPORTADAS
# =============================================================================

EXTENSIONES_SOPORTADAS = {".txt", ".md", ".pdf", ".docx"}


# =============================================================================
# MÓDULO DE HASHING  ──  Deduplicación
# =============================================================================

def calcular_hash(ruta_archivo: Path) -> str:
    """
    Calcula el hash SHA-256 del contenido binario de un archivo.

    Se lee en bloques de 8 KB para no cargar archivos grandes en memoria.

    Args:
        ruta_archivo: Ruta absoluta o relativa al archivo.

    Returns:
        Cadena hexadecimal del digest SHA-256 (64 caracteres).

    Raises:
        OSError: Si el archivo no se puede abrir o leer.
    """
    sha256 = hashlib.sha256()
    with open(ruta_archivo, "rb") as fh:
        for bloque in iter(lambda: fh.read(8192), b""):
            sha256.update(bloque)
    return sha256.hexdigest()


# =============================================================================
# MÓDULO DE EXTRACCIÓN DE TEXTO
# =============================================================================

def extraer_texto(ruta_archivo: Path) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extrae el contenido textual y metadatos (si aplica) de un archivo.
    Returns:
        Tupla con (texto_extraido, author, publication_date)
    """
    ext = ruta_archivo.suffix.lower()

    try:
        if ext in (".txt", ".md"):
            return _extraer_texto_plano(ruta_archivo), None, None
        elif ext == ".pdf":
            # Esta ya devuelve la tupla de 3 elementos
            return _extraer_texto_pdf(ruta_archivo)
        elif ext == ".docx":
            return _extraer_texto_docx(ruta_archivo), None, None
        else:
            log.warning("Extensión no soportada para extracción: %s", ext)
            return None, None, None

    except Exception as exc:  # pylint: disable=broad-except
        log.error("Error al extraer texto de '%s': %s", ruta_archivo.name, exc)
        return None, None, None


def _extraer_texto_plano(ruta: Path) -> str:
    """Lee archivos .txt y .md con UTF-8; hace fallback a latin-1."""
    try:
        return ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        log.warning("UTF-8 falló para '%s', reintentando con latin-1.", ruta.name)
        return ruta.read_text(encoding="latin-1")


def _extraer_texto_pdf(ruta: Path) -> tuple[str, Optional[str], Optional[str]]:
    """Extrae texto, author y publication_date de un PDF usando pypdf."""
    partes: list[str] = []
    author = None
    publication_date = None
    
    with open(ruta, "rb") as fh:
        lector = pypdf.PdfReader(fh)
        if lector.is_encrypted:
            raise ValueError("El PDF está encriptado y no se puede leer.")
        
        # ── Extraer Metadatos de Forma Segura ──
        if lector.metadata:
            meta = lector.metadata
            
            # Procesar Autor
            author_raw = meta.get('/Author')
            if author_raw:
                # Si es un IndirectObject (puntero), llamamos a getObject(), si no, lo usamos directo
                if hasattr(author_raw, 'getObject'):
                    author = str(author_raw.getObject()).strip()
                else:
                    author = str(author_raw).strip()
            
            # Procesar Fecha de Creación
            publication_date_raw = meta.get('/CreationDate') or meta.get('/ModDate')
            if publication_date_raw:
                if hasattr(publication_date_raw, 'getObject'):
                    publication_date = str(publication_date_raw.getObject()).strip()
                else:
                    publication_date = str(publication_date_raw).strip()

        # Si aún resolviendo el diccionario da vacío, buscamos en XMP por seguridad
        if not author and lector.xmp_metadata:
            xmp = lector.xmp_metadata
            if xmp.dc_creator and len(xmp.dc_creator) > 0:
                author = str(xmp.dc_creator[0]).strip()

        # ── Extraer Texto ──
        for num_pag, pagina in enumerate(lector.pages, start=1):
            texto_pag = pagina.extract_text() or ""
            if texto_pag.strip():
                partes.append(texto_pag)
            else:
                log.debug("Página %d sin texto extraíble en '%s'.", num_pag, ruta.name)
                
    return "\n".join(partes), author if author else None, publication_date if publication_date else None


def _extraer_texto_docx(ruta: Path) -> str:
    """Extrae texto de cada párrafo de un documento DOCX."""
    doc = DocxDoc(str(ruta))
    parrafos = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(parrafos)

def limpiar_texto(texto: str) -> str:
    """
    Normaliza el texto extraído eliminando ruido de formato.
    
    Transformaciones aplicadas:
      - Elimina \n, \t, \r y otros caracteres de control
      - Reemplaza múltiples espacios por uno solo
      - Elimina espacios al inicio y final
    """
    # Eliminar caracteres de control excepto \n (tabs, retorno de carro, etc.)
    texto = re.sub(r'[\n\t\r\x0b\x0c]', ' ', texto)
    
    # Colapsar múltiples espacios en uno
    texto = re.sub(r' {2,}', ' ', texto)
    
    # Eliminar espacios al inicio/final de cada línea
    texto = '\n'.join(line.strip() for line in texto.splitlines())
    
    return texto.strip()


# =============================================================================
# MÓDULO DE GOOGLE DRIVE
# =============================================================================

def construir_servicio_drive(ruta_credentials: str):
    """
    Autentica con Google Drive v3 usando OAuth con cuenta personal.

    - Primera ejecución: abre el navegador para que apruebes los permisos.
      Guarda el token en 'token.json' para las siguientes ejecuciones.
    - Ejecuciones siguientes: usa 'token.json' directamente, sin navegador.

    Args:
        ruta_credentials: Ruta al credentials.json descargado de Google Cloud.

    Returns:
        Objeto de servicio de Google Drive listo para usar.
    """
    creds = None
    token_path = "token.json"

    # Si ya existe un token guardado, cargarlo
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Si no hay token válido, iniciar el flujo OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expirado pero renovable automáticamente
            creds.refresh(Request())
            log.info("Token de OAuth renovado automáticamente.")
        else:
            # Primera vez: abre el navegador
            flow = InstalledAppFlow.from_client_secrets_file(
                ruta_credentials, SCOPES
            )
            creds = flow.run_local_server(port=0)
            log.info("Autenticación OAuth completada exitosamente.")

        # Guardar el token para la próxima ejecución
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
        log.info("Token guardado en '%s'.", token_path)

    servicio = build("drive", "v3", credentials=creds, cache_discovery=False)
    log.info("Servicio de Google Drive inicializado correctamente.")
    return servicio


def subir_drive(
    servicio,
    ruta_archivo: Path,
    folder_id: str,
) -> Optional[str]:
    """
    Sube un archivo a Google Drive dentro de la carpeta indicada.

    Tras la subida, solicita el campo 'webViewLink' para obtener el enlace
    público de visualización del archivo.

    Args:
        servicio   : Servicio autenticado de Google Drive.
        ruta_archivo: Ruta local al archivo que se subirá.
        folder_id  : ID de la carpeta destino en Google Drive.

    Returns:
        URL de 'webViewLink' como string, o None si la subida falló.
    """
    metadatos = {
        "name": ruta_archivo.name,
        "parents": [folder_id],
    }

    try:
        media = MediaFileUpload(
            str(ruta_archivo),
            resumable=True,         # Soporta archivos grandes con subida reanudable
        )

        archivo_drive = (
            servicio.files()
            .create(
                body=metadatos,
                media_body=media,
                fields="id, webViewLink",  # Solo pedimos lo que necesitamos
            )
            .execute()
        )

        enlace = archivo_drive.get("webViewLink")
        log.info(
            "Archivo subido a Drive: '%s'  →  %s",
            ruta_archivo.name,
            enlace,
        )
        return enlace

    except Exception as exc:  # pylint: disable=broad-except
        log.error("Fallo al subir '%s' a Google Drive: %s", ruta_archivo.name, exc)
        return None


# =============================================================================
# MÓDULO DE ELASTICSEARCH
# =============================================================================

def construir_cliente_es(host: str) -> Elasticsearch:
    """
    Construye y valida la conexión al cliente de Elasticsearch.

    Args:
        host: URL del clúster, p.ej. 'http://localhost:9200'.

    Returns:
        Instancia de Elasticsearch conectada.

    Raises:
        ESConnectionError: Si no se puede establecer conexión.
    """
    cliente = Elasticsearch(
        [host],
        request_timeout=60,      # ← sube de 10s (default) a 60s
        retry_on_timeout=True,   # ← reintenta automáticamente si hay timeout
        max_retries=3,
    )
    if not cliente.ping():
        raise ESConnectionError(f"No se pudo conectar a Elasticsearch en: {host}")
    log.info("Conexión a Elasticsearch establecida en %s", host)
    return cliente

def crear_indice_elasticsearch(cliente: Elasticsearch, indice: str) -> None:
    """
    Crea el índice de Elasticsearch si aún no existe.

    Se inicializa con el número de shards y réplicas definidos en variables
    de entorno y con mappings básicos para los campos usados por la búsqueda.

    Args:
        cliente: Cliente de Elasticsearch.
        indice : Nombre del índice a crear.
    """
    try:
        if cliente.indices.exists(index=indice):
            log.info("Índice '%s' ya existe. Se reutilizará.", indice)
            return



        cliente.indices.create(
            index=indice,
            settings={
                "number_of_shards": NUMERO_SHARDS,
                "number_of_replicas": NUMERO_REPLICAS,
            },
            mappings={
                "properties": {
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "author": {"type": "keyword"},
                    "publication_date": {"type": "keyword"},
                    "file_hash": {"type": "keyword", "index": True},
                    "file_extension": {"type": "keyword", "index": False},
                    "google_drive_link": {"type": "keyword", "index": False},
                    "upload_date": {"type": "date", "index": False},
                }
            },
        )
        log.info(
            "Índice '%s' creado con %d shard(s) y %d réplica(s).",
            indice,
            NUMERO_SHARDS,
            NUMERO_REPLICAS,
        )

    except Exception as exc:  # pylint: disable=broad-except
        log.warning("No se pudo crear el índice '%s': %s", indice, exc)


def indexar_elasticsearch(
    cliente: Elasticsearch,
    indice: str,
    documento: dict,
) -> bool:
    """
    Indexa un documento en Elasticsearch.

    Utiliza el 'file_hash' como ID del documento para evitar duplicados
    a nivel de índice (idempotencia en reindexaciones).

    Args:
        cliente   : Cliente de Elasticsearch.
        indice    : Nombre del índice destino.
        documento : Diccionario con los campos del documento a indexar.

    Returns:
        True si la indexación fue exitosa, False en caso contrario.
    """
    try:
        respuesta = cliente.index(
            index=indice,
            id=documento["file_hash"],   # Hash como ID → evita duplicados en ES
            document=documento,
        )
        resultado = respuesta.get("result", "unknown")
        log.info(
            "Indexado en ES [%s]: '%s'  (resultado: %s)",
            indice,
            documento["file_name"],
            resultado,
        )
        return True

    except Exception as exc:  # pylint: disable=broad-except
        log.error(
            "Error al indexar '%s' en Elasticsearch: %s",
            documento.get("file_name"),
            exc,
        )
        return False


# =============================================================================
# CONSULTA DE HASHES PREVIOS EN ELASTICSEARCH
# =============================================================================

def cargar_hashes_procesados(cliente: Elasticsearch, indice: str) -> set[str]:
    """
    Recupera todos los hashes ya indexados en Elasticsearch para
    inicializar el registro de control anti-duplicados.

    Usa la API scroll para índices con más de 10.000 documentos.

    Args:
        cliente: Cliente de Elasticsearch.
        indice : Nombre del índice a consultar.

    Returns:
        Set con todos los valores de 'file_hash' encontrados.
        Devuelve un set vacío si el índice no existe o no hay documentos.
    """
    hashes: set[str] = set()

    try:
        if not cliente.indices.exists(index=indice):
            log.info("Índice '%s' no existe aún. Se iniciará vacío.", indice)
            return hashes

        # Primera página
        respuesta = cliente.search(
            index=indice,
            body={"_source": ["file_hash"], "query": {"match_all": {}}},
            scroll="2m",
            size=1000,
        )

        scroll_id = respuesta["_scroll_id"]
        hits = respuesta["hits"]["hits"]

        while hits:
            for doc in hits:
                h = doc.get("_source", {}).get("file_hash")
                if h:
                    hashes.add(h)

            # Siguiente página
            respuesta = cliente.scroll(scroll_id=scroll_id, scroll="2m")
            scroll_id = respuesta["_scroll_id"]
            hits = respuesta["hits"]["hits"]

        # Liberar contexto de scroll
        cliente.clear_scroll(scroll_id=scroll_id)

        log.info(
            "Cargados %d hashes previos desde el índice '%s'.",
            len(hashes),
            indice,
        )

    except Exception as exc:  # pylint: disable=broad-except
        log.warning(
            "No se pudieron cargar hashes previos de ES (%s). "
            "Se usará solo el registro en memoria.",
            exc,
        )

    return hashes


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def procesar_directorio(
    directorio: str,
    ruta_credentials: str,
    folder_id: str,
    es_host: str,
    es_index: str,
) -> None:
    """
    Orquesta el pipeline completo para todos los archivos del directorio.

    Flujo por archivo:
        1. Filtrar por extensión soportada.
        2. Calcular hash SHA-256.
        3. Deduplicación (memoria + ES).
        4. Subir a Google Drive → obtener webViewLink.
        5. Extraer texto.
        6. Construir documento JSON.
        7. Indexar en Elasticsearch.
        8. Registrar hash como procesado.

    Args:
        directorio       : Ruta al directorio local con los documentos.
        ruta_credentials : Ruta al credentials.json de la Cuenta de Servicio.
        folder_id        : ID de la carpeta destino en Google Drive.
        es_host          : URL del clúster Elasticsearch.
        es_index         : Nombre del índice Elasticsearch.
    """
    # ── Validación del directorio ─────────────────────────────────────────────
    ruta_dir = Path(directorio).resolve()
    if not ruta_dir.is_dir():
        log.critical("El directorio '%s' no existe o no es accesible.", ruta_dir)
        sys.exit(1)

    # ── Inicializar servicios ─────────────────────────────────────────────────
    try:
        servicio_drive = construir_servicio_drive(ruta_credentials)
    except Exception as exc:  # pylint: disable=broad-except
        log.critical("Error al inicializar Google Drive: %s", exc)
        sys.exit(1)

    if ELASTICSEARCH_ACTIVO:
        try:
            cliente_es = construir_cliente_es(es_host)
            crear_indice_elasticsearch(cliente_es, es_index)
        except ESConnectionError as exc:
            log.critical("Error al conectar con Elasticsearch: %s", exc)
            sys.exit(1)

    # ── Registro anti-duplicados ──────────────────────────────────────────────
    # Inicializado con los hashes ya presentes en ES para tolerar reinicios.
    if ELASTICSEARCH_ACTIVO:
        hashes_procesados: set[str] = cargar_hashes_procesados(cliente_es, es_index)

    # ── Contadores de métricas ────────────────────────────────────────────────
    total = procesados = omitidos = errores = 0
    documentos_pendientes: list[dict] = []
    TAMAÑO_LOTE = 50

    log.info("=" * 60)
    log.info("Iniciando pipeline en: %s", ruta_dir)
    log.info("=" * 60)

    # ── Iteración sobre archivos ──────────────────────────────────────────────
    for archivo in sorted(ruta_dir.iterdir()):
        if not archivo.is_file():
            continue  

        total += 1
        ext = archivo.suffix.lower()

        # 1. Filtrar extensiones
        if ext not in EXTENSIONES_SOPORTADAS:
            log.debug("Ignorado (extensión no soportada): %s", archivo.name)
            continue

        log.info("── Procesando: %s", archivo.name)

        # 2. Calcular hash
        try:
            file_hash = calcular_hash(archivo)
        except OSError as exc:
            log.error("No se pudo leer el archivo '%s': %s", archivo.name, exc)
            errores += 1
            continue

        # 3. Deduplicación
        if ELASTICSEARCH_ACTIVO:
            if file_hash in hashes_procesados:
                log.info("   DUPLICADO — omitido: %s  (hash: %s…)", archivo.name, file_hash[:12])
                omitidos += 1
                continue

        # 4. Subir a Google Drive
        enlace_drive = subir_drive(servicio_drive, archivo, folder_id)
        if enlace_drive is None:
            log.error(
                "   FALLO en Drive — archivo '%s' no indexado para mantener consistencia.",
                archivo.name,
            )
            errores += 1
            continue  # No indexar si no hay enlace → evitar inconsistencia

        # 5. Extraer texto y metadatos
        texto, author_doc, publication_date_doc = extraer_texto(archivo)
        
        texto = limpiar_texto(texto) if texto else None
        if texto is None:
            texto = ""
            log.warning(
                "   Extracción de texto fallida para '%s'. Se indexará con texto vacío.",
                archivo.name,
            )

        # 6. Construir documento JSON
        documentos_pendientes.append({
            "title"            : archivo.name,
            "file_extension"   : ext,
            "file_hash"        : file_hash,
            "google_drive_link": enlace_drive,
            "content"          : texto,
            "upload_date"      : datetime.now(tz=timezone.utc).isoformat(),
            "author"            : author_doc,
            "publication_date": publication_date_doc,
        })

        # Marcar hash como procesado inmediatamente para deduplicar
        # dentro de la misma ejecución
        hashes_procesados.add(file_hash)

        total_lotes = -(-len(documentos_pendientes) // TAMAÑO_LOTE) or 0  # ceil

    log.info("=" * 60)

    if not documentos_pendientes:
        log.info("No hay documentos nuevos para indexar.")
    else:
        for i in range(0, len(documentos_pendientes), TAMAÑO_LOTE):
            lote = documentos_pendientes[i : i + TAMAÑO_LOTE]
            numero_lote = (i // TAMAÑO_LOTE) + 1

            log.info("   Lote %d/%d — %d documentos...", numero_lote, total_lotes, len(lote))

            # ── Guardado local en .txt (temporal hasta conectar ES) ───────────────
            if ELASTICSEARCH_ACTIVO:
                operaciones = [
                    {"_index": es_index, "_id": doc["file_hash"], "_source": doc}
                    for doc in lote
                ]
                try:
                    exitos, fallos = bulk(cliente_es, operaciones, raise_on_error=False)
                    procesados += exitos
                    errores += len(fallos)
                    for fallo in fallos:
                        log.error("   Fallo ES: %s", fallo)
                    log.info("   ✓ Lote %d/%d — %d indexados, %d fallos.",
                            numero_lote, total_lotes, exitos, len(fallos))
                except Exception as exc:
                    log.error("   Error en lote %d: %s", numero_lote, exc)
                    errores += len(lote)
            else:
                errores_lote = 0
                for doc in lote:
                    ruta_salida = SALIDA_JSON_DIR / f"{Path(doc['file_name']).stem}_{doc['file_hash'][:8]}.txt"
                    try:
                        ruta_salida.write_text(
                            json.dumps(doc, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                        procesados += 1
                    except OSError as exc:
                        log.error("   Error guardando '%s': %s", doc["file_name"], exc)
                        errores_lote += 1
                        errores += 1

                log.info("   ✓ Lote %d/%d completado — %d ok, %d errores.",
                        numero_lote, total_lotes, len(lote) - errores_lote, errores_lote)



    # ── Resumen final ─────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("Pipeline finalizado.")
    log.info("  Total archivos encontrados : %d", total)
    log.info("  Procesados exitosamente    : %d", procesados)
    log.info("  Omitidos por duplicado     : %d", omitidos)
    log.info("  Errores                    : %d", errores)
    log.info("=" * 60)


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

def main() -> None:
    """Parsea los argumentos de línea de comandos y lanza el pipeline."""
    parser = argparse.ArgumentParser(
        description="Pipeline de ingesta: Drive + Elasticsearch",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--directorio",
        required=True,
        help="Ruta al directorio local con los documentos a procesar.",
    )
    parser.add_argument(
        "--credentials",
        default="credentials.json",
        help="Ruta al archivo credentials.json de la Cuenta de Servicio de Google.",
    )
    parser.add_argument(
        "--folder-id",
        required=True,
        help="ID de la carpeta destino en Google Drive.",
    )
    parser.add_argument(
        "--es-host",
        default="http://localhost:9200",
        help="URL del clúster de Elasticsearch.",
    )
    parser.add_argument(
        "--es-index",
        default="documentos_busqueda",
        help="Nombre del índice de Elasticsearch.",
    )

    args = parser.parse_args()

    procesar_directorio(
        directorio=args.directorio,
        ruta_credentials=args.credentials,
        folder_id=args.folder_id,
        es_host=args.es_host,
        es_index=args.es_index,
    )


if __name__ == "__main__":
    main()


