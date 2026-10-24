"""Tests for Instagram Stub Adapter and Webhook endpoint."""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from app.adapters.instagram_stub import InstagramStubAdapter
from app.config import settings
from app.models.events import ActionType, Channel, EngineAction, EventType


@pytest.fixture
def ig_adapter():
    return InstagramStubAdapter(
        access_token="test_access_token",
        verify_token="test_verify_token_123",
        page_id="12345678",
    )


def test_instagram_webhook_verification(client: TestClient, ig_adapter: InstagramStubAdapter):
    with patch.object(settings, "INSTAGRAM_VERIFY_TOKEN", "meta_secret_token"):
        # 1. Successful verification
        res_ok = client.get(
            "/webhooks/instagram",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "meta_secret_token",
                "hub.challenge": "1158201444",
            },
        )
        assert res_ok.status_code == 200
        assert res_ok.text == "1158201444"

        # 2. Token mismatch -> 403 Forbidden
        res_fail = client.get(
            "/webhooks/instagram",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "1158201444",
            },
        )
        assert res_fail.status_code == 403


def test_instagram_normalize_comment_batch(ig_adapter: InstagramStubAdapter):
    raw_payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "12345678",
                "time": 1700000000,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comm_99",
                            "text": "Can I get the GUIDE?",
                            "from": {"id": "user_ig_1", "username": "ig_fan"},
                            "media": {"id": "post_media_55"},
                        },
                    }
                ],
            }
        ],
    }

    events = ig_adapter.normalize_batch(raw_payload)
    assert len(events) == 1
    event = events[0]
    assert event.channel == Channel.INSTAGRAM
    assert event.event_type == EventType.COMMENT
    assert event.user_id == "user_ig_1"
    assert event.username == "ig_fan"
    assert event.text == "Can I get the GUIDE?"
    assert event.post_id == "post_media_55"


def test_instagram_normalize_dm_batch(ig_adapter: InstagramStubAdapter):
    raw_payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "12345678",
                "messaging": [
                    {
                        "sender": {"id": "user_ig_dm"},
                        "message": {"mid": "m_123", "text": "What is the pricing?"},
                    }
                ],
            }
        ],
    }

    events = ig_adapter.normalize_batch(raw_payload)
    assert len(events) == 1
    assert events[0].event_type == EventType.DM
    assert events[0].user_id == "user_ig_dm"
    assert events[0].text == "What is the pricing?"


def test_instagram_send_action_dev_mode():
    adapter = InstagramStubAdapter(access_token=None)
    action = EngineAction(
        action_type=ActionType.REPLY_COMMENT,
        channel=Channel.INSTAGRAM,
        user_id="user_123",
        text="Check your DMs!",
        metadata={"comment_id": "comm_123"},
    )
    assert adapter.send_action(action) is True


def test_instagram_send_action_graph_api(ig_adapter: InstagramStubAdapter):
    action = EngineAction(
        action_type=ActionType.SEND_DM,
        channel=Channel.INSTAGRAM,
        user_id="user_123",
        text="Here is your guide!",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        assert ig_adapter.send_action(action) is True
        assert mock_post.called


def test_instagram_post_webhook(client: TestClient):
    payload = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comm_test",
                            "text": "GUIDE",
                            "from": {"id": "ig_client_user", "username": "ig_client"},
                            "media": {"id": "media_999"},
                        },
                    }
                ]
            }
        ],
    }

    res = client.post("/webhooks/instagram", json=payload)
    assert res.status_code == 200
    assert res.json() == {"status": "EVENT_RECEIVED"}
