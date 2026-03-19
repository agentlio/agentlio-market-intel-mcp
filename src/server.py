"""MCP server for Agentlio Market Intel."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from hashlib import sha1
from typing import Any, Callable, Dict, List, cast
from uuid import uuid4

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError

from .fetchers import FetcherError, fetch_app_store_reviews, fetch_google_play_reviews
from .utils import (
    HybridCache,
    ReviewRecord,
    SlidingWindowRateLimiter,
    benchmark_themes_and_growth,
    log_event,
    summarize_sentiment_hint,
)

REQUEST_TIMEOUT_SECONDS = 25
CACHE_TTL_SECONDS = 300
MAX_CALLS_PER_MINUTE = 60


class GooglePlayRequest(BaseModel):
    """Validated request schema for Google Play fetches."""

    app_id: str = Field(min_length=3)
    country: str = Field(default="us", min_length=2, max_length=2)
    lang: str = Field(default="en", min_length=2, max_length=5)
    count: int = Field(default=100, ge=1, le=1000)
    sort_by: str = Field(default="newest")
    since_date: str | None = None


class AppStoreRequest(BaseModel):
    """Validated request schema for App Store fetches."""

    app_name: str = Field(min_length=2)
    app_id: int = Field(gt=0)
    country: str = Field(default="us", min_length=2, max_length=2)
    count: int = Field(default=100, ge=1, le=1000)
    since_date: str | None = None


class UnifiedRequest(BaseModel):
    """Validated request schema for unified provider fetches."""

    provider: str = Field(min_length=3)
    app_id: str | None = None
    ios_app_id: int | None = None
    app_name: str | None = None
    country: str = Field(default="us", min_length=2, max_length=2)
    lang: str = Field(default="en", min_length=2, max_length=5)
    count: int = Field(default=100, ge=1, le=1000)
    sort_by: str = Field(default="newest")
    since_date: str | None = None


rate_limiter = SlidingWindowRateLimiter(
    max_calls=MAX_CALLS_PER_MINUTE,
    window_seconds=60,
)
response_cache: HybridCache[Dict[str, Any]] = HybridCache(
    default_ttl_seconds=CACHE_TTL_SECONDS
)

mcp = FastMCP("Agentlio Market Intel")


def _cache_key(prefix: str, payload: Dict[str, Any]) -> str:
    """Builds stable cache key for request payloads."""

    ordered = "|".join(f"{k}={payload[k]}" for k in sorted(payload.keys()))
    return f"{prefix}:{sha1(ordered.encode('utf-8')).hexdigest()}"


def _run_with_timeout(
    fn: Callable[[], Dict[str, Any]], timeout_sec: int
) -> Dict[str, Any]:
    """Executes blocking provider calls with a timeout boundary."""

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout_sec)
        except FutureTimeoutError as exc:
            raise FetcherError(f"Provider timeout ({timeout_sec}s)") from exc


def _error_payload(
    request_id: str,
    provider: str,
    error: str,
    details: Any = None,
) -> Dict[str, Any]:
    """Creates consistent error response payload."""

    return {
        "requestId": request_id,
        "provider": provider,
        "error": error,
        "details": details,
        "reviews": [],
    }


def _success_payload(
    request_id: str,
    provider: str,
    identifier: Dict[str, Any],
    reviews: List[ReviewRecord],
    cached: bool,
) -> Dict[str, Any]:
    """Creates consistent success response payload."""

    return {
        "requestId": request_id,
        "provider": provider,
        **identifier,
        "cached": cached,
        "reviewCount": len(reviews),
        "summary": summarize_sentiment_hint(reviews),
        "reviews": reviews,
    }


def _rate_limit_guard(request_id: str, provider: str) -> Dict[str, Any] | None:
    """Applies global in-memory rate-limit policy."""

    if rate_limiter.allow():
        return None
    log_event(
        "warning",
        "rate_limit_exceeded",
        request_id=request_id,
        provider=provider,
    )
    return _error_payload(
        request_id=request_id,
        provider=provider,
        error="Rate limit asildi. Lutfen biraz sonra tekrar deneyin.",
    )


@mcp.tool()
def get_google_play_reviews(
    app_id: str,
    country: str = "us",
    lang: str = "en",
    count: int = 100,
    sort_by: str = "newest",
    since_date: str | None = None,
) -> Dict[str, Any]:
    """Returns optimized Google Play reviews for AI agents.

    Args:
        app_id: Google Play package name.
        country: Two-letter store country.
        lang: Language code.
        count: Review limit.
        sort_by: newest, most_relevant, or rating.

    Returns:
        Dict[str, Any]: Provider metadata, sentiment-ready summary, and reviews.
    """

    request_id = str(uuid4())
    provider = "google_play"

    try:
        req = GooglePlayRequest.model_validate(
            {
                "app_id": app_id,
                "country": country,
                "lang": lang,
                "count": count,
                "sort_by": sort_by,
                "since_date": since_date,
            }
        )
    except ValidationError as exc:
        return _error_payload(request_id, provider, "Gecersiz parametre", exc.errors())

    limited = _rate_limit_guard(request_id, provider)
    if limited is not None:
        return limited

    cache_key = _cache_key("google_play", req.model_dump())
    cached_payload = response_cache.get(cache_key)
    if cached_payload is not None:
        log_event("info", "cache_hit", request_id=request_id, provider=provider)
        cached_payload["requestId"] = request_id
        cached_payload["cached"] = True
        return cached_payload

    try:
        reviews = cast(
            List[ReviewRecord],
            _run_with_timeout(
            lambda: {
                "reviews": fetch_google_play_reviews(
                    app_id=req.app_id,
                    country=req.country,
                    lang=req.lang,
                    count=req.count,
                    sort_by=req.sort_by,
                    since_date=req.since_date,
                )
            },
            REQUEST_TIMEOUT_SECONDS,
            )["reviews"],
        )
        payload = _success_payload(
            request_id=request_id,
            provider=provider,
            identifier={"appId": req.app_id},
            reviews=reviews,
            cached=False,
        )
        response_cache.set(cache_key, payload)
        log_event(
            "info",
            "fetch_success",
            request_id=request_id,
            provider=provider,
            count=len(reviews),
        )
        return payload
    except FetcherError as exc:
        log_event(
            "error",
            "fetch_failed",
            request_id=request_id,
            provider=provider,
            error=str(exc),
        )
        return _error_payload(request_id, provider, str(exc))


@mcp.tool()
def get_app_store_reviews(
    app_name: str,
    app_id: int,
    country: str = "us",
    count: int = 100,
    since_date: str | None = None,
) -> Dict[str, Any]:
    """Returns optimized Apple App Store reviews for AI agents.

    Args:
        app_name: Human-readable app name.
        app_id: Numeric iOS app id.
        country: Two-letter store country.
        count: Review limit.

    Returns:
        Dict[str, Any]: Provider metadata, sentiment-ready summary, and reviews.
    """

    request_id = str(uuid4())
    provider = "app_store"

    try:
        req = AppStoreRequest.model_validate(
            {
                "app_name": app_name,
                "app_id": app_id,
                "country": country,
                "count": count,
                "since_date": since_date,
            }
        )
    except ValidationError as exc:
        return _error_payload(request_id, provider, "Gecersiz parametre", exc.errors())

    limited = _rate_limit_guard(request_id, provider)
    if limited is not None:
        return limited

    cache_key = _cache_key("app_store", req.model_dump())
    cached_payload = response_cache.get(cache_key)
    if cached_payload is not None:
        log_event("info", "cache_hit", request_id=request_id, provider=provider)
        cached_payload["requestId"] = request_id
        cached_payload["cached"] = True
        return cached_payload

    try:
        reviews = cast(
            List[ReviewRecord],
            _run_with_timeout(
            lambda: {
                "reviews": fetch_app_store_reviews(
                    app_name=req.app_name,
                    app_id=req.app_id,
                    country=req.country,
                    count=req.count,
                    since_date=req.since_date,
                )
            },
            REQUEST_TIMEOUT_SECONDS,
            )["reviews"],
        )
        payload = _success_payload(
            request_id=request_id,
            provider=provider,
            identifier={"appName": req.app_name, "appId": req.app_id},
            reviews=reviews,
            cached=False,
        )
        response_cache.set(cache_key, payload)
        log_event(
            "info",
            "fetch_success",
            request_id=request_id,
            provider=provider,
            count=len(reviews),
        )
        return payload
    except FetcherError as exc:
        log_event(
            "error",
            "fetch_failed",
            request_id=request_id,
            provider=provider,
            error=str(exc),
        )
        return _error_payload(request_id, provider, str(exc))


@mcp.tool()
def get_market_reviews(
    provider: str,
    app_id: str = "",
    ios_app_id: int = 0,
    app_name: str = "",
    country: str = "us",
    lang: str = "en",
    count: int = 100,
    sort_by: str = "newest",
    since_date: str | None = None,
) -> Dict[str, Any]:
    """Unified fetch tool for both Google Play and App Store.

    Args:
        provider: google_play or app_store.
        app_id: Google Play package id.
        ios_app_id: iOS numeric app id.
        app_name: iOS app display name.
        country: Store country.
        lang: Review language.
        count: Review limit.
        sort_by: Google Play sort mode.

    Returns:
        Dict[str, Any]: Unified provider response.
    """

    try:
        req = UnifiedRequest.model_validate(
            {
                "provider": provider,
                "app_id": app_id or None,
                "ios_app_id": ios_app_id or None,
                "app_name": app_name or None,
                "country": country,
                "lang": lang,
                "count": count,
                "sort_by": sort_by,
                "since_date": since_date,
            }
        )
    except ValidationError as exc:
        return _error_payload(
            str(uuid4()),
            provider,
            "Gecersiz parametre",
            exc.errors(),
        )

    if req.provider.lower() == "google_play":
        if not req.app_id:
            return _error_payload(str(uuid4()), "google_play", "app_id zorunludur")
        return cast(
            Dict[str, Any],
            get_google_play_reviews(
            app_id=req.app_id,
            country=req.country,
            lang=req.lang,
            count=req.count,
            sort_by=req.sort_by,
                since_date=req.since_date,
            ),
        )

    if req.provider.lower() == "app_store":
        if not req.ios_app_id or not req.app_name:
            return _error_payload(
                str(uuid4()),
                "app_store",
                "ios_app_id ve app_name zorunludur",
            )
        return cast(
            Dict[str, Any],
            get_app_store_reviews(
            app_name=req.app_name,
            app_id=req.ios_app_id,
            country=req.country,
            count=req.count,
                since_date=req.since_date,
            ),
        )

    return _error_payload(
        str(uuid4()),
        provider,
        "provider sadece google_play veya app_store olabilir",
    )


@mcp.tool()
def compare_google_play_apps(
    app_ids: List[str],
    country: str = "us",
    lang: str = "en",
    count: int = 100,
) -> Dict[str, Any]:
    """Compares Google Play apps using review sentiment hints.

    Args:
        app_ids: Google Play package ids.
        country: Store country.
        lang: Review language.
        count: Per-app review limit.

    Returns:
        Dict[str, Any]: Comparison payload with ranking by average score.
    """

    request_id = str(uuid4())
    if len(app_ids) < 2:
        return _error_payload(
            request_id,
            "google_play",
            "Karsilastirma icin en az 2 app_id gerekli",
        )

    comparisons: List[Dict[str, Any]] = []
    for app_id in app_ids[:10]:
        payload = get_google_play_reviews(
            app_id=app_id,
            country=country,
            lang=lang,
            count=count,
            sort_by="newest",
        )

        reviews = cast(List[ReviewRecord], payload.get("reviews", []))
        benchmark = benchmark_themes_and_growth(reviews)
        comparisons.append(
            {
                "appId": app_id,
                "reviewCount": payload.get("reviewCount", 0),
                "averageScore": (payload.get("summary") or {}).get("averageScore"),
                "scoreDistribution": (
                    payload.get("summary") or {}
                ).get("scoreDistribution", {}),
                "themeMentions": benchmark.get("themeMentions", []),
                "negativeThemeMentions": benchmark.get("negativeThemeMentions", []),
                "growthSuggestions": benchmark.get("growthSuggestions", []),
                "error": payload.get("error"),
            }
        )

    def _score_key(item: Dict[str, Any]) -> float:
        value = item.get("averageScore")
        if isinstance(value, (int, float)):
            return float(value)
        return -1.0

    ranked = sorted(
        comparisons,
        key=_score_key,
        reverse=True,
    )

    return {
        "requestId": request_id,
        "provider": "google_play",
        "appsAnalyzed": len(comparisons),
        "rankingByAverageScore": ranked,
    }


def main() -> None:
    """Starts the MCP server."""

    mcp.run()


if __name__ == "__main__":
    main()
