"""Chat-endpointen: 202 + job_id, bakgrundskörning, polling — som i referensrepot.

Multi-tenant: nyckeln avgör tenant; agentkörningen och jobbresultatet är
skopade till den tenanten.
"""

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from . import rate_limit_db
from .deps import require_tenant
from .schemas import ChatRequest

logger = logging.getLogger("snajp-support")

router = APIRouter()

MAX_ATTACHMENT_BYTES = 6_000_000  # ~4,5 MB bild efter base64-påslag


def _validate_attachments(request: ChatRequest) -> list[str]:
    urls: list[str] = []
    for attachment in request.attachments[:3]:
        data_url = attachment.data_url
        if not data_url.startswith("data:image/"):
            raise HTTPException(status_code=422, detail="Endast bilder (data:image/...) stöds.")
        if len(data_url) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=422, detail="Bilden är för stor (max ~4 MB).")
        urls.append(data_url)
    return urls


async def _process(
    app_state,
    job_id: str,
    tenant_id: str,
    request: ChatRequest,
    attachments: list[str],
    scopes: list[rate_limit_db.Scope] | None = None,
    *,
    # Trådas vidare till run_support_agent för återupptagningsvägen
    # (INV-JOB-001, se app/agent/support_agent.py och app/jobs/stream.py).
    # Båda None som default: paritetsvägen (create_task, ingen ChattStrom)
    # kallar _process utan dem och beteendet är OFÖRÄNDRAT.
    aterta: dict[str, str] | None = None,
    vid_arende: Any = None,
) -> None:
    settings = get_settings()
    storage = app_state.storage
    try:
        if settings.is_simulation():
            from ..simulation.sim_agent import run_sim_agent

            result = await run_sim_agent(
                storage,
                tenant_id,
                message=request.message,
                subject=request.subject,
                channel=request.channel,
                customer_email=request.customer_email,
                customer_name=request.customer_name,
                has_image=bool(attachments),
            )
        else:
            from ..agent.support_agent import run_support_agent

            result = await run_support_agent(
                storage,
                tenant_id,
                message=request.message,
                subject=request.subject,
                channel=request.channel,
                customer_email=request.customer_email,
                customer_name=request.customer_name,
                attachments=attachments,
                aterta=aterta,
                vid_arende=vid_arende,
                is_test=request.is_test,
            )
        # Bokför de LLM-anrop körningen FAKTISKT gjorde — ett steg är ett
        # anrop, och antalet varierar med eskalering och omkörning. Ett tak
        # räknat i meddelanden hade mätt fel storhet (migration 019).
        #
        # Fas R2: en cacheträff (SEMANTIC_CACHE=on) lägger ett PSEUDO-steg i
        # step_log för spårbarhet (nyckeln "step", se
        # app/cache/svarscache.svara_fran_cache) men gjorde noll LLM-anrop.
        # Räkna bara posterna som FAKTISKT är ett LLM-steg (nyckeln "skill",
        # satt av app/agent/step_runner.RunTrace.as_log) — annars hade en
        # cachad replik bokförts som om den kostat lika mycket kvot som en
        # full körning, trots att den inte gjorde ett enda anrop.
        llm_steg = [steg for steg in (result.get("step_log") or []) if "skill" in steg]
        await rate_limit_db.record(storage, scopes or [], len(llm_steg))
        await app_state.jobs.complete(job_id, result)
    except Exception:  # noqa: BLE001 — jobbet får aldrig fastna i processing
        # Loggen får HELA stacken, jobbet får en mening.
        #
        # Utan raden nedan blev varje agentfel en enrads-gåta: en skarp körning
        # föll på "'ascii' codec can't encode character 'à' in position 7"
        # och ingenting i loggen sa VAR. Att felsöka en produktionsincident på
        # ett stringifierat undantag är att gissa. Jobbet ska däremot inte bära
        # en stack — den går till kunden.
        logger.exception("Agentkörningen misslyckades (job %s, tenant %s)", job_id, tenant_id)
        # En FAST mening, inte str(error): undantagstexten visades tidigare
        # ordagrant i den publika chattbubblan ("'ascii' codec can't encode
        # character 'à' in position 7"). Diagnosen finns redan i loggen ovan.
        await app_state.jobs.fail(
            job_id,
            "Svaret gick inte att ta fram den här gången. "
            "Prova gärna igen om en liten stund.",
        )


