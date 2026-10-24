"""Storage layer interface and in-memory implementation."""
from datetime import UTC, datetime
from typing import Any

from app.models.events import EngineAction, InspectorInfo, NormalizedEvent
from app.models.faq import FAQItem
from app.models.flow import ConversationState, QualificationFlow
from app.models.leads import Lead
from app.models.rules import TriggerRule


class Storage:
    """Storage interface for FunnelBot."""

    def get_rules(self) -> list[TriggerRule]:
        raise NotImplementedError

    def get_rule(self, rule_id: str) -> TriggerRule | None:
        raise NotImplementedError

    def save_rule(self, rule: TriggerRule) -> None:
        raise NotImplementedError

    def delete_rule(self, rule_id: str) -> bool:
        raise NotImplementedError

    def get_faqs(self) -> list[FAQItem]:
        raise NotImplementedError

    def get_faq(self, faq_id: str) -> FAQItem | None:
        raise NotImplementedError

    def save_faq(self, faq: FAQItem) -> None:
        raise NotImplementedError

    def delete_faq(self, faq_id: str) -> bool:
        raise NotImplementedError

    def get_flows(self) -> list[QualificationFlow]:
        raise NotImplementedError

    def get_flow(self, flow_id: str) -> QualificationFlow | None:
        raise NotImplementedError

    def save_flow(self, flow: QualificationFlow) -> None:
        raise NotImplementedError

    def delete_flow(self, flow_id: str) -> bool:
        raise NotImplementedError

    def get_state(self, channel: str, user_id: str) -> ConversationState | None:
        raise NotImplementedError

    def save_state(self, state: ConversationState) -> None:
        raise NotImplementedError

    def delete_state(self, channel: str, user_id: str) -> None:
        raise NotImplementedError

    def is_opted_out(self, channel: str, user_id: str) -> bool:
        raise NotImplementedError

    def set_opted_out(self, channel: str, user_id: str, opted_out: bool = True) -> None:
        raise NotImplementedError

    def record_rule_trigger(self, user_id: str, rule_id: str) -> None:
        raise NotImplementedError

    def get_last_rule_trigger(self, user_id: str, rule_id: str) -> datetime | None:
        raise NotImplementedError

    def clear_rule_triggers(self, user_id: str) -> None:
        raise NotImplementedError

    def save_lead(self, lead: Lead) -> None:
        raise NotImplementedError

    def get_leads(self) -> list[Lead]:
        raise NotImplementedError

    def log_conversation(
        self,
        event: NormalizedEvent,
        actions: list[EngineAction],
        inspector: InspectorInfo,
    ) -> None:
        raise NotImplementedError

    def get_conversation_logs(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        raise NotImplementedError


class InMemoryStorage(Storage):
    """Thread-safe, testable in-memory storage implementation."""

    def __init__(self):
        self.rules: dict[str, TriggerRule] = {}
        self.faqs: dict[str, FAQItem] = {}
        self.flows: dict[str, QualificationFlow] = {}
        self.states: dict[tuple[str, str], ConversationState] = {}
        self.opted_out_users: set[tuple[str, str]] = set()
        self.rule_triggers: dict[tuple[str, str], datetime] = {}
        self.leads: list[Lead] = []
        self.logs: list[dict[str, Any]] = []

    def get_rules(self) -> list[TriggerRule]:
        return [r for r in self.rules.values() if r.is_active]

    def get_rule(self, rule_id: str) -> TriggerRule | None:
        return self.rules.get(rule_id)

    def save_rule(self, rule: TriggerRule) -> None:
        self.rules[rule.id] = rule

    def delete_rule(self, rule_id: str) -> bool:
        return self.rules.pop(rule_id, None) is not None

    def get_faqs(self) -> list[FAQItem]:
        return [f for f in self.faqs.values() if f.is_active]

    def get_faq(self, faq_id: str) -> FAQItem | None:
        return self.faqs.get(faq_id)

    def save_faq(self, faq: FAQItem) -> None:
        self.faqs[faq.id] = faq

    def delete_faq(self, faq_id: str) -> bool:
        return self.faqs.pop(faq_id, None) is not None

    def get_flows(self) -> list[QualificationFlow]:
        return list(self.flows.values())

    def get_flow(self, flow_id: str) -> QualificationFlow | None:
        return self.flows.get(flow_id)

    def save_flow(self, flow: QualificationFlow) -> None:
        self.flows[flow.id] = flow

    def delete_flow(self, flow_id: str) -> bool:
        return self.flows.pop(flow_id, None) is not None

    def get_state(self, channel: str, user_id: str) -> ConversationState | None:
        return self.states.get((channel, user_id))

    def save_state(self, state: ConversationState) -> None:
        self.states[(state.channel, state.user_id)] = state

    def delete_state(self, channel: str, user_id: str) -> None:
        self.states.pop((channel, user_id), None)

    def is_opted_out(self, channel: str, user_id: str) -> bool:
        return (channel, user_id) in self.opted_out_users

    def set_opted_out(self, channel: str, user_id: str, opted_out: bool = True) -> None:
        key = (channel, user_id)
        if opted_out:
            self.opted_out_users.add(key)
        else:
            self.opted_out_users.discard(key)

    def record_rule_trigger(self, user_id: str, rule_id: str) -> None:
        self.rule_triggers[(user_id, rule_id)] = datetime.now(UTC)

    def get_last_rule_trigger(self, user_id: str, rule_id: str) -> datetime | None:
        return self.rule_triggers.get((user_id, rule_id))

    def clear_rule_triggers(self, user_id: str) -> None:
        keys_to_remove = [k for k in self.rule_triggers if k[0] == user_id]
        for k in keys_to_remove:
            self.rule_triggers.pop(k, None)

    def save_lead(self, lead: Lead) -> None:
        self.leads.append(lead)

    def get_leads(self) -> list[Lead]:
        return list(self.leads)

    def log_conversation(
        self,
        event: NormalizedEvent,
        actions: list[EngineAction],
        inspector: InspectorInfo,
    ) -> None:
        self.logs.insert(
            0,
            {
                "channel": event.channel.value,
                "user_id": event.user_id,
                "username": event.username,
                "event_type": event.event_type.value,
                "text": event.text,
                "post_id": event.post_id,
                "actions": [a.model_dump() for a in actions],
                "inspector": inspector.model_dump(),
                "timestamp": event.timestamp.isoformat(),
            },
        )

    def get_conversation_logs(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        return self.logs[offset : offset + limit]

    def clear(self) -> None:
        """Reset storage for tests or demo resets."""
        self.rules.clear()
        self.faqs.clear()
        self.flows.clear()
        self.states.clear()
        self.opted_out_users.clear()
        self.rule_triggers.clear()
        self.leads.clear()
        self.logs.clear()
