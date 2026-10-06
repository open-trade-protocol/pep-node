"""Search API router.

Provides the POST /api/v1/search endpoint that delegates to SearchService.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services.search.service import SearchService

router = APIRouter()


@router.post("/api/v1/search")
async def search_listings(
    query: str,
    category: str = "all",
    condition: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    buyer_lat: Optional[float] = None,
    buyer_lon: Optional[float] = None,
    sort: str = "relevance",
    limit: int = 20,
    cursor: Optional[str] = None,
):
    """Full-text search across all federated listings.

    Combines Meilisearch full-text search with PostgreSQL filters.
    Falls back to pure-DB search when Meilisearch is unavailable.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    service = SearchService()
    return await service.search(
        query=query.strip(),
        category=category,
        condition=condition,
        price_min=price_min,
        price_max=price_max,
        buyer_lat=buyer_lat,
        buyer_lon=buyer_lon,
        sort=sort,
        limit=limit,
        cursor=cursor,
    )