async def hantera_strom_jobb(app_state, payload: dict[str, Any]) -> None:
    """Kör ETT jobb ur chattströmmen.

    Det här är hanteraren som skickas till ChattStrom.worker_loop/atertag
    (app/jobs/stream.py) — samma funktion oavsett om posten läses för första
    gången eller är en ÅTERTAGEN post efter att en tidigare process dött.

    Jobbposten läses FÖRST. Bär den redan ett ticket_id/conversation_id (satt
    av vid_arende nedan i ett tidigare, avbrutet försök) är det här en
    återupptagning — run_support_agent får då `aterta` och hoppar över
    create_ticket/save_message för det inkommande meddelandet i stället för
    att skapa ett andra ärende av samma chattmeddelande (INV-JOB-001).
    Klockan för 300-sekundersgränsen (app/jobs/store.py JOB_TIMEOUT_SECONDS)
    flyttas BARA i det fallet — annars hade tid som redan gått åt i det
    avbrutna första försöket ätit upp återupptagningens egen tidsbudget.
    """
    job_id = payload["job_id"]
    tenant_id = payload["tenant_id"]
    jobs = app_state.jobs

    befintligt = await jobs.get(job_id) or {}
    # Dör processen i fönstret mellan jobs.complete() och XACK ligger posten
    # kvar okvitterad fast svaret redan är levererat. Utan den här vakten
    # hade återtaget kört HELA agentkedjan en gång till — sex-sju LLM-anrop,
    # ett dubblerat utgående svar och en andra agent_runs-rad för samma
    # chattmeddelande. Ett redan färdigt jobb kvitteras bara. ("failed" tas
    # däremot om med flit: en körning som hann märkas failed av ett hanterat
    # fel och SEDAN kraschade får en andra chans, och aterta-vägen gör
    # omtaget dubblettsäkert.)
    if befintligt.get("status") == "completed":
        return
    aterta = None
    if befintligt.get("ticket_id") and befintligt.get("conversation_id"):
        aterta = {
            "ticket_id": befintligt["ticket_id"],
            "conversation_id": befintligt["conversation_id"],
        }
        await jobs.annotate(job_id, created=time.time())

    async def vid_arende(ticket_id: str, conversation_id: str) -> None:
        await jobs.annotate(job_id, ticket_id=ticket_id, conversation_id=conversation_id)

    request = ChatRequest(
        message=payload["message"],
        subject=payload.get("subject") or "",
        channel=payload.get("channel") or "web",
        customer_email=payload.get("customer_email"),
        customer_name=payload.get("customer_name"),
        is_test=bool(payload.get("is_test")),
    )
    # x-snajp-user/is_demo gick igenom strömmen som RÅA primitiver (aldrig
    # ett Scope-objekt, se chat() nedan) — scopes byggs om här, exakt som de
    # byggdes vid enqueue.
    scopes = rate_limit_db.scopes_for(
        tenant_id,
        payload.get("rate_limit_user"),
        is_demo=bool(payload.get("rate_limit_is_demo")),
    )
    await _process(
        app_state,
        job_id,
        tenant_id,
        request,
        payload.get("attachments") or [],
        scopes,
        aterta=aterta,
        vid_arende=vid_arende,
    )


@router.post("/api/chat", status_code=202)
async def chat(
    request: Request, payload: ChatRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    attachments = _validate_attachments(payload)

    # X-Snajp-User sätts av Next-proxyn efter sessionen. Den är frivillig:
    # saknas den gäller bara tenant-taket, och en förfalskad rubrik kan bara
    # ge en snävare kvot åt den som förfalskar den.
    x_snajp_user = request.headers.get("x-snajp-user")
    is_demo = request.headers.get("x-snajp-demo") == "true"
    scopes = rate_limit_db.scopes_for(tenant["tenant_id"], x_snajp_user, is_demo=is_demo)
    try:
        await rate_limit_db.enforce(request.app.state.storage, scopes)
    except rate_limit_db.RateLimitDbExceededError as error:
        # 429 med svenskt besked. En slut kvot är inte ett fel i koden, och
        # meddelandet ska gå att förstå utan att läsa loggen.
        raise HTTPException(status_code=429, detail=str(error)) from error

    job_id = await request.app.state.jobs.create(tenant_id=tenant["tenant_id"])

    chattstrom = getattr(request.app.state, "chattstrom", None)
    if chattstrom is not None:
        # Strömvägen (Fas R1): jobbet körs av en worker-process — kanske en
        # annan än den som svarar på det här anropet — och överlever en
        # deploy av DEN HÄR processen. Se app/jobs/stream.py och INV-JOB-001.
        #
        # x-snajp-user och is_demo skickas som RÅA primitiver, ALDRIG som
        # Scope-objekt: ett Scope är inte JSON-serialiserbart som sig
        # självt, och att pickla/serialisera dataklassen hade bakat in ett
        # internt datakontrakt i Redis-nyttolasten. hantera_strom_jobb
        # rekonstruerar scopes med samma rate_limit_db.scopes_for.
        await chattstrom.enqueue(
            {
                "job_id": job_id,
                "tenant_id": tenant["tenant_id"],
                "message": payload.message,
                "subject": payload.subject,
                "channel": payload.channel,
                "customer_email": payload.customer_email,
                "customer_name": payload.customer_name,
                "attachments": attachments,
                "rate_limit_user": x_snajp_user,
                "rate_limit_is_demo": is_demo,
                "is_test": payload.is_test,
            }
        )
    else:
        # Paritetsvägen — OFÖRÄNDRAD i minsta detalj, det är den hela
        # testsviten redan bevisar (t.ex. tests/test_api.py).
        asyncio.create_task(
            _process(request.app.state, job_id, tenant["tenant_id"], payload, attachments, scopes)
        )
    return {"job_id": job_id, "status": "processing"}


@router.get("/api/jobs/{job_id}")
async def get_job(
    request: Request, job_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    job = await request.app.state.jobs.get(job_id)
    if not job or job.get("tenant_id") != tenant["tenant_id"]:
        raise HTTPException(status_code=404, detail="Jobbet finns inte eller har städats bort.")
    return {"status": job["status"], "result": job.get("result"), "error": job.get("error")}
