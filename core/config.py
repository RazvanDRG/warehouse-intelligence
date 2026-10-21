from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://wi@localhost:5433/wi"
    redis_url: str = "redis://localhost:6379/0"
    readiness_timeout_seconds: float = 2.0
