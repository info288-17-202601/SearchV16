from elasticsearch import Elasticsearch
from typing import Dict, Any, Optional, List
import logging
import time

logger = logging.getLogger(__name__)


class ElasticsearchSearch:
    """Cliente de búsqueda para Elasticsearch"""
    
    def __init__(self, host: str = "http://elasticsearch:9200", index: str = "library"):
        self.host = host
        self.index = index
        self.es = None
        self._connect_with_retry()

    def _connect_with_retry(self, retries=15, delay=3):
        for i in range(retries):
            try:
                es = Elasticsearch(self.host)
                es.info()  # health check
                self.es = es
                print(f"Connected to Elasticsearch ({self.host})")
                return
            except Exception as e:
                print(f"ES not ready (attempt {i+1}/{retries}): {e}")
                time.sleep(delay)

        raise Exception("Elasticsearch no disponible después de varios intentos")
    
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
        size: int = 50,
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
        search_params = {
            "index": self.index,
            "query": es_query,
            "size": size,
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
        size: int = 50,
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
        
        search_params = {
            "index": self.index,
            "query": es_query,
            "size": size,
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
