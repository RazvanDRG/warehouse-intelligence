from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # An explicit DATABASE_URL wins; otherwise the URL is built from the parts, which encodes any password safely.
    database_url: str = ""
    postgres_user: str = "wi"
    postgres_password: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "wi"
    redis_url: str = "redis://localhost:6379/0"
    readiness_timeout_seconds: float = 2.0

    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password or None,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)
