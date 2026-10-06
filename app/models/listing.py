"""Pydantic models for OpenTrade Protocol API.

Strictly matches the schemas defined in spec/openapi/openapi.yaml.
Includes both Pydantic DTO models and SQLModel database model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime
from sqlmodel import Field as SQLModelField, SQLModel


class Condition(str, Enum):
    NEW = "new"
    USED_LIKE_NEW = "used_like_new"
    USED_GOOD = "used_good"
    USED_FAIR = "used_fair"
    FOR_PARTS = "for_parts"


class SellerInfo(BaseModel):
    node_id: str = Field(..., example="node-snowboard-alpine-01")
    reputation_score: Optional[float] = Field(None, ge=0, le=100, example=98.5)


# ---------------------------------------------------------------------------
# SQLModel database model (persistence layer)
# ---------------------------------------------------------------------------


class ListingTable(SQLModel, table=True):
    """Database table for persisted listings.

    Maps to the ``listings`` table in PostgreSQL.
    """
    __tablename__ = "listings"

    id: str = SQLModelField(primary_key=True)
    type: str = SQLModelField(default="ot:Listing")
    title: str = SQLModelField(max_length=200)
    description: Optional[str] = SQLModelField(default=None, max_length=2000)
    price: float = SQLModelField(ge=0)
    currency: str = SQLModelField(default="RUB", max_length=10)
    category: str = SQLModelField(max_length=100)
    condition: str = SQLModelField(max_length=20)  # stores Condition enum value
    seller_node_id: str = SQLModelField(max_length=255)
    seller_reputation: Optional[float] = SQLModelField(default=None, ge=0, le=100)
    created_at: datetime = SQLModelField(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = SQLModelField(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column=Column(DateTime(timezone=True)),
    )


def table_to_pydantic(t: ListingTable) -> "Listing":
    """Convert a ListingTable row to a Pydantic Listing DTO."""
    return Listing(
        id=t.id,
        type=t.type,
        title=t.title,
        description=t.description,
        price=t.price,
        currency=t.currency,
        category=t.category,
        condition=Condition(t.condition),
        seller=SellerInfo(node_id=t.seller_node_id, reputation_score=t.seller_reputation),
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# ---------------------------------------------------------------------------
# Pydantic DTO models (API layer)
# ---------------------------------------------------------------------------


class Listing(BaseModel):
    """Response model matching the OpenAPI Listing schema."""

    model_config = ConfigDict(populate_by_name=True)

    context: str = Field(
        default="https://opentradeprotocol.com/contexts/listing-v1.jsonld",
        alias="@context",
    )
    id: str = Field(..., description="URN identifier for the listing")
    type: str = Field(default="ot:Listing")
    title: str = Field(..., max_length=200, example="Burton Custom X 2024")
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(..., ge=0, example=45000.00)
    currency: str = Field(default="RUB", example="RUB")
    category: str = Field(..., example="snowboards")
    condition: Condition = Field(default=Condition.USED_GOOD, example="used_good")
    seller: SellerInfo
    created_at: datetime
    updated_at: datetime


class ListingCreate(BaseModel):
    """Request model for creating a new listing."""

    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(..., ge=0)
    currency: str = Field(default="RUB")
    category: str
    condition: Condition = Field(default=Condition.USED_GOOD)
    seller_node_id: str = Field(..., alias="seller_node_id")


class ListingsResponse(BaseModel):
    """Response wrapper for the GET /listings endpoint."""

    total: int
    items: list[Listing]
