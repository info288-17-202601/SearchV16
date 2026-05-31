# SearchV16 Backend API

API REST en FastAPI que conecta con Elasticsearch para búsquedas distribuidas de documentos.

## Requisitos

- Python 3.8+
- Elasticsearch 8.13.x ejecutándose en `http://localhost:9200`
- pip (gestor de dependencias Python)

## Instalación

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Iniciar Elasticsearch (si no está corriendo)

**Primera vez:**
```bash
docker run --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.13.4
```

**Inicios posteriores:**
```bash
docker start elasticsearch
```

**Detener:**
```bash
docker stop elasticsearch
```

## Ejecutar la API

### Modo desarrollo (con recarga automática)

```bash
python main.py
```

O usando uvicorn directamente:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Modo producción

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Documentación Interactiva

Una vez que el servidor esté ejecutándose, accede a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints disponibles

### 1. Raíz
```
GET /
```
Información de la API.

### 2. Health Check
```
GET /health
```
Verifica el estado de la API y la conexión con Elasticsearch.

**Respuesta:**
```json
{
  "status": "ok",
  "elasticsearch": "conectado",
  "api": "activa"
}
```

### 3. Búsqueda Básica (POST)
```
POST /search
```

**Body (JSON):**
```json
{
  "query": "distributed systems",
  "size": 20,
  "fields": ["title", "content"],
  "highlight": true
}
```

### 4. Búsqueda Básica (GET)
```
GET /search?query=distributed+systems&size=10&highlight=true
```

### 5. Búsqueda Avanzada
```
GET /search/advanced?query=consensus&author=Tanenbaum&size=15
```

## Ejemplos de uso

### Con curl

```bash
# GET - búsqueda simple
curl "http://localhost:8000/search?query=distributed%20systems&size=10"

# POST - búsqueda avanzada
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "consensus algorithm",
    "size": 20,
    "highlight": true,
    "fields": ["title", "content", "author"]
  }'

# Health check
curl "http://localhost:8000/health"
```

### Con Python (requests)

```python
import requests

url = "http://localhost:8000/search"
payload = {
    "query": "blockchain",
    "size": 10,
    "highlight": True
}

response = requests.post(url, json=payload)
results = response.json()

for result in results["results"]:
    print(f"Título: {result['title']}")
    print(f"Score: {result['score']}")
    print(f"---")
```

### Con JavaScript/Fetch (desde Astro)

```javascript
async function search(query) {
  const response = await fetch('http://localhost:8000/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      size: 10,
      highlight: true
    })
  });

  const data = await response.json();
  return data.results;
}

// Uso
const results = await search('distributed systems');
console.log(results);
```

## Estructura de respuesta

```json
{
  "total": 150,
  "count": 10,
  "query": "distributed systems",
  "took_ms": 45,
  "results": [
    {
      "id": "doc_1",
      "title": "Distributed Systems: Principles and Paradigms",
      "content": "A comprehensive guide to distributed systems...",
      "score": 9.5,
      "highlight": {
        "content": [
          "A guide to <mark>distributed systems</mark>..."
        ]
      },
      "source": {
        "title": "Distributed Systems: Principles and Paradigms",
        "author": "Tanenbaum",
        "year": 2017,
        "content": "Full document content..."
      }
    }
  ]
}
```

## Archivos

- `main.py` - Aplicación FastAPI principal
- `models.py` - Modelos Pydantic para validación
- `search.py` - Lógica de búsqueda Elasticsearch
- `busqueda.py` - Scrips de búsqueda original (legacy)
- `requirements.txt` - Dependencias Python

## Configuración

Edita `main.py` para cambiar:
- Puerto de la API (línea ~260)
- Host de Elasticsearch (línea ~11)
- Índice por defecto (línea ~12)
- Configuración de CORS (línea ~38)

## Troubleshooting

### "Elasticsearch no está disponible"
Asegúrate de que Elasticsearch esté corriendo:
```bash
curl http://localhost:9200
```

### Error de CORS
El API está configurado para aceptar requests desde:
- `http://localhost:3000` (Astro dev)
- `http://localhost:4321` (Astro dev alternativo)
- Cualquier origen (producción: cambiar a origens específicos)

### Búsqueda sin resultados
- Verifica que el índice "library" exista en Elasticsearch
- Comprueba el formato de los documentos

## Conectar con Astro

En tu componente Astro:

```astro
---
interface SearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
  highlight?: Record<string, string[]>;
}

let results: SearchResult[] = [];
let query = '';

async function handleSearch(searchQuery: string) {
  const response = await fetch('http://localhost:8000/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: searchQuery,
      size: 20,
      highlight: true
    })
  });
  
  const data = await response.json();
  results = data.results;
}
---

<div>
  <input 
    type="text" 
    placeholder="Buscar..."
    on:keyup={(e) => {
      query = e.target.value;
      if (query.length > 2) handleSearch(query);
    }}
  />
  
  {results.map(result => (
    <div>
      <h3>{result.title}</h3>
      <p>{result.content.substring(0, 200)}...</p>
      <small>Score: {result.score.toFixed(2)}</small>
    </div>
  ))}
</div>
```

## Licencia

Este proyecto es parte de SearchV16 - Motor de búsqueda distribuido.
