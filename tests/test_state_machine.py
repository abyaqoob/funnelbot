"""Tests for StateMachine (choices, regex email validation, scoring, tiers, and 24h expiration)."""
from datetime import UTC, datetime, timedelta

import pytest

from app.engine.state_machine import StateMachine
from app.engine.storage import InMemoryStorage
from app.models.events import ActionType, Channel
from app.models.flow import (
    ConversationStatus,
    FlowChoice,
    FlowStep,
    FlowStepType,
    LeadTier,
    QualificationFlow,
)


@pytest.fixture
def flow():
    return QualificationFlow(
        id="test_flow",
        title="Test Qualification",
        hot_threshold=50,
        warm_threshold=30,
        closing_messages={
            "HOT": "HOT closing message",
            "WARM": "WARM closing message",
            "COLD": "COLD closing message",
        },
        steps=[
            FlowStep(
                id="s1",
                prompt="Select your package:",
                step_type=FlowStepType.CHOICE,
                choices=[
                    FlowChoice(id="c_starter", label="Starter Package", points=10, synonyms=["1", "a", "starter"]),
                    FlowChoice(id="c_pro", label="Pro Package", points=30, synonyms=["2", "b", "pro", "enterprise"]),
                ],
            ),
            FlowStep(
                id="s2",
                prompt="Enter your email:",
                step_type=FlowStepType.EMAIL,
                points_on_valid=25,
                error_message="Invalid email. Please provide name@example.com",
            ),
        ],
    )


def test_start_flow(empty_storage: InMemoryStorage, flow: QualificationFlow):
    sm = StateMachine(empty_storage)
    state, actions = sm.start_flow(Channel.SIMULATOR, "user_123", "alice", flow)

    assert state.user_id == "user_123"
    assert state.current_step_id == "s1"
    assert state.score == 0
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.SEND_DM
    assert "Starter Package" in actions[0].text


def test_choice_matching_variations(empty_storage: InMemoryStorage, flow: QualificationFlow):
    sm = StateMachine(empty_storage)
    choices = flow.steps[0].choices

    # Match by number
    assert sm.match_choice("1", choices).id == "c_starter"
    assert sm.match_choice("2", choices).id == "c_pro"

    # Match by letter
    assert sm.match_choice("a", choices).id == "c_starter"
    assert sm.match_choice("b", choices).id == "c_pro"

    # Match by synonym
    assert sm.match_choice("starter", choices).id == "c_starter"
    assert sm.match_choice("enterprise", choices).id == "c_pro"

    # Fuzzy match
    assert sm.match_choice("Pro pack", choices).id == "c_pro"

    # Non match
    assert sm.match_choice("something unrelated", choices) is None


def test_email_validation_invalid_and_valid(empty_storage: InMemoryStorage, flow: QualificationFlow):
    sm = StateMachine(empty_storage)
    state, _ = sm.start_flow(Channel.SIMULATOR, "user_1", "bob", flow)

    # Complete step 1
    state, _, is_valid = sm.process_step_input(state, flow, "2", Channel.SIMULATOR)
    assert is_valid is True
    assert state.current_step_id == "s2"
    assert state.score == 30

    # Step 2: Invalid email
    state, actions, is_valid = sm.process_step_input(state, flow, "not_an_email", Channel.SIMULATOR)
    assert is_valid is False
    assert state.current_step_id == "s2"  # does not advance
    assert state.score == 30  # no points added
    assert len(actions) == 1
    assert "Invalid email" in actions[0].text

    # Step 2: Valid email
    state, actions, is_valid = sm.process_step_input(state, flow, "bob@example.com", Channel.SIMULATOR)
    assert is_valid is True
    assert state.status == ConversationStatus.COMPLETED
    assert state.score == 55  # 30 + 25

    # Check lead generated
    leads = empty_storage.get_leads()
    assert len(leads) == 1
    lead = leads[0]
    assert lead.email == "bob@example.com"
    assert lead.score == 55
    assert lead.tier == LeadTier.HOT


def test_lead_tiers_warm_and_cold(empty_storage: InMemoryStorage, flow: QualificationFlow):
    sm = StateMachine(empty_storage)

    # 1. Warm Lead (Starter=10 + Email=25 -> 35, threshold hot=50, warm=30)
    state, _ = sm.start_flow(Channel.SIMULATOR, "user_warm", "charlie", flow)
    sm.process_step_input(state, flow, "1", Channel.SIMULATOR)  # +10
    state, actions, _ = sm.process_step_input(state, flow, "charlie@warm.com", Channel.SIMULATOR)  # +25
    assert state.score == 35
    assert empty_storage.get_leads()[-1].tier == LeadTier.WARM
    assert "WARM closing message" in actions[0].text

    # 2. Cold Lead (Flow where score < 30)
    flow_no_email_pts = flow.model_copy(deep=True)
    flow_no_email_pts.steps[1].points_on_valid = 0
    state2, _ = sm.start_flow(Channel.SIMULATOR, "user_cold", "david", flow_no_email_pts)
    sm.process_step_input(state2, flow_no_email_pts, "1", Channel.SIMULATOR)  # +10
    state2, actions2, _ = sm.process_step_input(state2, flow_no_email_pts, "david@cold.com", Channel.SIMULATOR)  # +0
    assert state2.score == 10
    assert empty_storage.get_leads()[-1].tier == LeadTier.COLD
    assert "COLD closing message" in actions2[0].text


def test_state_expiration_24h(empty_storage: InMemoryStorage, flow: QualificationFlow):
    sm = StateMachine(empty_storage)
    state, _ = sm.start_flow(Channel.SIMULATOR, "user_exp", "eve", flow)

    # Set last activity to 25 hours ago
    state.last_activity_at = datetime.now(UTC) - timedelta(hours=25)
    assert state.is_expired(timeout_seconds=86400) is True

    # Fresh state is not expired
    fresh_state = state.model_copy()
    fresh_state.last_activity_at = datetime.now(UTC)
    assert fresh_state.is_expired(timeout_seconds=86400) is False
