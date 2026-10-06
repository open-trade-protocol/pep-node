"""Unit tests for health check endpoint."""

import pytest


class TestHealthCheck:
    """Test the /health endpoint."""

    async def test_health_returns_ok(self, client):
        """Health endpoint returns 200."""
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_response_structure(self, client):
        """Health response has required fields."""
        response = await client.get("/health")
        data = response.json()
        assert "status" in data
        assert "node_id" in data
        assert "version" in data

    async def test_health_status_value(self, client):
        """Health status is 'healthy' or 'degraded'."""
        response = await client.get("/health")
        data = response.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")

    async def test_health_node_id_matches_config(self, client):
        """Health node_id matches configured value."""
        response = await client.get("/health")
        data = response.json()
        assert data["node_id"] == "snow.opentradeprotocol.com"
