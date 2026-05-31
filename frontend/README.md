# SearchV16 Frontend - Astro

Interfaz web moderna para SearchV16, construida con Astro y TypeScript.

## Requisitos

- Node.js 18+ 
- npm o yarn
- Backend FastAPI ejecutándose en \http://localhost:8000\

## Instalación

\\\ash
npm install
\\\

## Desarrollo

\\\ash
npm run dev
\\\

El servidor de desarrollo estará disponible en \http://localhost:3000\ o \http://localhost:4321\

## Quick Start

1. **Inicia Elasticsearch:**
   \\\ash
   docker start elasticsearch
   \\\

2. **Inicia el backend FastAPI:**
   \\\ash
   cd ../backend
   python main.py
   \\\

3. **Inicia el frontend:**
   \\\ash
   npm install
   npm run dev
   \\\

## Estructura del Proyecto

\\\
src/
├── components/
│   ├── SearchComponent.astro      # Componente de búsqueda reutilizable
│   └── ...otros componentes
│
├── lib/
│   └── searchClient.ts            # Cliente para API FastAPI
│
├── layouts/
│   └── Layout.astro               # Layout base
│
├── pages/
│   ├── index.astro                # Página principal
│   └── ...otras páginas
│
└── styles/
    └── ...archivos de estilo
\\\

## Uso del Componente SearchComponent

\\\stro
---
import SearchComponent from '../components/SearchComponent.astro';
---

<main>
  <SearchComponent 
    placeholder="Buscar documentos..." 
    maxResults={20} 
    minChars={2}
  />
</main>
\\\

## Troubleshooting

### "Failed to fetch from API"
- Verifica que el backend esté corriendo en \http://localhost:8000\
- Revisa la consola del navegador (F12) para CORS errors

### Resultados vacíos
- Verifica que Elasticsearch esté corriendo
- Comprueba que el índice "library" exista con datos

## Más información

Revisa \../backend/README.md\ para documentación de la API completa.
