from elasticsearch import Elasticsearch
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ElasticsearchSearch:
    """Cliente de búsqueda para Elasticsearch"""
    
    def __init__(self, host: str = "http://localhost:9200", index: str = "library"):
        """
        Inicializa el cliente de Elasticsearch
        
        Args:
            host: URL de Elasticsearch (default: localhost:9200)
            index: Índice a usar para búsquedas (default: library)
        """
        self.host = host
        self.index = index
        try:
            self.es = Elasticsearch(host)
            # Verificar conexión
            self.es.info()
            logger.info(f"Conectado a Elasticsearch en {host}")
        except Exception as e:
            logger.error(f"Error al conectar con Elasticsearch: {e}")
            self.es = None
    
    def is_connected(self) -> bool:
        """Verifica si el cliente está conectado"""
        if not self.es:
            return False
        try:
            self.es.info()
            return True
        except:
            return False
    
    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        size: int = 10,
        page: int = 1,
        highlight: bool = True,
    ) -> Dict[str, Any]:
        """
        Realiza una búsqueda en Elasticsearch
        
        Args:
            query: Término de búsqueda
            fields: Campos en los que buscar (default: title, content)
            size: Número máximo de resultados
            highlight: Si incluir highlights
            
        Returns:
            Diccionario con resultados
        """
        if not self.es:
            raise Exception("Elasticsearch no está conectado")
        
        if fields is None:
            fields = ["title", "content"]
        
        # Construcción de la query
        es_query = {
            "multi_match": {
                "query": query,
                "fields": fields,
                "fuzziness": "AUTO"  # Permite errores tipográficos
            }
        }
        
        # Parámetros de búsqueda
        from_offset = (page - 1) * size
        search_params = {
            "index": self.index,
            "query": es_query,
            "size": size,
            "from_": from_offset,
            "_source": True  # Retornar documento completo
        }
        
        if highlight:
            search_params["highlight"] = {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],

                "fields": {
                    "title": {},

                    "content": {
                        "fragment_size": 250,
                        "number_of_fragments": 2,
                        "max_analyzed_offset": 500000
                    }
                }
            }
        
        try:
            response = self.es.search(**search_params)
            return response
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            raise
    
    def search_with_filter(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        size: int = 10,
        page: int = 1,
        highlight: bool = True,
    ) -> Dict[str, Any]:
        """
        Realiza búsqueda con filtros adicionales
        
        Args:
            query: Término de búsqueda
            filters: Diccionario de filtros {campo: valor}
            fields: Campos en los que buscar
            size: Número máximo de resultados
            highlight: Si incluir highlights
            
        Returns:
            Diccionario con resultados
        """
        if not self.es:
            raise Exception("Elasticsearch no está conectado")
        
        if fields is None:
            fields = ["title", "content"]
        
        # Query con bool para combinar must y filter
        es_query = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": fields,
                            "fuzziness": "AUTO"
                        }
                    }
                ]
            }
        }
        
        # Agregar filtros si existen
        if filters:
            es_query["bool"]["filter"] = [
                {"term": {f"{k}.keyword": v}} for k, v in filters.items()
            ]

        from_offset = (page - 1) * size
        search_params = {
            "index": self.index,
            "query": es_query,
            "size": size,
            "from_": from_offset,
            "_source": True
        }
        
        if highlight:
            search_params["highlight"] = {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],

                "fields": {
                    "title": {},

                    "content": {
                        "fragment_size": 250,
                        "number_of_fragments": 2,
                        "max_analyzed_offset": 500000
                    }
                }
            }
        
        try:
            response = self.es.search(**search_params)
            return response
        except Exception as e:
            logger.error(f"Error en búsqueda con filtros: {e}")
            raise
