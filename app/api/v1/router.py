"""API v1 router for listings endpoints.

Uses Pydantic models from app.models.listing that strictly match
spec/openapi/openapi.yaml schemas. Data is persisted to PostgreSQL
via SQLModel.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from sqlmodel import select, func

from app.models.listing import (
    Listing,
    ListingCreate,
    ListingsResponse,
    Condition,
    SellerInfo,
    ListingTable,
    table_to_pydantic,
)
from app.db import get_session_context
from app.services.search.service import SearchService


router = APIRouter()

logger = logging.getLogger(__name__)


def _db_unavailable_error(exc: Exception) -> HTTPException:
    """Return a clear 500 error when the database is unreachable."""
    logger.error("Database request failed", exc_info=True)
    return HTTPException(
        status_code=500,
        detail=(
            "Database unavailable: could not reach PostgreSQL. "
            f"Please check that the 'db' service is running and DATABASE_URL is correct ({exc.__class__.__name__})."
        ),
    )


@router.get("/api/v1/listings", response_model=ListingsResponse)
async def get_listings(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    cursor: Optional[str] = Query(None, description="Pagination cursor (listing ID)"),
):
    """Search and retrieve a list of listings.

    Matches the OpenAPI GET /api/v1/listings specification.
    Supports limit/offset pagination (and optional cursor),
    category filtering and returns total count.
    """
    try:
        async with get_session_context() as session:
            # Build base query — SELECT from the `listings` table
            stmt = select(ListingTable)

            # Apply category filter (None or "all" → no filter)
            if category and category != "all":
                stmt = stmt.where(ListingTable.category == category)

            # Get total count (before pagination)
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = (await session.exec(count_stmt)).one()

            # Order deterministically so offset pages don't overlap
            stmt = stmt.order_by(ListingTable.created_at.desc(), ListingTable.id.desc())

            # Apply cursor-based pagination (listing ID seen last)
            if cursor:
                stmt = stmt.where(ListingTable.id > cursor)

            # Apply classic limit/offset pagination
            stmt = stmt.offset(offset).limit(limit)

            results = (await session.exec(stmt)).all()
    except (SQLAlchemyError, OSError, asyncio.TimeoutError) as e:
        raise _db_unavailable_error(e)

    items = [table_to_pydantic(r) for r in results]

    return ListingsResponse(total=total, limit=limit, offset=offset, items=items)


@router.post("/api/v1/listings", response_model=Listing, status_code=201)
async def create_listing(body: ListingCreate):
    """Publish a new listing.

    Matches the OpenAPI POST /api/v1/listings specification.
    Persists to PostgreSQL and indexes in Meilisearch.
    """
    listing_id = f"urn:opentrade:listing:{uuid.uuid4()}"
    now = datetime.now(timezone.utc)

    listing_table = ListingTable(
        id=listing_id,
        type="ot:Listing",
        title=body.title,
        description=body.description,
        price=body.price,
        currency=body.currency,
        category=body.category,
        condition=body.condition.value,
        seller_node_id=body.seller_node_id,
        seller_reputation=0.0,
        created_at=now,
        updated_at=now,
    )

    try:
        async with get_session_context() as session:
            # INSERT into the `listings` table
            session.add(listing_table)
    except (SQLAlchemyError, OSError, asyncio.TimeoutError) as e:
        raise _db_unavailable_error(e)

    # Index in Meilisearch (fire-and-forget — don't block the response)
    listing_data = {
        "id": listing_table.id,
        "db_id": listing_table.id,
        "title": listing_table.title,
        "description": listing_table.description or "",
        "price": listing_table.price,
        "currency": listing_table.currency,
        "category": listing_table.category,
        "condition": listing_table.condition,
        "seller_node_id": listing_table.seller_node_id,
        "created_at": listing_table.created_at.isoformat() if listing_table.created_at else None,
    }
    asyncio.create_task(_index_in_meilisearch(listing_data))

    return table_to_pydantic(listing_table)


# ---------------------------------------------------------------------------
# Background helpers
# ---------------------------------------------------------------------------




async def _index_in_meilisearch(listing_data: dict):
    """Index a listing in Meilisearch (non-blocking)."""
    try:
        service = SearchService()
        await service.initialize()
        await service.index_listing(listing_data)
    except Exception as e:
        from app.core.logging import get_logger
        logger = get_logger("search")
        logger.warning("Failed to index listing in Meilisearch", error=str(e))
