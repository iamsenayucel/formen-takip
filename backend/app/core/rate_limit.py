from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Depends

from app.api.deps import get_current_identity
from app.core.config import get_settings
from app.core.errors import RateLimitExceededError
from app.schemas.auth import Identity


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(bucket[0] + window_seconds - now) + 1)
                return False, retry_after
            bucket.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def rate_limit(scope: str, *, limit_attr: str, window_attr: str):
    def dependency(identity: Identity = Depends(get_current_identity)) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled or settings.environment == "test":
            return
        limit = getattr(settings, limit_attr)
        window_seconds = getattr(settings, window_attr)
        allowed, retry_after = limiter.check(f"{scope}:{identity.subject}", limit, window_seconds)
        if not allowed:
            raise RateLimitExceededError(
                "İstek limiti aşıldı, lütfen daha sonra tekrar deneyin.", retry_after_seconds=retry_after,
            )

    return dependency


rate_limit_default = rate_limit(
    "default", limit_attr="rate_limit_default_limit", window_attr="rate_limit_default_window_seconds"
)
rate_limit_llm = rate_limit(
    "llm", limit_attr="rate_limit_llm_limit", window_attr="rate_limit_llm_window_seconds"
)
rate_limit_report = rate_limit(
    "report", limit_attr="rate_limit_report_limit", window_attr="rate_limit_report_window_seconds"
)
rate_limit_pdf = rate_limit(
    "pdf", limit_attr="rate_limit_pdf_limit", window_attr="rate_limit_pdf_window_seconds"
)
