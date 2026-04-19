"""Tests for the health endpoint."""


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert "version" in body
    assert "groq_available" in body


def test_health_has_timing_header(client):
    resp = client.get("/health")
    assert "x-processing-time-ms" in resp.headers
