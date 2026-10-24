"""Tests for master FunnelEngine (triggers, flow progression, interruptions, cooldowns)."""
from app.engine.funnel_engine import FunnelEngine
from app.models.events import ActionType, Channel, EventType, NormalizedEvent


def test_comment_keyword_trigger_and_flow_initiation(engine: FunnelEngine):
    # User comments "Can you send the guide please?"
    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.COMMENT,
        user_id="user_recruiter",
        username="recruiter_demo",
        text="Can you send the guide please?",
        post_id="post_1",
    )

    result = engine.process_event(event)

    # Must produce: 1 public reply + 1 DM initiating the qualification flow
    assert len(result.actions) == 2

    # 1. Public comment reply
    reply_action = result.actions[0]
    assert reply_action.action_type == ActionType.REPLY_COMMENT
    assert "@recruiter_demo" in reply_action.text

    # 2. Direct message initiating flow
    dm_action = result.actions[1]
    assert dm_action.action_type == ActionType.SEND_DM
    assert "What are you looking to achieve" in dm_action.text

    # Inspector Info checks
    assert result.inspector_info.matched_rule == "Free Guide Automation"
    assert result.inspector_info.keyword_matched == "guide"
    assert result.inspector_info.flow_state["status"] == "active"


def test_comment_cooldown_deduplication(engine: FunnelEngine):
    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.COMMENT,
        user_id="user_repeat",
        username="repeat_user",
        text="GUIDE",
        post_id="post_1",
    )

    # First comment triggers actions
    res1 = engine.process_event(event)
    assert len(res1.actions) == 2

    # Second comment immediately after should be blocked by cooldown
    res2 = engine.process_event(event)
    assert len(res2.actions) == 0
    assert any("Duplicate trigger blocked by cooldown" in note for note in res2.inspector_info.execution_notes)


def test_qualification_flow_full_walkthrough_hot_lead(engine: FunnelEngine):
    user_id = "user_hot_lead"
    username = "jane_doe"

    # 1. Start flow via comment
    engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.COMMENT,
            user_id=user_id,
            username=username,
            text="send me the guide",
        )
    )

    # 2. Step 1: Goal -> Choice 1 (Scale sales = 30 pts)
    res_s1 = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="1",
        )
    )
    assert "budget" in res_s1.actions[0].text.lower()
    assert res_s1.inspector_info.lead_score == 30

    # 3. Step 2: Budget -> Choice 1 ($1,000 - $3,000+ = 30 pts)
    res_s2 = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="$1,000 - $3,000+ / month",
        )
    )
    assert "launch" in res_s2.actions[0].text.lower()
    assert res_s2.inspector_info.lead_score == 60

    # 4. Step 3: Timeline -> Choice 1 (Immediately = 20 pts)
    res_s3 = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="immediately",
        )
    )
    assert "email" in res_s3.actions[0].text.lower()
    assert res_s3.inspector_info.lead_score == 80

    # 5. Step 4: Email -> valid email (+20 pts -> 100 pts -> HOT lead)
    res_s4 = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="jane@growthcorp.com",
        )
    )
    assert res_s4.inspector_info.lead_score == 100
    assert res_s4.inspector_info.lead_tier == "HOT"
    assert any("cal.com" in a.text for a in res_s4.actions if a.text)

    # Check lead persisted
    leads = engine.storage.get_leads()
    assert any(lead.email == "jane@growthcorp.com" and lead.tier.value == "HOT" for lead in leads)


def test_faq_interruption_mid_flow(engine: FunnelEngine):
    user_id = "user_curious"
    username = "curious_user"

    # 1. Trigger flow
    engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.COMMENT,
            user_id=user_id,
            username=username,
            text="GUIDE",
        )
    )

    # 2. User is at Step 1. Instead of answering the question, asks an FAQ:
    res_faq = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="Where is your company located?",
        )
    )

    # Should output 2 messages:
    # 1. FAQ answer ("We are a remote-first team based across San Francisco and London...")
    # 2. Resume flow step ("Back to your question...\nWhat are you looking to achieve...")
    assert len(res_faq.actions) == 2
    assert "San Francisco" in res_faq.actions[0].text
    assert "Back to your question" in res_faq.actions[1].text
    assert "What are you looking to achieve" in res_faq.actions[1].text

    # 3. User now answers the resumed step 1 with "sales"
    res_next = engine.process_event(
        NormalizedEvent(
            channel=Channel.SIMULATOR,
            event_type=EventType.DM,
            user_id=user_id,
            username=username,
            text="sales",
        )
    )
    assert "budget" in res_next.actions[0].text.lower()


def test_standalone_faq_direct_dm(engine: FunnelEngine):
    # Direct DM asking about setup time with no active flow
    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.DM,
        user_id="user_visitor",
        username="visitor",
        text="How long does setup take?",
    )
    res = engine.process_event(event)

    assert len(res.actions) == 1
    assert "48 to 72 hours" in res.actions[0].text
    assert res.inspector_info.faq_match["confidence"] == "high"


def test_standalone_unrecognized_dm_triggers_fallback(engine: FunnelEngine):
    # Gibberish or irrelevant DM
    event = NormalizedEvent(
        channel=Channel.SIMULATOR,
        event_type=EventType.DM,
        user_id="user_alien",
        username="alien",
        text="quantum teleportation recipe for dinner",
    )
    res = engine.process_event(event)

    assert len(res.actions) == 2
    assert any("automated assistant" in a.text for a in res.actions)
    assert any(a.action_type == ActionType.NOTIFY for a in res.actions)
    assert res.inspector_info.faq_match["confidence"] == "low"
