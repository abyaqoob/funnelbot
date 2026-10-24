"""Normalized Event and Action models."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
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
    post_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EngineAction(BaseModel):
    action_type: ActionType
    channel: Channel
    user_id: str
    username: Optional[str] = None
    text: Optional[str] = None
    post_id: Optional[str] = None
    quick_replies: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InspectorInfo(BaseModel):
    matched_rule: Optional[str] = None
    keyword_matched: Optional[str] = None
    faq_match: Optional[Dict[str, Any]] = None
    flow_state: Optional[Dict[str, Any]] = None
    lead_score: int = 0
    lead_tier: Optional[str] = None
    is_opted_out: bool = False
    execution_notes: List[str] = Field(default_factory=list)


class EngineResult(BaseModel):
    actions: List[EngineAction] = Field(default_factory=list)
    inspector_info: InspectorInfo = Field(default_factory=InspectorInfo)
