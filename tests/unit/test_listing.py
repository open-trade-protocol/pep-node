"""Unit tests for listing CRUD operations."""

import pytest
from httpx import Response
from app.models.listing import Listing, ListingCreate, Condition, SellerInfo


class TestListingModels:
    """Test Pydantic models match OpenAPI spec."""

    def test_listing_create_valid(self):
        """ListingCreate accepts valid data."""
        data = {
            "title": "Burton Custom X 2024",
            "description": "Great snowboard",
            "price": 45000.00,
            "currency": "RUB",
            "category": "snowboards",
            "condition": Condition.USED_GOOD,
            "seller_node_id": "node-test-01",
        }
        listing = ListingCreate(**data)
        assert listing.title == "Burton Custom X 2024"
        assert listing.price == 45000.00
        assert listing.condition == Condition.USED_GOOD

    def test_listing_create_minimal(self):
        """ListingCreate works with minimal required fields."""
        data = {
            "title": "Test Board",
            "price": 1000.00,
            "category": "snowboards",
            "seller_node_id": "node-test-01",
        }
        listing = ListingCreate(**data)
        assert listing.currency == "RUB"  # default
        assert listing.condition == Condition.USED_GOOD  # default

    def test_listing_create_invalid_price(self):
        """ListingCreate rejects negative price."""
        data = {
            "title": "Test Board",
            "price": -100.00,
            "category": "snowboards",
            "seller_node_id": "node-test-01",
        }
        with pytest.raises(Exception):  # pydantic ValidationError
            ListingCreate(**data)

    def test_listing_create_title_too_long(self):
        """ListingCreate rejects title > 200 chars."""
        data = {
            "title": "A" * 201,
            "price": 1000.00,
            "category": "snowboards",
            "seller_node_id": "node-test-01",
        }
        with pytest.raises(Exception):
            ListingCreate(**data)

    def test_listing_response(self):
        """ListingsResponse wraps items correctly."""
        from app.models.listing import ListingsResponse

        items = [
            Listing(
                id="urn:opentrade:listing:test1",
                title="Board 1",
                price=1000.00,
                currency="RUB",
                category="snowboards",
                condition=Condition.NEW,
                seller=SellerInfo(node_id="node-1", reputation_score=95.0),
                created_at="2024-01-01T00:00:00+00:00",
                updated_at="2024-01-01T00:00:00+00:00",
            )
        ]
        response = ListingsResponse(total=1, items=items)
        assert response.total == 1
        assert len(response.items) == 1
        assert response.items[0].title == "Board 1"

    def test_condition_enum_values(self):
        """All Condition enum values are valid."""
        expected = {"new", "used_like_new", "used_good", "used_fair", "for_parts"}
        actual = {c.value for c in Condition}
        assert expected == actual
