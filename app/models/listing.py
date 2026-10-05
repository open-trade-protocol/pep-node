"""Database models for the peer node."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Text, Float, Boolean, Integer, JSON, ForeignKey,
    DateTime, Enum as SAEnum,
    create_engine, inspect
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import enum


Base = declarative_base()


class Condition(str, enum.Enum):
    """Product condition grades."""
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class ListingStatus(str, enum.Enum):
    """Listing status."""
    ACTIVE = "active"
    SOLD = "sold"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class EscrowStatus(str, enum.Enum):
    """Escrow state machine states."""
    CREATED = "created"
    FUNDED = "funded"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    INSPECTING = "inspecting"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    ARBITRATING = "arbitrating"
    SETTLED = "settled"
    REFUNDED = "refunded"


class OfferStatus(str, enum.Enum):
    """Offer status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTERED = "countered"
    EXPIRED = "expired"


class Node(Base):
    """Federation node registration."""
    __tablename__ = "nodes"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(String(255), unique=True, nullable=False, index=True)
    node_name = Column(String(255))
    node_public_key = Column(Text, nullable=False)
    node_url = Column(String(1024))
    capabilities = Column(JSON, default=list)
    supported_categories = Column(JSON, default=list)
    status = Column(String(50), default="active")
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime)
    listings_count = Column(Integer, default=0)
    
    listings = relationship("Listing", back_populates="node")
    
    def to_dict(self) -> dict:
        return {
            "nodeId": self.node_id,
            "nodeName": self.node_name,
            "nodeUrl": self.node_url,
            "capabilities": self.capabilities or [],
            "supportedCategories": self.supported_categories or [],
            "status": self.status,
            "registeredAt": self.registered_at.isoformat() if self.registered_at else None,
            "lastHeartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "listingsCount": self.listings_count,
        }


class Listing(Base):
    """Product listing."""
    __tablename__ = "listings"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(String(255), unique=True, nullable=False, index=True)
    node_id = Column(PG_UUID(as_uuid=True), ForeignKey("nodes.id"))
    
    # Product data
    category = Column(String(255), nullable=False, index=True)
    brand = Column(String(255), nullable=False)
    model = Column(String(255), nullable=False)
    model_year = Column(Integer)
    specifications = Column(JSON, default=dict)
    condition = Column(String(50), default="good")
    condition_details = Column(JSON, default=list)
    serial_number = Column(String(255))
    serial_verified = Column(Boolean, default=False)
    
    # Pricing
    ask_price = Column(Float, nullable=False)
    min_acceptable_price = Column(Float)
    currency = Column(String(3), default="RUB")
    price_history = Column(JSON, default=list)
    market_reference = Column(JSON)
    
    # Logistics
    seller_location = Column(JSON)
    dimensions = Column(JSON)
    shipping_options = Column(JSON, default=list)
    
    # Status
    status = Column(String(50), default="active", index=True)
    
    # Media
    media = Column(JSON, default=dict)
    
    # Verification
    ai_confidence = Column(Float)
    ai_verification_status = Column(String(50))
    ai_condition_report_url = Column(String(1024))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Federation
    federation_signature = Column(Text)
    federated_at = Column(DateTime)
    
    # Relationships
    node = relationship("Node", back_populates="listings")
    escrows = relationship("Escrow", back_populates="listing")
    offers = relationship("Offer", back_populates="listing")
    
    def to_listing_dict(self) -> dict:
        """Convert to OpenTrade Protocol listing format."""
        return {
            "@context": "https://opentradeprotocol.com/v1/context.jsonld",
            "@type": "ot:Listing",
            "ot:version": "1.0",
            "identifier": {
                "ot:listingId": self.listing_id,
                "ot:nodeId": self.node_id.hex if self.node_id else None,
                "ot:timestamp": self.created_at.isoformat() if self.created_at else None,
                "ot:expiresAt": self.expires_at.isoformat() if self.expires_at else None,
            },
            "ot:product": {
                "ot:category": self.category,
                "ot:brand": self.brand,
                "ot:model": self.model,
                "ot:modelYear": self.model_year,
                "ot:specifications": self.specifications or {},
                "ot:condition": {
                    "ot:overallGrade": self.condition,
                    "ot:defects": self.condition_details or [],
                },
                "ot:serialNumber": self.serial_number,
                "ot:serialVerified": self.serial_verified,
            },
            "ot:pricing": {
                "ot:askPrice": {
                    "ot:amount": self.ask_price,
                    "ot:currency": self.currency,
                },
                "ot:minAcceptablePrice": {
                    "ot:amount": self.min_acceptable_price,
                    "ot:currency": self.currency,
                } if self.min_acceptable_price else None,
                "ot:priceHistory": self.price_history or [],
                "ot:marketReference": self.market_reference,
            },
            "ot:logistics": {
                "ot:sellerLocation": self.seller_location or {},
                "ot:dimensions": self.dimensions or {},
                "ot:shippingOptions": self.shipping_options or [],
            },
            "ot:media": self.media or {},
            "ot:escrow": {
                "ot:enabled": True,
                "ot:inspectionPeriodHours": 48,
                "ot:disputeWindowHours": 72,
                "ot:platformFeePercent": 1.5,
                "ot:buyerProtectionLevel": "full",
            },
        }
    
    def to_search_result(self) -> dict:
        """Convert to search result format."""
        total_cost = self.ask_price  # Simplified - would include shipping in real impl
        return {
            "listing_id": self.listing_id,
            "node_id": self.node_id.hex if self.node_id else None,
            "product": {
                "category": self.category,
                "brand": self.brand,
                "model": self.model,
                "condition": {
                    "overall_grade": self.condition,
                },
            },
            "pricing": {
                "ask_price": {
                    "amount": self.ask_price,
                    "currency": self.currency,
                },
            },
            "total_landed_cost": {
                "product": self.ask_price,
                "shipping": 0,
                "insurance": 0,
                "platform_fee": self.ask_price * 0.015,  # 1.5% fee
                "total": total_cost,
            },
            "seller": {
                "did": None,  # Would be resolved from node
                "trust_score": 0.0,
            },
            "ai_confidence": self.ai_confidence or 0.0,
        }


