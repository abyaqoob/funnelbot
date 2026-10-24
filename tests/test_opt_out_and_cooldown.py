"""Tests for opt-out compliance, stop commands, and human takeover requests."""
from app.engine.funnel_engine import FunnelEngine
from app.models.events import ActionType, Channel, EventType, NormalizedEvent
from app.models.flow import ConversationStatus


def test_global_opt_out_via_stop_command(engine: FunnelEngine):
    user_id = "user_optout_test"
    username = "optout_user"

    # Start a conversation
    engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="/start",
        )
    )

    # User sends STOP
    res_stop = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="STOP",
        )
    )

    # Confirmation sent
    assert len(res_stop.actions) == 1
    assert "unsubscribed" in res_stop.actions[0].text.lower()
    assert res_stop.inspector_info.is_opted_out is True

    # State updated
    state = engine.storage.get_state(Channel.SIMULATOR.value, user_id)
    assert state.status == ConversationStatus.OPTED_OUT

    # Subsequent comment is completely ignored
    res_comment = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.COMMENT,
            user_id=user_id,
            username=username,
            text="GUIDE",
        )
    )
    assert len(res_comment.actions) == 0
    assert res_comment.inspector_info.is_opted_out is True

    # Subsequent DM is completely ignored
    res_dm = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="Hello are you there?",
        )
    )
    assert len(res_dm.actions) == 0
    assert res_dm.inspector_info.is_opted_out is True


def test_human_takeover_request(engine: FunnelEngine):
    user_id = "user_human_req"
    username = "human_user"

    # User in middle of flow requests human
    engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="/start",
        )
    )

    res_human = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="I want to speak with a human",
        )
    )

    # Must notify team and inform user
    assert any("team member" in a.text.lower() for a in res_human.actions)
    assert any(a.action_type == ActionType.NOTIFY for a in res_human.actions)

    state = engine.storage.get_state(Channel.SIMULATOR.value, user_id)
    assert state.status == ConversationStatus.HANDED_OFF
