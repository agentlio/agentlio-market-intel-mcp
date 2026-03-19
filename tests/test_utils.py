"""Unit tests for utility helpers."""

from src.utils import (
    SlidingWindowRateLimiter,
    benchmark_themes_and_growth,
    filter_reviews_since,
    optimize_reviews,
    redact_pii_text,
    summarize_sentiment_hint,
)


def test_optimize_reviews_keeps_only_expected_fields() -> None:
    records = [
        {
            "score": 5,
            "content": "Great",
            "date": "2026-03-19",
            "thumbsUp": 7,
            "extra": "drop-me",
        }
    ]

    optimized = optimize_reviews(records)

    assert list(optimized[0].keys()) == ["score", "content", "date", "thumbsUp"]


def test_summarize_sentiment_hint_distribution() -> None:
    reviews = [
        {"score": 5, "content": "a", "date": None, "thumbsUp": 1},
        {"score": 1, "content": "b", "date": None, "thumbsUp": 0},
        {"score": 5, "content": "c", "date": None, "thumbsUp": 2},
    ]

    summary = summarize_sentiment_hint(reviews)

    assert summary["total"] == 3
    assert summary["scoreDistribution"][5] == 2


def test_rate_limiter_blocks_when_window_exceeded() -> None:
    limiter = SlidingWindowRateLimiter(max_calls=2, window_seconds=60)

    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_pii_redaction_masks_email_and_phone() -> None:
    text = "Bana test@example.com uzerinden donun veya +90 555 123 4567 arayin"
    redacted = redact_pii_text(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_since_date_filter_keeps_newer_reviews() -> None:
    reviews = [
        {"score": 5, "content": "new", "date": "2026-03-19", "thumbsUp": 1},
        {"score": 3, "content": "old", "date": "2026-03-01", "thumbsUp": 0},
    ]
    filtered = filter_reviews_since(reviews, since_date="2026-03-10")
    assert len(filtered) == 1
    assert filtered[0]["content"] == "new"


def test_theme_benchmark_returns_growth_suggestions() -> None:
    reviews = [
        {
            "score": 1,
            "content": "App crash and bug issues, too expensive subscription",
            "date": "2026-03-19",
            "thumbsUp": 2,
        }
    ]
    benchmark = benchmark_themes_and_growth(reviews)
    assert len(benchmark["themeMentions"]) > 0
    assert len(benchmark["growthSuggestions"]) > 0
