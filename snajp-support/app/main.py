"""Snajp-Support — headless AI-kundtjänstbackend.

Arkitekturen följer jawwad-ali/ai-customer-support-agent: FastAPI som tunt
HTTP-lager, agentloop via OpenAI Agents SDK, Postgres/pgvector som CRM +
semantisk kunskapsbas, async jobb med 202 + polling. Utan databas/Redis/nyckel
degraderar tjänsten gracefully till in-memory + simuleringsläge.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import asyncio

from .api import chat, drafts, inbox, kb, keys, rules, tickets, triage
from .config import get_settings
from .jobs.store import MemoryJobStore, RedisJobStore
from .storage.memory import MemoryStorage

logger = logging.getLogger("snajp-support")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    storage = None
    if settings.database_url:
        try:
            from .storage.postgres import PostgresStorage

            storage = await PostgresStorage.connect(settings.database_url)
            logger.info("Lagring: Postgres (Supabase)")
        except Exception as error:
            logger.warning("Postgres otillgänglig (%s) — faller tillbaka till in-memory.", error)
    if storage is None:
        storage = MemoryStorage()
        logger.info("Lagring: in-memory (demo-läge)")
    app.state.storage = storage

    jobs = None
    if settings.redis_url:
        try:
            jobs = await RedisJobStore.connect(settings.redis_url)
            logger.info("Jobbkö: Redis")
        except Exception as error:
            logger.warning("Redis otillgänglig (%s) — faller tillbaka till in-memory.", error)
    if jobs is None:
        jobs = MemoryJobStore()
        logger.info("Jobbkö: in-memory")
    app.state.jobs = jobs

    if settings.is_simulation():
        logger.info("LLM-nyckel saknas/platshållare — SIMULERINGSLÄGE aktivt.")
    else:
        from .agent.llm import configure_agents_sdk

        configure_agents_sdk()
        logger.info(
            "LLM-nyckel hittad — riktig agent aktiv (provider=%s, modell=%s).",
            settings.llm_provider,
            settings.model,
        )

    poller_task = None
    if settings.inbox_poll_seconds > 0:
        from .email_pipeline.poller import run_poller

        poller_task = asyncio.create_task(run_poller(app.state))

    yield

    if poller_task:
        poller_task.cancel()
    await storage.close()


app = FastAPI(title="Snajp-Support", version="0.1.0", lifespan=lifespan)

app.include_router(chat.router)
app.include_router(triage.router)
app.include_router(tickets.router)
app.include_router(keys.router)
app.include_router(kb.router)
app.include_router(inbox.router)
app.include_router(drafts.router)
app.include_router(rules.router)


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "mode": "simulation" if settings.is_simulation() else "live",
        "model": settings.model,
        "storage": app.state.storage.name,
        "jobs": app.state.jobs.name,
    }


@app.get("/health/live")
async def health_live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict:
    return {"status": "ok", "storage": app.state.storage.name}
