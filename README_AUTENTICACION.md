# Documentación de Autenticación y Seguridad (SearchV16)

Este documento detalla todas las implementaciones, modificaciones y adiciones realizadas en el proyecto **SearchV16** para incorporar el sistema de autenticación de usuarios y la pantalla de inicio de sesión.

---

## 🏗️ Arquitectura y Flujo de Seguridad

La autenticación está diseñada bajo un esquema **Stateful/Cookie-based** con validación mediante **JSON Web Tokens (JWT)**:

```
[ Frontend: Astro ]
       │
   (Petición HTTP con Credentials)
       │
       ▼
[ Backend: FastAPI ] ──► [ Middleware / get_current_user ]
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
       [ Validar JWT Cookie ]       [ Consultar SQLite (users.db) ]
```

1.  **Inicio de Sesión e Inicio de Cuenta (Registro)**: El frontend se comunica con el backend mediante llamadas asíncronas de origen cruzado (CORS).
2.  **Protección de Rutas (Frontend)**: Cada página del frontend que herede de [Layout.astro](file:///home/edubn/Documentos/wash/sisDis/SearchV16/frontend/src/layouts/Layout.astro) verifica en segundo plano el endpoint `/api/auth/me` con el backend. Si el usuario no está autenticado (retorna `401`), es redirigido automáticamente a `/login`.
3.  **Protección de Endpoints (Backend)**: Todos los endpoints sensibles de Elasticsearch y de descargas requieren el token JWT mediante inyección de dependencias en FastAPI (`Depends(get_current_user)`).

---

## 🗄️ ¿Dónde se guardan los usuarios? (SQLite vs Elasticsearch)

Los usuarios del sistema se almacenan localmente en una base de datos relacional **SQLite** (`backend/users.db`). 

### ¿Por qué SQLite y no Elasticsearch?
Decidimos utilizar SQLite para las cuentas de usuario por las siguientes razones de diseño y arquitectura:
1.  **Separación de Conceptos (Separation of Concerns)**: Mantiene los datos transaccionales y de seguridad de los usuarios completamente separados de los índices de documentos y búsquedas en Elasticsearch.
2.  **Garantía ACID (Transaccional)**: SQLite ofrece transacciones ACID reales. Las operaciones de registro de usuarios e inicio de sesión requieren consistencia inmediata y cero pérdida de datos, lo cual es nativo en bases de datos relacionales.
3.  **Integridad y Simplicidad**: Las operaciones de control de accesos no se benefician de la búsqueda difusa (fuzzy search) ni del scoring de Elasticsearch. SQLite proporciona consultas rápidas, seguras y estructuradas sin añadir dependencias ni recursos adicionales al servidor.

---

## 🛠️ Archivos Creados y Modificados

### 1. Backend

*   **[NUEVO] [backend/auth.py](file:///home/edubn/Documentos/wash/sisDis/SearchV16/backend/auth.py)**:
    *   Lógica de inicialización y conexión a la base de datos de usuarios (`users.db` en SQLite).
    *   Hashing de contraseñas con sal usando **bcrypt**.
    *   Creación, verificación y expiración de tokens **JWT** (usando la firma `HS256` y `pyjwt`).
    *   Función [get_current_user](file:///home/edubn/Documentos/wash/sisDis/SearchV16/backend/auth.py#L136) inyectable para proteger rutas en FastAPI.
*   **[MODIFICADO] [backend/models.py](file:///home/edubn/Documentos/wash/sisDis/SearchV16/backend/models.py)**:
    *   Añadidos los esquemas de validación de datos Pydantic: `LoginRequest` (usuario y contraseña) y `UserRegisterRequest` (usuario, contraseña y nombre completo).
*   **[MODIFICADO] [backend/main.py](file:///home/edubn/Documentos/wash/sisDis/SearchV16/backend/main.py)**:
    *   Se agregó la inicialización automática de la base de datos de usuarios SQLite en el arranque (`lifespan`).
    *   Se expusieron los endpoints HTTP:
        *   `POST /api/auth/register`: Registrar nuevos usuarios.
        *   `POST /api/auth/login`: Autentica credenciales, crea el token JWT y lo inyecta en una cookie `HttpOnly`.
        *   `POST /api/auth/logout`: Elimina la cookie de sesión.
        *   `GET /api/auth/me`: Retorna los detalles del usuario autenticado actual.
    *   Se protegieron las rutas del buscador (`/search` POST/GET, `/search/advanced`, `/document/{id}`, `/download/{id}`) agregándoles la dependencia de autenticación.
*   **[MODIFICADO] [backend/requirements.txt](file:///home/edubn/Documentos/wash/sisDis/SearchV16/backend/requirements.txt)**:
    *   Se agregaron las librerías `pyjwt>=2.10.1` (segura contra falsificación de firmas y ataques micro-arquitectónicos) y `bcrypt>=4.0.0` para hashing de contraseñas.
    *   Se actualizó `python-docx>=1.1.2` (segura contra vulnerabilidades de inyección de entidades externas XML/XXE).


### 2. Frontend

*   **[MODIFICADO] [frontend/src/pages/login.astro](file:///home/edubn/Documentos/wash/sisDis/SearchV16/frontend/src/pages/login.astro)**:
    *   Pantalla de inicio de sesión con diseño premium (gradientes modernos en verde/azul, animaciones y transiciones de entrada).
    *   **Registro Integrado**: Se implementó una interfaz interactiva de pestañas/toggles. Ahora el usuario puede alternar instantáneamente entre la pantalla de **Iniciar Sesión** y la pantalla de **Registrarse (Crear Cuenta)** dentro de la misma tarjeta con transiciones suaves.
    *   El formulario de registro valida la contraseña (mínimo 6 caracteres), envía los datos al endpoint de registro y, si el registro es exitoso, realiza un auto-inicio de sesión para redirigir al usuario al buscador de inmediato.
*   **[MODIFICADO] [frontend/src/layouts/Layout.astro](file:///home/edubn/Documentos/wash/sisDis/SearchV16/frontend/src/layouts/Layout.astro)**:
    *   Se inyectó un script de protección global que valida si el usuario tiene una sesión activa (excepto en la propia página `/login`).
    *   Se agregó dinámicamente un **Badge de Usuario** flotante en la parte superior derecha (`👤 [Nombre de Usuario]`) con un botón para **Cerrar Sesión (Salir)**.
*   **[MODIFICADO] [frontend/src/lib/searchClient.ts](file:///home/edubn/Documentos/wash/sisDis/SearchV16/frontend/src/lib/searchClient.ts) e [index.astro](file:///home/edubn/Documentos/wash/sisDis/SearchV16/frontend/src/pages/index.astro)**:
    *   Se actualizó la configuración de todas las consultas fetch añadiendo `credentials: 'include'` para que los navegadores envíen y reciban la cookie del JWT.

---

## 🔑 Credenciales por Defecto

Al arrancar la aplicación por primera vez, el backend detecta que la base de datos SQLite está vacía e inicializa un usuario administrador por defecto para pruebas rápidas:

*   **Nombre de usuario**: `admin`
*   **Contraseña**: `admin123`

---

## 🚀 Guía de Ejecución

Para iniciar el proyecto completo con el nuevo sistema de seguridad:

1.  **Ejecutar Elasticsearch (Docker)**:
    ```bash
    docker start elasticsearch
    ```
2.  **Ejecutar Backend (FastAPI)**:
    ```bash
    cd backend
    python main.py
    ```
    *La base de datos SQLite `users.db` se creará y sembrará automáticamente al iniciar el servidor.*
3.  **Ejecutar Frontend (Astro)**:
    ```bash
    cd frontend
    npm run dev
    ```
    *   Visita `http://localhost:4321` en tu navegador.
    *   Serás redirigido a `/login` para autenticarte.
    *   Puedes usar el usuario por defecto (`admin` / `admin123`) o hacer clic en **"¿No tienes cuenta? Regístrate aquí"** para crear tu propia cuenta. Al registrarte exitosamente, iniciarás sesión de inmediato.
