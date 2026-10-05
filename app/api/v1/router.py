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


@router.get("/api/v1/listings", response_model=ListingsResponse)
async def get_listings(
    category: str = "all",
    limit: int = 20,
):
    """Search and retrieve a list of listings.

    Matches the OpenAPI GET /api/v1/listings specification.
    """
    # TODO: Replace with actual database/query implementation
    fake_listings = [
        Listing(
            id="urn:opentrade:listing:550e8400-e29b-41d4-a716-446655440000",
            type="ot:Listing",
            title="Burton Custom X 2024",
            description="Excellent condition, minimal wear. Perfect for freestyle.",
            price=45000.00,
            currency="RUB",
            category="snowboards",
            condition=Condition.USED_GOOD,
            seller=SellerInfo(node_id="node-snowboard-alpine-01", reputation_score=98.5),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Listing(
            id="urn:opentrade:listing:660f9511-f30c-52e5-b827-557766551111",
            type="ot:Listing",
            title="Jones Flagship 158",
            description="New season model. Deep snow specialist.",
            price=52000.00,
            currency="RUB",
            category="snowboards",
            condition=Condition.NEW,
            seller=SellerInfo(node_id="node-snowboard-alpine-02", reputation_score=95.0),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    if category != "all":
        fake_listings = [l for l in fake_listings if l.category == category]

    return ListingsResponse(
        total=len(fake_listings),
        items=fake_listings[:limit],
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
    return listing
