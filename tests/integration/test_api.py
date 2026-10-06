"""Integration tests for the listings API.

Tests the full request/response cycle with the FastAPI test client.
"""

import pytest


class TestListingsAPI:
    """Test listings API endpoints."""

    async def test_create_listing(self, client):
        """Test creating a listing returns 201."""
        data = {
            "title": "Burton Custom X 2024",
            "description": "Premium all-mountain snowboard",
            "price": 45000.00,
            "currency": "RUB",
            "category": "snowboards",
            "condition": "used_good",
            "seller_node_id": "node-test-01",
        }
        response = await client.post("/v1/api/v1/listings", json=data)
        assert response.status_code == 201
        listing = response.json()
        assert listing["title"] == "Burton Custom X 2024"
        assert listing["price"] == 45000.00
        assert listing["category"] == "snowboards"
        assert listing["type"] == "ot:Listing"
        assert listing["seller"]["node_id"] == "node-test-01"
        assert listing["id"].startswith("urn:opentrade:listing:")

    async def test_get_listings_empty(self, client):
        """Test GET /listings returns empty when no listings exist."""
        response = await client.get("/v1/api/v1/listings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_get_listings_after_create(self, client):
        """Test GET /listings returns the created listing."""
        # Create a listing
        create_data = {
            "title": "Nitro Team Concept 2023",
            "price": 35000.00,
            "currency": "RUB",
            "category": "snowboards",
            "condition": "new",
            "seller_node_id": "node-test-02",
        }
        await client.post("/v1/api/v1/listings", json=create_data)

        # Get listings
        response = await client.get("/v1/api/v1/listings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["title"] == "Nitro Team Concept 2023"

    async def test_get_listings_category_filter(self, client):
        """Test category filtering works."""
        # Create two listings in different categories
        await client.post("/v1/api/v1/listings", json={
            "title": "Board A", "price": 1000, "category": "snowboards",
            "seller_node_id": "node-test-01",
        })
        await client.post("/v1/api/v1/listings", json={
            "title": "Binding B", "price": 5000, "category": "bindings",
            "seller_node_id": "node-test-02",
        })

        # Filter by snowboards
        response = await client.get("/v1/api/v1/listings?category=snowboards")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["category"] == "snowboards"

    async def test_listings_response_has_all_fields(self, client):
        """Test listing response contains all required OpenAPI fields."""
        await client.post("/v1/api/v1/listings", json={
            "title": "Full Test Board",
            "description": "Full featured test listing",
            "price": 99999.99,
            "currency": "RUB",
            "category": "snowboards",
            "condition": "for_parts",
            "seller_node_id": "node-test-03",
        })
        response = await client.get("/v1/api/v1/listings")
        data = response.json()
        assert data["total"] >= 1

        listing = data["items"][-1]
        assert "@context" in listing or "context" in listing
        assert "id" in listing
        assert "type" in listing
        assert "title" in listing
        assert "price" in listing
        assert "currency" in listing
        assert "category" in listing
        assert "condition" in listing
        assert "seller" in listing
        assert "created_at" in listing
        assert "updated_at" in listing
