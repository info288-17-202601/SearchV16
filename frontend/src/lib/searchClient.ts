// Ejemplo de integración de búsqueda con la API FastAPI

/**
 * Cliente para la API de búsqueda SearchV16
 */
class SearchClient {
  private apiUrl: string;

  constructor(apiUrl: string = 'http://localhost:8000') {
    this.apiUrl = apiUrl;
  }

  /**
   * Realiza una búsqueda en la API
   * @param query - Término de búsqueda
   * @param size - Número de resultados (default: 10)
   * @param highlight - Incluir highlights (default: true)
   * @returns Promise con los resultados
   */
  async search(
    query: string,
    size: number = 10,
    highlight: boolean = true
  ) {
    try {
      const response = await fetch(`${this.apiUrl}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          size,
          highlight,
          fields: ['title', 'content', 'author'],
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error en búsqueda:', error);
      throw error;
    }
  }

  /**
   * Búsqueda avanzada con filtros
   * @param query - Término de búsqueda
   * @param author - Filtrar por autor (opcional)
   * @param size - Número de resultados
   * @returns Promise con los resultados filtrados
   */
  async searchAdvanced(
    query: string,
    author?: string,
    size: number = 10
  ) {
    try {
      const params = new URLSearchParams({
        query,
        size: size.toString(),
      });

      if (author) {
        params.append('author', author);
      }

      const response = await fetch(
        `${this.apiUrl}/search/advanced?${params}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error en búsqueda avanzada:', error);
      throw error;
    }
  }

  /**
   * Verifica el estado de la API y Elasticsearch
   */
  async health() {
    try {
      const response = await fetch(`${this.apiUrl}/health`);
      return await response.json();
    } catch (error) {
      console.error('Error al verificar salud:', error);
      return { status: 'error', elasticsearch: 'desconectado' };
    }
  }
}

export default SearchClient;
