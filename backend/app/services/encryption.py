"""AES encryption/decryption for Square access tokens."""

import os
from cryptography.fernet import Fernet
from app.config import settings


def _get_key() -> bytes:
    key = settings.TOKEN_ENCRYPTION_KEY
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set in environment")
    return key.encode() if isinstance(key, str) else key


def encrypt_token(token: str) -> str:
    """Encrypt a Square access/refresh token before storing in DB."""
    f = Fernet(_get_key())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a token retrieved from DB for API calls."""
    f = Fernet(_get_key())
    return f.decrypt(encrypted.encode()).decode()
