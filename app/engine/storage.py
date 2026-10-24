"""Storage layer interface and in-memory implementation."""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from app.models.faq import FAQItem
from app.models.flow import ConversationState, ConversationStatus, QualificationFlow
from app.models.leads import Lead
from app.models.rules import TriggerRule


class Storage:
    """Storage interface for FunnelBot."""

    def get_rules(self) -> List[TriggerRule]:
        raise NotImplementedError

    def get_rule(self, rule_id: str) -> Optional[TriggerRule]:
        raise NotImplementedError

    def save_rule(self, rule: TriggerRule) -> None:
        raise NotImplementedError

    def get_faqs(self) -> List[FAQItem]:
        raise NotImplementedError

    def save_faq(self, faq: FAQItem) -> None:
        raise NotImplementedError

    def get_flow(self, flow_id: str) -> Optional[QualificationFlow]:
        raise NotImplementedError

    def save_flow(self, flow: QualificationFlow) -> None:
        raise NotImplementedError

    def get_state(self, channel: str, user_id: str) -> Optional[ConversationState]:
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

    def get_last_rule_trigger(self, user_id: str, rule_id: str) -> Optional[datetime]:
        raise NotImplementedError

    def save_lead(self, lead: Lead) -> None:
        raise NotImplementedError

    def get_leads(self) -> List[Lead]:
        raise NotImplementedError


class InMemoryStorage(Storage):
    """Thread-safe, testable in-memory storage implementation."""

    def __init__(self):
        self.rules: Dict[str, TriggerRule] = {}
        self.faqs: Dict[str, FAQItem] = {}
        self.flows: Dict[str, QualificationFlow] = {}
        self.states: Dict[Tuple[str, str], ConversationState] = {}
        self.opted_out_users: Set[Tuple[str, str]] = set()
        self.rule_triggers: Dict[Tuple[str, str], datetime] = {}
        self.leads: List[Lead] = []

    def get_rules(self) -> List[TriggerRule]:
        return [r for r in self.rules.values() if r.is_active]

    def get_rule(self, rule_id: str) -> Optional[TriggerRule]:
        return self.rules.get(rule_id)

    def save_rule(self, rule: TriggerRule) -> None:
        self.rules[rule.id] = rule

    def get_faqs(self) -> List[FAQItem]:
        return [f for f in self.faqs.values() if f.is_active]

    def save_faq(self, faq: FAQItem) -> None:
        self.faqs[faq.id] = faq

    def get_flow(self, flow_id: str) -> Optional[QualificationFlow]:
        return self.flows.get(flow_id)

    def save_flow(self, flow: QualificationFlow) -> None:
        self.flows[flow.id] = flow

    def get_state(self, channel: str, user_id: str) -> Optional[ConversationState]:
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
        self.rule_triggers[(user_id, rule_id)] = datetime.now(timezone.utc)

    def get_last_rule_trigger(self, user_id: str, rule_id: str) -> Optional[datetime]:
        return self.rule_triggers.get((user_id, rule_id))

    def save_lead(self, lead: Lead) -> None:
        self.leads.append(lead)

    def get_leads(self) -> List[Lead]:
        return list(self.leads)

    def clear(self) -> None:
        """Reset storage for tests or demo resets."""
        self.rules.clear()
        self.faqs.clear()
        self.flows.clear()
        self.states.clear()
        self.opted_out_users.clear()
        self.rule_triggers.clear()
        self.leads.clear()
