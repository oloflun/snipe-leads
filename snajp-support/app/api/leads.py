"""Leads-API: kontextdokument (Fas A), prospekt, research (Fas B),
outreach-utkast (Fas C), samt körningsloggen som gör hela research-processen
granskningsbar från dashboarden.

Onboarding är ALDRIG ett hårt hinder: /api/leads/onboarding/status visar vad
som saknas, och kontextpaketet byggs alltid (med explicita luckmarkeringar)
så att Fas B/C kan köra på det som finns i stället för att dödlåsa sig.
"""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from ..leads.autonomy import LEVELS as AUTONOMY_LEVELS
from ..leads.autonomy import describe as describe_autonomy
from ..leads.autonomy import kan_aktivera_auto_send
from ..leads.autonomy import normalize as normalize_autonomy
from ..leads.business_context import ar_ifyllt as business_context_ar_ifyllt
from ..leads.exempelbolag import bygg_exempelbolag
from ..leads.context_pack import build_context_pack, materialize_product_marketing
from ..leads.geo import beskriv_region, kanda_regioner
from ..leads.icp import (
    MAX_PROSPECTS_TAK,
    SMAFORETAG_ANSTALLDA,
    IcpValidationError,
    normalize_icp,
    validate_icp,
)
from ..leads.icp import is_empty as icp_ar_tomt
from ..leads.sni import SNI_NAMN, beskriv_kod
from ..leads.onboarding_state import REQUIRED_KINDS, get_onboarding_state
from .deps import kraev_uuid, require_tenant
from ..leads.soul import SOUL_KIND, SOUL_MAX_CHARS
from .schemas import (
    AgentFeedbackRequest,
    ContextDocRequest,
    ExempelbolagRequest,
    LeadsBatchRequest,
    LeadsConfigRequest,
    ProspectPatchRequest,
    OnboardingChatRequest,
    OutreachDraftRequest,
    ProspectRequest,
    ProspectSourceRequest,
    ProspektsvarRequest,
    ResearchStepRequest,
    SoulRequest,
)

router = APIRouter()


#: Etiketter affärskontexten är skriven med. Onboardingen bygger `product` som
#: en fältlista ("Organisationsnummer: … / Webbplats: … / Vad vi säljer: …"),
#: och den formen är gjord för att LÄSAS av agenten, inte för att stoppas in i
#: en mening.
_KONTEXTETIKETTER = (
    "vad vi säljer",
    "vi säljer",
    "produkt",
    "produkten",
    "erbjudande",
    "erbjudandet",
)

#: Rader som aldrig hör hemma i en pitch, hur tidigt de än står i dokumentet.
_HOPPA_OVER = ("organisationsnummer", "webbplats", "hemsida", "org.nr", "särskilt fokus")


def _produktrad(text: str, *, max_tecken: int = 180) -> str:
    """Vad kunden säljer, formulerat så att det kan följa efter "Vi säljer ".

    ## Vad som gick fel utan den här

    Uppmätt mot dev-deployen: pitchen sa

        "Vi säljer Vad vi säljer: Inredning och utemiljö för företag …"

    Affärskontexten är en FÄLTLISTA — onboardingen skriver den så — och att ta
    dess första mening rakt av tar med etiketten. Läsaren ser inte ett mejl med
    ett skarvfel; hen ser ett bolag som inte läst sitt eget utskick.

    ## Ordningen

    1. Leta efter fältet som faktiskt beskriver produkten och ta det som står
       EFTER kolonet.
    2. Annars första meningen som inte är org.nr, webbplats eller fokus.
    3. Första bokstaven gemeniseras: raden fortsätter en mening som redan
       börjat, och versalen mitt i den läser som ett citat.

    Tom sträng returneras oförändrad — anroparen har en tydlig platshållare, och
    en tom plats är bättre än en halv rubrik mitt i ett mejl.
    """
    rader = [rad.strip(" -•\t") for rad in (text or "").splitlines() if rad.strip()]
    if not rader:
        return ""

    kandidat = ""
    for rad in rader:
        etikett, _, resten = rad.partition(":")
        nyckel = etikett.strip().lower()
        if resten.strip() and nyckel in _KONTEXTETIKETTER:
            kandidat = resten.strip()
            break
        if resten.strip() and nyckel in _HOPPA_OVER:
            continue
        if not kandidat:
            # Ingen etikett vi känner igen — men raden kan ändå vara texten.
            kandidat = rad if not resten.strip() else resten.strip()

    rent = " ".join(kandidat.split())
    if not rent:
        return ""

    punkt = rent.find(". ")
    if 0 < punkt <= max_tecken:
        rent = rent[:punkt]
    else:
        rent = rent[:max_tecken]
    rent = rent.rstrip(" .,;:-–—")

    # "Inredning och utemiljö" -> "inredning och utemiljö". Bara första
    # tecknet: ett egennamn längre in i raden ska behålla sin versal.
    return rent[:1].lower() + rent[1:] if rent else rent


