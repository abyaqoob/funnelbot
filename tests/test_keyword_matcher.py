"""Tests for keyword matcher (exact, contains, and RapidFuzz fuzzy algorithms)."""
import pytest
from app.engine.keyword_matcher import KeywordMatcher
from app.models.rules import MatchMode, TriggerRule


@pytest.fixture
def matcher() -> KeywordMatcher:
    return KeywordMatcher()


def test_exact_match_success(matcher: KeywordMatcher):
    rule = TriggerRule(
        id="r_exact",
        name="Exact Rule",
        keywords=["guide", "blueprint"],
        match_mode=MatchMode.EXACT,
    )
    # Exact lowercase
    matched, kw, score = matcher.match_rule("guide", rule)
    assert matched is True
    assert kw == "guide"
    assert score == 100.0

    # Case insensitivity & punctuation stripping
    matched, kw, score = matcher.match_rule("  GUIDE! ", rule)
    assert matched is True
    assert score == 100.0


def test_exact_match_failure(matcher: KeywordMatcher):
    rule = TriggerRule(
        id="r_exact",
        name="Exact Rule",
        keywords=["guide"],
        match_mode=MatchMode.EXACT,
    )
    # Substring is not exact
    matched, kw, score = matcher.match_rule("send me the guide please", rule)
    assert matched is False


def test_contains_match_success(matcher: KeywordMatcher):
    rule = TriggerRule(
        id="r_contains",
        name="Contains Rule",
        keywords=["price", "how much"],
        match_mode=MatchMode.CONTAINS,
    )
    # Single word within text
    matched, kw, score = matcher.match_rule("What is the price of this?", rule)
    assert matched is True
    assert kw == "price"

    # Multi-word phrase within text
    matched, kw, score = matcher.match_rule("Hey, how much does it cost?", rule)
    assert matched is True
    assert kw == "how much"


def test_contains_match_word_boundary(matcher: KeywordMatcher):
    rule = TriggerRule(
        id="r_contains",
        name="Contains Rule",
        keywords=["cat"],
        match_mode=MatchMode.CONTAINS,
    )
    # "catalog" should NOT match single-word keyword "cat"
    matched, kw, score = matcher.match_rule("Check our catalog", rule)
    assert matched is False


def test_fuzzy_match_typos(matcher: KeywordMatcher):
    rule = TriggerRule(
        id="r_fuzzy",
        name="Fuzzy Rule",
        keywords=["guide"],
        match_mode=MatchMode.FUZZY,
        fuzzy_threshold=80.0,
    )
    # Typo: "giude"
    matched, kw, score = matcher.match_rule("giude", rule)
    assert matched is True
    assert kw == "guide"
    assert score >= 80.0

    # Typo: "gudie"
    matched, kw, score = matcher.match_rule("gudie", rule)
    assert matched is True
    assert score >= 80.0

    # Typo embedded in a sentence
    matched, kw, score = matcher.match_rule("hey can you please send the giude?", rule)
    assert matched is True
    assert score >= 80.0


def test_fuzzy_match_below_threshold(matcher: KeywordMatcher):
    rule = TriggerRule(
        id="r_fuzzy",
        name="Fuzzy Rule",
        keywords=["guide"],
        match_mode=MatchMode.FUZZY,
        fuzzy_threshold=85.0,
    )
    # Completely different word
    matched, kw, score = matcher.match_rule("hello there", rule)
    assert matched is False
    assert score < 85.0


def test_post_id_scoping(matcher: KeywordMatcher):
    rule = TriggerRule(
        id="r_scoped",
        name="Scoped Rule",
        keywords=["guide"],
        match_mode=MatchMode.EXACT,
        post_id_scope="post_999",
    )
    # Matching post_id
    matched, _, _ = matcher.match_rule("guide", rule, post_id="post_999")
    assert matched is True

    # Non-matching post_id
    matched, _, _ = matcher.match_rule("guide", rule, post_id="post_888")
    assert matched is False


def test_inactive_rule_ignored(matcher: KeywordMatcher):
    rule = TriggerRule(
        id="r_inactive",
        name="Inactive",
        keywords=["guide"],
        is_active=False,
    )
    matched, _, _ = matcher.match_rule("guide", rule)
    assert matched is False


def test_find_matching_rule(matcher: KeywordMatcher):
    rules = [
        TriggerRule(id="r1", name="Inactive", keywords=["guide"], is_active=False),
        TriggerRule(id="r2", name="Active Guide", keywords=["guide"], match_mode=MatchMode.CONTAINS),
    ]
    res = matcher.find_matching_rule("send me the guide", rules)
    assert res is not None
    matched_rule, kw, score = res
    assert matched_rule.id == "r2"
    assert kw == "guide"
