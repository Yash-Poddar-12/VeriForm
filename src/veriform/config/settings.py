"""
veriform.config
===============
Application configuration loaded from environment variables / .env file.

All configuration is centralised here so that modules never import os.getenv
directly; they import from this module instead.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env only when running locally; CI/production injects env vars directly.
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)


class Settings:
    """Flat, typed configuration derived from environment variables."""

    env: str = os.getenv("VERIFORM_ENV", "development")
    log_level: str = os.getenv("VERIFORM_LOG_LEVEL", "INFO").upper()

    api_host: str = os.getenv("VERIFORM_API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("VERIFORM_API_PORT", "8000"))

    browser: str = os.getenv("VERIFORM_BROWSER", "chromium")
    headless: bool = os.getenv("VERIFORM_HEADLESS", "true").lower() == "true"
    timeout_ms: int = int(os.getenv("VERIFORM_TIMEOUT_MS", "30000"))

    reports_dir: Path = Path(os.getenv("VERIFORM_REPORTS_DIR", "reports"))

    # Phase 3 – Snowflake (intentionally not wired up yet).
    # snowflake_account: str | None = os.getenv("SNOWFLAKE_ACCOUNT")
    # snowflake_user: str | None    = os.getenv("SNOWFLAKE_USER")


# Singleton – import `settings` everywhere.
settings = Settings()
