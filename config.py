import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI", "")
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379")
    JWT_SECRET: str = os.environ.get("JWT_SECRET") or os.environ.get("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_EXPIRY_HOURS: int = int(os.environ.get("JWT_EXPIRY_HOURS", "2"))
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.environ.get("GOOGLE_REDIRECT_URI") or os.environ.get("GOOGLE_CALLBACK_URI", "")
    LLM_TIMEOUT_SECONDS: int = int(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
    SWAGGER_USERNAME: str = os.environ.get("SWAGGER_USERNAME", "")
    SWAGGER_PASSWORD: str = os.environ.get("SWAGGER_PASSWORD", "")
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    PHOENIX_ENDPOINT: str = os.environ.get("PHOENIX_ENDPOINT", "http://phoenix:6006/v1/traces")
    REFRESH_INTERVAL_DAYS: int = int(os.environ.get("REFRESH_INTERVAL_DAYS", "7"))
    TAG_SIMILARITY_THRESHOLD: float = float(os.environ.get("TAG_SIMILARITY_THRESHOLD", "0.88"))
    INGEST_SECRET: str = os.environ.get("INGEST_SECRET", "")
    SENTRY_DSN: str = os.environ.get("SENTRY_DSN", "")
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "production")


settings = Config()
