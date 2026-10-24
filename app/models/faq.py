"""FAQ models for DM automated answers."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FAQConfidence(str, Enum):
    HIGH = "high"       # >= 0.55: auto-answer
    MEDIUM = "medium"   # 0.30 - 0.55: "Did you mean...?" with quick replies
    LOW = "low"         # < 0.30: fallback & flag human takeover


class FAQItem(BaseModel):
    id: str
    question: str
    question_variants: List[str] = Field(default_factory=list)
    answer: str
    category: str = "General"
    is_active: bool = True

    def all_questions(self) -> List[str]:
        """Returns primary question + variants."""
        return [self.question] + [v for v in self.question_variants if v.strip()]


class FAQMatchResult(BaseModel):
    faq: Optional[FAQItem] = None
    matched_query: Optional[str] = None
    score: float = 0.0
    confidence: FAQConfidence = FAQConfidence.LOW
