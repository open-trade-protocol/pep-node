"""Application configuration."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment or config file."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # Node configuration
    node_id: str = "snow.opentradeprotocol.com"
    node_name: str = "Snowboard Reference Node"
    node_secret_key: Optional[str] = None
    category: str = "winter_sports/snowboard"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Database — accepts DATABASE_URL or OT_DATABASE_URL env vars, falls back to SQLite for local dev
    database_url: str = "sqlite+aiosqlite:///./pepnode.db"
    
    # Search — direct env var names (no prefix)
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_master_key: str = ""
    qdrant_url: str = "http://localhost:6333"
    
    # Federation — direct env var names
    federation_index_url: str = "https://api.opentradeprotocol.com/v1"
    federation_heartbeat_interval: int = 300  # 5 minutes
    federation_sync_interval: int = 60  # 1 minute
    
    # AI/ML
    ai_service_url: Optional[str] = None
    ai_model_path: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # CORS
    cors_origins: list[str] = ["*"]


# Singleton settings instance — loaded at module level
# DATABASE_URL env var is checked before Settings() creates the instance
_default_db = os.environ.get("DATABASE_URL") or os.environ.get("OT_DATABASE_URL") or "sqlite+aiosqlite:///./pepnode.db"
settings = Settings(database_url=_default_db)
