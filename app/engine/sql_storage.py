"""SQLModel database implementation of the Storage interface."""
import json
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, desc, select

from app.engine.storage import Storage
from app.models.db_models import (
    ConversationLogDB,
    ConversationStateDB,
    FAQItemDB,
    FlowDB,
    LeadDB,
    OptOutDB,
    RuleDB,
    RuleTriggerDB,
)
from app.models.events import EngineAction, InspectorInfo, NormalizedEvent
from app.models.faq import FAQItem
from app.models.flow import ConversationState, QualificationFlow
from app.models.leads import Lead
from app.models.rules import TriggerRule


class SQLStorage(Storage):
    """Database-backed storage using SQLModel (compatible with SQLite and Postgres)."""

    def __init__(self, session: Session):
        self.session = session

    def get_rules(self) -> list[TriggerRule]:
        rules_db = self.session.exec(select(RuleDB).where(RuleDB.is_active)).all()
        return [r.to_domain() for r in rules_db]

    def get_rule(self, rule_id: str) -> TriggerRule | None:
        rule_db = self.session.get(RuleDB, rule_id)
        return rule_db.to_domain() if rule_db else None

    def save_rule(self, rule: TriggerRule) -> None:
        rule_db = RuleDB.from_domain(rule)
        self.session.merge(rule_db)
        self.session.commit()

    def delete_rule(self, rule_id: str) -> bool:
        rule_db = self.session.get(RuleDB, rule_id)
        if rule_db:
            self.session.delete(rule_db)
            self.session.commit()
            return True
        return False

    def get_faqs(self) -> list[FAQItem]:
        faqs_db = self.session.exec(select(FAQItemDB).where(FAQItemDB.is_active)).all()
        return [f.to_domain() for f in faqs_db]

    def get_faq(self, faq_id: str) -> FAQItem | None:
        faq_db = self.session.get(FAQItemDB, faq_id)
        return faq_db.to_domain() if faq_db else None

    def save_faq(self, faq: FAQItem) -> None:
        faq_db = FAQItemDB.from_domain(faq)
        self.session.merge(faq_db)
        self.session.commit()

    def delete_faq(self, faq_id: str) -> bool:
        faq_db = self.session.get(FAQItemDB, faq_id)
        if faq_db:
            self.session.delete(faq_db)
            self.session.commit()
            return True
        return False

    def get_flows(self) -> list[QualificationFlow]:
        flows_db = self.session.exec(select(FlowDB)).all()
        return [fl.to_domain() for fl in flows_db]

    def get_flow(self, flow_id: str) -> QualificationFlow | None:
        flow_db = self.session.get(FlowDB, flow_id)
        return flow_db.to_domain() if flow_db else None

    def save_flow(self, flow: QualificationFlow) -> None:
        flow_db = FlowDB.from_domain(flow)
        self.session.merge(flow_db)
        self.session.commit()

    def delete_flow(self, flow_id: str) -> bool:
        flow_db = self.session.get(FlowDB, flow_id)
        if flow_db:
            self.session.delete(flow_db)
            self.session.commit()
            return True
        return False

    def get_state(self, channel: str, user_id: str) -> ConversationState | None:
        state_db = self.session.get(ConversationStateDB, (channel, user_id))
        return state_db.to_domain() if state_db else None

    def save_state(self, state: ConversationState) -> None:
        state_db = ConversationStateDB.from_domain(state)
        self.session.merge(state_db)
        self.session.commit()

    def delete_state(self, channel: str, user_id: str) -> None:
        state_db = self.session.get(ConversationStateDB, (channel, user_id))
        if state_db:
            self.session.delete(state_db)
            self.session.commit()

    def is_opted_out(self, channel: str, user_id: str) -> bool:
        opt_out = self.session.get(OptOutDB, (channel, user_id))
        return opt_out is not None

    def set_opted_out(self, channel: str, user_id: str, opted_out: bool = True) -> None:
        existing = self.session.get(OptOutDB, (channel, user_id))
        if opted_out:
            if not existing:
                self.session.add(OptOutDB(channel=channel, user_id=user_id))
                self.session.commit()
        else:
            if existing:
                self.session.delete(existing)
                self.session.commit()

    def record_rule_trigger(self, user_id: str, rule_id: str) -> None:
        trigger = RuleTriggerDB(
            user_id=user_id,
            rule_id=rule_id,
            triggered_at=datetime.now(UTC),
        )
        self.session.add(trigger)
        self.session.commit()

    def get_last_rule_trigger(self, user_id: str, rule_id: str) -> datetime | None:
        statement = (
            select(RuleTriggerDB)
            .where(RuleTriggerDB.user_id == user_id, RuleTriggerDB.rule_id == rule_id)
            .order_by(desc(RuleTriggerDB.triggered_at))
        )
        trigger = self.session.exec(statement).first()
        if trigger:
            dt = trigger.triggered_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        return None

    def clear_rule_triggers(self, user_id: str) -> None:
        statement = select(RuleTriggerDB).where(RuleTriggerDB.user_id == user_id)
        triggers = self.session.exec(statement).all()
        for t in triggers:
            self.session.delete(t)
        self.session.commit()

    def save_lead(self, lead: Lead) -> None:
        lead_db = LeadDB.from_domain(lead)
        self.session.merge(lead_db)
        self.session.commit()

    def get_leads(self) -> list[Lead]:
        statement = select(LeadDB).order_by(desc(LeadDB.created_at))
        leads_db = self.session.exec(statement).all()
        return [lead.to_domain() for lead in leads_db]

    def log_conversation(
        self,
        event: NormalizedEvent,
        actions: list[EngineAction],
        inspector: InspectorInfo,
    ) -> None:
        log_entry = ConversationLogDB(
            channel=event.channel.value,
            user_id=event.user_id,
            username=event.username,
            event_type=event.event_type.value,
            text=event.text,
            post_id=event.post_id,
            actions_json=json.dumps([a.model_dump() for a in actions]),
            inspector_json=json.dumps(inspector.model_dump()),
            timestamp=event.timestamp,
        )
        self.session.add(log_entry)
        self.session.commit()

    def get_conversation_logs(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        statement = select(ConversationLogDB).order_by(desc(ConversationLogDB.timestamp)).offset(offset).limit(limit)
        entries = self.session.exec(statement).all()
        result = []
        for e in entries:
            result.append(
                {
                    "id": e.id,
                    "channel": e.channel,
                    "user_id": e.user_id,
                    "username": e.username,
                    "event_type": e.event_type,
                    "text": e.text,
                    "post_id": e.post_id,
                    "actions": json.loads(e.actions_json),
                    "inspector": json.loads(e.inspector_json),
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                }
            )
        return result
