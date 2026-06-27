import pytest

from app.schemas.install import InstallBootstrapRequest


def test_install_bootstrap_username_normalization() -> None:
    payload = InstallBootstrapRequest(username="Admin", password="long-enough-password")
    assert payload.username == "admin"


def test_install_bootstrap_short_password_rejected() -> None:
    with pytest.raises(ValueError):
        InstallBootstrapRequest(username="admin", password="short")
