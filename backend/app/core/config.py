# Application settings.
# Loaded from environment variables / .env via pydantic-settings.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "CareerPilot AI"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # PostgreSQL connection string used by the SQLAlchemy engine.
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/careerpilot"

    # JWT settings. SECRET_KEY is required (no default) so a missing secret fails
    # fast at startup rather than silently signing tokens with a known key.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Single shared settings instance imported across the app.
settings = Settings()
