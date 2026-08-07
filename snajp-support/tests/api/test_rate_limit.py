import pytest

from app.api.rate_limit import RateLimitExceededError, RateLimitRule, SlidingWindowRateLimiter


def test_allows_up_to_the_limit():
    limiter = SlidingWindowRateLimiter()
    rule = RateLimitRule(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("ip:1.2.3.4", rule, now=0.0)  # kastar inte


def test_blocks_the_request_that_exceeds_the_limit():
    limiter = SlidingWindowRateLimiter()
    rule = RateLimitRule(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("ip:1.2.3.4", rule, now=0.0)
    with pytest.raises(RateLimitExceededError):
        limiter.check("ip:1.2.3.4", rule, now=0.0)


def test_window_slides_old_hits_expire():
    limiter = SlidingWindowRateLimiter()
    rule = RateLimitRule(max_requests=2, window_seconds=60)
    limiter.check("k", rule, now=0.0)
    limiter.check("k", rule, now=10.0)
    with pytest.raises(RateLimitExceededError):
        limiter.check("k", rule, now=20.0)
    # 61s efter det första anropet har det lämnat fönstret — nu finns bara ett kvar.
    limiter.check("k", rule, now=61.0)


def test_different_keys_are_independent():
    limiter = SlidingWindowRateLimiter()
    rule = RateLimitRule(max_requests=1, window_seconds=60)
    limiter.check("ip:1.2.3.4", rule, now=0.0)
    limiter.check("ip:5.6.7.8", rule, now=0.0)  # kastar inte — annan nyckel
