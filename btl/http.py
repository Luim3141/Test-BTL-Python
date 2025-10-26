"""HTTP helper utilities including retry and throttling logic."""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Iterable

import requests

LOGGER = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Simple rate limiter that sleeps between requests.

    The limiter supports randomised jitter to reduce the likelihood of hitting
    rate limits or bot detection heuristics on the target websites.
    """

    min_delay: float = 1.0
    max_delay: float = 3.0

    def wait(self) -> None:
        delay = random.uniform(self.min_delay, self.max_delay)
        LOGGER.debug("Sleeping for %.2f seconds before next request", delay)
        time.sleep(delay)


class HttpClient:
    """Wrapper around :mod:`requests` adding retry and throttling behaviour."""

    def __init__(
        self,
        session: requests.Session | None = None,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        status_forcelist: Iterable[int] | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.status_forcelist = set(status_forcelist or {429, 500, 502, 503, 504})
        self.session.headers.setdefault(
            "User-Agent",
            (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            ),
        )

    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform a GET request with retry, exponential backoff and throttling."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self.rate_limiter.wait()
                response = self.session.get(url, timeout=kwargs.pop("timeout", 30), **kwargs)
                if response.status_code in self.status_forcelist:
                    raise requests.HTTPError(f"Unexpected status {response.status_code}")
                return response
            except Exception as exc:  # noqa: BLE001 - we explicitly re-raise last error
                LOGGER.warning("Request to %s failed on attempt %s/%s: %s", url, attempt, self.max_retries, exc)
                last_error = exc
                time.sleep(self.backoff_factor ** attempt)
        assert last_error is not None
        raise last_error


__all__ = ["HttpClient", "RateLimiter", "LOGGER"]
