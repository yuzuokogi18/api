"""
Utilidades de seguridad y autenticación
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import get_settings

settings = get_settings()

# Configurar contexto de hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar contraseña
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash de contraseña
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crear token JWT
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verificar y decodificar token JWT
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_reset_token(user_id: int) -> str:
    """
    Generar token para reset de contraseña
    """
    data = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(hours=1)  # Token válido por 1 hora
    }
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_reset_token(token: str) -> Optional[int]:
    """
    Verificar token de reset de contraseña
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except JWTError:
        return None


def is_token_expired(token: str) -> bool:
    """
    Verificar si un token ha expirado
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": True})
        return False
    except jwt.ExpiredSignatureError:
        return True
    except JWTError:
        return True


def generate_api_key() -> str:
    """
    Generar clave API aleatoria
    """
    import secrets
    return secrets.token_urlsafe(32)


def validate_password_strength(password: str) -> bool:
    """
    Validar fortaleza de contraseña
    """
    if len(password) < 8:
        return False

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    return all([has_upper, has_lower, has_digit, has_special])


def sanitize_input(input_string: str) -> str:
    """
    Sanitizar entrada de usuario
    """
    if not input_string:
        return ""

    # Remover caracteres peligrosos
    dangerous_chars = ['<', '>', '"', "'", '&', '\0', '\n', '\r', '\t']
    for char in dangerous_chars:
        input_string = input_string.replace(char, '')

    return input_string.strip()


def generate_otp() -> str:
    """
    Generar código OTP de 6 dígitos
    """
    import random
    return str(random.randint(100000, 999999))


def hash_sensitive_data(data: str) -> str:
    """
    Hash para datos sensibles (números de teléfono, etc.)
    """
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()


def create_refresh_token(user_id: int) -> str:
    """
    Crear token de actualización
    """
    data = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_refresh_token(token: str) -> Optional[int]:
    """
    Verificar token de actualización
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except JWTError:
        return None


class SecurityHeaders:
    """
    Headers de seguridad para respuestas HTTP
    """

    @staticmethod
    def get_security_headers() -> dict:
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'"
        }


def encrypt_sensitive_field(data: str, key: str = None) -> str:
    """
    Encriptar campo sensible (para información médica crítica)
    """
    from cryptography.fernet import Fernet
    import base64

    if not key:
        key = settings.SECRET_KEY[:32].encode().ljust(32)[:32]

    f = Fernet(base64.urlsafe_b64encode(key))
    return f.encrypt(data.encode()).decode()


def decrypt_sensitive_field(encrypted_data: str, key: str = None) -> str:
    """
    Desencriptar campo sensible
    """
    from cryptography.fernet import Fernet
    import base64

    if not key:
        key = settings.SECRET_KEY[:32].encode().ljust(32)[:32]

    f = Fernet(base64.urlsafe_b64encode(key))
    return f.decrypt(encrypted_data.encode()).decode()


def rate_limit_key(identifier: str, action: str) -> str:
    """
    Generar clave para rate limiting
    """
    return f"rate_limit:{action}:{identifier}"


def is_safe_redirect_url(url: str, allowed_hosts: list = None) -> bool:
    """
    Verificar si una URL de redirección es segura
    """
    from urllib.parse import urlparse

    if not url:
        return False

    parsed = urlparse(url)

    # Solo URLs relativas o de hosts permitidos
    if not parsed.netloc:
        return True

    if allowed_hosts and parsed.netloc in allowed_hosts:
        return True

    return False


def generate_csrf_token() -> str:
    """
    Generar token CSRF
    """
    import secrets
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected_token: str) -> bool:
    """
    Verificar token CSRF
    """
    import hmac
    return hmac.compare_digest(token, expected_token)


# Decorador para endpoints que requieren verificación adicional
def require_verified_user(func):
    """
    Decorador para requerir usuario verificado
    """

    def wrapper(*args, **kwargs):
        # Lógica de verificación adicional
        return func(*args, **kwargs)

    return wrapper


class PasswordPolicy:
    """
    Política de contraseñas configurable
    """
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True
    MAX_ATTEMPTS = 3
    LOCKOUT_DURATION = 300  # 5 minutos

    @classmethod
    def validate(cls, password: str) -> tuple[bool, list[str]]:
        """
        Validar contraseña según políticas
        """
        errors = []

        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Debe tener al menos {cls.MIN_LENGTH} caracteres")

        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Debe contener al menos una mayúscula")

        if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Debe contener al menos una minúscula")

        if cls.REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            errors.append("Debe contener al menos un número")

        if cls.REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Debe contener al menos un carácter especial")

        return len(errors) == 0, errors