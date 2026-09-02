"""
Configuration settings for AIBD Backend.
Supports Supabase credentials, dual SQLite/Postgres storage, and AI providers.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        if self.supabase_db_url:
            url = self.supabase_db_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return self.database_url


settings = Settings()
