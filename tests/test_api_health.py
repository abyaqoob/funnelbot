"""Tests for /health endpoint."""
from fastapi.testclient import TestClient


def test_health_check_healthy(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["service"] == "FunnelBot"
    assert "timestamp" in data
