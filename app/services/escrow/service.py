"""Escrow service for the peer node."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.models.listing import Escrow, EscrowStatus


logger = get_logger("escrow")


class EscrowService:
    """Escrow service for managing transactions."""
    
    def __init__(self):
        self._escrows = {}  # In production, would use database
    
    async def create_offer(
        self,
        listing_id: str,
        offer_price: float,
        currency: str,
        message: str,
        expires_in: str,
        payment_method: str,
        buyer_did: str,
    ) -> dict:
        """Create an offer on a listing."""
        logger.info("Creating offer", listing_id=listing_id, price=offer_price)
        
        offer_id = f"off_{uuid.uuid4().hex[:8]}"
        expires_at = datetime.utcnow() + timedelta(hours=2)  # Parse expires_in in production
        
        return {
            "offerId": offer_id,
            "listingId": listing_id,
            "buyerDid": buyer_did,
            "sellerDid": None,  # Would be resolved from listing
            "offerPrice": {
                "amount": offer_price,
                "currency": currency,
            },
            "message": message,
            "status": "pending",
            "createdAt": datetime.utcnow().isoformat(),
            "expiresAt": expires_at.isoformat(),
            "signature": f"sig_{uuid.uuid4().hex[:16]}",  # Would be DID-signed JWT
        }
    
    async def respond_to_offer(
        self,
        listing_id: str,
        offer_id: str,
        action: str,
        counter_price: Optional[float] = None,
        counter_currency: str = "RUB",
        counter_expires_in: Optional[str] = None,
        counter_message: Optional[str] = None,
        seller_did: str = "",
    ) -> dict:
        """Respond to an offer."""
        logger.info("Responding to offer", offer_id=offer_id, action=action)
        
        if action == "accept":
            return {
                "status": "accepted",
                "message": "Offer accepted",
                "escrowId": f"esc_{uuid.uuid4().hex[:8]}",
            }
        elif action == "reject":
            return {
                "status": "rejected",
                "message": "Offer rejected",
            }
        elif action == "counter":
            if not counter_price:
                return {"error": "counter_price required for counter action"}
            return {
                "status": "countered",
                "message": counter_message or "Counter offer",
                "counterOfferPrice": {
                    "amount": counter_price,
                    "currency": counter_currency,
                },
                "counterExpiresAt": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            }
        else:
            return {"error": f"Invalid action: {action}"}
    
    async def create_escrow(
        self,
        listing_id: str,
        buyer_did: str,
        seller_did: str,
        shipping_method: str = "standard",
        insurance: bool = True,
        payment_method: str = "card",
    ) -> dict:
        """Create an escrow contract."""
        logger.info("Creating escrow", listing_id=listing_id, buyer=buyer_did)
        
        escrow_id = f"esc_{uuid.uuid4().hex[:8]}"
        inspection_period = datetime.utcnow() + timedelta(hours=48)
        dispute_window = inspection_period + timedelta(hours=24)
        
        # Simulate amounts (would be calculated from listing in production)
        product_price = 28000
        shipping_cost = 890
        insurance_cost = 140 if insurance else 0
        platform_fee = product_price * 0.015
        
        return {
            "escrowId": escrow_id,
            "status": "created",
            "listingId": listing_id,
            "buyerDid": buyer_did,
            "sellerDid": seller_did,
            "amounts": {
                "product": {"amount": product_price, "currency": "RUB"},
                "shipping": {"amount": shipping_cost, "currency": "RUB"},
                "insurance": {"amount": insurance_cost, "currency": "RUB"},
                "platformFee": {"amount": platform_fee, "currency": "RUB"},
                "total": {"amount": product_price + shipping_cost + insurance_cost + platform_fee, "currency": "RUB"},
            },
            "paymentUrl": f"https://pay.opentradeprotocol.com/esc/{escrow_id}",
            "paymentExpiresAt": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
            "inspectionPeriodHours": 48,
            "disputeWindowHours": 72,
            "inspectionPeriodExpires": inspection_period.isoformat(),
            "disputeWindowExpires": dispute_window.isoformat(),
            "timeline": [
                {"event": "created", "at": datetime.utcnow().isoformat()},
            ],
        }
    
    async def confirm_escrow(
        self,
        escrow_id: str,
        pin_code: str,
        photo_evidence: Optional[list] = None,
        buyer_did: str = "",
    ) -> dict:
        """Confirm receipt of escrowed item."""
        logger.info("Confirming escrow", escrow_id=escrow_id)
        
        # In production, would verify PIN code and update database
        return {
            "escrowId": escrow_id,
            "status": "confirmed",
            "message": "Escrow confirmed, funds released to seller",
            "confirmedAt": datetime.utcnow().isoformat(),
        }
    
    async def dispute_escrow(
        self,
        escrow_id: str,
        reason: str,
        description: str,
        photo_evidence: Optional[list] = None,
        buyer_did: str = "",
    ) -> dict:
        """File a dispute for an escrowed transaction."""
        logger.info("Disputing escrow", escrow_id=escrow_id, reason=reason)
        
        # In production, would update database and notify seller
        return {
            "escrowId": escrow_id,
            "status": "disputed",
            "message": "Dispute filed, funds held pending arbitration",
            "disputeId": f"disp_{uuid.uuid4().hex[:8]}",
            "filedAt": datetime.utcnow().isoformat(),
            "evidenceDeadline": (datetime.utcnow() + timedelta(hours=72)).isoformat(),
        }
