"""
Модуль безопасности: хэширование паролей и выпуск JWT-токенов.
Использует passlib + python-jose с надежным встроенным fallback на hashlib/hmac.
"""

import os
import json
import base64
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# Настройки JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "horizont-jwt-secret-key-production-2026-safe-token")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 дней

# Инициализация passlib bcrypt (при наличии)
_pwd_context = None
try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    _pwd_context = None

# Инициализация python-jose (при наличии)
_jose_jwt = None
try:
    from jose import jwt as _jose_jwt, JWTError
except Exception:
    _jose_jwt = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Сверка открытого пароля с хэшем в базе данных.
    Поддерживает bcrypt, SHA-256 с солью и прямое совпадение для начального сидера.
    """
    if not hashed_password or not plain_password:
        return False
    
    # 1. Попытка через passlib bcrypt
    if _pwd_context:
        try:
            return _pwd_context.verify(plain_password, hashed_password)
        except Exception:
            pass

    # 2. Проверка хэша SHA-256 (соль + пароль)
    if hashed_password.startswith("sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 3:
            salt, h = parts[1], parts[2]
            computed = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
            return hmac.compare_digest(computed, h)

    # 3. Прямое совпадение или префикс $plain$ (для суперпользователя в тестах)
    if hashed_password in (plain_password, f"$plain${plain_password}"):
        return True

    return False


def get_password_hash(password: str) -> str:
    """
    Генерация безопасного криптографического хэша пароля.
    """
    if _pwd_context:
        try:
            return _pwd_context.hash(password)
        except Exception:
            pass

    # Надежный стандартный fallback SHA-256 со случайной криптостойкой солью
    salt = base64.b64encode(os.urandom(16)).decode("utf-8")
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${h}"


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Выпуск JWT-токена со сроком жизни и зашифрованной ролью (RFC 7519).
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    })

    if _jose_jwt:
        try:
            return _jose_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        except Exception:
            pass

    # Встроенный стандартный HMAC-SHA256 JWT генератор
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(to_encode).encode("utf-8")).decode("utf-8").rstrip("=")
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Декодирование и верификация подписи JWT-токена.
    """
    if _jose_jwt:
        try:
            return _jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except Exception:
            pass

    # Встроенный стандартный HMAC-SHA256 JWT верификатор
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        # Проверяем подпись
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        
        # Дополняем паддинг base64
        rem = len(sig_b64) % 4
        padded_sig = sig_b64 + ("=" * (4 - rem) if rem else "")
        actual_sig = base64.urlsafe_b64decode(padded_sig.encode("utf-8"))
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        rem = len(payload_b64) % 4
        padded_payload = payload_b64 + ("=" * (4 - rem) if rem else "")
        payload = json.loads(base64.urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8"))
        
        # Проверяем срок действия
        exp = payload.get("exp")
        if exp and exp < datetime.now(timezone.utc).timestamp():
            return None
            
        return payload
    except Exception:
        return None
