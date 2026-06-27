from app.services.secrets import decrypt_secret, encrypt_secret


def test_encrypt_decrypt_roundtrip(monkeypatch) -> None:
    monkeypatch.setenv("COGITO_REVIEW_SECRETS_ENCRYPTION_KEY", "test-key-for-fernet")
    monkeypatch.setenv("COGITO_REVIEW_SESSION_SECRET", "session-fallback")
    from app.config import get_code_review_settings

    get_code_review_settings.cache_clear()

    original = "super-secret-value"
    encrypted = encrypt_secret(original)
    assert encrypted != original
    assert decrypt_secret(encrypted) == original

    get_code_review_settings.cache_clear()
