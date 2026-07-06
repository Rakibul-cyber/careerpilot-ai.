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

    # Background scheduler. Disabled by default so local/dev and test runs don't
    # spawn background jobs; enable explicitly via env in deployments.
    SCHEDULER_ENABLED: bool = False
    SCHEDULER_TIMEZONE: str = "Europe/Berlin"

    # Resume uploads. Files are stored on local disk under UPLOAD_DIR for now
    # (no S3 yet). MAX_RESUME_UPLOAD_MB caps a single resume's size.
    UPLOAD_DIR: str = "uploads"
    MAX_RESUME_UPLOAD_MB: int = 5

    # AI resume parsing (Anthropic Claude). ANTHROPIC_API_KEY is optional at
    # startup — the parser fails cleanly (parse_status=failed) if it's unset,
    # so the app still boots for everything else.
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-opus-4-8"
    AI_PARSER_MAX_TOKENS: int = 4096
    AI_COVER_LETTER_MAX_TOKENS: int = 2048
    AI_INTERVIEW_PREPARATION_MAX_TOKENS: int = 4096

    # Semantic search embeddings (OpenAI — Anthropic has no embeddings API).
    # Optional at startup; if unset, embedding ops fail cleanly (status=failed)
    # and semantic search returns a clean error. EMBEDDING_DIMENSIONS must match
    # app.models.job.JOB_EMBEDDING_DIM (1536 for text-embedding-3-small).
    OPENAI_API_KEY: str | None = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Single shared settings instance imported across the app.
settings = Settings()
