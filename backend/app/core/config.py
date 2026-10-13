from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "CLAIM LAGOS"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change_me_in_production_to_a_long_random_string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql+asyncpg://claim:claim_secret_change_me@localhost:5432/claim_lagos"
    REDIS_URL: str = "redis://localhost:6379/0"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "claimminio"
    MINIO_SECRET_KEY: str = "claimminio_secret_change_me"
    MINIO_BUCKET: str = "claim-assets"
    MINIO_SECURE: bool = False

    # Platform placeholders
    X_BEARER_TOKEN: str = ""
    META_ACCESS_TOKEN: str = ""
    YOUTUBE_API_KEY: str = ""
    TIKTOK_ACCESS_TOKEN: str = ""

    LLM_PROVIDER: str = "local"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen2.5:7b-instruct-q4_K_M"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
