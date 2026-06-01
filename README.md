# SearchV16

SearchV16 es un motor de búsqueda distribuido de alto rendimiento diseñado para entornos corporativos. El sistema permite la indexación y recuperación eficiente de grandes volúmenes de documentos mediante una arquitectura de cuatro capas, garantizando seguridad a nivel de documento y alta disponibilidad.

**Componentes:**
- **Backend**: API REST en FastAPI con Elasticsearch
- **Frontend**: Interfaz en Astro con buscador interactivo
- **Search Engine**: Elasticsearch 8.13.4 para búsquedas distribuidas

---

## Quick Start

### 1. Iniciar Elasticsearch

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

### 2. Instalar y ejecutar Backend (FastAPI)

```bash
cd backend

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python main.py
# O en PowerShell: .\run_server.ps1
```

El servidor estará disponible en `http://localhost:8000`
- Documentación interactiva: http://localhost:8000/docs
- API base: http://localhost:8000/api

### 3. Instalar y ejecutar Frontend (Astro)

```bash
cd frontend

# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev
```

El frontend estará disponible en `http://localhost:3000` o `http://localhost:4321`

---

## Estructura del Proyecto

```
SearchV16/
├── backend/
│   ├── main.py              # API FastAPI
│   ├── models.py            # Modelos Pydantic
│   ├── search.py            # Lógica Elasticsearch
│   ├── requirements.txt      # Dependencias Python
│   ├── README.md            # Documentación backend
│   ├── run_server.bat       # Script de ejecución Windows
│   ├── run_server.ps1       # Script de ejecución PowerShell
│   └── .env.example         # Configuración de ejemplo
│
├── frontend/
│   ├── src/
│   │   ├── pages/          # Páginas Astro
│   │   ├── components/     # Componentes reutilizables
│   │   ├── layouts/        # Layouts
│   │   └── styles/         # Estilos CSS
│   ├── package.json         # Dependencias Node.js
│   ├── astro.config.mjs     # Configuración Astro
│   └── README.md            # Documentación frontend
│
└── README.md               # Este archivo
```

---

## API Endpoints

### `/search` (POST)
Búsqueda básica con query
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "distributed systems",
    "size": 10,
    "highlight": true
  }'
```

### `/search` (GET)
Búsqueda rápida por parámetros
```bash
curl "http://localhost:8000/search?query=blockchain&size=10&highlight=true"
```

### `/search/advanced` (GET)
Búsqueda avanzada con filtros
```bash
curl "http://localhost:8000/search/advanced?query=consensus&author=Tanenbaum&size=15"
```

### `/health`
Verificar estado de la API y Elasticsearch
```bash
curl "http://localhost:8000/health"
```

---

## Flujo de Búsqueda

```
[Astro Frontend]
       ↓
   (Fetch POST)
       ↓
  [FastAPI API]
   - Validar query con Pydantic
   - Construir query Elasticsearch
   - Highlights de resultados
       ↓
  [Elasticsearch]
   - Búsqueda multi-match
   - Fuzzy matching (tolerancia a errores)
   - Scoring y ranking
       ↓
   [FastAPI API]
   - Procesar resultados
   - Formatear response JSON
       ↓
  [Astro Frontend]
   - Mostrar resultados
   - Highlights
   - Scores
```

---

## Desarrollo

### Backend (Python)

**Endpoints disponibles:**
- `GET /` - Información de la API
- `GET /health` - Estado de salud
- `POST /search` - Búsqueda básica
- `GET /search` - Búsqueda por parámetros
- `GET /search/advanced` - Búsqueda con filtros

**Modelos:**
- `SearchRequest` - Validación de solicitudes
- `SearchResult` - Resultado individual
- `SearchResponse` - Respuesta completa

**Agregar nuevos filtros:**
Edita `search.py` en la función `search_with_filter()` para soportar más filtros.

### Frontend (Astro)

**Componentes:**
- Buscador principal en `src/components/`
- Resultados en `src/components/`

**Conectar con API:**
```javascript
const response = await fetch('http://localhost:8000/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: searchTerm,
    size: 20,
    highlight: true
  })
});
```

---

## Configuración

Edita `backend/.env` para cambiar:
- `ELASTICSEARCH_HOST` - URL de Elasticsearch
- `ELASTICSEARCH_INDEX` - Índice a usar
- `API_PORT` - Puerto del servidor
- `CORS_ORIGINS` - Orígenes permitidos


## Tecnologías

- **Backend**: FastAPI, Uvicorn, Pydantic
- **Search Engine**: Elasticsearch 8.13.4
- **Frontend**: Astro, TypeScript
- **Deployment**: Docker

---

## Documentación Adicional

- [Backend README](./backend/README.md) - Documentación detallada de la API
- [Elasticsearch Docs](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Astro Docs](https://docs.astro.build/)