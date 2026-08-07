"""G8: den publika, oautentiserade demon. Ingen X-API-Key krävs — det är
hela poängen (ett smakprov utan friktion). Två oberoende rate-tak (session
+ IP) och en hårdkodad, isolerad demo-tenant som aldrig kan bytas ut av
klienten (samma princip som G2: tenant kommer aldrig från utsidan)."""

import uuid

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..config import (
    PUBLIC_DEMO_IP_WINDOW_SECONDS,
    PUBLIC_DEMO_MAX_PER_IP,
    PUBLIC_DEMO_MAX_PER_SESSION,
    PUBLIC_DEMO_SESSION_WINDOW_SECONDS,
    get_settings,
)
from .rate_limit import RateLimitExceededError, RateLimitRule, SlidingWindowRateLimiter

router = APIRouter()

_limiter = SlidingWindowRateLimiter()
_SESSION_COOKIE = "snajp_demo_session"
_IP_RULE = RateLimitRule(PUBLIC_DEMO_MAX_PER_IP, PUBLIC_DEMO_IP_WINDOW_SECONDS)
_SESSION_RULE = RateLimitRule(PUBLIC_DEMO_MAX_PER_SESSION, PUBLIC_DEMO_SESSION_WINDOW_SECONDS)


class DemoChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


def _client_ip(request: Request) -> str:
    # Bakom en proxy (Render) är X-Forwarded-For auktoritativ; annars client.host.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/api/demo/chat")
async def demo_chat(request: Request, response: Response, payload: DemoChatRequest) -> dict:
    session_id = request.cookies.get(_SESSION_COOKIE) or str(uuid.uuid4())
    response.set_cookie(_SESSION_COOKIE, session_id, max_age=PUBLIC_DEMO_SESSION_WINDOW_SECONDS, httponly=True)

    try:
        _limiter.check(f"ip:{_client_ip(request)}", _IP_RULE)
        _limiter.check(f"session:{session_id}", _SESSION_RULE)
    except RateLimitExceededError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error

    if get_settings().is_simulation():
        from ..simulation.sim_demo_agent import run_demo_sim_agent

        result = await run_demo_sim_agent(request.app.state.storage, message=payload.message)
    else:
        from ..agent.demo_agent import run_demo_agent

        result = await run_demo_agent(request.app.state.storage, message=payload.message)
    return result
