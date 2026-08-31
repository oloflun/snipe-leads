"""Snajp-Support — headless AI-kundtjänstbackend.

Arkitekturen följer jawwad-ali/ai-customer-support-agent: FastAPI som tunt
HTTP-lager, agentloop via OpenAI Agents SDK, Postgres/pgvector som CRM +
semantisk kunskapsbas, async jobb med 202 + polling. Utan databas/Redis/nyckel
degraderar tjänsten gracefully till in-memory + simuleringsläge.
"""

import logging
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

import asyncio

from .api import (
    admin,
    admin_konvertera,
    admin_kunddata,
    admin_profil,
    analytics,
    bookkeeping,
    chat,
    demo,
    drafts,
    inbox,
    kb,
    keys,
    leads,
    rules,
    tickets,
    triage,
)
from .api.events import install_exception_handler
from .config import DEFAULT_TENANT_ID, get_settings
from .jobs.store import MemoryJobStore, RedisJobStore
from .storage.memory import MemoryStorage

logger = logging.getLogger("snajp-support")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # DATASKYDDSSPÄRR — körs FÖRST, före databas, Redis och allt annat.
    #
    # Den fäller uppstarten om LLM_PROVIDER pekar på en leverantör som inte
    # får ta emot personuppgifter i den här miljön (idag: DeepSeek i main och
    # development). Se Settings.llm_provider_fault för hela motiveringen.
    #
    # ATT DEN LIGGER I lifespan OCH INTE VID FÖRSTA ANROPET är hela poängen:
    # ett fel som slår vid första kundmejlet har redan hunnit skicka ett
    # kundmejl. Railway markerar en deploy som misslyckad när processen dör
    # här, och den föregående versionen ligger kvar — alltså rätt utfall också
    # driftmässigt.
    provider_fel = settings.llm_provider_fault()
    if provider_fel:
        logger.critical("Startvägran: %s", provider_fel)
        raise RuntimeError(provider_fel)

    # Samma princip för masternyckeln: en databas-miljö som kör med den
    # incheckade dev-defaulten har en öppen adminyta, och det ska synas som
    # en död deploy inom minuter — inte som en tyst yta tills någon provar.
    master_fel = settings.master_key_fault()
    if master_fel:
        logger.critical("Startvägran: %s", master_fel)
        raise RuntimeError(master_fel)

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

    # Fas R2 (bd snipe-cku): embeddingcache + semantisk svarscache mot
    # Redis. EGEN klient, INTE jobs.client: den senare har
    # decode_responses=True (jobbposter är JSON-text), medan cachen lagrar
    # binärpackade float32-vektorer (struct, se app/cache/embeddingcache.py)
    # och FT.*-kommandon som vill ha råa bytes — att dela klienten hade gjort
    # den binära vägen tyst trasig varje gång jobbkön också var aktiv.
    # Samma gracefulla nedgradering som jobbkön ovan: går anslutningen inte
    # kör processen ändå vidare med MinnesEmbeddingCache/MinnesSvarscache,
    # som redan är den väg hela testsviten kör.
    if settings.redis_url:
        try:
            import redis.asyncio as redis_asyncio

            cache_redis = redis_asyncio.from_url(settings.redis_url, decode_responses=False)
            await cache_redis.ping()
            from .cache import embeddingcache, svarscache
            from .cache import versioner as cache_versioner
            from .minne import arbetsminne

            embeddingcache.konfigurera(cache_redis)
            svarscache.konfigurera(cache_redis)
            cache_versioner.konfigurera(cache_redis)
            # Fas R3 (bd snipe-7mk): SAMMA klient som svarscachen ovan — en
            # tredje HASH-yta i samma Redis, inget nytt anslutningsbehov.
            arbetsminne.konfigurera(cache_redis)
            logger.info(
                "Semantisk svarscache: Redis (embeddingcache + svarscache + "
                "versioner + arbetsminne)."
            )
        except Exception as error:  # noqa: BLE001 — samma gracefulla nedgradering som Redis-anslutningen ovan
            logger.warning(
                "Cache-Redis otillgänglig (%s) — embeddingcache/svarscache/versioner kör in-memory.",
                error,
            )

    # Fas R1 (bd snipe-lr7): chattkörningar ska ÖVERLEVA en deploy. Utan det
    # här körde POST /api/chat agentkedjan som asyncio.create_task i SAMMA
    # process — en deploy dödar den processen mitt i körningen, jobbposten
    # blir kvar som "processing" och auto-failas efter 300 s (JOB_TIMEOUT_
    # SECONDS i app/jobs/store.py). Kunden fick fel i stället för sitt svar.
    #
    # Bara meningsfullt med en RIKTIG Redis (jobs är RedisJobStore) — utan
    # Redis finns ingen ström att dela mellan processer, och paritetsvägen
    # (create_task i chat.py) är redan den befintliga, testade vägen.
    chattstrom = None
    chat_worker_tasks: list[asyncio.Task] = []
    if isinstance(jobs, RedisJobStore):
        try:
            from .api.chat import hantera_strom_jobb
            from .jobs.stream import ChattStrom, consumer_name

            # SAMMA klient som RedisJobStore redan öppnat — en anslutning
            # mindre att hantera i drift, se app/jobs/stream.py.
            chattstrom = ChattStrom(jobs.client)
            hanterare = partial(hantera_strom_jobb, app.state)
            # Engångssvep INNAN några worker-tasks startar: poster som en
            # process som dog FÖRE den här deployen lämnade okvitterade ska
            # plockas upp direkt, inte vänta på att en worker råkar hinna dit.
            atertagna = await chattstrom.atertag(hanterare)
            logger.info(
                "Chattström: Redis-baserad jobbkö aktiv (%d poster återtagna vid "
                "uppstart, %d workers).",
                atertagna,
                settings.chat_workers,
            )
            for i in range(max(settings.chat_workers, 1)):
                chat_worker_tasks.append(
                    asyncio.create_task(chattstrom.worker_loop(consumer_name(i), hanterare))
                )
        except Exception as error:  # noqa: BLE001 — samma gracefulla nedgradering som Redis-anslutningen ovan
            logger.warning(
                "Chattström kunde inte startas (%s) — /api/chat faller tillbaka på "
                "create_task i den här processen (samma beteende som utan Redis).",
                error,
            )
            for task in chat_worker_tasks:
                task.cancel()
            chattstrom = None
            chat_worker_tasks = []
    app.state.chattstrom = chattstrom

    # Fas R4 (bd snipe-2xj): leads-batchens per-prospekt-jobb ska ÖVERLEVA en
    # deploy på SAMMA strömmönster som chatten ovan — en batch på upp till 50
    # prospekt (LeadsBatchRequest.limit) tar minuter, och en deploy mitt i
    # lämnade tidigare resten av köade prospekt permanent okörda (asyncio.
    # create_task dör med processen). Egen ström (crm:jobb:leads) och egen
    # consumer-grupp, SAMMA ChattStrom-klass (app/jobs/stream.py generaliserad
    # minimalt för Fas R4) och SAMMA Redis-klient som RedisJobStore — ingen ny
    # anslutning. Bara meningsfullt när jobs faktiskt är RedisJobStore, av
    # samma skäl som chattströmmen.
    leadsstrom = None
    leads_worker_tasks: list[asyncio.Task] = []
    if isinstance(jobs, RedisJobStore):
        try:
            from .api.leads import hantera_leads_jobb
            from .jobs.stream import ChattStrom, consumer_name

            leadsstrom = ChattStrom(jobs.client, stream_key="crm:jobb:leads", group="agenter")
            leads_hanterare = partial(hantera_leads_jobb, app.state)
            # Engångssvep INNAN några leads-worker-tasks startar — samma skäl
            # som chattströmmens engångssvep ovan: en batch som stod mitt i
            # när en tidigare process dog ska plockas upp direkt vid uppstart.
            leads_atertagna = await leadsstrom.atertag(leads_hanterare)
            logger.info(
                "Leadsström: Redis-baserad jobbkö aktiv (%d poster återtagna vid "
                "uppstart, %d workers).",
                leads_atertagna,
                settings.leads_workers,
            )
            for i in range(max(settings.leads_workers, 1)):
                leads_worker_tasks.append(
                    asyncio.create_task(
                        leadsstrom.worker_loop(consumer_name(f"leads-{i}"), leads_hanterare)
                    )
                )
        except Exception as error:  # noqa: BLE001 — samma gracefulla nedgradering som chattströmmen
            logger.warning(
                "Leadsström kunde inte startas (%s) — /api/leads/runs/batch faller "
                "tillbaka på create_task i den här processen (samma beteende som "
                "utan Redis).",
                error,
            )
            for task in leads_worker_tasks:
                task.cancel()
            leadsstrom = None
            leads_worker_tasks = []
    app.state.leadsstrom = leadsstrom

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
    for task in chat_worker_tasks:
        task.cancel()
    for task in leads_worker_tasks:
        task.cancel()
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
# Skrivytan mot agentprofilen. Egen modul, samma prefix och samma master-nyckel —
# se docstringen i api/admin_profil.py för varför läsning och skrivning är skilda åt.
app.include_router(admin_profil.router)
# Kundregistret — fliken Kunder & Data. Egen modul av samma skäl som profilen,
# se docstringen i api/admin_kunddata.py.
app.include_router(admin_kunddata.router)
app.include_router(admin_konvertera.router)
app.include_router(analytics.router)
app.include_router(bookkeeping.router)

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

    # En TRASIG nyckel får sitt eget besked. "Ingen giltig LLM-nyckel" är sant
    # men oanvändbart när nyckeln är satt: den som läser det letar efter en
    # saknad variabel, inte efter ett felaktigt tecken i den som redan finns.
    key_fault = settings.llm_key_fault()
    if key_fault:
        warnings.append(key_fault)
    elif settings.is_simulation():
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

    # Embeddings har sin egen hälsa, och den var OSYNLIG här.
    #
    # `mode: live` mäter LLM-nyckeln. Embeddings går mot en ANNAN leverantör
    # med en annan nyckel och en annan modell, och den kedjan kan vara helt
    # trasig medan raden ovan säger att allt är bra. Två gånger nu:
    #
    #  1. Gemini-API:t var aldrig aktiverat på Google-projektet → 403 på varje
    #     anrop. Noll av 159 artiklar fick en vektor, och sökningen föll tyst
    #     tillbaka på fulltext.
    #  2. EMBEDDING_MODEL stod på `text-embedding-3-small` — ett OPENAI-namn —
    #     mot Geminis endpoint → 404. Samma klass av fel som produktionens
    #     MODEL-krock, och lika osynlig.
    #
    # Kontrollen är på NAMN och nyckel, inte ett riktigt anrop: en hälsokontroll
    # som kostar pengar per pollning blir avstängd, och då mäter den ingenting.
    for embedding_fel in settings.embedding_faults():
        warnings.append(embedding_fel)

    # Sändvägen rapporteras från providern i stället för från en SMTP-config,
    # eftersom det är LoggingSendProvider som är sanningen i dag: den loggar
    # och skickar ingenting. Att läsa av typen är ärligare än att gissa på
    # frånvaron av env-variabler som inte finns modellerade än.
    from .leads.send_provider import (
        DryRunMailer,
        LoggingSendProvider,
        ResendMailer,
        get_send_provider,
    )

    sandvag = get_send_provider()
    if isinstance(sandvag, ResendMailer):
        logger.info("Sändväg: Resend (HTTPS) — SMTP-blockeringen berör oss inte.")
    if isinstance(sandvag, DryRunMailer):
        warnings.append(
            "Torrkörningsläge (SNAJP_OUTBOX_DIR) — mejl skrivs till fil, "
            "ingenting skickas. Ska aldrig vara satt i en deployad miljö."
        )
    elif isinstance(sandvag, LoggingSendProvider):
        warnings.append(
            "Ingen riktig sändväg — godkända svar loggas men skickas aldrig till kund. "
            "Railway blockerar SMTP på Free/Trial/Hobby; sätt RESEND_API_KEY för "
            "utskick över HTTPS (DEPLOY.md)."
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
