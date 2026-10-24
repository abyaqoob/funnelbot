"""Telegram Channel Adapter using direct webhook & HTTP client."""
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.adapters.base import ChannelAdapter
from app.config import settings
from app.models.events import (
    ActionType,
    Channel,
    EngineAction,
    EventType,
    NormalizedEvent,
)

logger = logging.getLogger("funnelbot.adapters.telegram")


class TelegramAdapter(ChannelAdapter):
    """Channel adapter for Telegram Bot."""

    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token: str | None = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN

    def normalize_inbound(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> NormalizedEvent | None:
        """
        Parses a Telegram Update object into a NormalizedEvent.
        Supports text messages and button callback queries.
        """
        message = payload.get("message") or payload.get("edited_message")
        callback_query = payload.get("callback_query")

        user_data = None
        text = ""
        timestamp = datetime.now(UTC)

        if message:
            user_data = message.get("from") or message.get("chat")
            text = message.get("text", "")
            date_unix = message.get("date")
            if date_unix:
                timestamp = datetime.fromtimestamp(date_unix, tz=UTC)
        elif callback_query:
            user_data = callback_query.get("from")
            text = callback_query.get("data", "")
        else:
            logger.debug("Unsupported Telegram update format: %s", payload)
            return None

        if not user_data:
            return None

        user_id = str(user_data.get("id"))
        username = user_data.get("username") or user_data.get("first_name") or f"tg_{user_id}"

        return NormalizedEvent(
            channel=Channel.TELEGRAM,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text=text,
            timestamp=timestamp,
            metadata={"telegram_update_id": payload.get("update_id")},
        )

    def send_action(self, action: EngineAction) -> bool:
        """
        Dispatches EngineAction to Telegram API.
        If TELEGRAM_BOT_TOKEN is not configured, logs in simulation mode and succeeds.
        """
        if action.action_type not in (ActionType.SEND_DM, ActionType.REPLY_COMMENT):
            # TAG_LEAD or NOTIFY are internal admin events
            return True

        if not action.text:
            return True

        # Build interactive keyboard markup for quick replies
        reply_markup = None
        if action.quick_replies:
            reply_markup = {
                "keyboard": [[{"text": label}] for label in action.quick_replies],
                "one_time_keyboard": True,
                "resize_keyboard": True,
            }

        if not self.bot_token:
            logger.info(
                "[Telegram Dev Mode] Token not set. Simulated send to chat %s: %s (Quick replies: %s)",
                action.user_id,
                action.text,
                action.quick_replies,
            )
            return True

        payload = {
            "chat_id": action.user_id,
            "text": action.text,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        url = f"{self.BASE_URL}/bot{self.bot_token}/sendMessage"

        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    logger.info("Telegram message delivered to %s", action.user_id)
                    return True
                else:
                    logger.warning("Telegram API error (%s): %s", res.status_code, res.text)
                    return False
        except Exception as exc:
            logger.error("Failed to send Telegram message: %s", exc)
            return False

    def set_webhook(self, webhook_url: str, secret_token: str | None = None) -> bool:
        """Register the public webhook endpoint with Telegram."""
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be configured to set webhook.")

        url = f"{self.BASE_URL}/bot{self.bot_token}/setWebhook"
        payload = {"url": webhook_url}
        if secret_token:
            payload["secret_token"] = secret_token

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload)
                data = res.json()
                logger.info("Telegram setWebhook response: %s", data)
                return bool(data.get("ok"))
        except Exception as exc:
            logger.error("Failed to set Telegram webhook: %s", exc)
            return False

    def delete_webhook(self) -> bool:
        """Remove the active webhook from Telegram."""
        if not self.bot_token:
            return False

        url = f"{self.BASE_URL}/bot{self.bot_token}/deleteWebhook"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url)
                return bool(res.json().get("ok"))
        except Exception as exc:
            logger.error("Failed to delete Telegram webhook: %s", exc)
            return False
