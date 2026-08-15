from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://kaname:kaname@localhost:5432/kaname"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    allowed_emails_raw: str = Field(default="kasaubunts@gmail.com", alias="ALLOWED_EMAILS")

    session_secret_key: str = "change-me"
    session_cookie_name: str = "kaname_session"
    session_max_age_seconds: int = 14 * 24 * 60 * 60

    frontend_origin: str = "https://kaname.ajesta.work"
    cookie_domain: str | None = ".ajesta.work"
    cookie_secure: bool = True

    @property
    def allowed_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_emails_raw.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
