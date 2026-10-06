"""Test configuration for pep-node."""

import asyncio
import os
import pytest
import tempfile


# Create a temp file for test database BEFORE any app imports
_test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db_file.close()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db_file.name}"


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_db():
    """Reset database tables before and after each test."""
    from sqlmodel import SQLModel
    from app.models.listing import ListingTable  # noqa: F401
    from app.db import get_sync_engine

    # Create tables
    SQLModel.metadata.create_all(get_sync_engine())
    yield
    # Drop tables
    SQLModel.metadata.drop_all(get_sync_engine())


@pytest.fixture
async def app():
    """Create test FastAPI app."""
    from app.main import create_app
    app = create_app()
    return app


@pytest.fixture
async def client(app):
    """Create test client."""
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
