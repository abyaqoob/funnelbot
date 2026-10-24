"""Tests verifying static frontend file serving."""
from fastapi.testclient import TestClient


def test_static_index_html_served(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "FunnelBot" in response.text
    assert "Engine Inspector" in response.text
    assert "growth_automation" in response.text


def test_static_css_served(client: TestClient):
    response = client.get("/styles.css")
    assert response.status_code == 200
    assert "--ig-gradient" in response.text


def test_static_js_served(client: TestClient):
    response = client.get("/app.js")
    assert response.status_code == 200
    assert "FunnelSimulator" in response.text
