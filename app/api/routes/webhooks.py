"""Webhook endpoints for Telegram and Instagram external channels."""
import logging
import secrets
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from app.adapters.instagram_stub import InstagramStubAdapter
from app.adapters.telegram import TelegramAdapter
from app.api.deps import get_db_storage, get_funnel_engine
from app.config import settings
from app.engine.funnel_engine import FunnelEngine
from app.engine.storage import Storage

logger = logging.getLogger("funnelbot.routes.webhooks")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

telegram_adapter = TelegramAdapter()
instagram_adapter = InstagramStubAdapter()


# ==========================================
# TELEGRAM WEBHOOK
# ==========================================

@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    engine: FunnelEngine = Depends(get_funnel_engine),
    storage: Storage = Depends(get_db_storage),
    x_telegram_bot_api_secret_token: Optional[str] = Header(
        None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
):
    """
    Receives incoming Telegram updates, validates secret token,
    runs update through FunnelEngine, and sends actions back to Telegram.
    """
    # 1. Secret token verification (if configured)
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if not x_telegram_bot_api_secret_token or not secrets.compare_digest(
            x_telegram_bot_api_secret_token, settings.TELEGRAM_WEBHOOK_SECRET
        ):
            logger.warning("Rejected Telegram webhook: Invalid secret token.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret token.")

    payload = await request.json()

    # 2. Normalize Telegram update
    event = telegram_adapter.normalize_inbound(payload)
    if not event:
        return {"ok": True, "status": "ignored"}

    # 3. Process with FunnelEngine
    result = engine.process_event(event)

    # 4. Dispatch actions back out to Telegram
    for action in result.actions:
        telegram_adapter.send_action(action)

    # 5. Audit log
    storage.log_conversation(event, result.actions, result.inspector_info)

    return {"ok": True}


# ==========================================
# INSTAGRAM WEBHOOK (DEV-MODE STUB)
# ==========================================

@router.get("/instagram")
def instagram_verify(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Meta Graph API Webhook Verification Handshake.
    Responds to GET requests with the challenge code if the verify token matches.
    """
    challenge = instagram_adapter.verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch.")


@router.post("/instagram")
async def instagram_webhook(
    request: Request,
    engine: FunnelEngine = Depends(get_funnel_engine),
    storage: Storage = Depends(get_db_storage),
):
    """
    Receives Meta Graph API webhook events (Instagram comments and DMs).
    Processes events through FunnelEngine and dispatches responses.
    """
    payload = await request.json()
    events = instagram_adapter.normalize_batch(payload)

    for event in events:
        result = engine.process_event(event)
        for action in result.actions:
            instagram_adapter.send_action(action)
        storage.log_conversation(event, result.actions, result.inspector_info)

    return {"status": "EVENT_RECEIVED"}
