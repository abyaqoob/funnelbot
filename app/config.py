"""Application configuration loaded from environment variables and .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root if it exists
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    """FunnelBot configuration settings."""

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database (auto-fallback to writable /tmp on serverless environments like Vercel)
    _default_db: str = "sqlite:////tmp/funnelbot.db" if os.getenv("VERCEL") else "sqlite:///./funnelbot.db"
    DATABASE_URL: str = os.getenv("DATABASE_URL", _default_db)

    # Admin & Security
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "demo-funnel-pass-2026")
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
    MAX_INPUT_LENGTH: int = int(os.getenv("MAX_INPUT_LENGTH", "1000"))

    # Pluggable LLM fallback
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    # Channel Adapters
    TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_SECRET: str | None = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    INSTAGRAM_PAGE_ID: str | None = os.getenv("INSTAGRAM_PAGE_ID")
    INSTAGRAM_ACCESS_TOKEN: str | None = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    INSTAGRAM_VERIFY_TOKEN: str = os.getenv("INSTAGRAM_VERIFY_TOKEN", "meta_dev_secret")


settings = Settings()
