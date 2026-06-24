from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://app:app@localhost:5432/app?sslmode=disable"
    cors_origins: list[str] = ["http://localhost:5173"]
    static_dir: str = "/app/static"
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
