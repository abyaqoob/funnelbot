"""Lead models for captured qualified contacts."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.models.flow import LeadTier


class Lead(BaseModel):
    id: str
    user_id: str
    username: Optional[str] = None
    channel: str = "simulator"
    email: Optional[str] = None
    score: int = 0
    tier: LeadTier = LeadTier.COLD
    flow_id: str
    answers: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
