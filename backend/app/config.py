from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@db:5432/music"
    secret_key: str = "change-me-to-a-random-string-at-least-32-chars"
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    music_path: str = "/music"
    log_level: str = "info"
    audio_cache_ttl: int = 3600
    access_token_expire_minutes: int = 1440  # 24 hours
    default_language: str = "zh-CN"
    jwt_algorithm: str = "HS256"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
