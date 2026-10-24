"""Trigger Rule models for comment automation."""
from enum import Enum

from pydantic import BaseModel, Field


class MatchMode(str, Enum):
    EXACT = "exact"
    CONTAINS = "contains"
    FUZZY = "fuzzy"


class TriggerRule(BaseModel):
    id: str
    name: str
    keywords: list[str]
    match_mode: MatchMode = MatchMode.CONTAINS
    fuzzy_threshold: float = 80.0  # 0 to 100 for RapidFuzz
    post_id_scope: str | None = None  # If set, matches only on this post_id
    cooldown_seconds: int = 3600  # Default 1 hour per user per rule
    reply_templates: list[str] = Field(
        default_factory=lambda: [
            "Thanks @{username}! Just sent you a DM 📩",
            "Hey @{username}, check your inbox for details! 🚀",
            "Sent to your DMs @{username}! Let me know if you got it ✨",
        ]
    )
    flow_id: str | None = "lead_qualification"
    direct_dm_message: str | None = None
    is_active: bool = True
