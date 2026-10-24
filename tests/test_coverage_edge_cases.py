"""Additional tests targeting uncovered edge cases to maximize engine test coverage."""
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.engine.funnel_engine import FunnelEngine
from app.engine.llm_fallback import LLMProvider
from app.engine.storage import InMemoryStorage
from app.models.events import Channel, EventType, NormalizedEvent
from app.models.flow import ConversationState, ConversationStatus
from app.models.rules import TriggerRule


def test_already_opted_out_subsequent_stop(engine: FunnelEngine):
    user_id = "user_double_stop"
    engine.storage.set_opted_out(Channel.SIMULATOR.value, user_id, True)

    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.DM,
        user_id=user_id,
        username="double_stop",
        text="STOP",
    )
    res = engine.process_event(event)
    assert len(res.actions) == 1
    assert "unsubscribed" in res.actions[0].text.lower()


def test_comment_direct_dm_without_flow(empty_storage: InMemoryStorage):
    # Rule that sends a direct DM without a qualification flow
    empty_storage.save_rule(
        TriggerRule(
            id="rule_direct",
            name="Direct Rule",
            keywords=["direct"],
            flow_id=None,
            direct_dm_message="Here is your direct DM!",
        )
    )
    engine = FunnelEngine(storage=empty_storage)

    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.COMMENT,
        user_id="user_dir",
        username="direct_user",
        text="direct",
    )
    res = engine.process_event(event)
    assert len(res.actions) == 2
    assert res.actions[1].text == "Here is your direct DM!"


def test_expired_state_reset_on_dm(engine: FunnelEngine):
    user_id = "user_exp_dm"
    # Seed an expired state
    old_time = datetime.now(UTC) - timedelta(hours=30)
    expired_state = ConversationState(
        user_id=user_id,
        channel=Channel.SIMULATOR.value,
        flow_id="lead_qualification",
        current_step_id="step_goal",
        status=ConversationStatus.ACTIVE,
        last_activity_at=old_time,
    )
    engine.storage.save_state(expired_state)

    # User sends a normal DM
    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.DM,
        user_id=user_id,
        username="exp_user",
        text="How long does setup take?",
    )
    res = engine.process_event(event)
    # The expired state should be marked EXPIRED and treated as standalone DM FAQ answer
    assert any("48 to 72 hours" in a.text for a in res.actions)


def test_medium_confidence_faq_interruption_mid_flow(engine: FunnelEngine):
    user_id = "user_med_mid"
    # Start flow
    engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username="med_mid",
            text="/start",
        )
    )

    # In Step 1, user asks a partial query ("service timeline") which matches with medium confidence
    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.DM,
        user_id=user_id,
        username="med_mid",
        text="service timeline",
    )
    res = engine.process_event(event)
    assert len(res.actions) == 1
    assert "Did you mean" in res.actions[0].text
    assert "Back to our question" in res.actions[0].text


def test_standalone_dm_with_mocked_llm(seeded_storage: InMemoryStorage):
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.generate_reply.return_value = "This is a smart AI fallback answer."
    engine = FunnelEngine(storage=seeded_storage, llm_provider=mock_llm)

    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.DM,
        user_id="user_llm_test",
        username="llm_user",
        text="quantum teleportation recipe for dinner",
    )
    res = engine.process_event(event)
    assert len(res.actions) == 1
    assert res.actions[0].text == "This is a smart AI fallback answer."
