from pydantic import BaseModel, Field
from typing import Optional, List, Any


class SearchRequest(BaseModel):
    """Modelo para recibir solicitudes de búsqueda"""
    query: str = Field(..., min_length=1, max_length=500, description="Término de búsqueda")
    size: Optional[int] = Field(default=10, ge=1, le=100, description="Número de resultados")
    fields: Optional[List[str]] = Field(
        default=["title", "content"],
        description="Campos en los que buscar"
    )
    highlight: Optional[bool] = Field(
        default=True,
        description="Incluir highlight de coincidencias"
    )


class SearchResult(BaseModel):
    """Modelo para un resultado de búsqueda individual"""
    id: str
    title: str
    content: str
    score: float
    highlight: Optional[dict] = None
    google_drive_link: Optional[str] = Field(None, description="Enlace de descarga en Google Drive")
    source: dict = Field(..., description="Documento original de Elasticsearch")


class SearchResponse(BaseModel):
    """Modelo para la respuesta de búsqueda"""
    total: int = Field(..., description="Número total de resultados encontrados")
    count: int = Field(..., description="Número de resultados retornados")
    results: List[SearchResult]
    query: str
    took_ms: int = Field(..., description="Tiempo de ejecución en milisegundos")
