"""Unit tests for SQLStorage database persistence."""
from sqlmodel import Session

from app.engine.sql_storage import SQLStorage
from app.models.events import (
    ActionType,
    Channel,
    EngineAction,
    EventType,
    InspectorInfo,
    NormalizedEvent,
)
from app.models.faq import FAQItem
from app.models.flow import ConversationState, ConversationStatus
from app.models.rules import MatchMode, TriggerRule


def test_sql_storage_rules(test_db_session: Session):
    storage = SQLStorage(test_db_session)

    # Save custom rule
    rule = TriggerRule(
        id="sql_rule_1",
        name="SQL Rule",
        keywords=["database", "sql"],
        match_mode=MatchMode.CONTAINS,
    )
    storage.save_rule(rule)

    # Retrieve rule
    fetched = storage.get_rule("sql_rule_1")
    assert fetched is not None
    assert fetched.name == "SQL Rule"

    # Delete rule
    deleted = storage.delete_rule("sql_rule_1")
    assert deleted is True
    assert storage.get_rule("sql_rule_1") is None


def test_sql_storage_faqs(test_db_session: Session):
    storage = SQLStorage(test_db_session)

    faq = FAQItem(
        id="sql_faq_1",
        category="Tech",
        question="How does SQL persistence work?",
        question_variants=["Database persistence details"],
        answer="It uses SQLModel with SQLite or Postgres.",
    )
    storage.save_faq(faq)

    fetched = storage.get_faq("sql_faq_1")
    assert fetched is not None
    assert fetched.question == "How does SQL persistence work?"

    deleted = storage.delete_faq("sql_faq_1")
    assert deleted is True
    assert storage.get_faq("sql_faq_1") is None


def test_sql_storage_flows(test_db_session: Session):
    storage = SQLStorage(test_db_session)
    flows = storage.get_flows()
    assert len(flows) >= 1
    assert any(f.id == "lead_qualification" for f in flows)


def test_sql_storage_state_and_triggers(test_db_session: Session):
    storage = SQLStorage(test_db_session)
    user_id = "test_user_sql"
    channel = "simulator"

    # Save state
    state = ConversationState(
        user_id=user_id,
        channel=channel,
        flow_id="lead_qualification",
        current_step_id="step_goal",
        score=20,
        status=ConversationStatus.ACTIVE,
    )
    storage.save_state(state)

    fetched_state = storage.get_state(channel, user_id)
    assert fetched_state is not None
    assert fetched_state.score == 20

    # Delete state
    storage.delete_state(channel, user_id)
    assert storage.get_state(channel, user_id) is None

    # Opt-out
    assert storage.is_opted_out(channel, user_id) is False
    storage.set_opted_out(channel, user_id, True)
    assert storage.is_opted_out(channel, user_id) is True
    storage.set_opted_out(channel, user_id, False)
    assert storage.is_opted_out(channel, user_id) is False

    # Trigger record
    storage.record_rule_trigger(user_id, "rule_guide")
    last_trig = storage.get_last_rule_trigger(user_id, "rule_guide")
    assert last_trig is not None


def test_sql_storage_logging(test_db_session: Session):
    storage = SQLStorage(test_db_session)
    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.COMMENT,
        user_id="logger_user",
        username="logger",
        text="GUIDE",
    )
    actions = [
        EngineAction(
            action_type=ActionType.REPLY_COMMENT,
            channel=Channel.SIMULATOR,
            user_id="logger_user",
            text="Sent!",
        )
    ]
    inspector = InspectorInfo(matched_rule="Free Guide Automation")

    storage.log_conversation(event, actions, inspector)
    logs = storage.get_conversation_logs(limit=5)
    assert len(logs) >= 1
    assert logs[0]["user_id"] == "logger_user"
