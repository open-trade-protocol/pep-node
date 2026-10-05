"""Trust service for the peer node."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.models.listing import TrustScore


logger = get_logger("trust")


class TrustService:
    """Trust service for managing participant trust scores."""
    
    def __init__(self):
        self._scores = {}  # In production, would use database
    
    async def get_trust_score(self, did: str) -> Optional[dict]:
        """Get trust score for a DID."""
        logger.info("Getting trust score", did=did)
        
        # In production, would query database and compute from transaction history
        # For now, return sample data
        return {
            "trustScore": {
                "overall": 0.95,
                "components": {
                    "identity_verification": 1.0,
                    "transaction_completion": 0.98,
                    "dispute_resolution": 0.95,
                    "description_accuracy": 0.96,
                    "shipping_speed": 0.99,
                },
                "totalTransactions": 142,
                "disputeRate": 0.007,
                "avgResponseTimeMin": 12,
                "returnRate": 0.02,
                "verifiedIdentity": True,
                "verifiedSince": (datetime.utcnow() - timedelta(days=365)).isoformat(),
                "decay": "exponential_180d",
                "categoryExpertise": {
                    "winter_sports/snowboard": {
                        "deals": 89,
                        "score": 0.97,
                    },
                },
            },
        }
    
    async def update_trust_score(
        self,
        did: str,
        component: str,
        value: float,
    ) -> dict:
        """Update a trust score component."""
        logger.info("Updating trust score", did=did, component=component, value=value)
        
        # In production, would update database and recompute overall score
        return {
            "did": did,
            "component": component,
            "value": value,
            "updatedAt": datetime.utcnow().isoformat(),
        }
    
    async def compute_trust_score(self, did: str) -> dict:
        """Compute trust score from transaction history."""
        # In production, would query database for transaction history
        # and compute weighted components
        return {
            "overall": 0.95,
            "components": {
                "identity_verification": 1.0,
                "transaction_completion": 0.98,
                "dispute_resolution": 0.95,
                "description_accuracy": 0.96,
                "shipping_speed": 0.99,
            },
            "decay": "exponential_180d",
        }
    
    def _compute_overall_score(self, components: dict) -> float:
        """Compute overall trust score from components."""
        weights = {
            "identity_verification": 0.15,
            "transaction_completion": 0.30,
            "dispute_resolution": 0.20,
            "description_accuracy": 0.20,
            "shipping_speed": 0.15,
        }
        
        score = sum(
            components.get(k, 0) * w
            for k, w in weights.items()
        )
        return min(max(score, 0.0), 1.0)
    
    def _apply_decay(self, score: float, days_since_update: int) -> float:
        """Apply exponential decay to trust score."""
        # Exponential decay over 180 days
        decay_factor = math.exp(-0.00385 * days_since_update)
        return score * decay_factor
