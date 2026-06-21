"""Integration tests for the Flask API and security headers."""

import json


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_index_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Carbon Footprint Assistant" in resp.data


def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in resp.headers


def test_assess_success(client, valid_payload):
    resp = client.post(
        "/api/assess",
        data=json.dumps(valid_payload),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    # Contract: every documented key is present.
    for key in (
        "total_annual_kg", "per_capita_annual_kg", "breakdown", "rating",
        "rating_explanation", "feature_contributions", "insights",
    ):
        assert key in body
    # Dataset-trained model uses Low/Medium/High; synthetic fallback adds
    # Moderate/Very High.
    assert body["rating"] in {"Low", "Medium", "Moderate", "High", "Very High"}
    assert isinstance(body["insights"], list)


def test_assess_rejects_invalid_json(client):
    resp = client.post(
        "/api/assess", data="not-json", content_type="application/json"
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_assess_rejects_missing_field(client, valid_payload):
    del valid_payload["weekly_km"]
    resp = client.post(
        "/api/assess",
        data=json.dumps(valid_payload),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "weekly_km" in resp.get_json()["error"]


def test_assess_rejects_bad_category(client, valid_payload):
    valid_payload["diet_type"] = "carnivore"
    resp = client.post(
        "/api/assess",
        data=json.dumps(valid_payload),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_baseline_endpoint(client):
    resp = client.get("/api/baseline")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "transport" in body and "diet" in body
