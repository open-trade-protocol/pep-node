"""Federation service for the peer node."""

from __future__ import annotations

import json
import base64
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger("federation")


class FederationService:
    """Federation service for node-to-node communication."""
    
    def __init__(self):
        self.index_url = settings.federation_index_url
        self.heartbeat_interval = settings.federation_heartbeat_interval
        self._private_key = None
        self._public_key = None
        self._node_secret_key = None
        self._running = False
        self._heartbeat_task = None
        self._sync_task = None
    
    async def initialize(self):
        """Initialize federation service."""
        logger.info("Initializing federation service...")
        
        # Load or generate node key pair
        if settings.node_secret_key:
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
                base64.b64decode(settings.node_secret_key)
            )
        else:
            # Generate new key pair (in production, this would be done once)
            self._private_key = ed25519.Ed25519PrivateKey.generate()
        
        self._public_key = self._private_key.public_key()
        self._node_secret_key = base64.b64encode(
            self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        ).decode()
        
        logger.info("Federation service initialized", node_id=settings.node_id)
    
    async def start(self):
        """Start federation sync and heartbeat."""
        if self._running:
            return
        
        await self.initialize()
        self._running = True
        
        # Start heartbeat loop
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Start sync loop
        self._sync_task = asyncio.create_task(self._sync_loop())
        
        logger.info("Federation service started")
    
    async def stop(self):
        """Stop federation sync and heartbeat."""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Federation service stopped")
    
    async def register_node(self) -> dict:
        """Register this node with the PEP Index."""
        logger.info("Registering node with PEP Index")
        
        # In production, would make HTTP request to federation_index_url/federation/register
        # For now, return sample response
        return {
            "nodeId": settings.node_id,
            "nodeSecretKey": self._node_secret_key,
            "registeredAt": datetime.utcnow().isoformat(),
            "status": "active",
        }
    
    async def announce_listings(self, listings: List[dict]) -> dict:
        """Announce listings to the PEP Index."""
        logger.info("Announcing listings", count=len(listings))
        
        # Sign each listing
        signed_listings = []
        for listing in listings:
            signature = self._sign_listing(listing)
            signed_listings.append({
                "listingId": listing["listing_id"],
                "signature": signature,
                "data": listing,
            })
        
        # In production, would make HTTP request to federation_index_url/federation/announce
        # For now, return sample response
        return {
            "nodeId": settings.node_id,
            "status": "accepted",
            "listingsCount": len(signed_listings),
            "announcedAt": datetime.utcnow().isoformat(),
        }
    
    async def heartbeat(self) -> dict:
        """Send heartbeat to PEP Index."""
        logger.debug("Sending heartbeat")
        
        # In production, would make HTTP request to federation_index_url/federation/heartbeat
        # For now, return sample response
        return {
            "nodeId": settings.node_id,
            "status": "healthy",
            "listingsCount": 1000,  # Would be actual count
            "lastSyncAt": datetime.utcnow().isoformat(),
        }
    
    async def sync_full(self) -> List[dict]:
        """Perform full sync with PEP Index."""
        logger.info("Performing full sync")
        
        # In production, would fetch all listings from PEP Index
        # For now, return sample data
        return []
    
    async def sync_incremental(self, updated_since: datetime) -> List[dict]:
        """Perform incremental sync with PEP Index."""
        logger.info("Performing incremental sync", since=updated_since.isoformat())
        
        # In production, would fetch updated listings from PEP Index
        # For now, return sample data
        return []
    
    def _sign_listing(self, listing: dict) -> str:
        """Sign a listing with the node's private key."""
        # Canonical JSON
        listing_data = json.dumps(listing, sort_keys=True, separators=(',', ':'))
        
        # Sign
        signature = self._private_key.sign(listing_data.encode())
        
        # Return base64-encoded signature
        return base64.urlsafe_b64encode(signature).decode()
    
    async def _heartbeat_loop(self):
        """Periodically send heartbeats."""
        while self._running:
            try:
                await self.heartbeat()
            except Exception as e:
                logger.error("Heartbeat failed", error=str(e))
            
            await asyncio.sleep(self.heartbeat_interval)
    
    async def _sync_loop(self):
        """Periodically sync with PEP Index."""
        while self._running:
            try:
                await self.sync_incremental(datetime.utcnow() - timedelta(minutes=60))
            except Exception as e:
                logger.error("Sync failed", error=str(e))
            
            await asyncio.sleep(settings.federation_sync_interval)
