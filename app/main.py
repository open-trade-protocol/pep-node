"""OpenTrade Peer Node — Reference Implementation

Reference implementation of an OpenTrade Protocol node. This node publishes
listings to the OpenTrade Index and serves as a marketplace for a specific category.

Usage:
    python -m app.main          # Run the node
    python -m app.cli migrate   # Run migrations
    python -m app.cli register  # Register with PEP Index
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import router as v1_router
from app.services.federation.sync import FederationSync
from app.services.ai.assistant import AIAssistant
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logging.info("Starting OpenTrade Peer Node...")
    logging.info(f"Node ID: {settings.node_id}")
    logging.info(f"Category: {settings.node.category}")
    
    # Initialize services
    sync = FederationSync()
    await sync.start()
    
    ai_assistant = AIAssistant()
    await ai_assistant.initialize()
    
    yield
    
    # Shutdown
    logging.info("Shutting down OpenTrade Peer Node...")
    await sync.stop()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="OpenTrade Peer Node",
        description="Reference implementation of an OpenTrade Protocol node",
        version="0.1.0-draft",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(v1_router, prefix="/v1")
    
    # Health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "node_id": settings.node_id,
            "version": "0.1.0-draft",
        }
    
    return app


app = create_app()


def main():
    """Entry point for the peer node."""
    setup_logging()
    logging.info("Starting OpenTrade Peer Node...")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
