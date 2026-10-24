"""Simulator endpoints for recruiter interactive demo."""
import html
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_db_storage, get_funnel_engine
from app.config import settings
from app.engine.funnel_engine import FunnelEngine
from app.engine.storage import Storage
from app.models.events import Channel, EngineResult, EventType, NormalizedEvent

router = APIRouter(prefix="/api/simulator", tags=["Simulator"])

# In-memory idempotency cache: {key: (timestamp, EngineResult)}
_idempotency_cache: dict[str, EngineResult] = {}


class SimulatorEventRequest(BaseModel):
    channel: Channel = Channel.SIMULATOR
    event_type: EventType = EventType.COMMENT
    user_id: str = "demo_recruiter"
    username: str = "recruiter"
    text: str = Field(..., max_length=1000)
    post_id: str | None = "post_demo_1"


class SimulatorResetRequest(BaseModel):
    user_id: str = "demo_recruiter"
    channel: Channel = Channel.SIMULATOR


@router.post("/event", response_model=EngineResult)
def process_simulator_event(
    payload: SimulatorEventRequest,
    engine: FunnelEngine = Depends(get_funnel_engine),
    storage: Storage = Depends(get_db_storage),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
):
    """
    Process inbound simulated comment or DM, run through the funnel engine,
    and return output actions + live Engine Inspector metadata.
    """
    # 1. Idempotency Check
    if x_idempotency_key and x_idempotency_key in _idempotency_cache:
        return _idempotency_cache[x_idempotency_key]

    # 2. Input Sanitization & Length Caps
    clean_text = payload.text.strip()
    if len(clean_text) > settings.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message length exceeds maximum cap of {settings.MAX_INPUT_LENGTH} characters.",
        )
    # Sanitize HTML tags to prevent XSS
    escaped_text = html.escape(clean_text)

    # 3. Create Normalized Event
    event = NormalizedEvent(
        channel=payload.channel,
        event_type=payload.event_type,
        user_id=payload.user_id,
        username=payload.username,
        text=escaped_text,
        post_id=payload.post_id,
        timestamp=datetime.now(UTC),
    )

    # 4. Engine Processing
    result = engine.process_event(event)

    # 5. Log conversation for analytics and inspector history
    storage.log_conversation(event, result.actions, result.inspector_info)

    # 6. Cache idempotency if key provided
    if x_idempotency_key:
        _idempotency_cache[x_idempotency_key] = result
        if len(_idempotency_cache) > 1000:
            # Simple eviction
            _idempotency_cache.clear()

    return result


@router.post("/reset")
def reset_simulator_state(
    payload: SimulatorResetRequest,
    storage: Storage = Depends(get_db_storage),
):
    """Wipe state, rule cooldown triggers, and opt-out flags for a demo user."""
    storage.delete_state(payload.channel.value, payload.user_id)
    storage.set_opted_out(payload.channel.value, payload.user_id, False)
    storage.clear_rule_triggers(payload.user_id)

    return {
        "status": "success",
        "message": f"Reset demo user state for @{payload.user_id} on {payload.channel.value}.",
    }
