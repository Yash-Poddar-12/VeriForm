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

    # Phase 2 – Workflow Engine Limits
    max_workflow_depth: int = int(os.getenv("VERIFORM_MAX_WORKFLOW_DEPTH", "15"))
    max_states_explored: int = int(os.getenv("VERIFORM_MAX_STATES_EXPLORED", "100"))
    max_transitions_per_state: int = int(os.getenv("VERIFORM_MAX_TRANSITIONS_PER_STATE", "20"))
    
    # Phase 5 & 6 – Execution Engine & Concurrency Limits
    max_concurrent_runs: int = int(os.getenv("VERIFORM_MAX_CONCURRENT_RUNS", "2"))
    artifact_storage_dir: Path = Path(os.getenv("VERIFORM_ARTIFACTS_DIR", "artifacts"))

    # Autonomous Exploration & Self-Healing Limits
    enable_self_healing: bool = os.getenv("VERIFORM_ENABLE_SELF_HEALING", "true").lower() == "true"
    max_heal_attempts: int = int(os.getenv("VERIFORM_MAX_HEAL_ATTEMPTS", "3"))
    heal_timeout_seconds: int = int(os.getenv("VERIFORM_HEAL_TIMEOUT_SECONDS", "5"))
    enable_autonomous_exploration: bool = os.getenv("VERIFORM_ENABLE_AUTONOMOUS_EXPLORATION", "false").lower() == "true"

    # AI Integration Settings
    enable_ai: bool = os.getenv("VERIFORM_ENABLE_AI", "false").lower() == "true"
    ai_provider: str = os.getenv("VERIFORM_AI_PROVIDER", "mock")
    ai_timeout_seconds: int = int(os.getenv("VERIFORM_AI_TIMEOUT_SECONDS", "8"))
    ai_max_retries: int = int(os.getenv("VERIFORM_AI_MAX_RETRIES", "2"))
    ai_model: str = os.getenv("VERIFORM_AI_MODEL", "gpt-4o-mini")
    ai_temperature: float = float(os.getenv("VERIFORM_AI_TEMPERATURE", "0.2"))

# Singleton – import `settings` everywhere.
settings = Settings()
