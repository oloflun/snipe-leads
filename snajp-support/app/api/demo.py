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
from . import rate_limit_db
from .rate_limit import RateLimitExceededError, RateLimitRule, SlidingWindowRateLimiter

router = APIRouter()

# Sessionstaket blir kvar i processminnet med flit. Det är ett UPPLEVELSE-tak
# på en cookie som en besökare rensar med ett klick, och det nollställs ändå
# vid varje ny flik. IP-taket är kostnadstaket, och det är det som flyttas till
# databasen — annars nollställdes det vid varje Render-spin-down, alltså precis
# innan den trafik som kommer i skov efter en tyst period.
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

    ip_scope = rate_limit_db.demo_ip_scope(_client_ip(request))
    try:
        _limiter.check(f"ip:{_client_ip(request)}", _IP_RULE)
        _limiter.check(f"session:{session_id}", _SESSION_RULE)
    except RateLimitExceededError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error

    try:
        await rate_limit_db.enforce(request.app.state.storage, ip_scope)
    except rate_limit_db.RateLimitDbExceededError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error

    if get_settings().is_simulation():
        from ..simulation.sim_demo_agent import run_demo_sim_agent

        result = await run_demo_sim_agent(request.app.state.storage, message=payload.message)
    else:
        from ..agent.demo_agent import run_demo_agent

        result = await run_demo_agent(request.app.state.storage, message=payload.message)

    # Ett svar = ett event. Demons tak är räknat i svar, inte i LLM-anrop:
    # det är ett kostnadstak på besök, och variationen i svaret är själva
    # säljargumentet — den ska aldrig strypas.
    await rate_limit_db.record(request.app.state.storage, ip_scope, 1)
    return result
