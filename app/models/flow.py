"""Lead qualification flow and state machine models."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LeadTier(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class FlowStepType(str, Enum):
    CHOICE = "choice"
    TEXT = "text"
    EMAIL = "email"


class FlowChoice(BaseModel):
    id: str
    label: str
    points: int = 0
    synonyms: List[str] = Field(default_factory=list)


class FlowStep(BaseModel):
    id: str
    prompt: str
    step_type: FlowStepType = FlowStepType.CHOICE
    choices: List[FlowChoice] = Field(default_factory=list)
    validation_regex: Optional[str] = None
    error_message: Optional[str] = "Please provide a valid answer to continue."
    points_on_valid: int = 0


class QualificationFlow(BaseModel):
    id: str
    title: str
    steps: List[FlowStep]
    hot_threshold: int = 70
    warm_threshold: int = 40
    closing_messages: Dict[str, str] = Field(
        default_factory=lambda: {
            "HOT": "🔥 You're an ideal fit! Book your 1-on-1 strategy call with our senior specialist here: https://cal.com/funnelbot/priority-call",
            "WARM": "⚡ Thanks for the info! We've sent our Advanced Automation Blueprint to your inbox. Let's stay in touch!",
            "COLD": "🌱 Thank you! Here is our Free Starter Checklist to begin automating your workflows: https://example.com/starter-kit.pdf",
        }
    )

    def get_step(self, step_id: str) -> Optional[FlowStep]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_first_step(self) -> Optional[FlowStep]:
        return self.steps[0] if self.steps else None

    def get_next_step(self, current_step_id: str) -> Optional[FlowStep]:
        for i, step in enumerate(self.steps):
            if step.id == current_step_id:
                if i + 1 < len(self.steps):
                    return self.steps[i + 1]
                return None
        return None


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    HANDED_OFF = "handed_off"
    OPTED_OUT = "opted_out"


class ConversationState(BaseModel):
    user_id: str
    username: Optional[str] = None
    channel: str = "simulator"
    flow_id: Optional[str] = None
    current_step_id: Optional[str] = None
    collected_answers: Dict[str, Any] = Field(default_factory=dict)
    score: int = 0
    status: ConversationStatus = ConversationStatus.ACTIVE
    pending_resume_step_id: Optional[str] = None
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self, timeout_seconds: int = 86400) -> bool:
        """Check if state expired (default 24h)."""
        now = datetime.now(timezone.utc)
        diff = (now - self.last_activity_at).total_seconds()
        return diff > timeout_seconds
