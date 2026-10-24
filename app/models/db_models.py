"""SQLModel database table definitions for persistent storage."""
import json
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.faq import FAQItem
from app.models.flow import (
    ConversationState,
    ConversationStatus,
    FlowStep,
    LeadTier,
    QualificationFlow,
)
from app.models.leads import Lead
from app.models.rules import MatchMode, TriggerRule


class RuleDB(SQLModel, table=True):
    __tablename__ = "trigger_rules"

    id: str = Field(primary_key=True)
    name: str
    keywords_json: str
    match_mode: str = "contains"
    fuzzy_threshold: float = 80.0
    post_id_scope: str | None = None
    cooldown_seconds: int = 3600
    reply_templates_json: str
    flow_id: str | None = "lead_qualification"
    direct_dm_message: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_domain(self) -> TriggerRule:
        return TriggerRule(
            id=self.id,
            name=self.name,
            keywords=json.loads(self.keywords_json),
            match_mode=MatchMode(self.match_mode),
            fuzzy_threshold=self.fuzzy_threshold,
            post_id_scope=self.post_id_scope,
            cooldown_seconds=self.cooldown_seconds,
            reply_templates=json.loads(self.reply_templates_json),
            flow_id=self.flow_id,
            direct_dm_message=self.direct_dm_message,
            is_active=self.is_active,
        )

    @classmethod
    def from_domain(cls, rule: TriggerRule) -> "RuleDB":
        return cls(
            id=rule.id,
            name=rule.name,
            keywords_json=json.dumps(rule.keywords),
            match_mode=rule.match_mode.value,
            fuzzy_threshold=rule.fuzzy_threshold,
            post_id_scope=rule.post_id_scope,
            cooldown_seconds=rule.cooldown_seconds,
            reply_templates_json=json.dumps(rule.reply_templates),
            flow_id=rule.flow_id,
            direct_dm_message=rule.direct_dm_message,
            is_active=rule.is_active,
        )


class FAQItemDB(SQLModel, table=True):
    __tablename__ = "faq_items"

    id: str = Field(primary_key=True)
    category: str = "General"
    question: str
    question_variants_json: str
    answer: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_domain(self) -> FAQItem:
        return FAQItem(
            id=self.id,
            category=self.category,
            question=self.question,
            question_variants=json.loads(self.question_variants_json),
            answer=self.answer,
            is_active=self.is_active,
        )

    @classmethod
    def from_domain(cls, faq: FAQItem) -> "FAQItemDB":
        return cls(
            id=faq.id,
            category=faq.category,
            question=faq.question,
            question_variants_json=json.dumps(faq.question_variants),
            answer=faq.answer,
            is_active=faq.is_active,
        )


class FlowDB(SQLModel, table=True):
    __tablename__ = "qualification_flows"

    id: str = Field(primary_key=True)
    title: str
    hot_threshold: int = 70
    warm_threshold: int = 40
    closing_messages_json: str
    steps_json: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_domain(self) -> QualificationFlow:
        steps_raw = json.loads(self.steps_json)
        steps = [FlowStep(**s) for s in steps_raw]
        return QualificationFlow(
            id=self.id,
            title=self.title,
            hot_threshold=self.hot_threshold,
            warm_threshold=self.warm_threshold,
            closing_messages=json.loads(self.closing_messages_json),
            steps=steps,
        )

    @classmethod
    def from_domain(cls, flow: QualificationFlow) -> "FlowDB":
        return cls(
            id=flow.id,
            title=flow.title,
            hot_threshold=flow.hot_threshold,
            warm_threshold=flow.warm_threshold,
            closing_messages_json=json.dumps(flow.closing_messages),
            steps_json=json.dumps([s.model_dump() for s in flow.steps]),
        )


class ConversationStateDB(SQLModel, table=True):
    __tablename__ = "conversation_states"

    channel: str = Field(primary_key=True)
    user_id: str = Field(primary_key=True)
    username: str | None = None
    flow_id: str | None = None
    current_step_id: str | None = None
    collected_answers_json: str = "{}"
    score: int = 0
    status: str = "active"
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_domain(self) -> ConversationState:
        return ConversationState(
            channel=self.channel,
            user_id=self.user_id,
            username=self.username,
            flow_id=self.flow_id,
            current_step_id=self.current_step_id,
            collected_answers=json.loads(self.collected_answers_json),
            score=self.score,
            status=ConversationStatus(self.status),
            last_activity_at=self.last_activity_at,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, state: ConversationState) -> "ConversationStateDB":
        return cls(
            channel=state.channel,
            user_id=state.user_id,
            username=state.username,
            flow_id=state.flow_id,
            current_step_id=state.current_step_id,
            collected_answers_json=json.dumps(state.collected_answers),
            score=state.score,
            status=state.status.value,
            last_activity_at=state.last_activity_at,
            created_at=state.created_at,
        )


class RuleTriggerDB(SQLModel, table=True):
    __tablename__ = "rule_triggers"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    rule_id: str = Field(index=True)
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LeadDB(SQLModel, table=True):
    __tablename__ = "leads"

    id: str = Field(primary_key=True)
    user_id: str
    username: str | None = None
    channel: str = "simulator"
    email: str | None = Field(default=None, index=True)
    score: int = 0
    tier: str = Field(default="COLD", index=True)
    flow_id: str
    answers_json: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_domain(self) -> Lead:
        return Lead(
            id=self.id,
            user_id=self.user_id,
            username=self.username,
            channel=self.channel,
            email=self.email,
            score=self.score,
            tier=LeadTier(self.tier),
            flow_id=self.flow_id,
            answers=json.loads(self.answers_json),
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, lead: Lead) -> "LeadDB":
        return cls(
            id=lead.id,
            user_id=lead.user_id,
            username=lead.username,
            channel=lead.channel,
            email=lead.email,
            score=lead.score,
            tier=lead.tier.value,
            flow_id=lead.flow_id,
            answers_json=json.dumps(lead.answers),
            created_at=lead.created_at,
        )


class OptOutDB(SQLModel, table=True):
    __tablename__ = "opt_outs"

    channel: str = Field(primary_key=True)
    user_id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConversationLogDB(SQLModel, table=True):
    __tablename__ = "conversation_logs"

    id: int | None = Field(default=None, primary_key=True)
    channel: str
    user_id: str
    username: str | None = None
    event_type: str
    text: str
    post_id: str | None = None
    actions_json: str = "[]"
    inspector_json: str = "{}"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
