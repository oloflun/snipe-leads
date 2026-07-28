"""Snajp-Support — headless AI-kundtjänstbackend.

Arkitekturen följer jawwad-ali/ai-customer-support-agent: FastAPI som tunt
HTTP-lager, agentloop via OpenAI Agents SDK, Postgres/pgvector som CRM +
semantisk kunskapsbas, async jobb med 202 + polling. Utan databas/Redis/nyckel
degraderar tjänsten gracefully till in-memory + simuleringsläge.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from .api.deps import require_tenant

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
            # En färsk databas har tom KB. Utan artiklar tvingar grundningsregeln
            # eskalering av varje ärende — seeda text direkt (embeddings via
            # `python -m app.scripts.seed_kb` när en EMBEDDING_API_KEY finns).
            try:
                from .scripts.seed_kb import ensure_default_kb

                added = await ensure_default_kb(storage)
                if added:
                    logger.info("Kunskapsbasen var tom — seedade %s artiklar.", added)
            except Exception as error:  # noqa: BLE001 — seedning får aldrig fälla uppstarten
                logger.warning("Kunde inte seeda kunskapsbasen (%s).", error)
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

    # Pilot-arbetsytan: skyddad tenant med riktig inkorg, skild från publika demon.
    if settings.snajp_pilot_api_key:
        from .config import PILOT_TENANT_ID, PILOT_TENANT_SLUG

        try:
            await storage.ensure_tenant(
                PILOT_TENANT_ID, slug=PILOT_TENANT_SLUG, name=settings.pilot_tenant_name
            )
            logger.info("Pilot-arbetsyta aktiv: %s", settings.pilot_tenant_name)
        except Exception as error:  # noqa: BLE001 — får inte fälla uppstarten
            logger.warning("Kunde inte skapa pilot-arbetsytan: %s", error)

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


def _health_payload(tenant_id: str | None = None) -> dict:
    settings = get_settings()
    has_inbox = bool(
        tenant_id
        and tenant_id == settings.imap_tenant_id()
        and settings.imap_host
        and settings.imap_user
        and settings.imap_password
    )
    return {
        "status": "ok",
        "mode": "simulation" if settings.is_simulation() else "live",
        "model": settings.model,
        "storage": app.state.storage.name,
        "jobs": app.state.jobs.name,
        "can_send_email": settings.can_send_email(),
        "auto_send_enabled": settings.allow_auto_send,
        # Har DENNA arbetsyta en kopplad riktig inkorg?
        "has_inbox": has_inbox,
    }


@app.get("/health")
async def health() -> dict:
    return _health_payload()


# Alias under /api så frontendens catch-all-proxy (som prefixar /api) når den.
# Tenant-medveten: svaret speglar den anropande arbetsytans möjligheter.
@app.get("/api/health")
async def api_health(tenant: dict = Depends(require_tenant)) -> dict:
    payload = _health_payload(tenant["tenant_id"])
    payload["tenant_name"] = tenant["tenant_name"]
    return payload


@app.get("/health/live")
async def health_live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict:
    return {"status": "ok", "storage": app.state.storage.name}
