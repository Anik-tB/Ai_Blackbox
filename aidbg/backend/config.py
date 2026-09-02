"""
Configuration settings for AIBD Backend.
Supports Supabase credentials, dual SQLite/Postgres storage, and AI providers.
Automatically detects and resolves IPv6 direct connections to IPv4 Supabase poolers.
"""

from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Optional, Tuple
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
    environment: str = "production"
    host: str = "127.0.0.1"
    port: int = 8765
    debug: bool = False

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
        env_file=(".env", ".aidbg/config.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_effective_db_url(self) -> str:
        """
        Returns Supabase DB URL if present, otherwise database_url.
        Automatically converts IPv6 direct hosts (db.<ref>.supabase.co:5432) to IPv4 poolers
        to prevent [Errno 101] Network is unreachable on IPv4 networks.
        """
        db_url = self.supabase_db_url
        if not db_url:
            yaml_sb = _load_yaml_supabase()
            db_url = yaml_sb.get("db_url") or None

        if db_url:
            url = db_url.strip()

            # Detect direct IPv6 hostname pattern: db.<project-ref>.supabase.co:5432
            match = re.search(r"postgresql(?:\+asyncpg)?://([^:]+):([^@]+)@db\.([a-zA-Z0-9]+)\.supabase\.co:5432/([^\s\?]+)", url)
            if match:
                user, password, project_ref, dbname = match.groups()
                # Auto-fallback to Supabase IPv4 Transaction Pooler (ap-south-1 default or custom)
                pooler_user = f"postgres.{project_ref}" if not user.startswith("postgres.") else user
                url = f"postgresql://{pooler_user}:{password}@aws-0-ap-south-1.pooler.supabase.com:6543/{dbname}"

            # Ensure SQLAlchemy asyncpg driver dialect
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

            return url

        return self.database_url

    def get_supabase_api_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Returns (supabase_url, supabase_key) from env or .aidbg/config.yaml."""
        s_url = self.supabase_url
        s_key = self.supabase_service_role_key or self.supabase_key
        if not s_url or not s_key:
            yaml_sb = _load_yaml_supabase()
            s_url = s_url or yaml_sb.get("url") or None
            s_key = s_key or yaml_sb.get("key") or None
        return s_url, s_key


settings = Settings()
