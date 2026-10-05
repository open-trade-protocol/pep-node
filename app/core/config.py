"""Application configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment or config file."""
    
    # Node configuration
    node_id: str = "snow.opentradeprotocol.com"
    node_name: str = "Snowboard Reference Node"
    node_secret_key: Optional[str] = None
    category: str = "winter_sports/snowboard"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/opentrade"
    
    # Search
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_master_key: str = ""
    qdrant_url: str = "http://localhost:6333"
    
    # Federation
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
    
    class Config:
        env_prefix = "OT_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance
settings = Settings()
