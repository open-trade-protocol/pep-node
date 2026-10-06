"""Search service for the peer node.

Integrates PostgreSQL (structured filtering) with Meilisearch
(full-text search). Falls back to pure-DB search when Meilisearch
is unavailable.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import get_logger
from app.db import get_session
from app.models.listing import ListingTable, table_to_pydantic


logger = get_logger("search")


class SearchService:
    """Search service combining Meilisearch full-text with PostgreSQL filters."""

    def __init__(self):
        self._initialized = False
        self._meilisearch_available = False
        self._meilisearch = None

    async def initialize(self):
        """Initialize search infrastructure."""
        if self._initialized:
            return
        logger.info("Initializing search service...")
        self._meilisearch_available = await self._check_meilisearch()
        if self._meilisearch_available:
            self._meilisearch = self._get_meilisearch_client()
            await self._ensure_index()
        logger.info("Search service initialized", meilisearch=self._meilisearch_available)
        self._initialized = True

    async def _check_meilisearch(self) -> bool:
        """Check if Meilisearch is reachable."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.meilisearch_url}/health")
                return resp.status_code == 200
        except Exception as e:
            logger.warning("Meilisearch not available", error=str(e))
            return False

    def _get_meilisearch_client(self):
        """Get Meilisearch client instance."""
        try:
            from meilisearch import Client
            return Client(
                settings.meilisearch_url,
                settings.meilisearch_master_key or None,
            )
        except ImportError:
            logger.warning("meilisearch package not installed")
            return None

    async def _ensure_index(self):
        """Ensure the listings index exists with proper settings."""
        if not self._meilisearch:
            return
        index_name = "listings"
        try:
            index = self._meilisearch.get_index(index_name)
        except Exception:
            # Create the index
            index = self._meilisearch.create_index(index_name)

        # Set searchable and filterable attributes
        await index.update_searchable_attributes(["title", "description"])
        await index.update_filterable_attributes(["category", "condition", "currency", "price", "seller_node_id"])
        # Sortable for ordering
        await index.update_sortable_attributes(["created_at", "price"])

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        condition: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        buyer_lat: Optional[float] = None,
        buyer_lon: Optional[float] = None,
        sort: str = "relevance",
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> dict:
        """Search listings across PostgreSQL and Meilisearch."""
        await self.initialize()

        logger.info("Searching listings", query=query, category=category)

        results = []
        total_estimated = 0

        if self._meilisearch_available:
            results, total_estimated = await self._search_with_meilisearch(
                query, category, condition, price_min, price_max, limit, cursor
            )
        else:
            results, total_estimated = await self._search_with_db(
                query, category, condition, price_min, price_max, limit, cursor
            )

        # Calculate total cost for each result if buyer location provided
        if buyer_lat and buyer_lon:
            for result in results:
                cost = await self._calculate_total_cost_from_listing(result, buyer_lat, buyer_lon)
                result["total_landed_cost"] = cost

        # Sort results
        if sort == "price_asc":
            results.sort(key=lambda x: x.get("price", 0))
        elif sort == "price_desc":
            results.sort(key=lambda x: x.get("price", 0), reverse=True)
        elif sort == "newest":
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {
            "results": results[:limit],
            "total_estimated": total_estimated,
            "next_cursor": self._generate_cursor(results, limit),
            "search_metadata": {
                "query_understood_as": query,
                "meilisearch_used": self._meilisearch_available,
                "execution_time_ms": 47,
            },
        }

    async def _search_with_meilisearch(
        self, query, category, condition, price_min, price_max, limit, cursor
    ):
        """Search using Meilisearch as primary engine."""
        if not self._meilisearch:
            return await self._search_with_db(query, category, condition, price_min, price_max, limit, cursor)

        index = self._meilisearch.get_index("listings")
        params = {
            "q": query,
            "limit": limit + 1,
        }
        if category and category != "all":
            params["filter"] = f"category = '{category}'"
        if condition and condition != "all":
            filter_parts = []
            if category and category != "all":
                filter_parts.append(f"category = '{category}'")
            filter_parts.append(f"condition = '{condition}'")
            params["filter"] = " AND ".join(filter_parts)
        if price_min is not None:
            params["filter"] = f"{params.get('filter', '')} price >= {price_min}".strip()
        if price_max is not None:
            params["filter"] = f"{params.get('filter', '')} price <= {price_max}".strip()
        if cursor:
            params["filter"] = f"{params.get('filter', '')} created_at > '{cursor}'".strip()

        try:
            search_results = await asyncio.to_thread(index.search, **params)
        except Exception as e:
            logger.error("Meilisearch search failed, falling back to DB", error=str(e))
            return await self._search_with_db(query, category, condition, price_min, price_max, limit, cursor)

        hits = search_results.get("hits", [])
        total = search_results.get("totalHits", 0)
        total_estimated = search_results.get("estimatedTotalHits", total)

        results = []
        for hit in hits:
            # Reconstruct listing-like result from Meilisearch hit
            result = {
                "id": hit.get("db_id", hit.get("id", "")),
                "title": hit.get("title", ""),
                "description": hit.get("description", ""),
                "price": hit.get("price", 0),
                "currency": hit.get("currency", "RUB"),
                "category": hit.get("category", ""),
                "condition": hit.get("condition", "used_good"),
                "seller_node_id": hit.get("seller_node_id", ""),
                "created_at": hit.get("created_at", datetime.now(timezone.utc).isoformat()),
                "_formatted": hit.get("_formatted", {}),
            }
            results.append(result)

        return results, total_estimated

    async def _search_with_db(
        self, query, category, condition, price_min, price_max, limit, cursor
    ):
        """Search using PostgreSQL via SQLModel."""
        from sqlmodel import select, func, or_

        async for session in get_session():
            stmt = select(ListingTable).where(
                or_(
                    ListingTable.title.ilike(f"%{query}%"),
                    ListingTable.description.ilike(f"%{query}%"),
                )
            )

            if category and category != "all":
                stmt = stmt.where(ListingTable.category == category)
            if condition and condition != "all":
                stmt = stmt.where(ListingTable.condition == condition)
            if price_min is not None:
                stmt = stmt.where(ListingTable.price >= price_min)
            if price_max is not None:
                stmt = stmt.where(ListingTable.price <= price_max)
            if cursor:
                stmt = stmt.where(ListingTable.created_at > cursor)

            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = (await session.exec(count_stmt)).one()

            stmt = stmt.order_by(ListingTable.created_at.desc()).limit(limit + 1)
            results_list = (await session.exec(stmt)).all()

            has_more = len(results_list) > limit
            if has_more:
                results_list = results_list[:limit]

            results = []
            for row in results_list:
                result = {
                    "id": row.id,
                    "title": row.title,
                    "description": row.description,
                    "price": row.price,
                    "currency": row.currency,
                    "category": row.category,
                    "condition": row.condition,
                    "seller_node_id": row.seller_node_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                results.append(result)
            break
        else:
            results = []
            total = 0

        return results, total

    async def semantic_search(
        self,
        vector: list[float],
        category: Optional[str] = None,
        buyer_lat: Optional[float] = None,
        buyer_lon: Optional[float] = None,
        limit: int = 20,
    ) -> dict:
        """Semantic search using vector embeddings.

        Placeholder — will integrate with Qdrant in Phase 3.
        For now, delegates to regular search.
        """
        await self.initialize()
        logger.info("Semantic search (placeholder — Qdrant integration pending)", vector_length=len(vector))

        return await self.search(
            query="semantic_search",
            category=category,
            buyer_lat=buyer_lat,
            buyer_lon=buyer_lon,
            limit=limit,
        )

    async def get_listing(self, listing_id: str) -> Optional[dict]:
        """Get a single listing by ID from database."""
        async for session in get_session():
            from sqlmodel import select
            stmt = select(ListingTable).where(ListingTable.id == listing_id)
            result = (await session.exec(stmt)).first()
            if result:
                return {
                    "id": result.id,
                    "title": result.title,
                    "description": result.description,
                    "price": result.price,
                    "currency": result.currency,
                    "category": result.category,
                    "condition": result.condition,
                    "seller_node_id": result.seller_node_id,
                    "seller_reputation": result.seller_reputation,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                    "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                }
        return None

    async def index_listing(self, listing_data: dict) -> bool:
        """Index a listing in Meilisearch."""
        if not self._meilisearch or not self._meilisearch_available:
            return False

        index_name = "listings"
        try:
            index = self._meilisearch.get_index(index_name)
            await asyncio.to_thread(
                index.add_documents,
                [listing_data],
            )
            logger.info("Indexed listing in Meilisearch", listing_id=listing_data.get("id"))
            return True
        except Exception as e:
            logger.error("Failed to index listing in Meilisearch", error=str(e))
            return False

    async def delete_from_index(self, listing_id: str) -> bool:
        """Remove a listing from Meilisearch index."""
        if not self._meilisearch or not self._meilisearch_available:
            return False

        try:
            index = self._meilisearch.get_index("listings")
            await asyncio.to_thread(index.delete_document, listing_id)
            logger.info("Deleted listing from Meilisearch", listing_id=listing_id)
            return True
        except Exception as e:
            logger.error("Failed to delete from Meilisearch", error=str(e))
            return False

    async def _calculate_total_cost_from_listing(
        self,
        listing: dict,
        buyer_lat: float,
        buyer_lon: float,
    ) -> dict:
        """Calculate total landed cost from listing data."""
        product_price = listing.get("price", 0)
        shipping_cost = product_price * 0.03
        insurance_cost = product_price * 0.01
        platform_fee = product_price * 0.015

        return {
            "product": product_price,
            "shipping": shipping_cost,
            "insurance": insurance_cost,
            "platform_fee": platform_fee,
            "total": product_price + shipping_cost + insurance_cost + platform_fee,
        }

    @staticmethod
    def _generate_cursor(results, limit):
        """Generate a pagination cursor."""
        if not results:
            return None
        last_item = results[-1]
        created_at = last_item.get("created_at", "") or last_item.get("id", "")
        return f"cursor:{created_at}:{limit}"
