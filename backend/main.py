from starlette import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional, List

from models import SearchRequest, SearchResponse, SearchResult
from search import ElasticsearchSearch

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar cliente de Elasticsearch globalmente
es_client: Optional[ElasticsearchSearch] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación
    Inicializa conexión con Elasticsearch al startup
    """
    global es_client
    logger.info("Iniciando aplicación...")
    es_client = ElasticsearchSearch(
        host="http://localhost:9200",
        index="library"
    )
    
    if not es_client.is_connected():
        logger.warning("Advertencia: No se pudo conectar con Elasticsearch")
    else:
        logger.info("Elasticsearch conectado exitosamente")
    
    yield
    
    logger.info("Cerrando aplicación...")


# Crear aplicación FastAPI
app = FastAPI(
    title="SearchV16 API",
    description="API de búsqueda distribuida con Elasticsearch",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS para permitir solicitudes desde Astro
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Astro dev server
        "http://localhost:4321",      # Astro dev server (puerto alternativo)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4321",
        "*"  # Permitir desde cualquier origen (cambiar en producción)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Endpoint raíz - verifica estado de la API"""
    return {
        "mensaje": "SearchV16 API",
        "versión": "1.0.0",
        "descripción": "Motor de búsqueda distribuido con Elasticsearch"
    }


@app.get("/health", tags=["Health"])
async def health():
    """
    Verifica el estado de salud de la API y Elasticsearch
    """
    es_status = "conectado" if (es_client and es_client.is_connected()) else "desconectado"
    
    return {
        "status": "ok" if es_status == "conectado" else "error",
        "elasticsearch": es_status,
        "api": "activa"
    }


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest) -> SearchResponse:
    """
    Realiza una búsqueda en Elasticsearch
    
    **Parámetros:**
    - **query**: Término de búsqueda (requerido)
    - **size**: Número de resultados (1-100, default: 10)
    - **fields**: Campos en los que buscar (default: ["title", "content"])
    - **highlight**: Incluir resaltado de coincidencias (default: True)
    
    **Ejemplo:**
    ```json
    {
        "query": "distributed systems",
        "size": 20,
        page=1,
        "fields": ["title", "content"],
        "highlight": true
    }
    ```
    """
    if not es_client or not es_client.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Elasticsearch no está disponible. Verifique que esté ejecutándose."
        )
    
    try:
        # Realizar búsqueda en Elasticsearch
        response = es_client.search(
            query=request.query,
            fields=request.fields,
            size=request.size,
            page=request.page,
            highlight=request.highlight
        )
        
        # Procesar resultados
        results = []
        for hit in response["hits"]["hits"]:
            result = SearchResult(
                id=hit["_id"],
                title=hit["_source"].get("title", "Sin título"),
                content=hit["_source"].get("content", ""),
                score=hit["_score"],
                highlight=hit.get("highlight", None),
                google_drive_link=hit["_source"].get("google_drive_link"),
                source=hit["_source"]
            )
            results.append(result)
        
        # Crear respuesta
        return SearchResponse(
            total=response["hits"]["total"]["value"],
            count=len(results),
            results=results,
            query=request.query,
            took_ms=response["took"]
        )
    
    except Exception as e:
        logger.error(f"Error en búsqueda: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al realizar la búsqueda: {str(e)}"
        )


@app.get("/search", response_model=SearchResponse, tags=["Search"])
async def search_get(
    query: str = Query(None, min_length=1, max_length=500, description="Término de búsqueda"),
    q: str = Query(None, min_length=1, max_length=500, description="Alias para query"),
    size: int = Query(10, ge=1, le=100, description="Número de resultados"),
    page: int = Query(1, ge=1, description="Número de página"),
    highlight: bool = Query(True, description="Incluir highlights"),
) -> SearchResponse:
    """
    Realiza una búsqueda en Elasticsearch (GET)
    
    **Parámetros query:**
    - **query** o **q**: Término de búsqueda (requerido)
    - **size**: Número de resultados (1-100, default: 10)
    - **highlight**: Incluir resaltado (default: true)
    
    **Ejemplos:**
    - `GET /search?query=distributed%20systems&size=20&highlight=true`
    - `GET /search?q=blockchain&size=10`
    """
    # Aceptar tanto 'query' como 'q'
    search_query = query or q
    
    if not search_query:
        raise HTTPException(
            status_code=400,
            detail="Se requiere parámetro 'query' o 'q'"
        )
    
    request = SearchRequest(
        query=search_query,
        size=size,
        page=page,
        highlight=highlight
    )
    return await search(request)


