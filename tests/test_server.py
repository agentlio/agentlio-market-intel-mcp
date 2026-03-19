"""Unit tests for MCP server helper behavior."""

from src.server import compare_google_play_apps, get_market_reviews


def test_unified_tool_rejects_invalid_provider() -> None:
    payload = get_market_reviews(provider="invalid", app_id="com.example.app")

    assert "error" in payload


def test_unified_tool_requires_google_app_id() -> None:
    payload = get_market_reviews(provider="google_play", app_id="")

    assert "error" in payload


def test_unified_tool_accepts_since_date() -> None:
    payload = get_market_reviews(
        provider="google_play",
        app_id="com.spotify.music",
        since_date="2026-03-10",
        count=1,
    )
    assert "provider" in payload


def test_compare_google_play_apps_requires_min_two_apps() -> None:
    payload = compare_google_play_apps(app_ids=["com.spotify.music"])
    assert "error" in payload
