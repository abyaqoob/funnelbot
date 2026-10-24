"""Tests for Telegram Adapter and Webhook endpoint."""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from app.adapters.telegram import TelegramAdapter
from app.config import settings
from app.models.events import ActionType, Channel, EngineAction


@pytest.fixture
def tg_adapter():
    return TelegramAdapter(bot_token="test_bot_token")


def test_telegram_normalize_message(tg_adapter: TelegramAdapter):
    raw_payload = {
        "update_id": 99999,
        "message": {
            "message_id": 101,
            "date": 1700000000,
            "chat": {"id": 123456, "type": "private"},
            "from": {"id": 123456, "username": "recruiter_tg", "first_name": "Recruiter"},
            "text": "/start",
        },
    }
    event = tg_adapter.normalize_inbound(raw_payload)
    assert event is not None
    assert event.channel == Channel.TELEGRAM
    assert event.user_id == "123456"
    assert event.username == "recruiter_tg"
    assert event.text == "/start"


def test_telegram_normalize_callback_query(tg_adapter: TelegramAdapter):
    raw_payload = {
        "update_id": 100000,
        "callback_query": {
            "id": "cb_1",
            "from": {"id": 123456, "username": "recruiter_tg"},
            "data": "1",
        },
    }
    event = tg_adapter.normalize_inbound(raw_payload)
    assert event is not None
    assert event.user_id == "123456"
    assert event.text == "1"


def test_telegram_send_action_dev_mode():
    # Adapter without token operates safely in dev mode
    adapter = TelegramAdapter(bot_token=None)
    action = EngineAction(
        action_type=ActionType.SEND_DM,
        channel=Channel.TELEGRAM,
        user_id="123456",
        text="Hello via Telegram!",
        quick_replies=["1. Yes", "2. No"],
    )
    success = adapter.send_action(action)
    assert success is True


def test_telegram_send_action_api_call(tg_adapter: TelegramAdapter):
    action = EngineAction(
        action_type=ActionType.SEND_DM,
        channel=Channel.TELEGRAM,
        user_id="123456",
        text="What is your budget?",
        quick_replies=["$1,000+", "$300 - $1,000"],
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        success = tg_adapter.send_action(action)
        assert success is True
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["chat_id"] == "123456"
        assert "reply_markup" in call_kwargs["json"]


def test_telegram_set_and_delete_webhook(tg_adapter: TelegramAdapter):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True, "result": True}

    with patch("httpx.Client.post", return_value=mock_resp):
        assert tg_adapter.set_webhook("https://example.com/webhooks/telegram", "secret123") is True
        assert tg_adapter.delete_webhook() is True


def test_telegram_webhook_secret_verification(client: TestClient):
    # Set a secret token in settings for test
    with patch.object(settings, "TELEGRAM_WEBHOOK_SECRET", "super-secret-123"):
        payload = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 1700000000,
                "from": {"id": 123456, "username": "user"},
                "text": "/start",
            },
        }

        # 1. Invalid secret -> 403 Forbidden
        res_bad = client.post(
            "/webhooks/telegram",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )
        assert res_bad.status_code == 403

        # 2. Valid secret -> 200 OK
        res_good = client.post(
            "/webhooks/telegram",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "super-secret-123"},
        )
        assert res_good.status_code == 200
        assert res_good.json()["ok"] is True


def test_telegram_webhook_flow_progression(client: TestClient):
    user_id = "tg_flow_user_99"
    # Send /start
    res_start = client.post(
        "/webhooks/telegram",
        json={
            "update_id": 2,
            "message": {
                "message_id": 10,
                "date": 1700000000,
                "from": {"id": user_id, "username": "tg_flow_user"},
                "text": "/start",
            },
        },
    )
    assert res_start.status_code == 200

    # Answer Step 1
    res_s1 = client.post(
        "/webhooks/telegram",
        json={
            "update_id": 3,
            "message": {
                "message_id": 11,
                "date": 1700000001,
                "from": {"id": user_id, "username": "tg_flow_user"},
                "text": "1",
            },
        },
    )
    assert res_s1.status_code == 200
