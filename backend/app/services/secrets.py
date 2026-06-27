import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_code_review_settings


def _fernet_key() -> bytes:
    settings = get_code_review_settings()
    raw = settings.secrets_encryption_key.strip() or settings.session_secret
    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return Fernet(_fernet_key()).encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return Fernet(_fernet_key()).decrypt(value.encode()).decode()
    except InvalidToken as exc:
        msg = "failed to decrypt secret"
        raise ValueError(msg) from exc
