"""Lead models for captured qualified contacts."""
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.flow import LeadTier


class Lead(BaseModel):
    id: str
    user_id: str
    username: str | None = None
    channel: str = "simulator"
    email: str | None = None
    score: int = 0
    tier: LeadTier = LeadTier.COLD
    flow_id: str
    answers: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
