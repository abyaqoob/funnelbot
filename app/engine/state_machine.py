"""State machine for lead qualification flows, interruptions, and global commands."""
import re
from datetime import datetime, timezone

from rapidfuzz import fuzz

from app.engine.storage import Storage

UTC = timezone.utc
from app.models.events import ActionType, Channel, EngineAction
from app.models.flow import (
    ConversationState,
    ConversationStatus,
    FlowChoice,
    FlowStep,
    FlowStepType,
    LeadTier,
    QualificationFlow,
)
from app.models.leads import Lead

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$")
OPT_OUT_COMMANDS = {"stop", "unsubscribe", "cancel", "optout", "opt-out", "quit"}
HUMAN_TAKEOVER_COMMANDS = {"human", "agent", "support", "representative", "real person", "help"}


class StateMachine:
    """Manages conversational state, qualification transitions, scoring, and interruptions."""

    def __init__(self, storage: Storage):
        self.storage = storage

    @staticmethod
    def is_opt_out_command(text: str) -> bool:
        """Check if user entered an opt-out keyword."""
        return text.strip().lower() in OPT_OUT_COMMANDS

    @staticmethod
    def is_human_takeover_command(text: str) -> bool:
        """Check if user requested a human operator."""
        clean = text.strip().lower()
        if clean in HUMAN_TAKEOVER_COMMANDS:
            return True
        words = set(re.findall(r"\b\w+\b", clean))
        takeover_words = {"human", "agent", "representative", "support"}
        if words.intersection(takeover_words):
            if any(phrase in clean for phrase in ["talk to", "speak to", "speak with", "talk with", "need a", "want a", "transfer to"]):
                return True
            if len(words) <= 2:
                return True
        return False

    def start_flow(
        self, channel: Channel, user_id: str, username: str | None, flow: QualificationFlow
    ) -> tuple[ConversationState, list[EngineAction]]:
        """Initialize or reset a conversation to the first step of a flow."""
        first_step = flow.get_first_step()
        if not first_step:
            raise ValueError(f"Flow {flow.id} has no steps.")

        now = datetime.now(UTC)
        state = ConversationState(
            user_id=user_id,
            username=username,
            channel=channel.value,
            flow_id=flow.id,
            current_step_id=first_step.id,
            collected_answers={},
            score=0,
            status=ConversationStatus.ACTIVE,
            last_activity_at=now,
            created_at=now,
        )
        self.storage.save_state(state)

        # Build prompt action
        prompt_text = self.format_step_prompt(first_step)
        quick_replies = [c.label for c in first_step.choices] if first_step.choices else None

        action = EngineAction(
            action_type=ActionType.SEND_DM,
            channel=channel,
            user_id=user_id,
            username=username,
            text=prompt_text,
            quick_replies=quick_replies,
        )
        return state, [action]

    def format_step_prompt(self, step: FlowStep) -> str:
        """Format step prompt with numbered choices if applicable."""
        if step.step_type != FlowStepType.CHOICE or not step.choices:
            return step.prompt

        lines = [step.prompt, ""]
        for idx, choice in enumerate(step.choices, 1):
            lines.append(f"{idx}. {choice.label}")
        return "\n".join(lines)

    def match_choice(self, user_text: str, choices: list[FlowChoice]) -> FlowChoice | None:
        """Match user input to one of the choices via index, exact name, synonym, or fuzzy."""
        clean = user_text.strip().lower()

        # 1. Number index match (e.g. "1", "2")
        if clean.isdigit():
            idx = int(clean) - 1
            if 0 <= idx < len(choices):
                return choices[idx]

        # 2. Letter match (e.g. "a", "b", "c")
        if len(clean) == 1 and clean.isalpha():
            idx = ord(clean) - ord("a")
            if 0 <= idx < len(choices):
                return choices[idx]

        # 3. Exact or synonym match
        for choice in choices:
            if clean == choice.label.strip().lower() or clean == choice.id.lower():
                return choice
            for syn in choice.synonyms:
                if clean == syn.strip().lower():
                    return choice

        # 4. Contains or fuzzy match
        best_choice = None
        best_score = 0.0

        for choice in choices:
            label_lower = choice.label.strip().lower()
            if label_lower in clean or clean in label_lower:
                return choice

            score = fuzz.partial_ratio(clean, label_lower)
            if score > best_score:
                best_score = float(score)
                best_choice = choice

        if best_score >= 70.0 and best_choice is not None:
            return best_choice

        return None

    def process_step_input(
        self,
        state: ConversationState,
        flow: QualificationFlow,
        user_text: str,
        channel: Channel,
        username: str | None = None,
    ) -> tuple[ConversationState, list[EngineAction], bool]:
        """
        Processes user text against current step.
        Returns: (updated_state, actions, is_valid_input)
        """
        current_step = flow.get_step(state.current_step_id or "")
        if not current_step:
            return state, [], False

        actions: list[EngineAction] = []
        is_valid = False

        if current_step.step_type == FlowStepType.EMAIL:
            # Clean and validate email
            clean_email = user_text.strip()
            # If text has multiple words, look for an email token
            tokens = clean_email.split()
            matched_email = None
            for t in tokens:
                token_clean = t.strip("<>()[],;:")
                if EMAIL_REGEX.match(token_clean):
                    matched_email = token_clean
                    break

            if matched_email:
                is_valid = True
                state.collected_answers[current_step.id] = matched_email
                state.score += current_step.points_on_valid
            else:
                err_msg = current_step.error_message or "Please provide a valid email address (e.g., name@example.com) to continue."
                action = EngineAction(
                    action_type=ActionType.SEND_DM,
                    channel=channel,
                    user_id=state.user_id,
                    username=username or state.username,
                    text=err_msg,
                )
                return state, [action], False

        elif current_step.step_type == FlowStepType.CHOICE:
            choice = self.match_choice(user_text, current_step.choices)
            if choice:
                is_valid = True
                state.collected_answers[current_step.id] = choice.label
                state.score += choice.points
            else:
                return state, [], False

        elif current_step.step_type == FlowStepType.TEXT:
            if user_text.strip():
                is_valid = True
                state.collected_answers[current_step.id] = user_text.strip()
                state.score += current_step.points_on_valid
            else:
                return state, [], False

        state.last_activity_at = datetime.now(UTC)

        # Move to next step or complete flow
        next_step = flow.get_next_step(current_step.id)
        if next_step:
            state.current_step_id = next_step.id
            prompt_text = self.format_step_prompt(next_step)
            quick_replies = [c.label for c in next_step.choices] if next_step.choices else None

            actions.append(
                EngineAction(
                    action_type=ActionType.SEND_DM,
                    channel=channel,
                    user_id=state.user_id,
                    username=username or state.username,
                    text=prompt_text,
                    quick_replies=quick_replies,
                )
            )
            self.storage.save_state(state)
        else:
            # Complete the flow
            state.status = ConversationStatus.COMPLETED
            state.current_step_id = None
            self.storage.save_state(state)

            # Determine Lead Tier
            if state.score >= flow.hot_threshold:
                tier = LeadTier.HOT
            elif state.score >= flow.warm_threshold:
                tier = LeadTier.WARM
            else:
                tier = LeadTier.COLD

            # Extract email if present
            email = None
            for step in flow.steps:
                if step.step_type == FlowStepType.EMAIL:
                    email = state.collected_answers.get(step.id)

            lead = Lead(
                id=f"lead_{state.user_id}_{int(datetime.now(UTC).timestamp())}",
                user_id=state.user_id,
                username=username or state.username,
                channel=channel.value,
                email=email,
                score=state.score,
                tier=tier,
                flow_id=flow.id,
                answers=state.collected_answers,
            )
            self.storage.save_lead(lead)

            # Closing message
            closing_msg = flow.closing_messages.get(
                tier.value,
                "Thank you for sharing your information! We'll be in touch.",
            )

            actions.append(
                EngineAction(
                    action_type=ActionType.SEND_DM,
                    channel=channel,
                    user_id=state.user_id,
                    username=username or state.username,
                    text=closing_msg,
                )
            )
            actions.append(
                EngineAction(
                    action_type=ActionType.TAG_LEAD,
                    channel=channel,
                    user_id=state.user_id,
                    username=username or state.username,
                    text=tier.value,
                    metadata={"score": state.score, "tier": tier.value},
                )
            )
            actions.append(
                EngineAction(
                    action_type=ActionType.NOTIFY,
                    channel=channel,
                    user_id=state.user_id,
                    username=username or state.username,
                    text=f"New {tier.value} lead captured: @{username or state.user_id} (Score: {state.score})",
                    metadata={"lead_id": lead.id, "tier": tier.value, "score": state.score},
                )
            )

        return state, actions, is_valid