class Escrow(Base):
    """Escrow contract for a transaction."""
    __tablename__ = "escrows"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    escrow_id = Column(String(255), unique=True, nullable=False, index=True)
    listing_id = Column(PG_UUID(as_uuid=True), ForeignKey("listings.id"))
    
    buyer_did = Column(String(255), nullable=False)
    seller_did = Column(String(255), nullable=False)
    
    status = Column(SAEnum(EscrowStatus), default=EscrowStatus.CREATED)
    
    amounts = Column(JSON, default=dict)
    timeline = Column(JSON, default=list)
    pin_code = Column(String(10))
    inspection_period_expires = Column(DateTime)
    dispute_window_expires = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    listing = relationship("Listing", back_populates="escrows")
    
    def to_dict(self) -> dict:
        return {
            "escrowId": self.escrow_id,
            "listingId": self.listing_id.hex if self.listing_id else None,
            "buyerDid": self.buyer_did,
            "sellerDid": self.seller_did,
            "status": self.status.value,
            "amounts": self.amounts or {},
            "timeline": self.timeline or [],
            "pinCode": self.pin_code,
            "inspectionPeriodExpires": self.inspection_period_expires.isoformat() if self.inspection_period_expires else None,
            "disputeWindowExpires": self.dispute_window_expires.isoformat() if self.dispute_window_expires else None,
        }


class Offer(Base):
    """Negotiation offer."""
    __tablename__ = "offers"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(String(255), unique=True, nullable=False, index=True)
    listing_id = Column(PG_UUID(as_uuid=True), ForeignKey("listings.id"))
    
    buyer_did = Column(String(255), nullable=False)
    seller_did = Column(String(255), nullable=False)
    
    offer_price = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")
    message = Column(Text)
    status = Column(SAEnum(OfferStatus), default=OfferStatus.PENDING)
    
    expires_at = Column(DateTime)
    signature = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    listing = relationship("Listing", back_populates="offers")
    
    def to_dict(self) -> dict:
        return {
            "offerId": self.offer_id,
            "listingId": self.listing_id.hex if self.listing_id else None,
            "buyerDid": self.buyer_did,
            "sellerDid": self.seller_did,
            "offerPrice": {
                "amount": self.offer_price,
                "currency": self.currency,
            },
            "message": self.message,
            "status": self.status.value,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
            "signature": self.signature,
        }


class TrustScore(Base):
    """Trust score for a participant."""
    __tablename__ = "trust_scores"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    did = Column(String(255), unique=True, nullable=False, index=True)
    
    overall_score = Column(Float, default=0.0)
    components = Column(JSON, default=dict)
    total_transactions = Column(Integer, default=0)
    dispute_rate = Column(Float, default=0.0)
    avg_response_time_min = Column(Integer)
    return_rate = Column(Float, default=0.0)
    verified_identity = Column(Boolean, default=False)
    verified_since = Column(DateTime)
    decay = Column(String(50), default="exponential_180d")
    
    category_expertise = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "overall": self.overall_score,
            "components": self.components or {},
            "totalTransactions": self.total_transactions,
            "disputeRate": self.dispute_rate,
            "avgResponseTimeMin": self.avg_response_time_min,
            "returnRate": self.return_rate,
            "verifiedIdentity": self.verified_identity,
            "verifiedSince": self.verified_since.isoformat() if self.verified_since else None,
            "decay": self.decay,
            "categoryExpertise": self.category_expertise or {},
        }


def get_engine(database_url: str):
    """Create SQLAlchemy engine."""
    return create_engine(database_url, pool_size=10, max_overflow=20)


def get_session(engine):
    """Create a new database session."""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def init_db(engine):
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
