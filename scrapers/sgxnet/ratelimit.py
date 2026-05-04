"""Polite rate-limiting + retry helpers for SGXNet.

Every outbound request:
    - sleeps ``min_interval_s`` since the last request
    - retries up to 3 times with exponential backoff on transient failures
    - identifies itself with a contact-included User-Agent (so SGX can
      blocklist us cleanly if our scraping is causing harm)
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, Final, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

F = TypeVar("F", bound=Callable[..., Any])

DEFAULT_MIN_INTERVAL_S: Final[float] = 2.0
USER_AGENT: Final[str] = (
    "sg-eqdp-scanner/0.1 "
    "(+https://github.com/pachidam/sg-eqdp-scanner; "
    "research; contact: palani@unisongroup.com)"
)


class _RateLimiter:
    """Thread-safe minimum-interval gate."""

    def __init__(self, min_interval_s: float = DEFAULT_MIN_INTERVAL_S) -> None:
        self._min = float(min_interval_s)
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._min - (now - self._last)
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last = time.monotonic()


_DEFAULT_LIMITER = _RateLimiter()


def gate(*, limiter: _RateLimiter | None = None) -> None:
    """Block until the rate limiter allows the next call."""
    (limiter or _DEFAULT_LIMITER).wait()


# Shared retry decorator. Retries on common transient errors. Production
# fetch code wraps each request with this.
def transient(
    exc_types: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError),
) -> Callable[[F], F]:
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(exc_types),
        reraise=True,
    )
