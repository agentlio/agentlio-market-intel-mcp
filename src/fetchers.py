"""Store fetcher layer for Google Play and Apple App Store."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from google_play_scraper import Sort
from google_play_scraper import reviews as gp_reviews

from .utils import ReviewRecord, filter_reviews_since, optimize_reviews


class FetcherError(RuntimeError):
    """Raised when review fetching fails for a provider."""


def _with_retries(provider: str, fn: Any, attempts: int = 3) -> Any:
    """Executes provider calls with bounded retries.

    Args:
        provider: Provider label for diagnostics.
        fn: Callable without arguments.
        attempts: Maximum attempts.

    Returns:
        Any: Return value of fn.

    Raises:
        FetcherError: If all attempts fail.
    """

    last_exc: Exception | None = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(float(2 ** (attempt - 1)))

    raise FetcherError(f"{provider} fetch islemi basarisiz: {last_exc}") from last_exc


def _to_google_sort(sort_by: str) -> Sort:
    """Maps user sort input to google_play_scraper Sort enum.

    Args:
        sort_by: String value provided by user.

    Returns:
        Sort: Matching sort option.
    """

    mapping = {
        "newest": Sort.NEWEST,
        "most_relevant": Sort.MOST_RELEVANT,
        "rating": Sort.RATING,
    }
    return mapping.get(sort_by.lower(), Sort.NEWEST)


def fetch_google_play_reviews(
    app_id: str,
    country: str = "us",
    lang: str = "en",
    count: int = 100,
    sort_by: str = "newest",
    since_date: str | None = None,
) -> List[ReviewRecord]:
    """Fetches and optimizes Google Play reviews.

    Args:
        app_id: Google Play package name.
        country: Two-letter store country.
        lang: Review language code.
        count: Max number of reviews to fetch.
        sort_by: Sort mode: newest, most_relevant, or rating.
        since_date: Optional ISO-like lower date bound.

    Returns:
        List[ReviewRecord]: Optimized review objects.

    Raises:
        FetcherError: If provider call fails.
    """

    try:
        result, _ = _with_retries(
            provider="google_play",
            fn=lambda: gp_reviews(
                app_id,
                lang=lang,
                country=country,
                sort=_to_google_sort(sort_by),
                count=max(1, min(count, 1000)),
            ),
        )

        normalized: List[Dict[str, Any]] = []
        for item in result:
            normalized.append(
                {
                    "score": item.get("score"),
                    "content": item.get("content", ""),
                    "date": item.get("at"),
                    "thumbsUp": item.get("thumbsUpCount"),
                }
            )

        return filter_reviews_since(
            optimize_reviews(normalized, redact_pii=True),
            since_date=since_date,
        )
    except Exception as exc:
        raise FetcherError(f"Google Play yorumları alınamadı: {exc}") from exc


def fetch_app_store_reviews(
    app_name: str,
    app_id: int,
    country: str = "us",
    count: int = 100,
    since_date: str | None = None,
) -> List[ReviewRecord]:
    """Fetches and optimizes Apple App Store reviews.

    Args:
        app_name: Display name of iOS app.
        app_id: Numeric App Store app id.
        country: Two-letter store country.
        count: Max number of reviews to fetch.
        since_date: Optional ISO-like lower date bound.

    Returns:
        List[ReviewRecord]: Optimized review objects.

    Raises:
        FetcherError: If provider call fails.
    """

    try:
        # Lazy import prevents server bootstrap failures when optional provider
        # deps are temporarily incompatible with active Python runtime.
        from app_store_scraper import AppStore

        app = AppStore(country=country, app_name=app_name, app_id=app_id)
        _with_retries(
            provider="app_store",
            fn=lambda: app.review(how_many=max(1, min(count, 1000))),
        )

        normalized: List[Dict[str, Any]] = []
        for item in app.reviews:
            normalized.append(
                {
                    "score": item.get("rating"),
                    "content": item.get("review", ""),
                    "date": item.get("date"),
                    # Apple payload commonly does not expose helpful vote count.
                    "thumbsUp": item.get("helpful_count"),
                }
            )

        return filter_reviews_since(
            optimize_reviews(normalized, redact_pii=True),
            since_date=since_date,
        )
    except ImportError as exc:
        raise FetcherError(
            "App Store fetcher bagimliligi yuklenemedi veya Python surumu ile uyumsuz."
        ) from exc
    except Exception as exc:
        raise FetcherError(f"App Store yorumları alınamadı: {exc}") from exc
