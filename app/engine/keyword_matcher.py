"""Keyword matcher with exact, contains, and RapidFuzz fuzzy algorithms."""
import re
import string
from typing import List, Optional, Tuple
from rapidfuzz import fuzz
from app.models.rules import MatchMode, TriggerRule


class KeywordMatcher:
    """Matches text against TriggerRules using exact, contains, or fuzzy matching."""

    @staticmethod
    def _clean_text(text: str) -> str:
        """Strip surrounding punctuation and lowercase."""
        return text.strip().lower()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Extract alphanumeric words from text."""
        # Replace punctuation with spaces to tokenize
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        return [w for w in clean.split() if w]

    def match_rule(
        self, text: str, rule: TriggerRule, post_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], float]:
        """
        Check if text matches a given rule.
        Returns: (is_matched, matched_keyword, score_0_to_100)
        """
        if not rule.is_active:
            return False, None, 0.0

        # Scope check: if rule is scoped to a specific post_id
        if rule.post_id_scope and post_id and rule.post_id_scope != post_id:
            return False, None, 0.0

        clean_text = self._clean_text(text)
        if not clean_text:
            return False, None, 0.0

        # Stripped of all punctuation for exact comparisons
        text_no_punct = clean_text.strip(string.punctuation)
        tokens = self._tokenize(text)

        best_kw = None
        best_score = 0.0

        for raw_kw in rule.keywords:
            kw = self._clean_text(raw_kw)
            if not kw:
                continue

            if rule.match_mode == MatchMode.EXACT:
                if clean_text == kw or text_no_punct == kw:
                    return True, raw_kw, 100.0

            elif rule.match_mode == MatchMode.CONTAINS:
                # Word-boundary check for single-word keywords, substring for phrases
                if " " in kw:
                    if kw in clean_text:
                        return True, raw_kw, 100.0
                else:
                    pattern = rf"\b{re.escape(kw)}\b"
                    if re.search(pattern, clean_text):
                        return True, raw_kw, 100.0

            elif rule.match_mode == MatchMode.FUZZY:
                # 1. Whole text ratio
                score_whole = fuzz.ratio(kw, clean_text)
                # 2. Substring partial ratio
                score_partial = fuzz.partial_ratio(kw, clean_text)
                # 3. Token-by-token comparison (handles typos inside longer sentences)
                token_scores = [fuzz.ratio(kw, t) for t in tokens] if tokens else [0.0]
                score_tokens = max(token_scores)

                score = max(score_whole, score_partial, score_tokens)
                if score > best_score:
                    best_score = float(score)
                    best_kw = raw_kw

        if rule.match_mode == MatchMode.FUZZY:
            if best_score >= rule.fuzzy_threshold and best_kw is not None:
                return True, best_kw, best_score
            return False, None, best_score

        return False, None, 0.0

    def find_matching_rule(
        self, text: str, rules: List[TriggerRule], post_id: Optional[str] = None
    ) -> Optional[Tuple[TriggerRule, str, float]]:
        """
        Find the first matching rule from a list of rules.
        Returns: (matched_rule, matched_keyword, score) or None.
        """
        for rule in rules:
            matched, kw, score = self.match_rule(text, rule, post_id=post_id)
            if matched and kw:
                return rule, kw, score
        return None
