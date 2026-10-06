"""API v1 router for listings endpoints.

Uses Pydantic models from app.models.listing that strictly match
spec/openapi/openapi.yaml schemas. Data is persisted to PostgreSQL
via SQLModel.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, HTTPException, Query
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


@router.get("/api/v1/listings", response_model=ListingsResponse)
async def get_listings(
    category: str = Query("all", description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor (listing ID)"),
):
    """Search and retrieve a list of listings.

    Matches the OpenAPI GET /api/v1/listings specification.
    Supports cursor-based pagination and category filtering.
    """
    async with get_session_context() as session:
        # Build base query
        stmt = select(ListingTable)

        # Apply category filter
        if category != "all":
            stmt = stmt.where(ListingTable.category == category)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.exec(count_stmt)).one()

        # Apply cursor-based pagination
        if cursor:
            # Cursor is the listing id we saw last
            stmt = stmt.where(ListingTable.id > cursor)

        # Order by created_at descending (newest first)
        stmt = stmt.order_by(ListingTable.created_at.desc())

        # Apply limit (fetch one extra to detect more pages)
        stmt = stmt.limit(limit + 1)

        results = (await session.exec(stmt)).all()

        # Check if there are more results
        has_more = len(results) > limit
        if has_more:
            results = results[:limit]

        items = [table_to_pydantic(r) for r in results]

    return ListingsResponse(total=total, items=items)


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

    async with get_session_context() as session:
        session.add(listing_table)
        await session.commit()
        await session.refresh(listing_table)

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

import asyncio


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
