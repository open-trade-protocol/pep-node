"""API v1 router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import uuid

router = APIRouter()


# Import services
from app.services.search.service import SearchService
from app.services.escrow.service import EscrowService
from app.services.trust.service import TrustService
from app.services.federation.service import FederationService
from app.models.listing import Listing, Escrow, Offer, TrustScore


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "opentrade-peer-node",
        "version": "0.1.0-draft",
    }


@router.post("/search")
async def search_listings(
    query: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Category filter"),
    condition: Optional[str] = Query(None, description="Condition filter"),
    price_min: Optional[float] = Query(None, description="Minimum price"),
    price_max: Optional[float] = Query(None, description="Maximum price"),
    buyer_lat: Optional[float] = Query(None, description="Buyer latitude"),
    buyer_lon: Optional[float] = Query(None, description="Buyer longitude"),
    sort: str = Query("relevance_score", description="Sort order"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search listings across all federated nodes."""
    search_service = SearchService()
    results = await search_service.search(
        query=query,
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
    return results


@router.post("/search/semantic")
async def semantic_search(
    vector: list[float] = Query(..., description="Embedding vector"),
    category: Optional[str] = Query(None, description="Category filter"),
    buyer_lat: Optional[float] = Query(None, description="Buyer latitude"),
    buyer_lon: Optional[float] = Query(None, description="Buyer longitude"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    """Semantic search using vector embeddings."""
    search_service = SearchService()
    results = await search_service.semantic_search(
        vector=vector,
        category=category,
        buyer_lat=buyer_lat,
        buyer_lon=buyer_lon,
        limit=limit,
    )
    return results


@router.get("/listings/{listing_id}")
async def get_listing(
    listing_id: str,
    buyer_lat: Optional[float] = Query(None, description="Buyer latitude"),
    buyer_lon: Optional[float] = Query(None, description="Buyer longitude"),
):
    """Get a single listing by ID."""
    search_service = SearchService()
    listing = await search_service.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if buyer_lat and buyer_lon:
        cost = await search_service.calculate_total_cost(
            listing_id, buyer_lat, buyer_lon
        )
        listing["total_landed_cost"] = cost
    
    return listing


@router.get("/listings/{listing_id}/total-cost")
async def get_total_cost(
    listing_id: str,
    buyer_lat: float = Query(..., description="Buyer latitude"),
    buyer_lon: float = Query(..., description="Buyer longitude"),
    insurance: bool = Query(True, description="Include insurance"),
):
    """Calculate total landed cost for a listing."""
    search_service = SearchService()
    cost = await search_service.calculate_total_cost(
        listing_id, buyer_lat, buyer_lon, insurance
    )
    return cost


@router.post("/listings/{listing_id}/offers")
async def create_offer(
    listing_id: str,
    offer_price: float = Query(..., description="Offer price"),
    currency: str = Query("RUB", description="Currency"),
    message: str = Query(..., description="AI reasoning"),
    expires_in: str = Query("PT2H", description="TTL"),
    payment_method: str = Query("escrow", description="Payment method"),
    buyer_did: str = Query(..., description="Buyer DID"),
):
    """Create an offer on a listing."""
    escrow_service = EscrowService()
    offer = await escrow_service.create_offer(
        listing_id=listing_id,
        offer_price=offer_price,
        currency=currency,
        message=message,
        expires_in=expires_in,
        payment_method=payment_method,
        buyer_did=buyer_did,
    )
    return offer


@router.post("/listings/{listing_id}/offers/{offer_id}/respond")
async def respond_to_offer(
    listing_id: str,
    offer_id: str,
    action: str = Query(..., description="Action: accept, reject, counter"),
    counter_price: Optional[float] = Query(None, description="Counter offer price"),
    counter_currency: str = Query("RUB", description="Counter currency"),
    counter_expires_in: Optional[str] = Query(None, description="Counter TTL"),
    counter_message: Optional[str] = Query(None, description="Counter message"),
    seller_did: str = Query(..., description="Seller DID"),
):
    """Respond to an offer."""
    escrow_service = EscrowService()
    response = await escrow_service.respond_to_offer(
        listing_id=listing_id,
        offer_id=offer_id,
        action=action,
        counter_price=counter_price,
        counter_currency=counter_currency,
        counter_expires_in=counter_expires_in,
        counter_message=counter_message,
        seller_did=seller_did,
    )
    return response


@router.post("/escrow/create")
async def create_escrow(
    listing_id: str = Query(..., description="Listing ID"),
    buyer_did: str = Query(..., description="Buyer DID"),
    seller_did: str = Query(..., description="Seller DID"),
    shipping_method: str = Query("standard", description="Shipping method"),
    insurance: bool = Query(True, description="Include insurance"),
    payment_method: str = Query("card", description="Payment method"),
):
    """Create an escrow contract."""
    escrow_service = EscrowService()
    escrow = await escrow_service.create_escrow(
        listing_id=listing_id,
        buyer_did=buyer_did,
        seller_did=seller_did,
        shipping_method=shipping_method,
        insurance=insurance,
        payment_method=payment_method,
    )
    return escrow


@router.post("/escrow/{escrow_id}/confirm")
async def confirm_escrow(
    escrow_id: str,
    pin_code: str = Query(..., description="PIN code"),
    photo_evidence: Optional[list] = Query(None, description="Photo evidence"),
    buyer_did: str = Query(..., description="Buyer DID"),
):
    """Confirm receipt of escrowed item."""
    escrow_service = EscrowService()
    result = await escrow_service.confirm_escrow(
        escrow_id=escrow_id,
        pin_code=pin_code,
        photo_evidence=photo_evidence,
        buyer_did=buyer_did,
    )
    return result


@router.post("/escrow/{escrow_id}/dispute")
async def dispute_escrow(
    escrow_id: str,
    reason: str = Query(..., description="Dispute reason"),
    description: str = Query(..., description="Dispute description"),
    photo_evidence: Optional[list] = Query(None, description="Photo evidence"),
    buyer_did: str = Query(..., description="Buyer DID"),
):
    """File a dispute for an escrowed transaction."""
    escrow_service = EscrowService()
    result = await escrow_service.dispute_escrow(
        escrow_id=escrow_id,
        reason=reason,
        description=description,
        photo_evidence=photo_evidence,
        buyer_did=buyer_did,
    )
    return result


@router.get("/trust/{did}")
async def get_trust_score(
    did: str,
):
    """Get trust score for a DID."""
    trust_service = TrustService()
    score = await trust_service.get_trust_score(did)
    if not score:
        raise HTTPException(status_code=404, detail="Trust score not found")
    return score


@router.post("/logistics/calculate")
async def calculate_logistics(
    origin_lat: float = Query(..., description="Origin latitude"),
    origin_lon: float = Query(..., description="Origin longitude"),
    destination_lat: float = Query(..., description="Destination latitude"),
    destination_lon: float = Query(..., description="Destination longitude"),
    length_cm: float = Query(..., description="Package length"),
    width_cm: float = Query(..., description="Package width"),
    height_cm: float = Query(..., description="Package height"),
    weight_kg: float = Query(..., description="Package weight"),
    declared_value: float = Query(..., description="Declared value"),
    insurance: bool = Query(True, description="Include insurance"),
):
    """Calculate shipping options."""
    search_service = SearchService()
    result = await search_service.calculate_logistics(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        destination_lat=destination_lat,
        destination_lon=destination_lon,
        length_cm=length_cm,
        width_cm=width_cm,
        height_cm=height_cm,
        weight_kg=weight_kg,
        declared_value=declared_value,
        insurance=insurance,
    )
    return result


@router.get("/categories/{category_id}/schema")
async def get_category_schema(
    category_id: str,
):
    """Get JSON Schema for a product category."""
    search_service = SearchService()
    schema = await search_service.get_category_schema(category_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Category schema not found")
    return schema


@router.get("/listings/bulk")
async def bulk_listings(
    updated_since: Optional[str] = Query(None, description="Updated since"),
    categories: Optional[str] = Query(None, description="Categories filter"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
):
    """Bulk fetch listings for indexing."""
    search_service = SearchService()
    result = await search_service.bulk_listings(
        updated_since=updated_since,
        categories=categories,
        cursor=cursor,
        limit=limit,
    )
    return result
