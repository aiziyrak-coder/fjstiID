import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_secret(value: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return hash_secret(value) == hashed


def generate_token(n: int = 32) -> str:
    return secrets.token_urlsafe(n)


def create_access_token(subject: str, extra: dict[str, Any] | None = None, minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return None


def _fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        # derive from secret for dev
        digest = hashlib.sha256(settings.secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    elif len(key) != 44:
        digest = hashlib.sha256(key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_bytes(data: bytes) -> str:
    return _fernet().encrypt(data).decode()


def decrypt_bytes(token: str) -> bytes:
    return _fernet().decrypt(token.encode())