def _require_live_llm() -> None:
    if get_settings().is_simulation():
        raise HTTPException(
            status_code=503,
            detail="Kräver en riktig LLM-nyckel (DEEPSEEK_API_KEY). Se DEPLOY_KEYS.md — "
            "ingen simuleringsersättning finns för leads-ytorna.",
        )


# -- Fas A: kontextdokument och onboarding-status -------------------------


@router.post("/api/leads/context-docs", status_code=201)
async def add_context_doc(
    request: Request, payload: ContextDocRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    doc = await storage.save_context_doc(
        tenant["tenant_id"], kind=payload.kind, content=payload.content, source=payload.source
    )
    if payload.kind == "product_marketing":
        materialize_product_marketing(tenant["tenant_id"], payload.content)
    return {"doc": doc}


@router.get("/api/leads/context-docs")
async def list_context_docs(
    request: Request, tenant: dict = Depends(require_tenant), kind: str | None = None
) -> dict:
    docs = await request.app.state.storage.list_context_docs(tenant["tenant_id"], kind=kind)
    return {"docs": docs}


@router.get("/api/leads/onboarding/status")
async def onboarding_status(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Vad som saknas — underlaget för att trigga onboarding i efterhand."""
    state = await get_onboarding_state(request.app.state.storage, tenant["tenant_id"])
    return {
        "complete": state.complete,
        "started": state.started,
        "present": list(state.present),
        "missing": list(state.missing),
        "required": list(REQUIRED_KINDS),
    }


@router.get("/api/leads/context-pack")
async def get_context_pack(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    rendered, missing = await build_context_pack(request.app.state.storage, tenant["tenant_id"])
    return {"context_pack": rendered, "onboarding_missing": list(missing)}


@router.post("/api/leads/onboarding/chat")
async def onboarding_chat(
    request: Request, payload: OnboardingChatRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Fas A: en tur i onboarding-samtalet. Kan köras när som helst, även i
    efterhand för att fylla luckor som upptäckts under research."""
    _require_live_llm()
    from ..agent.leads_agent import run_onboarding_turn

    result = await run_onboarding_turn(
        request.app.state.storage, tenant["tenant_id"], message=payload.message
    )
    state = await get_onboarding_state(request.app.state.storage, tenant["tenant_id"])
    result["onboarding_missing"] = list(state.missing)
    return result


# -- Prospekt (ingången till hela pipelinen) ------------------------------


@router.post("/api/leads/prospects", status_code=201)
async def create_prospect(
    request: Request, payload: ProspectRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    prospect = await request.app.state.storage.create_prospect(
        tenant["tenant_id"],
        company_name=payload.company_name,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
    )
    return {"prospect": prospect}


@router.post("/api/leads/prospects/exempel", status_code=201)
async def create_example_prospects(
    request: Request, payload: ExempelbolagRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Exempelbolag som ligger inom ICP:t — vägen in för en tom arbetsyta.

    KRÄVER INTE en riktig LLM-nyckel, till skillnad från körningen den leder
    till. Generatorn är deterministisk (`leads/exempelbolag.py`), och en
    demonstrationsfunktion som bara fungerar när allt annat redan fungerar
    demonstrerar ingenting.

    Bolagen märks `origin='example'` och kan aldrig mejlas: scheduler-
    guarden slår upp kolumnen innan `provider.send()`.
    """
    storage = request.app.state.storage
    settings_rad = await storage.get_agent_settings(tenant["tenant_id"], agent_type="leads")
    icp = dict(normalize_icp(settings_rad.get("icp")))

    # Överskrivningarna gäller den här genereringen, precis som de gäller
    # körningen de leder till — annars beskriver formulärets fält en målgrupp
    # och de skapade bolagen en annan.
    if payload.overrides is not None and payload.overrides.har_nagot():
        over = payload.overrides.model_dump(exclude_none=True)
        for nyckel in ("industries", "exclude_industries", "geography", "roles",
                       "must_have", "deal_breakers"):
            if nyckel in over:
                icp[nyckel] = over[nyckel]
        if "anstallda_min" in over or "anstallda_max" in over:
            storlek = dict(icp.get("company_size") or {})
            if "anstallda_min" in over:
                storlek["min"] = over["anstallda_min"]
            if "anstallda_max" in over:
                storlek["max"] = over["anstallda_max"]
            icp["company_size"] = storlek

    # Pitchen ska handla om KUNDENS produkt, inte om en påhittad.
    #
    # Texten hämtas ur affärskontexten (`product_marketing`), som kunden själv
    # skrivit. Saknas den lämnas en tydlig plats att fylla i stället för en
    # uppfunnen produkt: en påhittad produkt i ett exempelmejl är en text kunden
    # måste skriva OM, och den läser dessutom som att vi gissat vad de säljer.
    produktdoc = await storage.get_latest_context_doc(
        tenant["tenant_id"], kind="product_marketing"
    )
    produkt = _produktrad((produktdoc or {}).get("content", ""))

    skapade = []
    for bolag in bygg_exempelbolag(
        icp,
        antal=payload.limit,
        produkt=produkt,
        avsandare=tenant.get("tenant_name") or None,
        # Ett nytt frö per anrop. Knappen "Uppdatera" ska ge NYA bolag och nya
        # utkast — samma tre varje gång hade sett trasigt ut, och poängen med
        # att uppdatera är att se agenten formulera sig om ett annat läge.
        fro=payload.fro or uuid.uuid4().hex[:8],
    ):
        prospect = await storage.create_prospect(
            tenant["tenant_id"],
            company_name=bolag["company_name"],
            contact_name=bolag["contact_name"],
            origin="example",
            # Org.nr, ort, webbplats och storlek SPARAS, de skickas inte bara
            # tillbaka. Vyn som listar exempelbolagen är samma vy som listar
            # riktiga prospekt, och ett bolag som bara har ett namn ser ut som
            # ett prospekt vars research misslyckats.
            profil={
                "orgnr": bolag["orgnr"],
                "ort": bolag["ort"],
                "website": bolag["website"],
                "anstallda": bolag["anstallda"],
            },
        )
        skapade.append(
            {
                **prospect,
                # Beskrivningen och motiveringen härleds ur ICP:t och hör inte
                # hemma i en kolumn — de beror på vilket ICP som gällde vid
                # genereringen, och sparade hade de blivit osanna nästa gång
                # kunden ändrar sin målgrupp.
                "beskrivning": bolag["beskrivning"],
                "signal": bolag["signal"],
                "bransch": bolag["bransch"],
                "motivering": bolag["motivering"],
                # Utkastet som öppnas i Email Studio. Sparas INTE som ett
                # outreach_message: ingenting här har passerat send_guard, och
                # ett utkast i kön är ett utkast som kan godkännas av misstag.
                "pitch_subject": bolag["pitch_subject"],
                "pitch_body": bolag["pitch_body"],
                "pitch_varfor_nu": bolag["pitch_varfor_nu"],
            }
        )

    return {"created": skapade, "count": len(skapade)}


@router.get("/api/leads/prospects")
async def list_prospects(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    prospects = await request.app.state.storage.list_prospects(tenant["tenant_id"])
    return {"prospects": prospects}


@router.get("/api/leads/prospects/{prospect_id}")
async def get_prospect(
    request: Request, prospect_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Ett prospekt plus dess källor — underlaget till bolagssidan i arbetsytan.

    Fanns inte förut, och det syntes: `/dashboard/companies/<id>` renderade
    `findCompany()` ur Next-appens mock-data, som faller tillbaka på FÖRSTA
    exempelbolaget när id:t inte hittas. Varje klick på ett riktigt prospekt
    visade alltså Byggkompaniet Syds påhittade researchpromemoria under det
    riktiga bolagets namn — värre än en 404, eftersom sidan såg komplett ut.

    404 här är med flit ett riktigt 404: ett prospekt som inte finns i den här
    tenanten ska inte kunna skiljas från ett som aldrig funnits.
    """
    kraev_uuid(prospect_id, "Prospektet")
    prospect = await request.app.state.storage.get_prospect(tenant["tenant_id"], prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")

    urls = await request.app.state.storage.list_prospect_source_urls(
        tenant["tenant_id"], prospect_id
    )
    # Sorterad lista och inte set: JSON har ingen mängdtyp, och en ordning som
    # varierar mellan anrop ger en sida som hoppar utan att något ändrats.
    return {"prospect": prospect, "sources": sorted(urls)}


@router.post("/api/leads/prospects/{prospect_id}/sources", status_code=201)
async def add_prospect_source(
    request: Request,
    prospect_id: str,
    payload: ProspectSourceRequest,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Registrerar en källa. INV-DATA-002 verkställs här: LinkedIn får inte
    vara prospektets FÖRSTA källa."""
    storage = request.app.state.storage
    if not await storage.get_prospect(tenant["tenant_id"], prospect_id):
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")

    existing = await storage.list_prospect_source_urls(tenant["tenant_id"], prospect_id)
    if payload.source_type == "linkedin" and not existing:
        raise HTTPException(
            status_code=422,
            detail="INV-DATA-002: LinkedIn får aldrig vara ett prospekts första källa — "
            "registrera en annan källa (företagswebb, register, nyhet) först.",
        )

    source = await storage.create_prospect_source(
        tenant["tenant_id"],
        prospect_id=prospect_id,
        source_url=payload.source_url,
        source_type=payload.source_type,
        lawful_basis=payload.lawful_basis,
    )
    return {"source": source}


# -- SOUL: kundens röstdokument -------------------------------------------


@router.get("/api/leads/soul")
async def get_soul(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    doc = await request.app.state.storage.get_latest_context_doc(
        tenant["tenant_id"], kind=SOUL_KIND
    )
    return {
        "content": (doc or {}).get("content", ""),
        "version": (doc or {}).get("version"),
        "max_chars": SOUL_MAX_CHARS,
    }


@router.put("/api/leads/soul")
async def put_soul(
    request: Request, payload: SoulRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Enda vägen SOUL skrivs.

    MEDVETET INTE exponerad som ett agentverktyg: kind-allowlisten i
    leads_tools._save_context_doc_impl utesluter 'soul' och ska fortsätta
    göra det. Onboarding-agenten ska inte kunna skriva kundens röstdokument
    — det är kundens egen text, och en agent som kan skriva den kan också
    skriva instruktioner till sig själv i den.
    """
    doc = await request.app.state.storage.save_context_doc(
        tenant["tenant_id"], kind=SOUL_KIND, content=payload.content, source="tenant-edit"
    )
    return {"saved": True, "version": doc["version"], "chars": len(payload.content)}


# -- Fas B/C: research och outreach ---------------------------------------


@router.post("/api/leads/research/step")
async def research_step(
    request: Request, payload: ResearchStepRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    _require_live_llm()
    from ..agent.leads_agent import run_research_step

    storage = request.app.state.storage
    if not await storage.get_prospect(tenant["tenant_id"], payload.prospect_id):
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")

    # Ingen overrides-parameter: ResearchStepRequest har bara prospect_id och
    # brief. Raden stod tidigare med `overrides=overrides` — en variabel som
    # aldrig bands i funktionen, alltså NameError och 500 på VARJE anrop med
    # skarp nyckel. Ingen test nådde routen, och simuleringsläget svarar 503
    # innan den raden, så sviten var grön.
    context_pack, missing = await build_context_pack(storage, tenant["tenant_id"])
    result = await run_research_step(
        storage,
        tenant["tenant_id"],
        prospect_id=payload.prospect_id,
        tenant_name=tenant["tenant_name"],
        context_pack=context_pack,
        brief=payload.brief,
    )
    result["onboarding_missing"] = list(missing)
    return result


@router.post("/api/leads/outreach/draft")
async def outreach_draft(
    request: Request, payload: OutreachDraftRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    _require_live_llm()
    from ..agent.leads_agent import run_outreach_draft as _run_outreach_draft

    storage = request.app.state.storage
    thread_id = await _los_trad(storage, tenant["tenant_id"], payload.thread_id, payload.prospect_id)
    context_pack, missing = await build_context_pack(storage, tenant["tenant_id"])
    result = await _run_outreach_draft(
        storage,
        tenant["tenant_id"],
        thread_id=thread_id,
        prospect_email=payload.prospect_email,
        tenant_name=tenant["tenant_name"],
        company_name=payload.company_name,
        offer_summary=payload.offer_summary,
        context_pack=context_pack,
        brief=payload.brief,
        research_summary=payload.research_summary,
        research_evidence=tuple(payload.research_evidence),
    )
    result["onboarding_missing"] = list(missing)
    return result


# -- Granskning: hela processen synlig från dashboarden -------------------


@router.get("/api/leads/runs")
async def list_runs(
    request: Request,
    tenant: dict = Depends(require_tenant),
    agent_type: str | None = None,
    limit: int = 50,
) -> dict:
    """G10-revisionsloggen. step_log innehåller ett steg per faktiskt
    LLM-anrop: vilken skill, antal försök, om steget eskalerade, latens och
    de sources_used/context_refs steget rapporterade."""
    runs = await request.app.state.storage.list_agent_runs(
        tenant["tenant_id"], agent_type=agent_type, limit=min(limit, 200)
    )
    return {"runs": runs}


# -- Fas 4: kundens kontroller över agenten -------------------------------
#
# Autonominivå, målgrupp (ICP) och granskningskö. Det är kunden som bestämmer
# hur långt agenten får gå, och det beslutet ska gå att ändra utan att vi
# deployar något.


async def _los_trad(
    storage, tenant_id: str, thread_id: str | None, prospect_id: str | None
) -> str:
    """Tråden ett anrop gäller: befintlig via id, annars skapad/återanvänd via
    prospektet. 404/422 med namnet på det som saknas — inte en död FK längre
    ned."""
    if thread_id:
        if not await storage.get_outreach_thread(tenant_id, thread_id):
            raise HTTPException(status_code=404, detail="Tråden finns inte.")
        return thread_id
    if prospect_id:
        if not await storage.get_prospect(tenant_id, prospect_id):
            raise HTTPException(status_code=404, detail="Prospektet finns inte.")
        thread = await storage.ensure_outreach_thread(tenant_id, prospect_id=prospect_id)
        return str(thread["id"])
    raise HTTPException(status_code=422, detail="Ange thread_id eller prospect_id.")


@router.post("/api/leads/svar")
async def ta_emot_prospektsvar(
    request: Request, payload: ProspektsvarRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Ett inkommande prospektsvar: klassificera och agera.

    Det här är produktionsanroparen som saknades — svaret sparas i
    outreach_messages (fliken Svar slutar vara tom), köade utskick ställs in
    eller skjuts, positiva svar blir handoff med sa:call-prep-underlag, och
    invändningar/frågor får ett svarsutkast som ALLTID hamnar i
    granskningskön. Se app/leads/svar.py.
    """
    _require_live_llm()
    from ..leads.svar import hantera_prospektsvar

    storage = request.app.state.storage
    thread_id = await _los_trad(storage, tenant["tenant_id"], payload.thread_id, payload.prospect_id)
    context_pack, _missing = await build_context_pack(storage, tenant["tenant_id"])
    return await hantera_prospektsvar(
        storage,
        tenant["tenant_id"],
        thread_id=thread_id,
        body=payload.body,
        tenant_name=tenant["tenant_name"],
        context_pack=context_pack,
        publik_bas_url=get_settings().publik_bas_url,
    )


@router.post("/api/leads/uppfoljning/svep")
async def kor_uppfoljningssvep(
    request: Request, tenant: dict = Depends(require_tenant)
) -> dict:
    """Kör uppföljningssvepet för DEN HÄR tenanten, nu.

    Schemaläggaren kör samma svep varje timme (scheduler.sweep_follow_ups);
    endpointen finns för dashboarden och för verifiering — "generera det som
    är förfallet, visa vad som hände" utan att vänta på nästa tick.
    """
    _require_live_llm()
    from datetime import datetime, timezone

    from ..leads.follow_up_generator import generate_due_follow_ups

    storage = request.app.state.storage
    context_pack, missing = await build_context_pack(storage, tenant["tenant_id"])
    if "product_marketing" in missing:
        raise HTTPException(
            status_code=422,
            detail="Affärskontexten saknas — uppföljningar kan inte grundas.",
        )
    rader = await generate_due_follow_ups(
        storage,
        tenant["tenant_id"],
        now=datetime.now(timezone.utc),
        tenant_name=tenant["tenant_name"],
        context_pack=context_pack,
    )
    return {"generated": rader, "count": len(rader)}


# -- Agentens föreslagna lärdomar (självlärning, migration 051) ------------


@router.get("/api/agent/forslag")
async def list_forslag(
    request: Request,
    status: str | None = None,
    limit: int = 50,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Förslagen agenterna samlat: KB-artiklar ur supportärenden,
    marknadsinsikter ur researchvarv. Agenten skriver aldrig själv in dem —
    listan finns för att en människa ska godkänna eller avfärda
    (INV-LEARN-001)."""
    rader = await request.app.state.storage.list_agent_suggestions(
        tenant["tenant_id"], status=status, limit=limit
    )
    return {"suggestions": rader}


@router.post("/api/agent/forslag/{suggestion_id}/godkann")
async def godkann_forslag(
    request: Request, suggestion_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Godkänn ett förslag. kb_article: artikeln SKAPAS här, i kod, av
    endpointen — det är människans klick som skriver, aldrig agenten.
    marknadsinsikt: markeras godkänd; själva ICP-/kontextändringen görs av
    människan i sina egna ytor, med insiktens text som underlag."""
    kraev_uuid(suggestion_id, "suggestion_id")
    storage = request.app.state.storage
    rad = await storage.update_agent_suggestion_status(
        tenant["tenant_id"], suggestion_id, status="godkand"
    )
    if rad is None:
        raise HTTPException(status_code=404, detail="Förslaget finns inte.")

    created = None
    if rad.get("kind") == "kb_article":
        innehall = rad.get("content") or {}
        if isinstance(innehall, str):
            import json as _json

            innehall = _json.loads(innehall)
        embedding = None
        if not get_settings().is_simulation():
            from ..agent.embeddings import embed_text

            embedding = await embed_text(f"{innehall.get('title')}\n{innehall.get('content')}")
        created = await storage.add_kb_article(
            tenant["tenant_id"],
            title=str(innehall.get("title") or rad["title"]),
            content=str(innehall.get("content") or ""),
            category=str(innehall.get("category") or "ovrigt"),
            embedding=embedding,
        )
    return {"suggestion": rad, "created_article": created}


@router.post("/api/agent/feedback", status_code=201)
async def lamna_agent_feedback(
    request: Request, payload: AgentFeedbackRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Kundens dom över en körning — första kodvägen till agent_feedback,
    som funnits i schemat sedan migration 010 utan att någon skrev till den.
    Samma felklass som instructions_md: tabellen sa att signalen samlades in,
    och ingenting gjorde det. En nedtummad körning med corrected_output är
    det starkaste underlaget lärandeflödet kan få."""
    kraev_uuid(payload.run_id, "run_id")
    storage = request.app.state.storage
    try:
        rad = await storage.save_agent_feedback(
            tenant["tenant_id"],
            run_id=payload.run_id,
            verdict=payload.verdict,
            comment=payload.comment,
            corrected_output=payload.corrected_output,
        )
    except ValueError as fel:
        raise HTTPException(status_code=404, detail=str(fel)) from fel

    # Langfuse/promptfoo-mönstret: golden-setet växer ur VERKLIGA fel. En
    # nedtummad körning med rättad text är per definition ett produktionsfel
    # med facit — den blir automatiskt ett eval-case (agent_evals), så nästa
    # eval-körning mäter att just det felet inte kommer tillbaka. Mekaniskt,
    # ingen modell: input är körningens input, facit är människans text.
    eval_case = None
    if payload.verdict == "bad" and payload.corrected_output:
        runs = await storage.list_agent_runs(tenant["tenant_id"], limit=200)
        run = next((r for r in runs if str(r.get("id")) == payload.run_id), None)
        if run and str(run.get("input") or "").strip():
            eval_case = await storage.save_eval_case(
                tenant["tenant_id"],
                agent_type="support" if run.get("agent_type") == "support" else "leads",
                input_text=str(run["input"]),
                expected_traits={"kalla": "feedback", "kommentar": payload.comment or ""},
                approved_output=payload.corrected_output,
            )
    return {"feedback": rad, "eval_case": eval_case}


@router.get("/api/agent/feedback")
async def list_agent_feedback(
    request: Request,
    verdict: str | None = None,
    limit: int = 50,
    tenant: dict = Depends(require_tenant),
) -> dict:
    rader = await request.app.state.storage.list_agent_feedback(
        tenant["tenant_id"], verdict=verdict, limit=limit
    )
    return {"feedback": rader}


@router.post("/api/agent/forslag/{suggestion_id}/avfard")
async def avfard_forslag(
    request: Request, suggestion_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(suggestion_id, "suggestion_id")
    rad = await request.app.state.storage.update_agent_suggestion_status(
        tenant["tenant_id"], suggestion_id, status="avfard"
    )
    if rad is None:
        raise HTTPException(status_code=404, detail="Förslaget finns inte.")
    return {"suggestion": rad}


@router.get("/api/leads/svar")
async def list_replies(
    request: Request, limit: int = 50, tenant: dict = Depends(require_tenant)
) -> dict:
    """Inkomna svar — arbetsytans Svar-flik.

    Fanns inte förut, och fliken visade därför sju PÅHITTADE svar ur Next-appens
    mock-data ("Låter relevant. Skicka gärna exempel...") för varje inloggad
    kund. Samma fel som bolagslistan och analysvyn hade.
    """
    svar = await request.app.state.storage.list_replies(tenant["tenant_id"], limit=limit)
    return {"replies": svar}


@router.get("/api/leads/config")
async def get_leads_config(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    settings = await request.app.state.storage.get_agent_settings(
        tenant["tenant_id"], agent_type="leads"
    )
    autonomy = normalize_autonomy(settings.get("autonomy"))
    return {
        "autonomy": autonomy,
        "autonomy_description": describe_autonomy(autonomy),
        "autonomy_levels": [
            {"value": level, "description": describe_autonomy(level)} for level in AUTONOMY_LEVELS
        ],
        "icp": normalize_icp(settings.get("icp")),
        # Valen som finns att välja MELLAN, inte kundens val. UI:t ska kunna
        # rendera en lista utan att ha en egen kopia av geo.py och sni.py —
        # en andra kopia hade drivit isär, och symptomet blivit att ett
        # regionval som ser giltigt ut i webbläsaren ger 422 vid sparning.
        "options": {
            "geo": [
                {"value": nyckel, "label": beskriv_region(nyckel)}
                for nyckel in kanda_regioner()
            ],
            "sni": [
                {"value": kod, "label": beskriv_kod(kod)} for kod in sorted(SNI_NAMN)
            ],
            "max_prospects_per_run_tak": MAX_PROSPECTS_TAK,
            "smaforetag_anstallda": list(SMAFORETAG_ANSTALLDA),
        },
    }


@router.put("/api/leads/config")
async def put_leads_config(
    request: Request, payload: LeadsConfigRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    current = await storage.get_agent_settings(tenant["tenant_id"], agent_type="leads")

    # Slår ihop i stället för att ersätta: UI:t har två separata formulär
    # (autonomi och ICP), och en PUT från det ena får inte nolla det andra.
    merged = dict(current)
    if payload.autonomy is not None:
        merged["autonomy"] = normalize_autonomy(payload.autonomy)
    if payload.icp is not None:
        # Skrivvägen är STRIKT (DEL 1.1). Ett ICP som inte går att tolka ska ge
        # 422 med ett begripligt svenskt fel — aldrig tyst falla tillbaka på
        # "alla företag i Sverige", vilket är vad ett bortfiltrerat geo-fält
        # hade betytt i praktiken.
        #
        # validate_icp returnerar det normaliserade värdet, så den tysta
        # borttagningen av okända nycklar (skyddet mot insmugglade
        # `system_prompt`) ligger kvar oförändrad. Se app/leads/icp.py.
        try:
            merged["icp"] = validate_icp(payload.icp)
        except IcpValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None

    # auto_send-grinden körs EFTER sammanslagningen, mot det ICP som faktiskt
    # kommer att gälla. Hade den körts mot `current` kunde en och samma PUT
    # både fylla i målgruppen och slå på automatiskt utskick, och grinden
    # hade bedömt ett läge som var sant en millisekund tidigare.
    if merged.get("autonomy") == "auto_send":
        produkt = await storage.get_latest_context_doc(
            tenant["tenant_id"], kind="product_marketing"
        )
        beslut = kan_aktivera_auto_send(
            icp_ar_ifyllt=not icp_ar_tomt(normalize_icp(merged.get("icp"))),
            business_context_ar_ifyllt=business_context_ar_ifyllt(
                (produkt or {}).get("content")
            ),
            avsandardoman=merged.get("sender_domain") or tenant.get("sender_domain"),
        )
        if not beslut.tillaten:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Automatiskt utskick går inte att aktivera än. "
                    + " ".join(beslut.hinder)
                ),
            )

    saved = await storage.set_agent_settings(
        tenant["tenant_id"], agent_type="leads", settings=merged
    )
    autonomy = normalize_autonomy(saved.get("autonomy"))
    return {
        "autonomy": autonomy,
        "autonomy_description": describe_autonomy(autonomy),
        "icp": normalize_icp(saved.get("icp")),
    }


@router.get("/api/leads/queue")
async def list_review_queue(
    request: Request, tenant: dict = Depends(require_tenant), limit: int = 100
) -> dict:
    """Utkast som väntar på granskning. Tom lista är ett giltigt svar och
    betyder att agenten inte har något att visa — inte att något är fel."""
    items = await request.app.state.storage.list_review_queue(
        tenant["tenant_id"], limit=min(limit, 200)
    )
    return {"items": items}


@router.post("/api/leads/queue/{item_id}/approve")
async def approve_queue_item(
    request: Request, item_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Släpper ett granskat utkast till schemaläggaren.

    Går via status 'queued', inte direkt till utskick: schemaläggaren kör
    språk- och tidsgrindarna en gång till vid faktisk utskickstid, och den
    kontrollen ska inte gå att hoppa över genom att godkänna."""
    await request.app.state.storage.update_send_queue_status(
        tenant["tenant_id"],
        item_id,
        status="queued",
        gate_checks={"approved_by": "human", "via": "granskningskön"},
    )
    return {"id": item_id, "status": "queued"}


@router.post("/api/leads/queue/{item_id}/reject")
async def reject_queue_item(
    request: Request, item_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Avbryter ett utkast. 'cancelled' fanns i check-villkoret sedan 010 men
    hade ingen kodväg som någonsin skrev det."""
    await request.app.state.storage.update_send_queue_status(
        tenant["tenant_id"],
        item_id,
        status="cancelled",
        gate_checks={"rejected_by": "human", "via": "granskningskön"},
    )
    return {"id": item_id, "status": "cancelled"}


@router.patch("/api/leads/prospects/{prospect_id}")
async def patch_prospect(
    request: Request,
    prospect_id: str,
    payload: ProspectPatchRequest,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Exponerar storage.update_prospect, som funnits men varit onåbar över
    HTTP. Granskningskön behöver kunna skriva tillbaka en bedömning."""
    fields = payload.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=422, detail="Inga fält att uppdatera.")

    updated = await request.app.state.storage.update_prospect(
        tenant["tenant_id"], prospect_id, **fields
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")
    return {"prospect": updated}


@router.post("/api/leads/runs/batch", status_code=202)
async def start_batch_run(
    request: Request, payload: LeadsBatchRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Startar en körning över N prospekt.

    En jobbrad PER PROSPEKT, inte en för hela batchen: ett prospekt med en död
    skrapkälla ska inte fälla de andra nitton, och en enda jobbrad hade gjort
    "fyra av tjugo gick fel" omöjligt att se — batchen hade bara varit röd.
    """
    _require_live_llm()
    storage = request.app.state.storage

    prospects = await storage.list_prospects(tenant["tenant_id"], limit=payload.limit)
    if not prospects:
        raise HTTPException(
            status_code=422,
            detail="Inga prospekt att köra på. Lägg till prospekt först.",
        )

    # Överskrivningarna löses ut EN gång, inte per prospekt: alla jobb i
    # batchen ska köra mot samma målgrupp, annars går utfallet inte att jämföra.
    overrides = (
        payload.overrides.model_dump(exclude_none=True)
        if payload.overrides and payload.overrides.har_nagot()
        else None
    )

    jobs = []
    for prospect in prospects[: payload.limit]:
        job_id = await request.app.state.jobs.create(tenant_id=tenant["tenant_id"])
        asyncio.create_task(
            _run_batch_prospect(
                request.app.state,
                job_id,
                tenant,
                prospect_id=prospect["id"],
                scope=payload.scope,
                overrides=overrides,
                is_test=payload.is_test,
            )
        )
        jobs.append({"job_id": job_id, "prospect_id": prospect["id"]})

    return {
        "jobs": jobs,
        "scope": payload.scope,
        "count": len(jobs),
        # Ekas tillbaka så att den som startade körningen ser vad den FAKTISKT
        # kördes med — inte vad formuläret råkade innehålla.
        "overrides": overrides,
        "is_test": payload.is_test,
    }


async def _run_batch_prospect(
    app_state, job_id: str, tenant: dict, *, prospect_id: str, scope: str,
    overrides: dict | None = None,
    is_test: bool = False,
) -> None:
    from ..agent.leads_agent import run_research_step

    storage = app_state.storage
    try:
        # `overrides` togs emot av funktionen men skickades aldrig vidare, så
        # varje jobb i batchen kördes mot den SPARADE ICP:n oavsett vad
        # formuläret angav — och svaret ekade ändå tillbaka överskrivningarna
        # som om de gällt. Ett tyst fel: utfallet såg rimligt ut, det svarade
        # bara på fel fråga.
        context_pack, missing = await build_context_pack(
            storage, tenant["tenant_id"], overrides=overrides
        )
        result = await run_research_step(
            storage,
            tenant["tenant_id"],
            prospect_id=prospect_id,
            tenant_name=tenant["tenant_name"],
            context_pack=context_pack,
            brief="",
            is_test=is_test,
        )
        result["onboarding_missing"] = list(missing)
        result["prospect_id"] = prospect_id

        if scope == "research_and_draft":
            # Utkastet skrivs i samma jobb men KÖAS enligt autonominivån —
            # batchen ger aldrig agenten mer befogenhet än den enskilda
            # körningen gör.
            result["draft_note"] = (
                "Utkast skrivs av /api/leads/outreach/draft när tråden finns. "
                "Batchen researchar; utkastet kräver ett thread_id."
            )

        await app_state.jobs.complete(job_id, result)
    except Exception as error:  # noqa: BLE001 — ett trasigt prospekt fäller inte batchen
        await app_state.jobs.fail(job_id, f"Prospekt {prospect_id}: {error}")
