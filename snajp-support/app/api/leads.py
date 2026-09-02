"""Leads-API: kontextdokument (Fas A), prospekt, research (Fas B),
outreach-utkast (Fas C), samt körningsloggen som gör hela research-processen
granskningsbar från dashboarden.

Onboarding är ALDRIG ett hårt hinder: /api/leads/onboarding/status visar vad
som saknas, och kontextpaketet byggs alltid (med explicita luckmarkeringar)
så att Fas B/C kan köra på det som finns i stället för att dödlåsa sig.
"""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import CATEGORY_LABELS, DEFAULT_TENANT_ID, get_settings
from ..leads.autonomy import LEVELS as AUTONOMY_LEVELS
from ..leads.autonomy import describe as describe_autonomy
from ..leads.autonomy import kan_aktivera_auto_send
from ..leads.autonomy import normalize as normalize_autonomy
from ..leads.befordran import saknade_falt
from ..leads.business_context import (
    MissingBusinessContextError,
    ar_ifyllt as business_context_ar_ifyllt,
)
from ..leads.budget import LeadsBudgetExceededError, kontrollera_leads_budget
from ..leads.exempelbolag import bygg_exempelbolag
from ..leads.context_pack import (
    _med_overrides,
    build_context_pack,
    materialize_product_marketing,
)
from ..leads.discovery import (
    DiscoveryError,
    LAGLIG_GRUND_EGEN_WEBB,
    hitta_bolag,
    sla_upp_webbplats,
    webbplats_ar_bolagets,
)
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
from ..leads.skatteverket import atkomst_for_tenant
from .schemas import (
    AgentFeedbackRequest,
    BefordraRequest,
    ContextDocRequest,
    ExempelbolagRequest,
    LeadsBatchRequest,
    LeadsConfigRequest,
    LeadsListaRequest,
    LeadsRunOverrides,
    ProspectPatchRequest,
    OnboardingChatRequest,
    OutreachDraftRequest,
    ProcessaOmRequest,
    ProspectRequest,
    ProspectSourceRequest,
    ProspektsvarRequest,
    ResearchStepRequest,
    SoulRequest,
)

router = APIRouter()
logger = logging.getLogger("snajp-support.leads")

_FEL_INGEN_MALGRUPP = (
    "Beskriv vilka bolag ni söker (bransch eller region) så agenten "
    "kan leta, eller fyll i bolag ni själva vill träffa."
)
_FEL_INGA_TRAFFAR = (
    "Inga bolag hittades som matchar målgruppen. Prova en bredare "
    "bransch eller region, eller fyll i bolag ni själva vill träffa."
)
_FEL_SOKNING = (
    "Kunde inte söka efter bolag just nu. Försök igen, eller fyll i Egna bolag."
)


def _har_sokbar_malgrupp(icp: dict) -> bool:
    return bool(
        icp.get("industries") or icp.get("geography") or icp.get("must_have") or icp.get("sni_codes")
    )


def _http_feltext(fel: HTTPException) -> str:
    detalj = fel.detail
    return detalj if isinstance(detalj, str) else _FEL_INGA_TRAFFAR


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


def _valj_leads_kedja():
    """(research_fn, draft_fn) enligt settings.leads_pipeline.

    V2 (1 research-anrop + 2 utkastanrop, app/agent/leads_research_v2.py)
    är opt-in via env LEADS_PIPELINE=v2 tills benchmarken godkänt den —
    se research_playbook.RESEARCH_V2 för hela resonemanget. Importerna är
    uppskjutna av samma skäl som övriga agentimporter i den här filen."""
    from ..agent.leads_agent import run_outreach_draft, run_research_step

    if get_settings().leads_pipeline == "v2":
        from ..agent.leads_research_v2 import run_outreach_draft_v2, run_research_step_v2

        return run_research_step_v2, run_outreach_draft_v2
    return run_research_step, run_outreach_draft


async def _kraev_leads_budget(storage, tenant_id: str) -> None:
    """Budgetgrinden (app/leads/budget.py) som HTTP-svar: 429 med det
    svenska beskedet när dygnstaket är nått. Anropas av varje endpoint som
    STARTAR nya LLM-jobb — batch, processa-om och direktutkastet — innan
    något köas. En slut budget är inte ett fel i koden (samma resonemang
    som chattens 429 i app/api/chat.py)."""
    try:
        await kontrollera_leads_budget(storage, tenant_id)
    except LeadsBudgetExceededError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error


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

    # Tokenen sätts av Next-proxyn ur en httpOnly-kaka. Saknas den har kunden
    # inte legitimerat sig med BankID, och uppslaget är inte tillgängligt.
    skatteverket = await atkomst_for_tenant(
        storage, tenant["tenant_id"], request.headers.get("X-Skatteverket-Token")
    )

    result = await run_onboarding_turn(
        request.app.state.storage,
        tenant["tenant_id"],
        message=payload.message,
        skatteverket=skatteverket,
    )
    state = await get_onboarding_state(request.app.state.storage, tenant["tenant_id"])
    result["onboarding_missing"] = list(state.missing)
    return result


# -- Prospekt (ingången till hela pipelinen) ------------------------------


