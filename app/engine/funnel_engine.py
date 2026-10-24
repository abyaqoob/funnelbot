"""Master Funnel Engine coordinating Keyword Triggers, FAQ Matcher, State Machine, and LLM fallback."""
import random
from datetime import datetime, timezone

from app.engine.faq_matcher import FAQMatcher

UTC = timezone.utc
from app.engine.keyword_matcher import KeywordMatcher
from app.engine.llm_fallback import LLMProvider, get_llm_provider
from app.engine.state_machine import StateMachine
from app.engine.storage import Storage
from app.models.events import (
    ActionType,
    EngineAction,
    EngineResult,
    EventType,
    InspectorInfo,
    NormalizedEvent,
)
from app.models.faq import FAQConfidence
from app.models.flow import ConversationStatus, FlowStepType


class FunnelEngine:
    """Channel-agnostic automation engine."""

    def __init__(
        self,
        storage: Storage,
        llm_provider: LLMProvider | None = None,
    ):
        self.storage = storage
        self.keyword_matcher = KeywordMatcher()
        self.state_machine = StateMachine(storage)
        self.llm_provider = llm_provider or get_llm_provider()
        self.faq_matcher = FAQMatcher(storage.get_faqs())

    def reload_faqs(self) -> None:
        """Re-fit TF-IDF vectorizer when FAQs update."""
        self.faq_matcher.fit(self.storage.get_faqs())

    def process_event(self, event: NormalizedEvent) -> EngineResult:
        """
        Process normalized inbound event and return engine actions + inspector metadata.
        """
        inspector = InspectorInfo()
        channel_val = event.channel.value
        user_id = event.user_id
        username = event.username
        text = event.text.strip()
        now = datetime.now(UTC)

        # 1. Global Opt-Out Check
        if self.storage.is_opted_out(channel_val, user_id):
            inspector.is_opted_out = True
            if self.state_machine.is_opt_out_command(text):
                # Acknowledge opt-out again
                inspector.execution_notes.append("User is already opted out.")
                return EngineResult(
                    actions=[
                        EngineAction(
                            action_type=ActionType.SEND_DM,
                            channel=event.channel,
                            user_id=user_id,
                            username=username,
                            text="You are unsubscribed and will receive no further messages.",
                        )
                    ],
                    inspector_info=inspector,
                )
            inspector.execution_notes.append("User is opted out. Dropped event without actions.")
            return EngineResult(actions=[], inspector_info=inspector)

        # 2. Check for Global Opt-Out Command
        if self.state_machine.is_opt_out_command(text):
            self.storage.set_opted_out(channel_val, user_id, True)
            state = self.storage.get_state(channel_val, user_id)
            if state:
                state.status = ConversationStatus.OPTED_OUT
                self.storage.save_state(state)

            inspector.is_opted_out = True
            inspector.execution_notes.append("Global opt-out command received. User unsubscribed.")
            return EngineResult(
                actions=[
                    EngineAction(
                        action_type=ActionType.SEND_DM,
                        channel=event.channel,
                        user_id=user_id,
                        username=username,
                        text="You have been unsubscribed and will receive no further messages. Reply START anytime to re-enable.",
                    )
                ],
                inspector_info=inspector,
            )

        # 3. Check for Human Takeover Command
        if self.state_machine.is_human_takeover_command(text):
            state = self.storage.get_state(channel_val, user_id)
            if state:
                state.status = ConversationStatus.HANDED_OFF
                self.storage.save_state(state)

            inspector.flow_state = {"status": "handed_off"}
            inspector.execution_notes.append("User requested human agent takeover.")
            return EngineResult(
                actions=[
                    EngineAction(
                        action_type=ActionType.SEND_DM,
                        channel=event.channel,
                        user_id=user_id,
                        username=username,
                        text="A team member has been notified and will take over shortly. 🙋‍♂️",
                    ),
                    EngineAction(
                        action_type=ActionType.NOTIFY,
                        channel=event.channel,
                        user_id=user_id,
                        username=username,
                        text=f"User @{username or user_id} requested human takeover on {channel_val}.",
                    ),
                ],
                inspector_info=inspector,
            )

        # 4. Handle COMMENT Events
        if event.event_type == EventType.COMMENT:
            return self._handle_comment(event, inspector, now)

        # 5. Handle DM Events
        if event.event_type == EventType.DM:
            return self._handle_dm(event, inspector, now)

        inspector.execution_notes.append(f"Unknown event type: {event.event_type}")
        return EngineResult(actions=[], inspector_info=inspector)

    def _handle_comment(
        self, event: NormalizedEvent, inspector: InspectorInfo, now: datetime
    ) -> EngineResult:
        """Process incoming public comment for keyword triggers and cooldown."""
        rules = self.storage.get_rules()
        match_result = self.keyword_matcher.find_matching_rule(
            event.text, rules, post_id=event.post_id
        )

        if not match_result:
            inspector.execution_notes.append("No comment keyword rule matched.")
            return EngineResult(actions=[], inspector_info=inspector)

        rule, matched_kw, score = match_result
        inspector.matched_rule = rule.name
        inspector.keyword_matched = matched_kw

        # Check cooldown per user per rule
        last_trigger = self.storage.get_last_rule_trigger(event.user_id, rule.id)
        if last_trigger:
            elapsed = (now - last_trigger).total_seconds()
            if elapsed < rule.cooldown_seconds:
                inspector.execution_notes.append(
                    f"Duplicate trigger blocked by cooldown. Fired {int(elapsed)}s ago (cooldown: {rule.cooldown_seconds}s)."
                )
                return EngineResult(actions=[], inspector_info=inspector)

        # Record trigger
        self.storage.record_rule_trigger(event.user_id, rule.id)

        actions: list[EngineAction] = []

        # 1. Randomized public reply to avoid spam
        template = (
            random.choice(rule.reply_templates)
            if rule.reply_templates
            else "Thanks @{username}! Just sent you a DM 📩"
        )
        public_reply = template.format(username=event.username or "there")
        actions.append(
            EngineAction(
                action_type=ActionType.REPLY_COMMENT,
                channel=event.channel,
                user_id=event.user_id,
                username=event.username,
                post_id=event.post_id,
                text=public_reply,
            )
        )

        # 2. Start qualification flow or direct DM
        if rule.flow_id:
            flow = self.storage.get_flow(rule.flow_id)
            if flow:
                state, flow_actions = self.state_machine.start_flow(
                    event.channel, event.user_id, event.username, flow
                )
                actions.extend(flow_actions)
                inspector.flow_state = {
                    "flow_id": flow.id,
                    "current_step_id": state.current_step_id,
                    "status": state.status.value,
                }
                inspector.lead_score = state.score
                inspector.execution_notes.append(
                    f"Matched rule '{rule.name}' on keyword '{matched_kw}' (score: {score:.1f}). Started flow '{flow.id}'."
                )
            else:
                inspector.execution_notes.append(f"Flow '{rule.flow_id}' not found.")
        elif rule.direct_dm_message:
            actions.append(
                EngineAction(
                    action_type=ActionType.SEND_DM,
                    channel=event.channel,
                    user_id=event.user_id,
                    username=event.username,
                    text=rule.direct_dm_message,
                )
            )
            inspector.execution_notes.append(
                f"Matched rule '{rule.name}' on keyword '{matched_kw}'. Sent direct DM."
            )

        return EngineResult(actions=actions, inspector_info=inspector)

    def _handle_dm(
        self, event: NormalizedEvent, inspector: InspectorInfo, now: datetime
    ) -> EngineResult:
        """Process incoming direct message (qualification flow, FAQ, interruption, or fallback)."""
        channel_val = event.channel.value
        user_id = event.user_id
        username = event.username
        text = event.text.strip()
        state = self.storage.get_state(channel_val, user_id)

        # Reset expired conversation state
        if state and state.is_expired():
            inspector.execution_notes.append("Previous conversation state expired (> 24h).")
            state.status = ConversationStatus.EXPIRED
            self.storage.save_state(state)
            state = None

        # Check if user sent a start command to trigger a flow
        if text.lower() in {"start", "/start"}:
            flow = self.storage.get_flow("lead_qualification")
            if flow:
                new_state, flow_actions = self.state_machine.start_flow(
                    event.channel, user_id, event.username, flow
                )
                inspector.flow_state = {
                    "flow_id": flow.id,
                    "current_step_id": new_state.current_step_id,
                    "status": new_state.status.value,
                }
                inspector.execution_notes.append("Started qualification flow via /start.")
                return EngineResult(actions=flow_actions, inspector_info=inspector)

        # Active Flow Handling
        if state and state.status == ConversationStatus.ACTIVE and state.flow_id and state.current_step_id:
            flow = self.storage.get_flow(state.flow_id)
            if flow:
                current_step = flow.get_step(state.current_step_id)

                # Try step input processing
                updated_state, step_actions, is_valid = self.state_machine.process_step_input(
                    state, flow, text, event.channel, event.username
                )

                if is_valid:
                    inspector.flow_state = {
                        "flow_id": flow.id,
                        "current_step_id": updated_state.current_step_id,
                        "status": updated_state.status.value,
                    }
                    inspector.lead_score = updated_state.score
                    if updated_state.status == ConversationStatus.COMPLETED:
                        inspector.lead_tier = (
                            "HOT"
                            if updated_state.score >= flow.hot_threshold
                            else "WARM"
                            if updated_state.score >= flow.warm_threshold
                            else "COLD"
                        )
                        inspector.execution_notes.append(
                            f"Flow completed! Final score: {updated_state.score} -> Tier: {inspector.lead_tier}"
                        )
                    else:
                        inspector.execution_notes.append(
                            f"Step answer accepted. Advanced to step '{updated_state.current_step_id}'. Score: {updated_state.score}"
                        )
                    return EngineResult(actions=step_actions, inspector_info=inspector)

                # Input was not valid for the current step. Could it be an FAQ mid-flow? (Interruption)
                faq_result = self.faq_matcher.match(text)
                if faq_result.confidence == FAQConfidence.HIGH and faq_result.faq:
                    inspector.faq_match = {
                        "question": faq_result.matched_query,
                        "score": faq_result.score,
                        "confidence": faq_result.confidence.value,
                    }
                    inspector.flow_state = {
                        "flow_id": flow.id,
                        "current_step_id": state.current_step_id,
                        "status": state.status.value,
                    }
                    inspector.lead_score = state.score
                    inspector.execution_notes.append(
                        f"FAQ interruption matched '{faq_result.matched_query}' (score: {faq_result.score:.2f}). Resuming flow."
                    )

                    # Action 1: FAQ Answer
                    faq_action = EngineAction(
                        action_type=ActionType.SEND_DM,
                        channel=event.channel,
                        user_id=user_id,
                        username=event.username,
                        text=f"💡 {faq_result.faq.answer}",
                    )
                    # Action 2: Resume step
                    prompt_text = (
                        f"Back to your question...\n\n"
                        f"{self.state_machine.format_step_prompt(current_step)}"
                        if current_step
                        else "Let's continue!"
                    )
                    quick_replies = (
                        [c.label for c in current_step.choices]
                        if (current_step and current_step.choices)
                        else None
                    )
                    resume_action = EngineAction(
                        action_type=ActionType.SEND_DM,
                        channel=event.channel,
                        user_id=user_id,
                        username=event.username,
                        text=prompt_text,
                        quick_replies=quick_replies,
                    )
                    return EngineResult(
                        actions=[faq_action, resume_action], inspector_info=inspector
                    )

                if faq_result.confidence == FAQConfidence.MEDIUM and faq_result.faq:
                    inspector.faq_match = {
                        "question": faq_result.matched_query,
                        "score": faq_result.score,
                        "confidence": faq_result.confidence.value,
                    }
                    inspector.execution_notes.append(
                        f"Medium FAQ match '{faq_result.matched_query}' (score: {faq_result.score:.2f}) mid-flow."
                    )
                    prompt_resume = (
                        f"Did you mean: '{faq_result.matched_query}'?\n\n"
                        f"💡 {faq_result.faq.answer}\n\n"
                        f"Back to our question:\n"
                        f"{self.state_machine.format_step_prompt(current_step)}"
                        if current_step
                        else ""
                    )
                    quick_replies = (
                        [c.label for c in current_step.choices]
                        if (current_step and current_step.choices)
                        else None
                    )
                    return EngineResult(
                        actions=[
                            EngineAction(
                                action_type=ActionType.SEND_DM,
                                channel=event.channel,
                                user_id=user_id,
                                username=event.username,
                                text=prompt_resume,
                                quick_replies=quick_replies,
                            )
                        ],
                        inspector_info=inspector,
                    )

                # Invalid input for step and not an FAQ
                if current_step and current_step.step_type == FlowStepType.EMAIL:
                    # state_machine.process_step_input already generated the email error action
                    inspector.execution_notes.append("Invalid email provided. Sent re-prompt.")
                    return EngineResult(actions=step_actions, inspector_info=inspector)

                # Choice re-prompt
                inspector.execution_notes.append("Unrecognized choice input. Sent helper prompt.")
                help_text = (
                    f"Please pick one of the options below to continue:\n\n"
                    f"{self.state_machine.format_step_prompt(current_step)}\n\n"
                    f"(Or type 'human' to talk with our team.)"
                    if current_step
                    else "Please choose an option."
                )
                quick_replies = (
                    [c.label for c in current_step.choices]
                    if (current_step and current_step.choices)
                    else None
                )
                return EngineResult(
                    actions=[
                        EngineAction(
                            action_type=ActionType.SEND_DM,
                            channel=event.channel,
                            user_id=user_id,
                            username=event.username,
                            text=help_text,
                            quick_replies=quick_replies,
                        )
                    ],
                    inspector_info=inspector,
                )

        # Standalone DM (No active flow)
        faq_result = self.faq_matcher.match(text)
        inspector.faq_match = {
            "question": faq_result.matched_query,
            "score": faq_result.score,
            "confidence": faq_result.confidence.value,
        }

        if faq_result.confidence == FAQConfidence.HIGH and faq_result.faq:
            inspector.execution_notes.append(
                f"FAQ high confidence auto-reply for '{faq_result.matched_query}' (score: {faq_result.score:.2f})."
            )
            return EngineResult(
                actions=[
                    EngineAction(
                        action_type=ActionType.SEND_DM,
                        channel=event.channel,
                        user_id=user_id,
                        username=event.username,
                        text=faq_result.faq.answer,
                    )
                ],
                inspector_info=inspector,
            )

        if faq_result.confidence == FAQConfidence.MEDIUM and faq_result.faq:
            inspector.execution_notes.append(
                f"FAQ medium confidence match for '{faq_result.matched_query}' (score: {faq_result.score:.2f})."
            )
            med_text = (
                f"Did you mean: '{faq_result.matched_query}'?\n\n"
                f"{faq_result.faq.answer}\n\n"
                f"If you need more help, reply 'human' to reach our team."
            )
            return EngineResult(
                actions=[
                    EngineAction(
                        action_type=ActionType.SEND_DM,
                        channel=event.channel,
                        user_id=user_id,
                        username=event.username,
                        text=med_text,
                    )
                ],
                inspector_info=inspector,
            )

        # Confidence < 0.30: Try optional LLM provider or fallback
        llm_reply = self.llm_provider.generate_reply(text)
        if llm_reply:
            inspector.execution_notes.append(
                f"Low FAQ similarity ({faq_result.score:.2f}). Answered via optional LLM provider."
            )
            return EngineResult(
                actions=[
                    EngineAction(
                        action_type=ActionType.SEND_DM,
                        channel=event.channel,
                        user_id=user_id,
                        username=event.username,
                        text=llm_reply,
                    )
                ],
                inspector_info=inspector,
            )

        # Pure rule-based fallback and flag human takeover
        inspector.execution_notes.append(
            f"Low FAQ similarity ({faq_result.score:.2f}). Fallback triggered and flagged for human review."
        )
        fallback_msg = (
            "Thanks for reaching out! I'm an automated assistant. For specific questions, "
            "type 'human' to speak with our team, or reply 'START' to explore our services."
        )
        return EngineResult(
            actions=[
                EngineAction(
                    action_type=ActionType.SEND_DM,
                    channel=event.channel,
                    user_id=user_id,
                    username=event.username,
                    text=fallback_msg,
                ),
                EngineAction(
                    action_type=ActionType.NOTIFY,
                    channel=event.channel,
                    user_id=user_id,
                    username=event.username,
                    text=f"Unrecognized DM from @{username or user_id}: '{text}'",
                ),
            ],
            inspector_info=inspector,
        )
