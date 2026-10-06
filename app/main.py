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
from app.api.v1.search_router import router as search_router
from app.services.federation.service import FederationService
from app.services.ai.assistant import AIAssistant
from app.db import init_db, drop_all_tables
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logging.info("Starting OpenTrade Peer Node...")
    logging.info(f"Node ID: {settings.node_id}")
    logging.info(f"Category: {settings.category}")

    # Initialize database tables
    try:
        await init_db()
        logging.info("Database tables initialized successfully")
    except Exception as e:
        logging.warning(f"Database init skipped (will work on first request): {e}")

    # Initialize services
    sync = FederationService()
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
    app.include_router(search_router, prefix="/v1")

    # Health check
    @app.get("/health")
    async def health_check():
        db_status = "error"
        meilisearch_status = "error"

        # Check database — use asyncpg directly since sqlmodel sync engine won't work with async drivers
        try:
            import asyncpg
            db_url = os.environ.get("DATABASE_URL") or settings.database_url
            # postgresql://user:pass@host:port/db
            if "postgres" in db_url or "postgresql" in db_url:
                import re
                match = re.match(r"postgresql(?!ite)://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
                if match:
                    conn = await asyncpg.connect(
                        user=match.group(1),
                        password=match.group(2),
                        host=match.group(3),
                        port=match.group(4),
                        database=match.group(5),
                    )
                    await conn.close()
                    db_status = "ok"
        except Exception as e:
            logging.warning(f"Database health check failed: {e}")

        # Check Meilisearch
        ms_url = os.environ.get("MEILISEARCH_URL") or settings.meilisearch_url
        ms_key = os.environ.get("MEILISEARCH_MASTER_KEY") or settings.meilisearch_master_key
        if "localhost" in ms_url or "127.0.0.1" in ms_url:
            meilisearch_status = "skipped (local)"
        else:
            try:
                headers = {"Authorization": f"Bearer {ms_key}"} if ms_key else {}
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(
                        f"{ms_url}/health",
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        meilisearch_status = "ok"
                    else:
                        meilisearch_status = f"http_{resp.status_code}"
            except Exception as e:
                logging.warning(f"Meilisearch health check failed: {e}")

        overall = "healthy" if (db_status == "ok" and meilisearch_status == "ok") else "degraded"

        return {
            "status": overall,
            "node_id": settings.node_id,
            "version": "0.1.0-draft",
            "database": db_status,
            "meilisearch": meilisearch_status,
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
