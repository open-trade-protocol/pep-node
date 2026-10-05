"""API v1 router for listings endpoints.

Uses Pydantic models from app.models.listing that strictly match
spec/openapi/openapi.yaml schemas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.models.listing import Listing, ListingCreate, ListingsResponse, Condition, SellerInfo

router = APIRouter()

# In-memory storage for listings (replace with DB in production)
_listings: list[Listing] = []


@router.get("/api/v1/listings", response_model=ListingsResponse)
async def get_listings(
    category: str = "all",
    limit: int = 20,
):
    """Search and retrieve a list of listings.

    Matches the OpenAPI GET /api/v1/listings specification.
    """
    result = _listings

    if category != "all":
        result = [l for l in result if l.category == category]

    # Sort by created_at descending (newest first)
    result = sorted(result, key=lambda x: x.created_at or datetime.now(timezone.utc), reverse=True)

    return ListingsResponse(
        total=len(result),
        items=result[:limit],
    )


@router.post("/api/v1/listings", response_model=Listing, status_code=201)
async def create_listing(body: ListingCreate):
    """Publish a new listing.

    Matches the OpenAPI POST /api/v1/listings specification.
    """
    # TODO: Validate against category schema, persist to DB, federate
    listing = Listing(
        id=f"urn:opentrade:listing:{id(body.seller_node_id)}",
        type="ot:Listing",
        title=body.title,
        description=body.description,
        price=body.price,
        currency=body.currency,
        category=body.category,
        condition=body.condition,
        seller=SellerInfo(node_id=body.seller_node_id, reputation_score=0.0),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _listings.append(listing)
    return listing
