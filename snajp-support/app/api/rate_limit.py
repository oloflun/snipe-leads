"""G8: "en publik LLM-endpoint utan tak är en räkning som skriver sig
själv." Enkel glidande-fönster-räknare i minnet, per nyckel (IP eller
session-id).

ponytail: global in-memory-räknare, en process. Tak: håller inte ihop
mellan flera instanser bakom en lastbalanserare. Uppgradera till en delad
räknare (Redis INCR + EXPIRE) den dagen tjänsten skalas horisontellt.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


class RateLimitExceededError(RuntimeError):
    pass


@dataclass(frozen=True)
class RateLimitRule:
    max_requests: int
    window_seconds: float


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, rule: RateLimitRule, *, now: float | None = None) -> None:
        """Kastar RateLimitExceededError om `key` redan gjort >= max_requests
        anrop inom window_seconds. Registrerar detta anropet om det tillåts."""
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        cutoff = now - rule.window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= rule.max_requests:
            raise RateLimitExceededError(
                f"Rate limit: {key!r} har redan {len(hits)} anrop senaste "
                f"{rule.window_seconds:.0f}s (max {rule.max_requests})."
            )
        hits.append(now)