@app.post("/search/advanced", response_model=SearchResponse, tags=["Search"])
async def search_advanced(
    query: str = Query(..., description="Término de búsqueda"),
    author: Optional[str] = Query(None, description="Filtrar por autor"),
    size: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1, description="Número de página"),
    fields: Optional[List[str]] = Query(None, description="Campos a buscar")
) -> SearchResponse:
    """
    Búsqueda avanzada con filtros adicionales
    
    **Parámetros:**
    - **query**: Término de búsqueda
    - **author**: Filtrar resultados por autor (opcional)
    - **size**: Número de resultados
    - **fields**: Campos a buscar
    
    **Ejemplo:**
    `GET /search/advanced?query=consensus&author=Tanenbaum&size=15`
    """
    if not es_client or not es_client.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Elasticsearch no está disponible"
        )
    
    if fields is None:
        fields = ["title", "content"]
    
    filters = {}
    if author:
        filters["author"] = author
    
    try:
        response = es_client.search_with_filter(
            query=query,
            filters=filters if filters else None,
            fields=fields,
            size=size,
            page=page,
            highlight=True,
        )
        
        results = []
        for hit in response["hits"]["hits"]:
            result = SearchResult(
                id=hit["_id"],
                title=hit["_source"].get("title", "Sin título"),
                content=hit["_source"].get("content", ""),
                score=hit["_score"],
                highlight=hit.get("highlight", None),
                google_drive_link=hit["_source"].get("google_drive_link"),
                source=hit["_source"]
            )
            results.append(result)
        
        return SearchResponse(
            total=response["hits"]["total"]["value"],
            count=len(results),
            results=results,
            query=query,
            took_ms=response["took"]
        )
    
    except Exception as e:
        logger.error(f"Error en búsqueda avanzada: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


@app.get("/document/{document_id}", tags=["Documents"])
async def get_document(document_id: str) -> dict:
    """
    Obtiene los detalles de un documento específico, incluyendo el enlace de descarga
    
    **Parámetros:**
    - **document_id**: ID del documento (file_hash)
    
    **Ejemplo:**
    `GET /document/abc123def456`
    """
    if not es_client or not es_client.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Elasticsearch no está disponible"
        )
    
    try:
        # Obtener documento por su ID (file_hash)
        response = es_client.es.get(index="library", id=document_id)
        source = response["_source"]
        
        return {
            "id": document_id,
            "title": source.get("title", "Sin título"),
            "content": source.get("content", ""),
            "google_drive_link": source.get("google_drive_link"),
            "file_extension": source.get("file_extension"),
            "upload_date": source.get("upload_date"),
            "source": source
        }
    except Exception as e:
        logger.error(f"Error al obtener documento: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Documento no encontrado: {document_id}"
        )


@app.get("/download/{document_id}", tags=["Documents"])
async def download_document(document_id: str):
    """
    Obtiene el enlace de descarga de un documento desde Google Drive
    
    **Parámetros:**
    - **document_id**: ID del documento (file_hash)
    
    **Ejemplo:**
    `GET /download/abc123def456`
    """
    if not es_client or not es_client.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Elasticsearch no está disponible"
        )
    
    try:
        response = es_client.es.get(index="library", id=document_id)
        source = response["_source"]
        google_drive_link = source.get("google_drive_link")
        
        if not google_drive_link:
            raise HTTPException(
                status_code=404,
                detail="Este documento no tiene enlace de descarga disponible"
            )
        
        return {
            "download_url": google_drive_link,
            "title": source.get("title"),
            "file_extension": source.get("file_extension")
        }
    except Exception as e:
        logger.error(f"Error al obtener enlace de descarga: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Documento no encontrado: {document_id}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
