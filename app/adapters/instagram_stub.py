"""Instagram Graph API dev-mode stub adapter for comments and direct messages."""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.adapters.base import ChannelAdapter
from app.config import settings
from app.models.events import ActionType, Channel, EngineAction, EventType, NormalizedEvent

logger = logging.getLogger("funnelbot.adapters.instagram")


class InstagramStubAdapter(ChannelAdapter):
    """
    Instagram Graph API adapter (dev-mode stub).
    Supports webhook verification (hub.challenge), comment & DM parsing,
    and outbound Graph API dispatch behind env flags.
    """

    GRAPH_API_URL = "https://graph.facebook.com/v21.0"

    def __init__(
        self,
        access_token: Optional[str] = None,
        verify_token: Optional[str] = None,
        page_id: Optional[str] = None,
    ):
        self.access_token = access_token or settings.INSTAGRAM_ACCESS_TOKEN
        self.verify_token = verify_token or settings.INSTAGRAM_VERIFY_TOKEN
        self.page_id = page_id or settings.INSTAGRAM_PAGE_ID

    def verify_webhook(self, mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Optional[str]:
        """
        Handles Meta webhook verification handshake (GET hub.challenge).
        Returns challenge string if verified, or None.
        """
        expected_token = self.verify_token or settings.INSTAGRAM_VERIFY_TOKEN
        if mode == "subscribe" and token and expected_token and token == expected_token:
            logger.info("Instagram webhook handshake verified successfully.")
            return challenge
        logger.warning("Instagram webhook verification mismatch or missing token.")
        return None

    def normalize_inbound(
        self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> Optional[NormalizedEvent]:
        """
        Extracts a single normalized event from Meta Graph API webhook payload.
        (For batch payloads, use normalize_batch).
        """
        batch = self.normalize_batch(payload)
        return batch[0] if batch else None

    def normalize_batch(self, payload: Dict[str, Any]) -> List[NormalizedEvent]:
        """
        Parses Meta Graph API webhook JSON payload into a list of NormalizedEvents.
        Handles both comment events and direct messaging events.
        """
        events: List[NormalizedEvent] = []
        entries = payload.get("entry", [])

        for entry in entries:
            # 1. Comment events (changes -> field: comments)
            for change in entry.get("changes", []):
                if change.get("field") == "comments":
                    val = change.get("value", {})
                    from_user = val.get("from", {})
                    text = val.get("text", "")
                    post_id = val.get("media", {}).get("id") or val.get("post_id")
                    user_id = str(from_user.get("id", ""))
                    username = from_user.get("username", f"ig_{user_id}")

                    if user_id and text:
                        events.append(
                            NormalizedEvent(
                                channel=Channel.INSTAGRAM,
                                event_type=EventType.COMMENT,
                                user_id=user_id,
                                username=username,
                                text=text,
                                post_id=post_id,
                                timestamp=datetime.now(timezone.utc),
                                metadata={"comment_id": val.get("id")},
                            )
                        )

            # 2. Messaging events (Direct Messages)
            for msg_item in entry.get("messaging", []):
                sender = msg_item.get("sender", {})
                message = msg_item.get("message", {})
                user_id = str(sender.get("id", ""))
                text = message.get("text", "")

                if user_id and text:
                    events.append(
                        NormalizedEvent(
                            channel=Channel.INSTAGRAM,
                            event_type=EventType.DM,
                            user_id=user_id,
                            username=f"ig_{user_id}",
                            text=text,
                            timestamp=datetime.now(timezone.utc),
                            metadata={"mid": message.get("mid")},
                        )
                    )

        return events

    def send_action(self, action: EngineAction) -> bool:
        """
        Sends an action via Meta Graph API.
        If INSTAGRAM_ACCESS_TOKEN is missing (dev mode), logs and simulates success.
        """
        if action.action_type not in (ActionType.REPLY_COMMENT, ActionType.SEND_DM):
            return True

        if not action.text:
            return True

        # Dev mode simulation
        if not self.access_token:
            logger.info(
                "[Instagram Dev Mode] Simulated %s to %s (@%s): %s",
                action.action_type.value,
                action.user_id,
                action.username,
                action.text,
            )
            return True

        # Graph API dispatch
        try:
            with httpx.Client(timeout=8.0) as client:
                if action.action_type == ActionType.REPLY_COMMENT:
                    # Reply to a comment on a media object
                    comment_id = action.metadata.get("comment_id") or action.post_id
                    if not comment_id:
                        logger.warning("Cannot reply to comment: missing comment_id/post_id.")
                        return False

                    url = f"{self.GRAPH_API_URL}/{comment_id}/replies"
                    res = client.post(
                        url,
                        params={"access_token": self.access_token},
                        json={"message": action.text},
                    )
                    return res.status_code == 200

                elif action.action_type == ActionType.SEND_DM:
                    # Send direct message via Messenger / Instagram Direct API
                    url = f"{self.GRAPH_API_URL}/me/messages"
                    res = client.post(
                        url,
                        params={"access_token": self.access_token},
                        json={
                            "recipient": {"id": action.user_id},
                            "message": {"text": action.text},
                        },
                    )
                    return res.status_code == 200

        except Exception as exc:
            logger.error("Failed to send Instagram Graph API request: %s", exc)
            return False

        return True
