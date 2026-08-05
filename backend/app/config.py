from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FJSTI ID"
    app_env: str = "development"
    secret_key: str = "change-me"
    encryption_key: str = ""
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    face_match_threshold: float = 0.45
    face_provider: str = "insightface"
    database_url: str = "postgresql+asyncpg://fjsti:fjsti_secret@localhost:5432/fjsti_id"
    database_url_sync: str = "postgresql+psycopg://fjsti:fjsti_secret@localhost:55432/fjsti_id"
    cors_origins: str = "http://localhost:5173"
    admin_email: str = "admin@fjsti.uz"
    admin_password: str = "Admin123!"
    admin_full_name: str = "Tizim Administratori"
    oidc_issuer: str = "http://localhost:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
