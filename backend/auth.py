import os
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
import bcrypt
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger(__name__)

# Configuración de JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "searchv16_super_secret_key_2026_longer_32b")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 horas
COOKIE_NAME = "auth_token"

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# Iniciar esquema de OAuth2 (opcional para documentación y compatibilidad)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)



# =============================================================================
# MANEJO DE BASE DE DATOS (SQLite)
# =============================================================================

def get_db_connection():
    """Establece una conexión a la base de datos de usuarios"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea la tabla de usuarios y añade un usuario por defecto si no existen"""
    logger.info(f"Inicializando base de datos en {DB_PATH}")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fullname TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    conn.commit()

    # Verificar si ya hay usuarios
    cursor.execute("SELECT COUNT(*) as count FROM users")
    row = cursor.fetchone()
    if row["count"] == 0:
        logger.info("Base de datos vacía, creando usuario por defecto: admin / admin123")
        # Contraseña por defecto: admin123
        hashed = hash_password("admin123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, fullname, role) VALUES (?, ?, ?, ?)",
            ("admin", hashed, "Administrador de Búsquedas", "admin")
        )
        conn.commit()
    conn.close()


# =============================================================================
# HASHING DE CONTRASEÑAS
# =============================================================================

def hash_password(password: str) -> str:
    """Aplica hashing bcrypt a una contraseña de texto plano"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception as e:
        logger.error(f"Error al verificar contraseña: {e}")
        return False


# =============================================================================
# GENERACIÓN Y VERIFICACIÓN DE JWT
# =============================================================================

def create_access_token(data: dict) -> str:
    """Crea un token de acceso JWT firmado"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica y verifica la firma y expiración del JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("El token JWT ha expirado")
        return None
    except jwt.PyJWTError as e:
        logger.warning(f"Error de validación de JWT: {e}")
        return None


# =============================================================================
# OPERACIONES DE USUARIO
# =============================================================================

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Obtiene un usuario por su nombre de usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, fullname, role FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def register_user(username: str, password_clear: str, fullname: Optional[str] = None, role: str = "user") -> bool:
    """Registra un nuevo usuario en el sistema"""
    if get_user_by_username(username):
        return False
    
    hashed = hash_password(password_clear)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, fullname, role) VALUES (?, ?, ?, ?)",
            (username, hashed, fullname or username, role)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error al registrar usuario: {e}")
        return False
    finally:
        conn.close()


# =============================================================================
# DEPENDENCIAS DE SEGURIDAD PARA FASTAPI
# =============================================================================

async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependencia de FastAPI para obtener el usuario actual autenticado.
    Verifica el token JWT guardado en la cookie HttpOnly o en la cabecera Authorization.
    """
    token = None
    
    # 1. Intentar obtener de la Cookie (Método preferido en frontend)
    token = request.cookies.get(COOKIE_NAME)
    
    # 2. Intentar obtener del header de autorización si no está en la cookie
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Por favor inicie sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado. Inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido (sub missing).",
        )
        
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
        )
        
    # Retornar el usuario sin la contraseña hash por seguridad
    user.pop("password_hash", None)
    return user
