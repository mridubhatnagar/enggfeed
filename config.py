import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str = os.environ.get("DATABASE_URL") or os.environ.get(
        "DATABASE_URI", ""
    )
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379")
    LLM_TIMEOUT_SECONDS: int = int(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
    SWAGGER_USERNAME: str = os.environ.get("SWAGGER_USERNAME", "")
    SWAGGER_PASSWORD: str = os.environ.get("SWAGGER_PASSWORD", "")
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    PHOENIX_ENDPOINT: str = os.environ.get(
        "PHOENIX_ENDPOINT", "http://phoenix:6006/v1/traces"
    )
    TAG_SIMILARITY_THRESHOLD: float = float(
        os.environ.get("TAG_SIMILARITY_THRESHOLD", "0.88")
    )
    INGEST_SECRET: str = os.environ.get("INGEST_SECRET", "")
    SENTRY_DSN: str = os.environ.get("SENTRY_DSN", "")
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "production")
    LLM_MONTHLY_COST_ALERT_USD: float = float(
        os.environ.get("LLM_MONTHLY_COST_ALERT_USD", "10.00")
    )
    LLM_DAILY_COST_ALERT_USD: float = float(
        os.environ.get("LLM_DAILY_COST_ALERT_USD", "3.00")
    )
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.environ.get("SMTP_FROM_EMAIL", "") or os.environ.get(
        "SMTP_USERNAME", ""
    )
    ALERT_EMAIL_TO: str = os.environ.get("ALERT_EMAIL_TO", "")


settings = Config()
