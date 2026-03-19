"""Utility helpers for Agentlio Market Intel."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypedDict, TypeVar, cast

import pandas as pd

T = TypeVar("T")


LOGGER = logging.getLogger("agentlio.market_intel")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s event=%(message)s"
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)


class ReviewRecord(TypedDict):
    """Normalized review schema used by MCP responses.

    Attributes:
        score: Numeric review score.
        content: Review body text.
        date: ISO-8601 formatted date string.
        thumbsUp: Number of helpful votes when available.
    """

    score: Optional[int]
    content: str
    date: Optional[str]
    thumbsUp: Optional[int]


THEME_KEYWORDS: Dict[str, List[str]] = {
    "stability": ["crash", "bug", "freeze", "lag", "stuck", "slow"],
    "pricing": ["price", "expensive", "subscription", "trial", "cost", "pay"],
    "ux": ["ui", "ux", "design", "confusing", "navigation", "difficult"],
    "performance": ["battery", "performance", "loading", "latency", "memory"],
    "content": ["content", "feature", "podcast", "song", "catalog", "quality"],
}

THEME_GROWTH_ACTIONS: Dict[str, str] = {
    "stability": (
        "Crash ve ANR odakli hotfix sprinti ac, release notunda guven mesajini "
        "one cikar."
    ),
    "pricing": (
        "Fiyat algisi icin deneme suresini uzat ve value communication A/B testi yap."
    ),
    "ux": (
        "Onboarding ve kritik flowlarda friction point azaltmak icin task-based "
        "usability iyilestirmesi yap."
    ),
    "performance": (
        "Low-end cihaz segmentinde performans optimizasyonu ve lazy-loading "
        "iyilestirmesi uygula."
    ),
    "content": (
        "En cok talep edilen icerik/ozellik boslugunu roadmapte hizli kazanima cevir."
    ),
}


class TTLCache(Generic[T]):
    """Simple thread-safe in-memory TTL cache.

    Args:
        default_ttl_seconds: Default expiration for cached values.
    """

    def __init__(self, default_ttl_seconds: int = 300) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._store: Dict[str, tuple[float, T]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[T]:
        """Returns cached value when not expired.

        Args:
            key: Cache key.

        Returns:
            Optional[T]: Cached value or None.
        """

        now = time.time()
        with self._lock:
            payload = self._store.get(key)
            if payload is None:
                return None
            expires_at, value = payload
            if now >= expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """Stores a value with TTL.

        Args:
            key: Cache key.
            value: Payload value.
            ttl_seconds: Optional custom TTL.
        """

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = time.time() + max(1, ttl)
        with self._lock:
            self._store[key] = (expires_at, value)


class HybridCache(Generic[T]):
    """Two-layer cache using in-memory TTL and optional Redis backend.

    Args:
        default_ttl_seconds: Default TTL for memory and Redis entries.
        redis_url: Redis connection URL; when omitted, REDIS_URL env is used.
    """

    def __init__(
        self,
        default_ttl_seconds: int = 300,
        redis_url: Optional[str] = None,
    ) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._memory = TTLCache[T](default_ttl_seconds=default_ttl_seconds)
        self._redis_client: Any = None

        resolved_url = redis_url or os.getenv("REDIS_URL")
        if not resolved_url:
            return

        try:
            import redis

            client = redis.Redis.from_url(resolved_url, decode_responses=True)
            client.ping()
            self._redis_client = client
            log_event("info", "redis_cache_enabled", redis_url=resolved_url)
        except Exception as exc:  # noqa: BLE001
            log_event("warning", "redis_cache_disabled", error=str(exc))

    def get(self, key: str) -> Optional[T]:
        """Gets value from memory first, then Redis.

        Args:
            key: Cache key.

        Returns:
            Optional[T]: Cached payload when available.
        """

        in_memory = self._memory.get(key)
        if in_memory is not None:
            return in_memory

        if self._redis_client is None:
            return None

        try:
            raw = self._redis_client.get(key)
            if raw is None:
                return None
            value = cast(T, json.loads(raw))
            self._memory.set(key, value, ttl_seconds=self.default_ttl_seconds)
            return value
        except Exception as exc:  # noqa: BLE001
            log_event("warning", "redis_get_failed", key=key, error=str(exc))
            return None

    def set(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """Stores value in memory and Redis when configured.

        Args:
            key: Cache key.
            value: Payload value.
            ttl_seconds: Optional custom TTL.
        """

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        self._memory.set(key, value, ttl_seconds=ttl)

        if self._redis_client is None:
            return

        try:
            self._redis_client.setex(key, max(1, ttl), json.dumps(value))
        except Exception as exc:  # noqa: BLE001
            log_event("warning", "redis_set_failed", key=key, error=str(exc))


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter.

    Args:
        max_calls: Maximum calls in window.
        window_seconds: Window length in seconds.
    """

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._events: List[float] = []
        self._lock = threading.Lock()

    def allow(self) -> bool:
        """Checks whether a new call is allowed.

        Returns:
            bool: True when request can proceed.
        """

        now = time.time()
        threshold = now - self.window_seconds
        with self._lock:
            self._events = [ts for ts in self._events if ts >= threshold]
            if len(self._events) >= self.max_calls:
                return False
            self._events.append(now)
            return True