@router.post("/api/leads/prospects", status_code=201)
async def create_prospect(
    request: Request,
    payload: ProspectRequest,
    tenant: dict = Depends(require_tenant),
    # Query-parameter, inte ett fält i ProspectRequest: kroppen som skickas i
    # dag är EXAKT ProspectRequest-fälten (LeadsRunForm.tsx postar bara
    # {company_name}), och ett andra body-objekt i signaturen hade fått
    # FastAPI att kräva en nästlad kropp i stället — och tyst brutit varje
    # befintlig anropare.
    #
    # "Egna bolag" i en testkörning (LeadsRunForm.tsx, samma isTest-flagga som
    # skickas till /leads/runs/batch) skapar sina prospekt HÄR, samma väg som
    # en riktig kund. Utan flaggan landade de som origin='manual' — omöjliga
    # att skilja från kundens riktiga lista och oskyddade av send-guardens
    # spärr noll (migration 054). is_test=false (default) är oförändrat.
    is_test: bool = False,
) -> dict:
    prospect = await request.app.state.storage.create_prospect(
        tenant["tenant_id"],
        company_name=payload.company_name,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        origin="test" if is_test else "manual",
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

    Bara demotenanten (Nordlys Handel) får skapa dem. Kundprofiler och
    Snajp Admin ska köra på riktiga bolag — exempelvägen där visade
    färdigskrivna pitchar och såg ut som en körning.
    """
    if tenant["tenant_id"] != DEFAULT_TENANT_ID:
        raise HTTPException(
            status_code=403,
            detail="Exempelbolag finns bara i demon. Lägg till bolag ni vill träffa, eller starta en körning mot befintliga prospekt.",
        )
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
    # Exempelbolag syns bara hos demotenanten. Kvarlämnade rader från den
    # gamla default-checkboxen ska inte dyka upp som "fynd" hos en kund.
    if tenant["tenant_id"] != DEFAULT_TENANT_ID:
        prospects = [p for p in prospects if p.get("origin") != "example"]
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


@router.get("/api/leads/prospects/{prospect_id}/utkast")
async def senaste_utkast(
    request: Request, prospect_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Senaste mejlutkastet för ETT prospekt (Fas 5.5).

    Bolagssidan renderar Email-studion inline och ska kunna återfinna ett
    redan skapat utkast efter en omladdning. Kön (GET /api/leads/queue)
    duger inte som läsväg: den listar bara status='awaiting_review' och bär
    inget prospect_id — ett godkänt eller avvisat utkast försvann ur den och
    gick inte att hitta alls. Läsningen är strikt läsande:
    find_outreach_thread skapar ALDRIG en tråd (se storage/base.py).

    Kö-id:t (send_queue-raden, det POST /api/leads/queue/{id}/approve tar)
    är INTE meddelande-id:t — de är två tabeller länkade via thread_id.
    Svarets `queue_item_id` är därför uppslaget ur granskningskön när tråden
    har en post som väntar, annars None (redan godkänt/avvisat utkast går
    att LÄSA men inte godkänna igen — det är rätt, inte en lucka).
    """
    kraev_uuid(prospect_id, "Prospektet")
    storage = request.app.state.storage
    prospect = await storage.get_prospect(tenant["tenant_id"], prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")
    thread = await storage.find_outreach_thread(
        tenant["tenant_id"], prospect_id=prospect_id
    )
    if not thread:
        return {"utkast": None, "thread_id": None, "queue_item_id": None}
    messages = await storage.list_outreach_messages(tenant["tenant_id"], thread["id"])
    senaste = messages[-1] if messages else None
    ko_id = None
    if senaste:
        vantande = await storage.list_review_queue(tenant["tenant_id"], limit=200)
        ko_id = next(
            (item["id"] for item in vantande if item.get("thread_id") == thread["id"]),
            None,
        )
    return {"utkast": senaste, "thread_id": thread["id"], "queue_item_id": ko_id}


@router.post("/api/leads/prospects/{prospect_id}/befordra")
async def befordra_prospekt(
    request: Request, prospect_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Flyttar ett prospekt från testkörning/exempel till kundens riktiga lista.

    `origin='manual'` är precis det send-guarden (scheduler.py, spärr noll)
    kollar innan `provider.send()`: 'test' och 'example' blockeras, 'manual'
    och 'import' gör det inte. Befordran är alltså den enda vägen ett prospekt
    som skapades under en provkörning kan bli skickbart — och därför krävs det
    att bolaget faktiskt ÄR riktigt (Fas 3): ett exempelbolags Luhn-ogiltiga
    org.nr och `.example`-domän får inte glida igenom bara för att en människa
    klickade en knapp.

    Motsatt riktning: `degradera` nedan.
    """
    kraev_uuid(prospect_id, "Prospektet")
    storage = request.app.state.storage
    prospect = await storage.get_prospect(tenant["tenant_id"], prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")

    origin = prospect.get("origin") or "manual"
    if origin not in ("test", "example"):
        # Redan i kundens riktiga lista (eller en import) — inget att göra.
        # 200 och inte 409: knappen "Flytta över valda" ska kunna köras om över
        # en blandad markering utan att fråga vilka rader som redan gått igenom.
        return {"prospect": prospect, "andrad": False}

    # Ifyllnad i samma anrop: PATCH sedan validera. Tom kropp är tillåten —
    # befintliga tester POSTar utan JSON och ska fortsätta göra det.
    raw = await request.body()
    if raw:
        try:
            extra = BefordraRequest.model_validate_json(raw)
        except Exception as fel:  # noqa: BLE001 — 422 med svensk text, inte pydantic-rått
            raise HTTPException(
                status_code=422,
                detail="Ifyllnaden kunde inte läsas. Ange organisationsnummer, webbplats och e-post.",
            ) from fel
        fält = extra.model_dump(exclude_none=True)
        if fält:
            uppdaterad = await storage.update_prospect(
                tenant["tenant_id"], prospect_id, **fält
            )
            if uppdaterad:
                prospect = uppdaterad

    brister = saknade_falt(
        orgnr=prospect.get("orgnr"),
        website=prospect.get("website"),
        contact_email=prospect.get("contact_email"),
    )
    if brister:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Prospektet saknar det som krävs för att flyttas över.",
                "saknas": brister,
            },
        )

    updated = await storage.update_prospect(tenant["tenant_id"], prospect_id, origin="manual")
    return {"prospect": updated, "andrad": True}


@router.post("/api/leads/prospects/{prospect_id}/degradera")
async def degradera_prospekt(
    request: Request, prospect_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Flyttar ett prospekt från kundens riktiga lista till en egen provkörning.

    Motsatsen till `befordra` ovan, och lika viktig av samma skäl: send-guarden
    (scheduler.py, `_kor_send_guard`, "spärr noll") blockerar VARJE utskick där
    prospektets `origin` är 'test' eller 'example' — okontrollerat, innan något
    av de sex reglerna ens hinner köras (se scheduler.py rad ~69). Att sätta
    `origin='test'` här är alltså inte bara en etikett, det är knappen som gör
    prospektet OSKICKBART. Det är hela poängen med "Flytta till testytan" i
    Bolagsregistret: ett prospekt som hamnat fel — eller som en människa
    medvetet vill experimentera vidare på utan risk — ska aldrig kunna mejlas
    av misstag.

    Ingen ifyllnad krävs, till skillnad från `befordra`: att bli oskickbar har
    inga förutsättningar att uppfylla, bara att bli skickbar har det.
    """
    kraev_uuid(prospect_id, "Prospektet")
    storage = request.app.state.storage
    prospect = await storage.get_prospect(tenant["tenant_id"], prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")

    origin = prospect.get("origin") or "manual"
    if origin in ("test", "example"):
        # Redan oskickbar — inget att göra. 200 och inte 409, av samma skäl
        # som befordra ovan: knappen ska kunna köras om över en blandad
        # markering utan att fråga vilka rader som redan gått igenom.
        return {"prospect": prospect, "andrad": False}

    updated = await storage.update_prospect(tenant["tenant_id"], prospect_id, origin="test")
    return {"prospect": updated, "andrad": True}


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
    run_research_step, _ = _valj_leads_kedja()

    storage = request.app.state.storage
    if not await storage.get_prospect(tenant["tenant_id"], payload.prospect_id):
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")

    # Ingen overrides-parameter: ResearchStepRequest har bara prospect_id och
    # brief. Raden stod tidigare med `overrides=overrides` — en variabel som
    # aldrig bands i funktionen, alltså NameError och 500 på VARJE anrop med
    # skarp nyckel. Ingen test nådde routen, och simuleringsläget svarar 503
    # innan den raden, så sviten var grön.
    context_pack, missing = await build_context_pack(storage, tenant["tenant_id"])
    # Tokenen sätts av Next-proxyn ur en httpOnly-kaka. Saknas den har kunden
    # inte legitimerat sig med BankID, och uppslaget är inte tillgängligt.
    skatteverket = await atkomst_for_tenant(
        storage, tenant["tenant_id"], request.headers.get("X-Skatteverket-Token")
    )

    result = await run_research_step(
        storage,
        tenant["tenant_id"],
        prospect_id=payload.prospect_id,
        tenant_name=tenant["tenant_name"],
        context_pack=context_pack,
        brief=payload.brief,
        skatteverket=skatteverket,
    )
    result["onboarding_missing"] = list(missing)
    return result


@router.post("/api/leads/outreach/draft", status_code=202)
async def outreach_draft(
    request: Request, payload: OutreachDraftRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Köar utkastet. LLM-körningen får inte ligga i POST-svaret — Next-proxyn
    avbryter efter 9 s och UI:t visade 'Kunde inte skapa utkast (status 503)'.
    """
    _require_live_llm()
    storage = request.app.state.storage
    await _kraev_leads_budget(storage, tenant["tenant_id"])
    thread_id = await _los_trad(storage, tenant["tenant_id"], payload.thread_id, payload.prospect_id)
    job_id = await request.app.state.jobs.create(tenant_id=tenant["tenant_id"], status="queued")
    await storage.set_leads_job_status(
        tenant["tenant_id"], job_id=job_id, status="queued", scope="draft"
    )
    post = {
        "kind": "draft",
        "job_id": job_id,
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "thread_id": thread_id,
        "prospect_email": payload.prospect_email,
        "company_name": payload.company_name,
        "offer_summary": payload.offer_summary,
        "brief": payload.brief,
        "research_summary": payload.research_summary,
        "research_evidence": list(payload.research_evidence),
        "skatteverket_token": request.headers.get("X-Skatteverket-Token"),
    }
    leadsstrom = getattr(request.app.state, "leadsstrom", None)
    if leadsstrom is not None:
        await leadsstrom.enqueue(post)
    else:
        asyncio.create_task(_run_draft_job(request.app.state, post))
    return {"job_id": job_id, "status": "processing", "fase": "skriver"}


async def _run_draft_job(app_state, payload: dict) -> None:
    _, _run_outreach_draft = _valj_leads_kedja()

    job_id = payload["job_id"]
    storage = app_state.storage
    await app_state.jobs.start(job_id)
    await storage.set_leads_job_status(
        payload["tenant_id"], job_id=job_id, status="processing", scope="draft"
    )
    try:
        context_pack, missing = await build_context_pack(storage, payload["tenant_id"])
        skatteverket = await atkomst_for_tenant(
            storage, payload["tenant_id"], payload.get("skatteverket_token")
        )
        result = await _run_outreach_draft(
            storage,
            payload["tenant_id"],
            thread_id=payload["thread_id"],
            prospect_email=payload["prospect_email"],
            tenant_name=payload["tenant_name"],
            company_name=payload["company_name"],
            offer_summary=payload["offer_summary"],
            context_pack=context_pack,
            brief=payload["brief"],
            research_summary=payload.get("research_summary") or "",
            research_evidence=tuple(payload.get("research_evidence") or ()),
            skatteverket=skatteverket,
        )
        result["onboarding_missing"] = list(missing)
        await app_state.jobs.complete(job_id, result)
        await storage.set_leads_job_status(
            payload["tenant_id"], job_id=job_id, status="completed", scope="draft"
        )
    except HTTPException as fel:
        await app_state.jobs.fail(job_id, _http_feltext(fel))
        await storage.set_leads_job_status(
            payload["tenant_id"], job_id=job_id, status="failed", scope="draft"
        )
    except MissingBusinessContextError as fel:
        await app_state.jobs.fail(job_id, str(fel))
        await storage.set_leads_job_status(
            payload["tenant_id"], job_id=job_id, status="failed", scope="draft"
        )
    except Exception as fel:  # noqa: BLE001 — jobbet ska bli failed, inte tyst dö
        logger.exception("Utkastjobb misslyckades (%s)", job_id)
        await app_state.jobs.fail(job_id, str(fel))
        await storage.set_leads_job_status(
            payload["tenant_id"], job_id=job_id, status="failed", scope="draft"
        )


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


@router.post("/api/agent/forslag/{suggestion_id}/arende", status_code=201)
async def oppna_forslag_som_arende(
    request: Request, suggestion_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Öppnar förslaget som ett undersökningsärende, utan att skriva i KB.

    Testchatten ska kunna säga 'vi undersöker och återkommer' — inte
    'vi lade till det i kunskapsbasen'. Artikeln kan fortfarande sparas
    via /godkann om medarbetaren vill det.
    """
    kraev_uuid(suggestion_id, "suggestion_id")
    storage = request.app.state.storage
    forslag = next(
        (
            r
            for r in await storage.list_agent_suggestions(tenant["tenant_id"], limit=100)
            if str(r.get("id")) == suggestion_id
        ),
        None,
    )
    if forslag is None:
        raise HTTPException(status_code=404, detail="Förslaget finns inte.")
    innehall = forslag.get("content") or {}
    if isinstance(innehall, str):
        import json as _json

        innehall = _json.loads(innehall)
    titel = str(innehall.get("title") or forslag.get("title") or "Undersökning")
    brod = str(innehall.get("content") or "")
    kategori = str(innehall.get("category") or "ovrigt")
    kund = await storage.find_or_create_customer(
        tenant["tenant_id"],
        email="undersokning@test.snajp.se",
        phone=None,
        name="Intern undersökning",
    )
    ticket = await storage.create_ticket(
        tenant["tenant_id"],
        customer_id=kund["id"],
        subject=f"Undersökning: {titel[:180]}",
        category=kategori if kategori in CATEGORY_LABELS else "ovrigt",
        channel="web",
        priority="high",
        is_test=True,
    )
    await storage.save_message(
        tenant["tenant_id"],
        conversation_id=ticket["conversation_id"],
        direction="inbound",
        content=brod or titel,
    )
    await storage.update_ticket(
        tenant["tenant_id"],
        ticket["id"],
        status="open",
        escalation_reason="Väntar på underlag — öppnat från testchatten.",
    )
    return {"ticket": ticket, "suggestion": forslag}


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
    korningar = await storage.list_agent_runs(tenant["tenant_id"], limit=200)
    korning = next((r for r in korningar if str(r.get("id")) == payload.run_id), None)
    if korning is None:
        raise HTTPException(status_code=404, detail="Körningen finns inte.")
    if not korning.get("is_test"):
        raise HTTPException(
            status_code=403,
            detail="Feedback kan bara lämnas på testkörningar, inte på riktiga kundsamtal.",
        )
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


async def _registrera_webb(storage, tenant_id: str, prospect_id: str, website: str) -> None:
    if not webbplats_ar_bolagets(website):
        return
    try:
        await storage.create_prospect_source(
            tenant_id,
            prospect_id=prospect_id,
            source_url=website,
            source_type="company_website",
            lawful_basis=LAGLIG_GRUND_EGEN_WEBB,
        )
    except Exception:  # noqa: BLE001 — dublett eller grind får inte fälla körningen
        logger.exception("Kunde inte registrera källa för %s", prospect_id)


async def _samla_korningens_prospekt(
    storage,
    tenant: dict,
    payload: LeadsBatchRequest,
) -> list[dict]:
    """Prospekten DEN HÄR körningen ska researcha — inte registret i stort.

    Egna namn är opt-in. Resten hittas mot ICP:t. Gamla rader (E2E-fixturer,
    förra testet) blandas inte in.
    """
    tenant_id = tenant["tenant_id"]
    origin_namn = "test" if payload.is_test else "manual"
    origin_fynd = "test" if payload.is_test else "import"
    overrides = (
        payload.overrides.model_dump(exclude_none=True)
        if payload.overrides and payload.overrides.har_nagot()
        else None
    )
    settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
    icp = normalize_icp(_med_overrides(settings.get("icp"), overrides) or {})

    namn = [n.strip() for n in payload.company_names if n and n.strip()]
    skapade: list[dict] = []
    geo = (icp.get("geography") or [None])[0]

    for bolagsnamn in namn[: payload.limit]:
        prospect = await storage.create_prospect(
            tenant_id,
            company_name=bolagsnamn,
            origin=origin_namn,
        )
        webb = await sla_upp_webbplats(bolagsnamn, geografi=geo)
        if webb:
            uppdaterad = await storage.update_prospect(
                tenant_id, prospect["id"], website=webb
            )
            if uppdaterad:
                prospect = uppdaterad
            await _registrera_webb(storage, tenant_id, prospect["id"], webb)
        skapade.append(prospect)

    saknas = payload.limit - len(skapade)
    if saknas > 0 and tenant_id == DEFAULT_TENANT_ID:
        # /demo: exempelbolag som redan laddats. Inte en sökväg för riktiga konton.
        befintliga = await storage.list_prospects(tenant_id, limit=payload.limit * 2)
        exempel = [p for p in befintliga if p.get("origin") == "example"][:saknas]
        skapade.extend(exempel)
        saknas = payload.limit - len(skapade)

    if saknas > 0:
        har_malgrupp = _har_sokbar_malgrupp(icp)
        if not har_malgrupp and not skapade:
            raise HTTPException(status_code=422, detail=_FEL_INGEN_MALGRUPP)
        if har_malgrupp:
            try:
                fynd = await hitta_bolag(
                    icp,
                    saknas,
                    uteslut_namn={p["company_name"] for p in skapade},
                )
            except DiscoveryError as fel:
                if not skapade:
                    raise HTTPException(status_code=503, detail=_FEL_SOKNING) from fel
                fynd = []
            for bolag in fynd:
                prospect = await storage.create_prospect(
                    tenant_id,
                    company_name=bolag["company_name"],
                    # `contact_name` glömdes tidigare helt här — hitta_bolag()
                    # kunde hitta en namngiven person men prospektraden fick
                    # ändå bara e-postadressen, aldrig namnet. En del av
                    # varför "hittar nästan aldrig en kontaktperson" var sant
                    # även de gånger sökningen faktiskt fann en.
                    contact_name=bolag.get("contact_name"),
                    contact_email=bolag.get("contact_email"),
                    origin=origin_fynd,
                    profil={
                        k: bolag[k]
                        for k in (
                            "orgnr",
                            "website",
                            "ort",
                            "anstallda",
                            # Fallback-trappans nivå (migration 058) — se
                            # app/leads/discovery.py:KONTAKTNIVAER. Utan den
                            # kan varken UI:t eller utkastnoten nedan skilja
                            # en verifierad rollpost från en namngiven träff.
                            "contact_role",
                            "contact_level",
                            "contact_form_url",
                        )
                        if bolag.get(k) is not None
                    },
                )
                if bolag.get("website"):
                    await _registrera_webb(storage, tenant_id, prospect["id"], bolag["website"])
                skapade.append(prospect)

    if not skapade:
        raise HTTPException(status_code=422, detail=_FEL_INGA_TRAFFAR)
    return skapade


async def _validera_batch_kan_starta(storage, tenant: dict, payload: LeadsBatchRequest) -> None:
    """Snabba avvisningar — inget Gemini. Det som tar tid hör hemma i jobbet."""
    namn = [n.strip() for n in payload.company_names if n and n.strip()]
    if namn:
        return
    settings = await storage.get_agent_settings(tenant["tenant_id"], agent_type="leads")
    overrides = (
        payload.overrides.model_dump(exclude_none=True)
        if payload.overrides and payload.overrides.har_nagot()
        else None
    )
    icp = normalize_icp(_med_overrides(settings.get("icp"), overrides) or {})
    if _har_sokbar_malgrupp(icp):
        return
    if tenant["tenant_id"] == DEFAULT_TENANT_ID:
        befintliga = await storage.list_prospects(tenant["tenant_id"], limit=payload.limit * 2)
        if any(p.get("origin") == "example" for p in befintliga):
            return
    raise HTTPException(status_code=422, detail=_FEL_INGEN_MALGRUPP)


def _payload_till_request(payload: dict) -> LeadsBatchRequest:
    ov = payload.get("overrides")
    return LeadsBatchRequest(
        scope=payload.get("scope") or "research",
        limit=int(payload.get("limit") or 10),
        is_test=bool(payload.get("is_test")),
        company_names=list(payload.get("company_names") or []),
        overrides=LeadsRunOverrides(**ov) if ov else None,
    )


async def _lagg_prospektjobb(
    app_state,
    tenant: dict,
    prospects: list[dict],
    *,
    scope: str,
    overrides: dict | None,
    is_test: bool,
    limit: int,
) -> list[dict]:
    """En research-rad per prospekt. Sökningen är redan klar här.

    Jobben skapas som "queued", inte "processing": med leads_workers=1 står
    de sekventiellt i kö, och 300-sekundersklockan (app/jobs/store.py) ska
    inte börja ticka förrän arbetet faktiskt börjar (INV-JOB-002). Liggaren
    (leads_job_ledger) får sin queued-rad HÄR — den är vaktens sanning vid
    ett återtag, oavsett vad Redis-posten hunnit flippa till.
    """
    leadsstrom = getattr(app_state, "leadsstrom", None)
    jobs: list[dict] = []
    for prospect in prospects[:limit]:
        job_id = await app_state.jobs.create(tenant_id=tenant["tenant_id"], status="queued")
        await app_state.storage.set_leads_job_status(
            tenant["tenant_id"],
            job_id=job_id,
            status="queued",
            scope=scope,
            prospect_id=prospect["id"],
        )
        if leadsstrom is not None:
            await leadsstrom.enqueue(
                {
                    "job_id": job_id,
                    "tenant_id": tenant["tenant_id"],
                    "tenant_name": tenant["tenant_name"],
                    "prospect_id": prospect["id"],
                    "scope": scope,
                    "overrides": overrides,
                    "is_test": is_test,
                }
            )
        else:
            asyncio.create_task(
                _run_batch_prospect(
                    app_state,
                    job_id,
                    tenant,
                    prospect_id=prospect["id"],
                    scope=scope,
                    overrides=overrides,
                    is_test=is_test,
                )
            )
        jobs.append({"job_id": job_id, "prospect_id": prospect["id"]})
    return jobs


async def _run_batch(app_state, payload: dict) -> None:
    """Sök bolag + köa research. Körs som jobb, inte i POST-svaret.

    POST /leads/runs/batch hade Gemini+Google-sökningen i samma request som
    knappen väntar på. Next-proxyn avbryter efter 9 s (kallstarts-budget),
    Safari ser det som TypeError och visar 'Kunde inte nå servern'. Sökningen
    fortsatte på servern och skapade spökprospekt utan job_id i UI:t.
    """
    job_id = payload["job_id"]
    tenant = {"tenant_id": payload["tenant_id"], "tenant_name": payload["tenant_name"]}
    # Arbetet börjar HÄR: flytta 300-sekundersklockan från köandet till
    # starten, och skriv liggaren (INV-JOB-002) så ett återtag efter deploy
    # ser sanningen även när Redis-posten hunnit auto-failas eller TTL:at.
    await app_state.jobs.start(job_id)
    await app_state.storage.set_leads_job_status(
        tenant["tenant_id"], job_id=job_id, status="processing", scope="batch"
    )
    try:
        req = _payload_till_request(payload)
        prospects = await _samla_korningens_prospekt(app_state.storage, tenant, req)
        if req.scope == "sok":
            # Snabbsökningen stannar EFTER sökningen: bolagen är hittade och
            # sparade i registret, men inga researchjobb köas. Kundkravet
            # "kontaktperson vid funnet lead" avgör vad som listas — rader
            # utan någon kontaktväg räknas separat i stället för att visas
            # som färdiga leads.
            #
            # Kontaktväg = nivå ELLER konkret kontaktfält, samma breddning
            # som grinden i run_research_step och av samma skäl: rader som
            # inte kommer ur discovery (exempelbolag, egna namn) bär aldrig
            # contact_level ens när de har en fullt användbar e-postadress.
            # Uppmätt live 2026-09-02: demo-tenantens sok gav count=0 med
            # tre exempelbolag gömda i utan_kontakt.
            med_kontakt = [
                p
                for p in prospects
                if p.get("contact_level")
                or p.get("contact_email")
                or p.get("contact_name")
                or p.get("contact_form_url")
            ]
            await app_state.jobs.complete(
                job_id,
                {
                    "fase": "klar",
                    "prospects": [
                        {
                            "prospect_id": p["id"],
                            "company_name": p.get("company_name"),
                            "website": p.get("website"),
                            "ort": p.get("ort"),
                            "contact_name": p.get("contact_name"),
                            "contact_role": p.get("contact_role"),
                            "contact_email": p.get("contact_email"),
                            "contact_level": p.get("contact_level"),
                            "contact_form_url": p.get("contact_form_url"),
                        }
                        for p in med_kontakt
                    ],
                    "count": len(med_kontakt),
                    "utan_kontakt": len(prospects) - len(med_kontakt),
                },
            )
            await app_state.storage.set_leads_job_status(
                tenant["tenant_id"], job_id=job_id, status="completed", scope="batch"
            )
            return
        barn = await _lagg_prospektjobb(
            app_state,
            tenant,
            prospects,
            scope=req.scope,
            overrides=payload.get("overrides"),
            is_test=req.is_test,
            limit=req.limit,
        )
        await app_state.jobs.complete(
            job_id,
            {"fase": "research", "jobs": barn, "count": len(barn)},
        )
        await app_state.storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="completed", scope="batch"
        )
    except HTTPException as fel:
        await app_state.jobs.fail(job_id, _http_feltext(fel))
        await app_state.storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="failed", scope="batch"
        )
    except DiscoveryError:
        await app_state.jobs.fail(job_id, _FEL_SOKNING)
        await app_state.storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="failed", scope="batch"
        )
    except Exception as fel:  # noqa: BLE001 — jobbet ska bli failed, inte tyst dö
        logger.exception("Batchsökning misslyckades (%s)", job_id)
        await app_state.jobs.fail(job_id, str(fel))
        await app_state.storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="failed", scope="batch"
        )


@router.post("/api/leads/runs/batch", status_code=202)
async def start_batch_run(
    request: Request, payload: LeadsBatchRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Startar en körning: hitta bolag (om inga namn gavs), researcha, ev. utkast.

    Svaret kommer INNAN sökningen. `fase=soker` och ett jobb; när det är
    completed ligger research-jobben i `result.jobs`. En jobbrad PER PROSPEKT
    därefter, så ett dött prospekt inte fäller de andra.
    """
    _require_live_llm()
    await _kraev_leads_budget(request.app.state.storage, tenant["tenant_id"])
    await _validera_batch_kan_starta(request.app.state.storage, tenant, payload)

    overrides = (
        payload.overrides.model_dump(exclude_none=True)
        if payload.overrides and payload.overrides.har_nagot()
        else None
    )
    job_id = await request.app.state.jobs.create(
        tenant_id=tenant["tenant_id"], status="queued"
    )
    await request.app.state.storage.set_leads_job_status(
        tenant["tenant_id"], job_id=job_id, status="queued", scope="batch"
    )
    post = {
        "kind": "batch",
        "job_id": job_id,
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "scope": payload.scope,
        "overrides": overrides,
        "is_test": payload.is_test,
        "limit": payload.limit,
        "company_names": [n.strip() for n in payload.company_names if n and n.strip()],
    }
    leadsstrom = getattr(request.app.state, "leadsstrom", None)
    if leadsstrom is not None:
        await leadsstrom.enqueue(post)
    else:
        asyncio.create_task(_run_batch(request.app.state, post))
    return {
        "jobs": [{"job_id": job_id}],
        "scope": payload.scope,
        "count": 0,
        "overrides": overrides,
        "is_test": payload.is_test,
        "fase": "soker",
    }


async def _run_batch_prospect(
    app_state, job_id: str, tenant: dict, *, prospect_id: str, scope: str,
    overrides: dict | None = None,
    is_test: bool = False,
) -> None:
    run_research_step, run_outreach_draft = _valj_leads_kedja()

    storage = app_state.storage
    await app_state.jobs.start(job_id)
    await storage.set_leads_job_status(
        tenant["tenant_id"], job_id=job_id, status="processing", scope=scope, prospect_id=prospect_id
    )
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

        if scope == "research_and_draft" and result.get("stopped_early"):
            # Grinden i run_research_step föll — antingen kvalificerar bolaget
            # inte mot ICP:n, eller så finns ingen kontaktväg. Ett utkast är
            # 4–7 LLM-anrop till, för ett mejl som aldrig ska skickas.
            result["draft_note"] = (
                "Hoppar över utkastet: bolaget kvalificerar inte mot målgruppen."
                if result["stopped_early"] == "ej_kvalificerad"
                else "Hoppar över utkastet: ingen kontaktperson eller kontaktväg "
                "hittades. Komplettera kontakten i registret och kör Processa om."
            )
        elif scope == "research_and_draft":
            prospect = await storage.get_prospect(tenant["tenant_id"], prospect_id) or {}
            email = prospect.get("contact_email")
            # Kontaktnivån (fallback-trappan, app/leads/discovery.py) följer
            # med i svaret oavsett utfall — UI:t och draft_note nedan ska
            # kunna säga ÄRLIGT vad kontakten faktiskt bygger på, inte bara
            # om ett utkast blev av eller inte.
            result["contact_name"] = prospect.get("contact_name")
            result["contact_role"] = prospect.get("contact_role")
            result["contact_level"] = prospect.get("contact_level")
            result["contact_form_url"] = prospect.get("contact_form_url")
            from ..leads.discovery import ar_arbetsmejl

            if email and not ar_arbetsmejl(email, webb=prospect.get("website")):
                email = None
            if not email:
                # Kontaktformulär är inte en mottagare. Hoppa till nästa bolag.
                result["draft_note"] = (
                    "Research klar. Hoppar över utkastet: inget arbetsmejl "
                    "hittades på bolagets sajt. Går vidare till nästa bolag."
                )
            else:
                try:
                    from ..leads.business_context import require_business_context

                    offer = await require_business_context(storage, tenant["tenant_id"])
                    thread = await storage.ensure_outreach_thread(
                        tenant["tenant_id"], prospect_id=prospect_id
                    )
                    # V1:s returdict bär inte company_summary/likely_pains på
                    # toppnivå — bara inbakade i final_output-JSON:en. Raden
                    # nedan serialiserade därför {null, null, null} i ett
                    # halvår utan att någon såg det (utkastet blev bara lite
                    # sämre, aldrig trasigt). final_output är fallbacken; V2
                    # lägger fälten på toppnivå och träffar dem direkt.
                    try:
                        ur_final = json.loads(result.get("final_output") or "{}")
                    except (TypeError, ValueError):
                        ur_final = {}
                    sammanfattning = json.dumps(
                        {
                            "company_summary": result.get("company_summary")
                            or ur_final.get("company_summary"),
                            "qualified": result.get("qualified"),
                            "likely_pains": result.get("likely_pains")
                            or ur_final.get("likely_pains"),
                        },
                        ensure_ascii=False,
                    )
                    draft = await run_outreach_draft(
                        storage,
                        tenant["tenant_id"],
                        thread_id=thread["id"],
                        prospect_email=email,
                        tenant_name=tenant["tenant_name"],
                        company_name=prospect.get("company_name") or "",
                        offer_summary=offer[:2000],
                        context_pack=context_pack,
                        brief="",
                        research_summary=sammanfattning,
                        # Grundningsgrindens belägg (INV-GROUND-001). Skickades
                        # aldrig i batch-vägen — direktvägen gjorde det — så
                        # build_permitted_facts saknade researchcitaten här.
                        research_evidence=tuple(result.get("research_evidence") or ()),
                        is_test=is_test,
                    )
                    result["draft"] = {
                        "subject": draft.get("subject"),
                        "queued": True,
                    }
                except MissingBusinessContextError as fel:
                    result["draft_note"] = str(fel)
                except Exception as fel:  # noqa: BLE001 — researchen är klar, utkastet är bonus
                    result["draft_note"] = f"Research klar, utkastet kunde inte skrivas: {fel}"

        await app_state.jobs.complete(job_id, result)
        await storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="completed", scope=scope, prospect_id=prospect_id
        )
    except Exception as error:  # noqa: BLE001 — ett trasigt prospekt fäller inte batchen
        await app_state.jobs.fail(job_id, f"Prospekt {prospect_id}: {error}")
        await storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="failed", scope=scope, prospect_id=prospect_id
        )


@router.post("/api/leads/prospects/processa-om", status_code=202)
async def processa_om(
    request: Request, payload: ProcessaOmRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Kör om research (och ev. utkast) för valda, REDAN SPARADE prospekt.

    Skapar inga nya rader. Samma jobbkö som batch-research, så proxyns
    9-sekundersgräns inte träffar LLM-körningen.
    """
    _require_live_llm()
    storage = request.app.state.storage
    await _kraev_leads_budget(storage, tenant["tenant_id"])
    hittade: list[dict] = []
    for pid in payload.prospect_ids:
        rad = await storage.get_prospect(tenant["tenant_id"], pid)
        if rad:
            hittade.append(rad)
    if not hittade:
        raise HTTPException(status_code=404, detail="Inga av de valda prospekten finns.")
    jobs = await _lagg_prospektjobb(
        request.app.state,
        tenant,
        hittade,
        scope=payload.scope,
        overrides=None,
        is_test=payload.is_test,
        limit=len(hittade),
    )
    return {
        "jobs": jobs,
        "scope": payload.scope,
        "count": len(jobs),
        "fase": "research",
    }


# -- Leadslistor (tillägget 'leadlists', migration 060) ---------------------


@router.post("/api/leads/listor", status_code=202)
async def bestall_leadslista(
    request: Request, payload: LeadsListaRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Beställer en leadslista: volymkörning via discovery-federationen,
    ingen research-kedja, inga utkast, ingen sändning (INV-SEC-004 — jobbet
    har inget sändverktyg alls).

    Addon-grinden ('leadlists' på workspace-raden) ligger i Next-appen som
    för övriga tillägg; här grindar budgeten (samma som batch) och
    require_tenant. ICP:t fryses på listraden vid beställningen så
    resultatet alltid kan granskas mot det som faktiskt beställdes.
    """
    _require_live_llm()
    storage = request.app.state.storage
    await _kraev_leads_budget(storage, tenant["tenant_id"])

    settings_rad = await storage.get_agent_settings(tenant["tenant_id"], agent_type="leads")
    overrides = (
        payload.overrides.model_dump(exclude_none=True)
        if payload.overrides and payload.overrides.har_nagot()
        else None
    )
    icp = normalize_icp(_med_overrides(settings_rad.get("icp"), overrides) or {})

    lista = await storage.create_lead_list(
        tenant["tenant_id"],
        titel=payload.titel,
        icp=icp,
        antal=payload.antal,
        is_test=payload.is_test,
    )
    job_id = await request.app.state.jobs.create(tenant_id=tenant["tenant_id"], status="queued")
    await storage.set_leads_job_status(
        tenant["tenant_id"], job_id=job_id, status="queued", scope="lista"
    )
    post = {
        "kind": "lista",
        "job_id": job_id,
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "list_id": lista["id"],
        "is_test": payload.is_test,
    }
    leadsstrom = getattr(request.app.state, "leadsstrom", None)
    if leadsstrom is not None:
        await leadsstrom.enqueue(post)
    else:
        asyncio.create_task(_run_list_job(request.app.state, post))
    return {"list_id": lista["id"], "job_id": job_id, "status": "bestalld"}


@router.get("/api/leads/listor")
async def lista_leadslistor(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    return {"lists": await request.app.state.storage.list_lead_lists(tenant["tenant_id"])}


@router.get("/api/leads/listor/{list_id}")
async def hamta_leadslista(
    request: Request, list_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(list_id)
    storage = request.app.state.storage
    lista = await storage.get_lead_list(tenant["tenant_id"], list_id)
    if not lista:
        raise HTTPException(status_code=404, detail="Listan finns inte.")
    return {"list": lista, "items": await storage.list_lead_list_items(tenant["tenant_id"], list_id)}


async def _run_list_job(app_state, payload: dict) -> None:
    """Bygger EN leadslista: discovery-federationen (JobTech + nyhets-RSS
    först, max ett grounded Gemini-anrop som utfyllnad — se
    discovery.hitta_bolag) skriver granskningsbara rader till
    lead_list_items. Inga research-anrop per rad i MVP:n — kontaktvägen
    kommer ur samma fallback-trappa som discoveryn redan verifierar, och en
    per-rad-berikning (V2:s list-läge) är nästa iteration, inte den här.
    """
    job_id = payload["job_id"]
    tenant_id = payload["tenant_id"]
    storage = app_state.storage
    await app_state.jobs.start(job_id)
    await storage.set_leads_job_status(tenant_id, job_id=job_id, status="processing", scope="lista")

    lista = await storage.get_lead_list(tenant_id, payload["list_id"])
    if not lista:
        await app_state.jobs.fail(job_id, "Listan finns inte längre.")
        await storage.set_leads_job_status(tenant_id, job_id=job_id, status="failed", scope="lista")
        return
    if lista.get("status") == "klar":
        # Idempotens utöver liggarvakten: ett återtag av ett redan byggt
        # listjobb ska inte dubblera raderna.
        await app_state.jobs.complete(job_id, {"list_id": lista["id"], "status": "klar"})
        await storage.set_leads_job_status(tenant_id, job_id=job_id, status="completed", scope="lista")
        return

    await storage.set_lead_list_status(tenant_id, lista["id"], status="byggs")
    try:
        traffar = await hitta_bolag(lista.get("icp") or {}, int(lista["antal"]))
        for traff in traffar:
            await storage.add_lead_list_item(
                tenant_id,
                list_id=lista["id"],
                company_name=traff.get("company_name"),
                website=traff.get("website"),
                ort=traff.get("ort"),
                contact_name=traff.get("contact_name"),
                contact_role=traff.get("contact_role"),
                contact_email=traff.get("contact_email"),
                contact_level=traff.get("contact_level"),
                source_name=traff.get("source_name") or "gemini_sok",
                source_url=traff.get("source_url"),
                signal=traff.get("signal"),
                signal_detalj=traff.get("signal_detalj"),
            )
        await storage.set_lead_list_status(tenant_id, lista["id"], status="klar")
        await app_state.jobs.complete(
            job_id, {"list_id": lista["id"], "count": len(traffar), "status": "klar"}
        )
        await storage.set_leads_job_status(tenant_id, job_id=job_id, status="completed", scope="lista")
    except DiscoveryError:
        await storage.set_lead_list_status(tenant_id, lista["id"], status="fel", felorsak=_FEL_SOKNING)
        await app_state.jobs.fail(job_id, _FEL_SOKNING)
        await storage.set_leads_job_status(tenant_id, job_id=job_id, status="failed", scope="lista")
    except Exception as fel:  # noqa: BLE001 — listan ska bli 'fel', inte tyst dö
        logger.exception("Listbygget misslyckades (%s)", job_id)
        await storage.set_lead_list_status(tenant_id, lista["id"], status="fel", felorsak=str(fel))
        await app_state.jobs.fail(job_id, str(fel))
        await storage.set_leads_job_status(tenant_id, job_id=job_id, status="failed", scope="lista")


async def hantera_leads_jobb(app_state, payload: dict) -> None:
    """Kör ETT jobb ur leads-strömmen (Fas R4, bd snipe-2xj, `crm:jobb:leads`).

    Speglar app.api.chat.hantera_strom_jobb: det här är hanteraren som
    skickas till ChattStrom.worker_loop/atertag (app/jobs/stream.py), samma
    funktion oavsett om posten läses för första gången eller är en ÅTERTAGEN
    post efter att en tidigare process dött mitt i batchen.

    Jobbposten läses FÖRST. Dör processen i fönstret mellan
    app_state.jobs.complete() och XACK ligger posten kvar okvitterad fast
    resultatet redan är levererat — utan den här vakten hade ett återtag
    kört HELA research-steget en gång till (åtta LLM-anrop). Ett redan
    färdigt jobb kvitteras bara, precis som chattens vakt (se
    app/api/chat.py:hantera_strom_jobb för samma fönsterresonemang).

    Leads-jobbet har ingen aterta-motsvarighet — research skapar inget
    ärende (till skillnad från chatten), så det finns inget ticket_id/
    conversation_id att återanvända vid en omtagning. Missar vakten någon
    gång ändå (t.ex. en process som dör EFTER complete() men FÖRE XACK, det
    fönster vakten normalt stänger) kan en omkörning i värsta fall dubblera
    en agent_runs-rad och några prospect_sources-rader för samma prospekt.
    Det är acceptabelt: slutläget på PROSPEKTRADEN är konvergent (samma
    ICP-bedömning skrivs över, den adderas inte, och research läser om
    samma källor snarare än att skapa nya), och alternativet — en halvkörd
    batch som tyst försvinner vid nästa deploy och lämnar tio-tjugo prospekt
    utan research — är sämre.
    """
    job_id = payload["job_id"]
    jobs = app_state.jobs

    # LIGGAREN FÖRST (INV-JOB-002, migration 059): Redis-posten auto-failar
    # efter 300 s och TTL:ar efter 3 600 s — för köade batchjobb såg vakten
    # nedan därför aldrig "completed" vid ett återtag efter deploy, och körde
    # om hela research+utkast-kedjan (uppmätt 2026-09-01: ~18 kr utan
    # användarhandling). Postgres-raden överlever bådadera och är sanningen;
    # Redis-vakten behålls som snabbväg för jobb från före migrationen.
    tenant_id = payload.get("tenant_id")
    if tenant_id:
        try:
            liggarstatus = await app_state.storage.get_leads_job_status(tenant_id, job_id)
        except Exception:  # noqa: BLE001 — en trasig liggarläsning får inte stoppa kön
            logger.exception("Kunde inte läsa leads_job_ledger för %s — kör på Redis-vakten.", job_id)
            liggarstatus = None
        if liggarstatus == "completed":
            return

    befintligt = await jobs.get(job_id) or {}
    if befintligt.get("status") == "completed":
        return

    if payload.get("kind") == "batch":
        await _run_batch(app_state, payload)
        return

    if payload.get("kind") == "draft":
        await _run_draft_job(app_state, payload)
        return

    if payload.get("kind") == "lista":
        await _run_list_job(app_state, payload)
        return

    # tenant byggs om ur de RÅA primitiverna i nyttolasten — exakt samma
    # nycklar som _run_batch_prospect faktiskt läser (tenant_id, tenant_name;
    # "master" används aldrig i den funktionen och skickas därför inte med).
    await _run_batch_prospect(
        app_state,
        job_id,
        {"tenant_id": payload["tenant_id"], "tenant_name": payload["tenant_name"]},
        prospect_id=payload["prospect_id"],
        scope=payload["scope"],
        overrides=payload.get("overrides"),
        is_test=bool(payload.get("is_test")),
    )
