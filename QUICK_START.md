# 🚀 SearchV16 - Quick Start Guide

## Setup Inicial (5 minutos)

### 1️⃣ Elasticsearch

**Inicia Elasticsearch en Docker:**

```bash
# Primera vez
docker run --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.13.4

# Siguientes veces
docker start elasticsearch

# Para detener
docker stop elasticsearch
```

**Verifica que esté activo:**
```bash
curl http://localhost:9200
```

### 2️⃣ Backend (FastAPI)

```bash
cd backend

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python main.py
```

✅ **Backend disponible:** http://localhost:8000
📚 **Documentación:** http://localhost:8000/docs

### 3️⃣ Frontend (Astro)

```bash
cd frontend

# Instalar dependencias
npm install

# Ejecutar servidor
npm run dev
```

✅ **Frontend disponible:** http://localhost:3000 o http://localhost:4321

---

## Endpoints principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado de la API |
| POST | `/search` | Búsqueda (JSON body) |
| GET | `/search?query=...` | Búsqueda rápida |
| GET | `/search/advanced?query=...&author=...` | Búsqueda con filtros |

### Ejemplos de uso

**GET - Búsqueda simple:**
```bash
curl "http://localhost:8000/search?query=distributed+systems&size=10"
```

**POST - Búsqueda avanzada:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "blockchain consensus",
    "size": 20,
    "highlight": true,
    "fields": ["title", "content"]
  }'
```

**Health check:**
```bash
curl "http://localhost:8000/health"
```

---

## Estructura de respuesta

```json
{
  "total": 150,
  "count": 10,
  "query": "blockchain",
  "took_ms": 32,
  "results": [
    {
      "id": "doc_1",
      "title": "Blockchain Fundamentals",
      "content": "Distributed ledger technology...",
      "score": 9.8,
      "highlight": {
        "content": ["<mark>Blockchain</mark> is a distributed..."]
      },
      "source": {
        "author": "Satoshi Nakamoto",
        "year": 2008
      }
    }
  ]
}
```

---

## Estructura del Proyecto

```
SearchV16/
├── backend/
│   ├── main.py              ← API FastAPI
│   ├── models.py            ← Validación Pydantic
│   ├── search.py            ← Lógica Elasticsearch
│   ├── requirements.txt      ← Dependencias Python
│   ├── run_server.bat       ← Script Windows
│   └── README.md            ← Documentación
│
├── frontend/
│   ├── src/
│   │   ├── components/SearchComponent.astro
│   │   ├── lib/searchClient.ts
│   │   ├── pages/index.astro
│   │   └── styles/
│   ├── package.json         ← Dependencias Node
│   └── README.md            ← Documentación
│
└── README.md                ← Este proyecto
```

---

## 🔧 Troubleshooting

### ❌ "Connection refused"
**Elasticsearch no está corriendo**
```bash
docker ps  # Ver contenedores activos
docker start elasticsearch
```

### ❌ Error CORS en frontend
**Asegúrate que el puerto esté en CORS del backend**
```python
# backend/main.py - línea ~38
allow_origins=[
    "http://localhost:3000",      ← Añade aquí si falta
    "http://localhost:4321",
    ...
]
```

### ❌ "Cannot import searchClient"
**Verifica la ruta en el componente**
```astro
import SearchClient from '../lib/searchClient';  ← Ruta correcta
```

### ❌ Búsqueda sin resultados
- Verifica que el índice "library" exista en Elasticsearch
- Comprueba que haya documentos indexados
- Usa Kibana: http://localhost:5601 (opcional)

---

## 📚 Recursos

- 📖 [Backend API Docs](./backend/README.md)
- 📖 [Frontend Docs](./frontend/README.md)
- 🔗 [FastAPI Documentación](https://fastapi.tiangolo.com/)
- 🔗 [Elasticsearch Documentación](https://www.elastic.co/guide/en/elasticsearch/reference/current/)
- 🔗 [Astro Documentación](https://docs.astro.build/)

---

## 🎯 Flujo de búsqueda

```
┌─────────────────────────────────────────────────────────┐
│                  USUARIO (Astro)                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Escribe: "blockchain"
                       ↓
┌─────────────────────────────────────────────────────────┐
│            FRONTEND (SearchComponent)                    │
│  - Input validation                                      │
│  - Debounce (300ms)                                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ POST /search
                       │ { query: "blockchain", ... }
                       ↓
┌─────────────────────────────────────────────────────────┐
│             API (FastAPI)                               │
│  - Validar con Pydantic                                  │
│  - Construir query Elasticsearch                         │
│  - Agregar highlights                                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Query Elasticsearch
                       ↓
┌─────────────────────────────────────────────────────────┐
│          ELASTICSEARCH                                   │
│  - Multi-match search                                    │
│  - Fuzzy matching                                        │
│  - Scoring                                               │
│  - Highlights                                            │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Resultados
                       ↓
┌─────────────────────────────────────────────────────────┐
│             API (FastAPI)                               │
│  - Procesar resultados                                   │
│  - Formatear JSON                                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Response JSON
                       ↓
┌─────────────────────────────────────────────────────────┐
│            FRONTEND (SearchComponent)                    │
│  - Mostrar resultados                                    │
│  - Renderizar highlights                                 │
│  - Mostrar scores                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 💡 Tips

- Usa `?query=...` para búsquedas rápidas en GET
- Usa POST para búsquedas complejas con más opciones
- El debounce en el frontend evita exceso de requests
- Los highlights muestran donde se encontró el término
- El score indica relevancia (0-10)

---

## 📝 Notas

- Desarrollado para Python 3.8+, Node.js 18+
- Compatible con Windows, Linux, macOS
- Base de datos: Elasticsearch 8.13.4
- Framework backend: FastAPI 0.110.0
- Framework frontend: Astro