def log_event(level: str, message: str, **fields: Any) -> None:
    """Emits structured log events.

    Args:
        level: Logging level (info, warning, error).
        message: Event message.
        **fields: Extra key-value context.
    """

    suffix = " ".join(f"{k}={v}" for k, v in fields.items())
    line = f"{message} {suffix}".strip()
    if level == "error":
        LOGGER.error(line)
    elif level == "warning":
        LOGGER.warning(line)
    else:
        LOGGER.info(line)


def redact_pii_text(text: str) -> str:
    """Redacts common PII patterns from free-text reviews.

    Args:
        text: Raw review text.

    Returns:
        str: Redacted text.
    """

    if not text:
        return text

    redacted = re.sub(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "[REDACTED_EMAIL]",
        text,
    )
    redacted = re.sub(r"\+?\d[\d\s().-]{7,}\d", "[REDACTED_PHONE]", redacted)
    return redacted


def to_iso_date(value: Any) -> Optional[str]:
    """Converts a date-like object to ISO-8601 string.

    Args:
        value: Date value from scraper payload.

    Returns:
        Optional[str]: ISO formatted date string, or None when unavailable.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    # Some providers return plain strings; keep them if parse fails.
    try:
        parsed = pd.to_datetime(value, utc=False)
        if pd.isna(parsed):
            return None
        return cast(str, parsed.isoformat())
    except Exception:
        return str(value)


def optimize_reviews(
    records: List[Dict[str, Any]], redact_pii: bool = True
) -> List[ReviewRecord]:
    """Reduces raw review payload to context-efficient fields.

    Args:
        records: Raw review objects from store providers.

    Returns:
        List[ReviewRecord]: Optimized records containing score, content, date,
            and thumbsUp fields only.
    """

    if not records:
        return []

    df = pd.DataFrame(records)
    # Keep only agent-relevant columns to prevent context window bloat.
    reduced = pd.DataFrame(
        {
            "score": df.get("score"),
            "content": df.get("content", "").fillna(""),
            "date": df.get("date"),
            "thumbsUp": df.get("thumbsUp"),
        }
    )

    reduced["date"] = reduced["date"].apply(to_iso_date)

    if redact_pii:
        reduced["content"] = reduced["content"].apply(lambda x: redact_pii_text(str(x)))

    return cast(List[ReviewRecord], reduced.to_dict(orient="records"))


def filter_reviews_since(
    reviews: List[ReviewRecord],
    since_date: Optional[str],
) -> List[ReviewRecord]:
    """Filters reviews newer than or equal to since_date.

    Args:
        reviews: Review list.
        since_date: ISO-like date string.

    Returns:
        List[ReviewRecord]: Filtered reviews.
    """

    if not since_date:
        return reviews

    try:
        threshold = pd.to_datetime(since_date, utc=False)
    except Exception:
        return reviews

    filtered: List[ReviewRecord] = []
    for review in reviews:
        raw_date = review.get("date")
        if raw_date is None:
            continue
        try:
            parsed = pd.to_datetime(raw_date, utc=False)
            if parsed >= threshold:
                filtered.append(review)
        except Exception:
            continue

    return filtered


def summarize_sentiment_hint(reviews: List[ReviewRecord]) -> Dict[str, Any]:
    """Builds lightweight sentiment-ready stats for AI agents.

    Args:
        reviews: Normalized review list.

    Returns:
        Dict[str, Any]: Aggregate metrics such as mean score and distribution.
    """

    if not reviews:
        return {
            "total": 0,
            "averageScore": None,
            "scoreDistribution": {},
        }

    df = pd.DataFrame(reviews)
    score_series = pd.to_numeric(df["score"], errors="coerce").dropna()

    distribution = (
        score_series.astype(int)
        .value_counts()
        .sort_index()
        .to_dict()
    )

    return {
        "total": int(len(df)),
        "averageScore": float(score_series.mean()) if not score_series.empty else None,
        "scoreDistribution": distribution,
    }


def benchmark_themes_and_growth(reviews: List[ReviewRecord]) -> Dict[str, Any]:
    """Extracts theme-level benchmark and growth suggestions from reviews.

    Args:
        reviews: Normalized review list.

    Returns:
        Dict[str, Any]: Theme frequencies and action-oriented growth suggestions.
    """

    theme_counts: Dict[str, int] = {name: 0 for name in THEME_KEYWORDS}
    negative_theme_counts: Dict[str, int] = {name: 0 for name in THEME_KEYWORDS}

    for review in reviews:
        content = str(review.get("content", "")).lower()
        score_value = review.get("score")
        score = int(score_value) if isinstance(score_value, int) else 0

        for theme, keywords in THEME_KEYWORDS.items():
            if any(keyword in content for keyword in keywords):
                theme_counts[theme] += 1
                if score <= 2:
                    negative_theme_counts[theme] += 1

    ranked_themes = sorted(theme_counts.items(), key=lambda item: item[1], reverse=True)
    top_negative = sorted(
        negative_theme_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    top_negative_themes = [theme for theme, count in top_negative if count > 0][:3]
    suggestions = [
        {
            "theme": theme,
            "negativeMentions": negative_theme_counts[theme],
            "action": THEME_GROWTH_ACTIONS.get(theme, "Tema bazli deneyi olustur."),
        }
        for theme in top_negative_themes
    ]

    return {
        "themeMentions": [
            {"theme": theme, "mentions": count}
            for theme, count in ranked_themes
            if count > 0
        ],
        "negativeThemeMentions": [
            {"theme": theme, "mentions": count}
            for theme, count in top_negative
            if count > 0
        ],
        "growthSuggestions": suggestions,
    }
