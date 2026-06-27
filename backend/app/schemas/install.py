import re

from pydantic import BaseModel, Field, field_validator


class InstallStatusResponse(BaseModel):
    setup_required: bool


class InstallBootstrapRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=128)
    email: str | None = Field(default=None, max_length=256)
    name: str | None = Field(default=None, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,63}", normalized):
            msg = "username must be 3-64 chars: lowercase letters, digits, . _ -"
            raise ValueError(msg)
        return normalized


class LocalLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
