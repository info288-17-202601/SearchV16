# SearchV16

SearchV16 es un motor de búsqueda distribuido de alto rendimiento diseñado para entornos corporativos. El sistema permite la indexación y recuperación eficiente de grandes volúmenes de documentos mediante una arquitectura basada en Elasticsearch, ofreciendo búsquedas rápidas, escalabilidad y una interfaz web intuitiva.

## Componentes

* **Backend:** API REST desarrollada en FastAPI.
* **Frontend:** Interfaz web desarrollada con Astro.
* **Search Engine:** Elasticsearch 8.13.4.
* **Visualización:** Kibana 8.13.4.
* **Caché:** Redis.


# Instalación y ejecución

## Requisitos

* Docker
* Docker Compose
* Node.js 22 o superior
* npm

---

# 1. Levantar la infraestructura

Desde la raíz del proyecto ejecutar:

```bash
docker compose up -d --build
```

Este comando iniciará automáticamente:

* Elasticsearch (http://localhost:9200)
* Kibana (http://localhost:5601)
* Redis (puerto 6379)
* Backend FastAPI (http://localhost:8000)

La documentación interactiva de la API estará disponible en:

```
http://localhost:8000/docs
```

---

# 2. Poblar el índice de búsqueda

Antes de utilizar el buscador es necesario indexar los documentos.

```bash
cd backend

python pipeline_ingesta.py \
    --directorio ./Documentos \
    --credentials credentials.json \
    --folder-id 1fT3PKeERCtWcEYh1LO7nYcT3_USX9wsj \
    --es-host http://localhost:9200 \
    --es-index library
```

Este proceso descarga e indexa los documentos en Elasticsearch bajo el índice `library`.

---

# 3. Ejecutar el frontend

```bash
cd frontend

npm install

npm run dev
```

El frontend estará disponible en:

```
http://localhost:4321
```

---

# Resumen

```text
1. docker compose up -d --build

2. cd backend
   python pipeline_ingesta.py \
       --directorio ./Documentos \
       --credentials credentials.json \
       --folder-id 1fT3PKeERCtWcEYh1LO7nYcT3_USX9wsj \
       --es-host http://localhost:9200 \
       --es-index library

3. cd frontend
   npm install
   npm run dev

4. Abrir http://localhost:4321
```
