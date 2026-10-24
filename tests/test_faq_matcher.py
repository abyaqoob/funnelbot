"""Tests for FAQ matcher using TF-IDF and Cosine Similarity."""
import pytest
from app.engine.faq_matcher import FAQMatcher
from app.models.faq import FAQConfidence, FAQItem


@pytest.fixture
def sample_faqs():
    return [
        FAQItem(
            id="faq_price",
            question="How much does your service cost?",
            question_variants=["What are your prices?", "What is the fee?"],
            answer="Plans start at $499/mo.",
            category="Pricing",
        ),
        FAQItem(
            id="faq_time",
            question="How long does setup take?",
            question_variants=["What is onboarding time?"],
            answer="Setup takes 48 hours.",
            category="Onboarding",
        ),
        FAQItem(
            id="faq_loc",
            question="Where are you located?",
            question_variants=["Where is your office?"],
            answer="We are in San Francisco and London.",
            category="Company",
        ),
    ]


def test_high_confidence_auto_reply(sample_faqs):
    matcher = FAQMatcher(sample_faqs)

    # Near-exact question
    res = matcher.match("How much does your service cost?")
    assert res.confidence == FAQConfidence.HIGH
    assert res.score >= 0.55
    assert res.faq is not None
    assert res.faq.id == "faq_price"

    # Variant match
    res_var = matcher.match("what are your prices")
    assert res_var.confidence == FAQConfidence.HIGH
    assert res_var.score >= 0.55
    assert res_var.faq.id == "faq_price"


def test_medium_confidence_did_you_mean(sample_faqs):
    matcher = FAQMatcher(sample_faqs)

    # Partial overlap query ("service timeline" overlaps with "service" in faq_price)
    res = matcher.match("service timeline")
    assert res.confidence in {FAQConfidence.HIGH, FAQConfidence.MEDIUM}
    assert res.score >= 0.30
    assert res.faq is not None


def test_low_confidence_fallback(sample_faqs):
    matcher = FAQMatcher(sample_faqs)

    # Completely irrelevant query
    res = matcher.match("Can you bake a chocolate cake?")
    assert res.confidence == FAQConfidence.LOW
    assert res.score < 0.30
    assert res.faq is None


def test_empty_query_safely_handled(sample_faqs):
    matcher = FAQMatcher(sample_faqs)
    res = matcher.match("   ")
    assert res.confidence == FAQConfidence.LOW
    assert res.score == 0.0
    assert res.faq is None


def test_empty_faqs_safely_handled():
    matcher = FAQMatcher([])
    res = matcher.match("How much is pricing?")
    assert res.confidence == FAQConfidence.LOW
    assert res.score == 0.0
    assert res.faq is None
