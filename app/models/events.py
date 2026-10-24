"""Normalized Event and Action models."""
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Channel(str, Enum):
    SIMULATOR = "simulator"
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"


class EventType(str, Enum):
    COMMENT = "comment"
    DM = "dm"


class ActionType(str, Enum):
    REPLY_COMMENT = "reply_comment"
    SEND_DM = "send_dm"
    TAG_LEAD = "tag_lead"
    NOTIFY = "notify"


class NormalizedEvent(BaseModel):
    channel: Channel
    event_type: EventType
    user_id: str
    username: str
    text: str
    post_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class EngineAction(BaseModel):
    action_type: ActionType
    channel: Channel
    user_id: str
    username: str | None = None
    text: str | None = None
    post_id: str | None = None
    quick_replies: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InspectorInfo(BaseModel):
    matched_rule: str | None = None
    keyword_matched: str | None = None
    faq_match: dict[str, Any] | None = None
    flow_state: dict[str, Any] | None = None
    lead_score: int = 0
    lead_tier: str | None = None
    is_opted_out: bool = False
    execution_notes: list[str] = Field(default_factory=list)


class EngineResult(BaseModel):
    actions: list[EngineAction] = Field(default_factory=list)
    inspector_info: InspectorInfo = Field(default_factory=InspectorInfo)
