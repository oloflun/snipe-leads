"""Snajp-Support — headless AI-kundtjänstbackend.

Arkitekturen följer jawwad-ali/ai-customer-support-agent: FastAPI som tunt
HTTP-lager, agentloop via OpenAI Agents SDK, Postgres/pgvector som CRM +
semantisk kunskapsbas, async jobb med 202 + polling. Utan databas/Redis/nyckel
degraderar tjänsten gracefully till in-memory + simuleringsläge.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

import asyncio

from .api import admin, chat, demo, drafts, inbox, kb, keys, leads, rules, tickets, triage
from .api.events import install_exception_handler
from .config import DEFAULT_TENANT_ID, get_settings
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
                from .scripts.seed_kb import ensure_default_kb, ensure_public_demo_kb

                added = await ensure_default_kb(storage)
                if added:
                    logger.info("Kunskapsbasen var tom — seedade %s artiklar.", added)
                demo_added = await ensure_public_demo_kb(storage)
                if demo_added:
                    logger.info("G8-demons kunskapsbas var tom — seedade %s artiklar.", demo_added)
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

    poller_task = None
    if settings.inbox_poll_seconds > 0:
        from .email_pipeline.poller import run_poller

        poller_task = asyncio.create_task(run_poller(app.state))

    send_scheduler_task = None
    if settings.send_queue_poll_seconds > 0:
        from .leads.scheduler import run_send_scheduler

        send_scheduler_task = asyncio.create_task(run_send_scheduler(app.state))

    yield

    if poller_task:
        poller_task.cancel()
    if send_scheduler_task:
        send_scheduler_task.cancel()
    await storage.close()


app = FastAPI(title="Snajp-Support", version="0.1.0", lifespan=lifespan)

# CORS är AV som default och behövs inte för vår egen frontend — Next-proxyn
# anropar backenden server-side, så webbläsaren träffar aldrig den här
# tjänsten direkt. Den finns för den dag en kund anropar API:t från sin egen
# webbapp. `allow_credentials=False` med flit: auth sker med X-API-Key, inte
# med cookies, och att slå på credentials tillsammans med en bred origin-lista
# är precis hur en CORS-konfiguration blir en läcka.
_origins = [o.strip() for o in get_settings().allowed_origins.split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

app.include_router(chat.router)
app.include_router(triage.router)
app.include_router(tickets.router)
app.include_router(keys.router)
app.include_router(kb.router)
app.include_router(leads.router)
app.include_router(demo.router)
app.include_router(inbox.router)
app.include_router(drafts.router)
app.include_router(rules.router)
app.include_router(admin.router)

# Ohanterade fel hamnar i platform_events i stället för att rulla förbi i
# Renders stdout och försvinna vid nästa spin-down (migration 026).
install_exception_handler(app)


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
    """Liveness: processen svarar. Det är den Renders health check pollar."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(response: Response) -> dict:
    """Readiness: kan tjänsten faktiskt göra sitt jobb?

    Svarade tidigare alltid `{"status": "ok"}` oavsett läge, vilket gjorde den
    oanvändbar — en tjänst utan LLM-nyckel och utan databas rapporterade sig
    som frisk. Nu listas det som saknas i klartext.

    **200 även vid degraderat läge.** En 503 hade fått Render att ta ner en
    tjänst som fungerar, bara med simulerade svar eller utan persistens.
    `degraded` + `warnings` bär informationen; 503 ges bara när lagringen
    faktiskt är otillgänglig, vilket är det enda tillstånd där tjänsten inte
    kan svara på något alls.
    """
    settings = get_settings()
    warnings: list[str] = []

    if settings.is_simulation():
        warnings.append(
            "Ingen giltig LLM-nyckel — svaren genereras av den deterministiska "
            "regelmotorn, inte av AI."
        )
    if app.state.storage.name == "memory":
        warnings.append(
            "Ingen DATABASE_URL — data ligger i minnet och försvinner vid omstart."
        )
    if not (settings.imap_host and settings.imap_user and settings.imap_password):
        warnings.append("IMAP saknas — inga inkommande mail hämtas.")

    # Sändvägen rapporteras från providern i stället för från en SMTP-config,
    # eftersom det är LoggingSendProvider som är sanningen i dag: den loggar
    # och skickar ingenting. Att läsa av typen är ärligare än att gissa på
    # frånvaron av env-variabler som inte finns modellerade än.
    from .leads.send_provider import LoggingSendProvider, get_send_provider

    if isinstance(get_send_provider(), LoggingSendProvider):
        warnings.append(
            "Ingen riktig sändväg — godkända svar loggas men skickas aldrig till kund."
        )

    storage_ok = True
    try:
        await app.state.storage.get_channel_config(DEFAULT_TENANT_ID, "web")
    except Exception as error:  # noqa: BLE001 — readiness får aldrig kasta
        storage_ok = False
        warnings.append(f"Lagringen svarar inte: {error}")
        response.status_code = 503

    return {
        "status": "ok" if storage_ok else "unavailable",
        "degraded": bool(warnings),
        "storage": app.state.storage.name,
        "mode": "simulation" if settings.is_simulation() else "live",
        "warnings": warnings,
    }
