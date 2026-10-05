"""Pydantic models for OpenTrade Protocol API.

Strictly matches the schemas defined in spec/openapi/openapi.yaml.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Condition(str, Enum):
    NEW = "new"
    USED_LIKE_NEW = "used_like_new"
    USED_GOOD = "used_good"
    USED_FAIR = "used_fair"
    FOR_PARTS = "for_parts"


class SellerInfo(BaseModel):
    node_id: str = Field(..., example="node-snowboard-alpine-01")
    reputation_score: Optional[float] = Field(None, ge=0, le=100, example=98.5)


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
