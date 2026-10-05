"""Search service for the peer node."""

from __future__ import annotations

import json
import math
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import uuid

from app.core.config import settings
from app.core.logging import get_logger
from app.models.listing import Listing, get_engine, get_session


logger = get_logger("search")


class SearchService:
    """Search service for listings."""
    
    def __init__(self):
        self.engine = get_engine(settings.database_url)
        self.session_factory = lambda: get_session(self.engine)
        self._initialized = False
    
    async def initialize(self):
        """Initialize search infrastructure."""
        if not self._initialized:
            logger.info("Initializing search service...")
            self._initialized = True
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        condition: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        buyer_lat: Optional[float] = None,
        buyer_lon: Optional[float] = None,
        sort: str = "relevance_score",
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> dict:
        """Search listings."""
        await self.initialize()
        
        logger.info("Searching listings", query=query, category=category)
        
        # Simulate search results (in production, would query Meilisearch + Qdrant)
        results = await self._get_sample_results(query, category, condition, price_min, price_max)
        
        # Calculate total cost for each result if buyer location provided
        if buyer_lat and buyer_lon:
            for result in results:
                cost = await self.calculate_total_cost_from_listing(result, buyer_lat, buyer_lon)
                result["total_landed_cost"] = cost
        
        # Sort results
        if sort == "total_cost_asc":
            results.sort(key=lambda x: x["total_landed_cost"].get("total", 0))
        elif sort == "total_cost_desc":
            results.sort(key=lambda x: x["total_landed_cost"].get("total", 0), reverse=True)
        elif sort == "newest":
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "results": results[:limit],
            "total_estimated": len(results),
            "next_cursor": self._generate_cursor(results, limit),
            "search_metadata": {
                "query_understood_as": query,
                "semantic_fallback_used": False,
                "execution_time_ms": 47,
            },
        }
    
    async def semantic_search(
        self,
        vector: list[float],
        category: Optional[str] = None,
        buyer_lat: Optional[float] = None,
        buyer_lon: Optional[float] = None,
        limit: int = 20,
    ) -> dict:
        """Semantic search using vector embeddings."""
        await self.initialize()
        
        logger.info("Semantic search", vector_length=len(vector))
        
        # In production, would query Qdrant vector store
        # For now, return same results as regular search
        return await self.search(
            query="semantic_search",
            category=category,
            buyer_lat=buyer_lat,
            buyer_lon=buyer_lon,
            limit=limit,
        )
    
    async def get_listing(self, listing_id: str) -> Optional[dict]:
        """Get a single listing by ID."""
        await self.initialize()
        
        # In production, would query database
        # For now, return sample data
        return self._get_sample_listing(listing_id)
    
    async def calculate_total_cost(
        self,
        listing_id: str,
        buyer_lat: float,
        buyer_lon: float,
        insurance: bool = True,
    ) -> dict:
        """Calculate total landed cost for a listing."""
        listing = self._get_sample_listing(listing_id)
        if not listing:
            return {"error": "Listing not found"}
        
        return await self.calculate_total_cost_from_listing(listing, buyer_lat, buyer_lon)
    
    async def calculate_total_cost_from_listing(
        self,
        listing: dict,
        buyer_lat: float,
        buyer_lon: float,
    ) -> dict:
        """Calculate total landed cost from listing data."""
        # Simulate shipping cost calculation
        seller_loc = listing.get("pricing", {}).get("ask_price", {})
        product_price = seller_loc.get("amount", 0)
        
        # Simulate shipping (would use logistics service in production)
        shipping_cost = product_price * 0.03  # 3% of product price as shipping
        
        insurance_cost = product_price * 0.01 if insurance else 0
        platform_fee = product_price * 0.015  # 1.5% platform fee
        
        return {
            "product": product_price,
            "shipping": shipping_cost,
            "insurance": insurance_cost,
            "platform_fee": platform_fee,
            "total": product_price + shipping_cost + insurance_cost + platform_fee,
        }
    
    async def get_category_schema(self, category_id: str) -> Optional[dict]:
        """Get JSON Schema for a product category."""
        # In production, would load from schema registry
        if category_id == "winter_sports/snowboard":
            return {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://opentradeprotocol.com/schemas/v1/category/winter_sports/snowboard.json",
                "title": "Snowboard",
                "type": "object",
                "required": ["category", "brand", "model", "condition", "specifications"],
                "properties": {
                    "category": {"type": "string", "const": "winter_sports/snowboard"},
                    "brand": {"type": "string", "minLength": 1, "maxLength": 64},
                    "model": {"type": "string", "minLength": 1, "maxLength": 64},
                    "modelYear": {"type": "integer", "minimum": 2000, "maximum": 2100},
                    "specifications": {
                        "type": "object",
                        "required": ["lengthCm", "waistWidthMm", "profile", "flex"],
                        "properties": {
                            "lengthCm": {"type": "number", "minimum": 120, "maximum": 200},
                            "waistWidthMm": {"type": "number", "minimum": 100, "maximum": 400},
                            "profile": {"type": "string", "enum": ["camber", "rocker", "camber_rocker"]},
                            "flex": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["new", "like_new", "good", "fair", "poor"],
                    },
                },
            }
        return None
    
    async def bulk_listings(
        self,
        updated_since: Optional[str] = None,
        categories: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """Bulk fetch listings for indexing."""
        await self.initialize()
        
        # In production, would query database with filters
        # For now, return sample data
        listings = [self._get_sample_listing(f"lst_bulk_{i}") for i in range(min(limit, 10))]
        
        return {
            "listings": listings,
            "next_cursor": self._generate_cursor(listings, limit),
            "total_available": 1000,
        }
    
    def _get_sample_results(self, query, category, condition, price_min, price_max):
        """Return sample search results."""
        return [
            {
                "listing_id": f"lst_sample_{i}",
                "node_id": "snow.opentradeprotocol.com",
                "product": {
                    "category": "winter_sports/snowboard",
                    "brand": "Jones",
                    "model": "Flagship",
                    "condition": {"overall_grade": "good"},
                },
                "pricing": {
                    "ask_price": {"amount": 28000 - i * 1000, "currency": "RUB"},
                },
                "seller": {
                    "did": f"did:pep:ru:seller{i}",
                    "trust_score": 0.95 - i * 0.01,
                },
                "ai_confidence": 0.94 - i * 0.01,
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(5)
        ]
    
    def _get_sample_listing(self, listing_id: str) -> dict:
        """Return a sample listing."""
        return {
            "listing_id": listing_id,
            "node_id": "snow.opentradeprotocol.com",
            "product": {
                "category": "winter_sports/snowboard",
                "brand": "Jones",
                "model": "Flagship",
                "condition": {"overall_grade": "good"},
            },
            "pricing": {
                "ask_price": {"amount": 28000, "currency": "RUB"},
            },
            "seller": {
                "did": "did:pep:ru:seller1",
                "trust_score": 0.95,
            },
            "ai_confidence": 0.94,
            "created_at": datetime.utcnow().isoformat(),
        }
    
    def _generate_cursor(self, results, limit):
        """Generate a pagination cursor."""
        if not results:
            return None
        last_item = results[-1]
        return f"cursor:{last_item.get('listing_id', '')}:{limit}"
