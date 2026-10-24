"""Integration tests for Simulator API endpoints."""
from fastapi.testclient import TestClient


def test_simulator_comment_trigger_event(client: TestClient):
    payload = {
        "channel": "simulator",
        "event_type": "comment",
        "user_id": "recruiter_test",
        "username": "recruiter",
        "text": "Hey please send the guide!",
        "post_id": "post_100",
    }
    response = client.post("/api/simulator/event", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must contain actions: reply_comment and send_dm
    assert len(data["actions"]) == 2
    assert data["actions"][0]["action_type"] == "reply_comment"
    assert data["actions"][1]["action_type"] == "send_dm"

    # Inspector Info
    inspector = data["inspector_info"]
    assert inspector["matched_rule"] == "Free Guide Automation"
    assert inspector["keyword_matched"] == "guide"
    assert inspector["flow_state"]["status"] == "active"


def test_simulator_flow_walkthrough_and_reset(client: TestClient):
    user_id = "recruiter_lead"

    # 1. Start flow via comment
    client.post(
        "/api/simulator/event",
        json={
            "channel": "simulator",
            "event_type": "comment",
            "user_id": user_id,
            "username": "lead_user",
            "text": "GUIDE",
        },
    )

    # 2. Step 1: Goal -> Choice 1 (30 pts)
    res_s1 = client.post(
        "/api/simulator/event",
        json={
            "channel": "simulator",
            "event_type": "dm",
            "user_id": user_id,
            "username": "lead_user",
            "text": "1",
        },
    )
    assert res_s1.status_code == 200
    assert "budget" in res_s1.json()["actions"][0]["text"].lower()

    # 3. Reset demo state
    res_reset = client.post(
        "/api/simulator/reset",
        json={"user_id": user_id, "channel": "simulator"},
    )
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "success"

    # 4. Comment again should succeed immediately because cooldown was reset
    res_after = client.post(
        "/api/simulator/event",
        json={
            "channel": "simulator",
            "event_type": "comment",
            "user_id": user_id,
            "username": "lead_user",
            "text": "GUIDE",
        },
    )
    assert res_after.status_code == 200
    assert len(res_after.json()["actions"]) == 2


def test_simulator_idempotency_key(client: TestClient):
    payload = {
        "channel": "simulator",
        "event_type": "comment",
        "user_id": "idempotent_user",
        "username": "idem_user",
        "text": "GUIDE",
    }
    headers = {"X-Idempotency-Key": "test-key-12345"}

    # First request
    res1 = client.post("/api/simulator/event", json=payload, headers=headers)
    assert res1.status_code == 200

    # Second request with identical key should return cached result
    res2 = client.post("/api/simulator/event", json=payload, headers=headers)
    assert res2.status_code == 200
    assert res1.json() == res2.json()


def test_simulator_max_input_length_exceeded(client: TestClient):
    payload = {
        "channel": "simulator",
        "event_type": "comment",
        "user_id": "spam_user",
        "username": "spammer",
        "text": "A" * 1500,
    }
    res = client.post("/api/simulator/event", json=payload)
    # Pydantic or FastAPI validation will reject text > 1000 characters
    assert res.status_code == 422


def test_simulator_html_escaping(client: TestClient):
    payload = {
        "channel": "simulator",
        "event_type": "comment",
        "user_id": "xss_user",
        "username": "attacker",
        "text": "<script>alert('xss')</script> GUIDE",
    }
    res = client.post("/api/simulator/event", json=payload)
    assert res.status_code == 200
    # Engine processes sanitized text without executing raw html
    assert res.json()["inspector_info"]["keyword_matched"] == "guide"
