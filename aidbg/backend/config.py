"""
Configuration settings for AIBD Backend.
Supports Supabase credentials, dual SQLite/Postgres storage, and AI providers.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_yaml_supabase() -> dict:
    """Helper to read supabase settings from .aidbg/config.yaml if present."""
    cfg_file = Path(".aidbg/config.yaml")
    if cfg_file.exists():
        try:
            with open(cfg_file, "r") as f:
                data = yaml.safe_load(f) or {}
                return data.get("supabase", {})
        except Exception:
            pass
    return {}


class Settings(BaseSettings):
    # App & Server
    app_name: str = "AI Black Box Debugger"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8765
    debug: bool = True

    # Supabase & Database Configuration
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_db_url: Optional[str] = None

    # Fallback / Default DB URL (uses SQLite locally if Supabase DB URL is not set)
    database_url: str = "sqlite+aiosqlite:///./aidbg.db"

    # AI Configuration
    ai_provider: str = "fallback"  # 'gemini', 'openai', 'anthropic', 'ollama', 'fallback'
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    ai_timeout_seconds: float = 15.0

    # Project repository path for Git & AST analysis
    repo_path: str = "."

    model_config = SettingsConfigDict(
        env_file=(".aidbg/config.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_effective_db_url(self) -> str:
        """Returns Supabase DB URL if present, otherwise database_url."""
        db_url = self.supabase_db_url
        if not db_url:
            yaml_sb = _load_yaml_supabase()
            db_url = yaml_sb.get("db_url") or None

        if db_url:
            url = db_url.strip()
            # Normalize to asyncpg dialect for SQLAlchemy
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return self.database_url

    def get_supabase_api_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Returns (supabase_url, supabase_key) from env or .aidbg/config.yaml."""
        s_url = self.supabase_url
        s_key = self.supabase_service_role_key or self.supabase_key
        if not s_url or not s_key:
            yaml_sb = _load_yaml_supabase()
            s_url = s_url or yaml_sb.get("url") or None
            s_key = s_key or yaml_sb.get("key") or None
        return s_url, s_key


settings = Settings()
