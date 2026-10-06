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
import weakref
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import CATEGORY_LABELS, DEFAULT_TENANT_ID, get_settings
from ..jobs.stadare import (
    UPPGIVET_JOBB,
    UPPGIVET_LISTA,
    avregistrera_aktiv,
    faila_jobb_om_oppet,
    registrera_aktiv,
    stada_tenant,
)
from ..kvotfel import ar_kreditslut, kundtext_for, larma_kreditslut
from ..leads import existens, sidhamtning, upptagna
from ..leads.webbsignal import mat_webbplats
from ..leads.autonomy import LEVELS as AUTONOMY_LEVELS
from ..leads.autonomy import describe as describe_autonomy
from ..leads.autonomy import kan_aktivera_auto_send
from ..leads.autonomy import normalize as normalize_autonomy
from ..leads.befordran import saknade_falt
from ..leads.rollkoppling import med_rollflagga
from ..leads import automation, crm_synk, eskalering
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
from ..agentcore.insyn import samla_anrop
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
from ..leads.signatur import bygg_signaturtext
from ..leads.signatur import normalisera as normalisera_signatur
from ..leads.sni import SNI_NAMN, beskriv_kod
from ..leads.onboarding_state import REQUIRED_KINDS, get_onboarding_state
from ..leads import korning as iris_korning
from ..leads.profil import las_kundtext, sakerstall_profil, slå_ihop, som_icp
from .deps import kraev_uuid, require_tenant
from ..agent.leads_research_v2 import las_produkter
from ..agentcore.baka_in import baka_in
from ..leads import onskemal
from ..leads.profil import validera_segment
from ..leads.soul import SOUL_KIND, SOUL_MAX_CHARS
from .schemas import (
    AgentFeedbackRequest,
    BefordraRequest,
    ContextDocRequest,
    ExempelbolagRequest,
    LeadsBatchRequest,
    LeadsConfigRequest,
    KombineraListorRequest,
    LeadsListaRequest,
    TillIrisRequest,
    LeadsRunOverrides,
    ProspectPatchRequest,
    OnboardingChatRequest,
    OutreachDraftRequest,
    ProcessaOmRequest,
    ProspectRequest,
    ProspectSourceRequest,
    ProspektsvarRequest,
    ResearchStepRequest,
    OnskemalRequest,
    SoulRequest,
)

router = APIRouter()
logger = logging.getLogger("snajp-support.leads")

_FEL_INGEN_MALGRUPP = (
    "Iris vet inte vad ni säljer än. Fyll i Affärskontext under Inställningar "
    "(vad ni säljer och till vem), eller fyll i bolag ni själva vill träffa."
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


async def _larma_vid_kreditslut(app_state, tenant_id: str, fel: Exception) -> None:
    """Kreditslut i ett bakgrundsjobb: larma oss (dygnsdeduplicerat).

    Kundtexten skrivs av felvägen själv (_jobbfeltext nedan); det här är den
    andra halvan av samma beslut: kunden ska aldrig vara den som upptäcker
    att krediterna är slut."""
    if ar_kreditslut(fel):
        await larma_kreditslut(app_state.storage, tenant_id=tenant_id, kalla="leads", fel=fel)


#: Jobbfel som kommer från AI-leverantören eller transporten men inte är
#: kvotklassen. Råtexten ("Error code: 403 - [{'error': ...}]") hör hemma i
#: loggen, inte i kundens jobbruta.
_FEL_INTERNT = (
    "Körningen kunde inte slutföras på grund av ett fel hos oss. Felet är "
    "loggat — kör om den, och hör av dig om det upprepas."
)
_FEL_UTKAST = (
    "ett fel hos oss stoppade det. Felet är loggat — kör Processa om för ett "
    "nytt försök."
)
_FEL_LISTBYGGE = (
    "Listan kunde inte byggas på grund av ett fel hos oss. Felet är loggat och "
    "inga halvfärdiga rader sparades — beställ listan igen."
)
_FEL_INGEN_MALGRUPP_LISTA = (
    "Listan behöver något att söka efter. Ange en titel eller roll, en bransch "
    "eller en region — eller spara en målgrupp i leadsinställningarna — och "
    "beställ igen."
)

#: Moduler vars undantag bär leverantörens eller transportens råtext.
_LEVERANTORSMODULER = ("openai", "httpx", "httpcore", "google", "agents")


def _ar_leverantorsfel(fel: BaseException) -> bool:
    led: BaseException | None = fel
    for _ in range(5):
        if led is None:
            return False
        if getattr(led, "status_code", None) is not None:
            return True
        if type(led).__module__.split(".", 1)[0] in _LEVERANTORSMODULER:
            return True
        led = led.__cause__ or led.__context__
    return False


def _jobbfeltext(fel: BaseException, *, reserv: str = _FEL_INTERNT) -> str:
    """Den mening ett misslyckat leads-jobb bär ut till kunden.

    Kvotklassen får sin ärliga text (KUNDTEXT_KREDITSLUT utan "försök igen",
    eller KUNDTEXT_KVOT). Övriga leverantörsfel får en fast mening — aldrig
    råtexten. Våra EGNA domänfel (ValueError("Prospektet saknar …") och
    liknande) passerar som förut: de är skrivna för att läsas, och att gömma
    dem bakom en generisk mening vore att gömma diagnosen. Fram till
    2026-09-13 bar jobbet str(fel) för allt, och kreditslutet nådde kunden
    bara tack vare läsvägens översättning — som inte ser draft_note eller
    lead_lists.felorsak.
    """
    kundtext = kundtext_for(fel)
    if kundtext:
        return kundtext
    if _ar_leverantorsfel(fel):
        return reserv
    return str(fel) or reserv


async def _stada_lat(app_state, tenant_id: str) -> None:
    """Lat städning vid läsning (app/jobs/stadare.py). Får aldrig fälla läsningen."""
    try:
        await stada_tenant(app_state, tenant_id)
    except Exception:  # noqa: BLE001 — kunden ska se sina listor även om städningen hickar
        logger.exception("Lat städning misslyckades för %s", tenant_id)


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

    result = await run_onboarding_turn(
        request.app.state.storage,
        tenant["tenant_id"],
        message=payload.message,
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
    # Bara leads som uppfyller kraven visas (Antons krav 2026-10-06): ett
    # bortvalt bolag med motiveringen "uppfyller inte ..." är brus för kunden.
    # Raden står kvar i databasen så att nästa sökning utesluter bolaget.
    # `?bortvalda=1` listar i stället just de bortvalda (Sebbe 2026-10-06:
    # inget får SE UT som raderat — ett dolt bolag måste gå att hitta igen;
    # raderas görs bara med uttrycklig handling).
    if request.query_params.get("bortvalda") == "1":
        prospects = [p for p in prospects if p.get("niva") == "C" or p.get("qualified") is False]
    else:
        prospects = [p for p in prospects if p.get("niva") != "C" and p.get("qualified") is not False]
    # Senaste händelse (Leads Suite): EN läsning av statusloggen, grupperad
    # här, i stället för en fråga per prospekt.
    senast: dict[str, str] = {}
    for rad in await request.app.state.storage.list_status_logg(tenant["tenant_id"]):
        pid = str(rad["prospect_id"])
        if rad["created_at"] > senast.get(pid, ""):
            senast[pid] = rad["created_at"]
    # rollkoppling_oklar: underlag för intresseavvägningen, härlett vid
    # läsning — se app/leads/rollkoppling.py för varför den inte lagras.
    return {
        "prospects": [
            {
                **med_rollflagga(p),
                "senaste_handelse_at": senast.get(str(p["id"])) or p.get("created_at"),
            }
            for p in prospects
        ]
    }


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
    return {"prospect": med_rollflagga(prospect), "sources": sorted(urls)}


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


# -- Fas 8: kundens egna önskemål till sin agent ------------------------------


def _onskemal_agent(agent: str) -> str:
    if agent not in onskemal.AGENTER:
        raise HTTPException(status_code=404, detail="Agenten finns inte.")
    return agent


@router.get("/api/agent/onskemal/{agent}")
async def hamta_onskemal(agent: str, request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Kundens dokument som agenten läser det, plus historiken (nyast först)."""
    docs = await request.app.state.storage.list_context_docs(
        tenant["tenant_id"], kind=onskemal.kind(_onskemal_agent(agent))
    )
    return {
        "dokument": (docs[0]["content"] if docs else ""),
        "max_tecken": onskemal.MAX_TECKEN,
        "historik": [
            {"id": d["id"], "created_at": d.get("created_at"), "content": d.get("content") or "",
             "feedback": d.get("source") or ""}
            for d in docs[:20]
        ],
    }


async def _kraev_under_dygnstak(storage, tenant_id: str, agent: str) -> None:
    if await onskemal.sparade_idag(storage, tenant_id, agent) >= onskemal.MAX_PER_DYGN:
        raise HTTPException(
            status_code=429,
            detail=f"Högst {onskemal.MAX_PER_DYGN} ändringar per dygn och agent. Försök igen i morgon.",
        )


@router.post("/api/agent/onskemal/{agent}/forhandsgranska")
async def forhandsgranska_onskemal(
    agent: str, payload: OnskemalRequest, request: Request, tenant: dict = Depends(require_tenant)
) -> dict:
    """Bakar in feedbacken UTAN att spara och visar varje ändring med skäl."""
    storage = request.app.state.storage
    _onskemal_agent(agent)
    await _kraev_under_dygnstak(storage, tenant["tenant_id"], agent)
    doc = await storage.get_latest_context_doc(tenant["tenant_id"], kind=onskemal.kind(agent))
    bakning = await baka_in((doc or {}).get("content") or "", payload.feedback, tak=onskemal.MAX_TECKEN)
    return bakning.som_dict()


@router.put("/api/agent/onskemal/{agent}")
async def spara_onskemal(
    agent: str, payload: OnskemalRequest, request: Request, tenant: dict = Depends(require_tenant)
) -> dict:
    """Sparar en ny version. Kunden har sett förhandsgranskningen och skickar
    det godkända dokumentet; utan dokument bakas feedbacken in här."""
    storage = request.app.state.storage
    _onskemal_agent(agent)
    await _kraev_under_dygnstak(storage, tenant["tenant_id"], agent)
    dokument = payload.dokument
    if dokument is None:
        doc = await storage.get_latest_context_doc(tenant["tenant_id"], kind=onskemal.kind(agent))
        dokument = (await baka_in((doc or {}).get("content") or "", payload.feedback,
                                  tak=onskemal.MAX_TECKEN)).dokument
    rad = await storage.save_context_doc(
        tenant["tenant_id"], kind=onskemal.kind(agent), content=dokument.strip()[: onskemal.MAX_TECKEN],
        source=payload.feedback.strip()[:4000],
    )
    return {"id": rad["id"], "dokument": rad.get("content") or dokument}


@router.post("/api/agent/onskemal/{agent}/aterstall/{doc_id}")
async def aterstall_onskemal(
    agent: str, doc_id: str, request: Request, tenant: dict = Depends(require_tenant)
) -> dict:
    """En tidigare version blir aktiv igen, som en ny rad: historiken ska visa
    att en återställning skett."""
    storage = request.app.state.storage
    docs = await storage.list_context_docs(tenant["tenant_id"], kind=onskemal.kind(_onskemal_agent(agent)))
    gammal = next((d for d in docs if str(d["id"]) == doc_id), None)
    if gammal is None:
        raise HTTPException(status_code=404, detail="Versionen finns inte.")
    rad = await storage.save_context_doc(
        tenant["tenant_id"], kind=onskemal.kind(agent), content=gammal.get("content") or "",
        source=f"Återställd version från {gammal.get('created_at')}",
    )
    return {"id": rad["id"], "dokument": rad.get("content") or ""}


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
    registrera_aktiv(job_id)
    try:
        context_pack, missing = await build_context_pack(storage, payload["tenant_id"])
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
        await _larma_vid_kreditslut(app_state, payload["tenant_id"], fel)
        await app_state.jobs.fail(job_id, _jobbfeltext(fel))
        await storage.set_leads_job_status(
            payload["tenant_id"], job_id=job_id, status="failed", scope="draft"
        )
    finally:
        avregistrera_aktiv(job_id)


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
        "eskalering": eskalering.normalisera(settings.get("eskalering")),
        "automation": automation.normalisera(settings.get("automation")),
        "crm_synk": _crm_synk_val(settings),
        # Normaliserad — UI:t ska se samma värde som köningen använder.
        "signatur": normalisera_signatur(settings.get("signatur")),
        # Fas 8: kundens egna produkter och segment, som researchen läser dem.
        "produkter": las_produkter(settings),
        "segment": validera_segment(settings.get("segment")),
        "offentlig_sektor": bool(settings.get("offentlig_sektor")),
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
    if payload.eskalering is not None:
        # Fältvis sammanslagning: en växel skickar bara sitt eget fält.
        merged["eskalering"] = eskalering.normalisera(
            {
                **eskalering.normalisera(current.get("eskalering")),
                **payload.eskalering.model_dump(exclude_none=True),
            }
        )
    if payload.automation is not None:
        # Fältvis per typ, samma princip som eskaleringen.
        regler = automation.normalisera(current.get("automation"))
        andrat = payload.automation.model_dump(exclude_none=True, by_alias=True)
        for typ, falt in (andrat.get("per_typ") or {}).items():
            regler["per_typ"][typ].update(falt)
        if "jev_bortval" in andrat:
            regler["jev_bortval"] = andrat["jev_bortval"]
        merged["automation"] = automation.normalisera(regler)
    if payload.crm_synk is not None:
        val = payload.crm_synk.model_dump()
        if val["integration_id"]:
            kraev_uuid(val["integration_id"], "Integrationen")
            from ..integrationer import lagring as integrationer

            if not await integrationer.hamta(storage, tenant["tenant_id"], val["integration_id"]):
                raise HTTPException(status_code=422, detail="Integrationen finns inte.")
        merged["crm_synk"] = val
    if payload.signatur is not None:
        # Sparas som den skickades (minus None-fält); läsarna normaliserar.
        # `aktiv: false` är avstängningen — fältet nollas aldrig tyst av en
        # PUT från ett annat formulär, samma princip som autonomi/ICP.
        merged["signatur"] = payload.signatur.model_dump(exclude_none=True)
    # Produkter, målsegment och offentlig sektor (2026-10-06). Kundens
    # uttryckliga val: produktvalet i researchen läser `produkter`, och
    # profilkompilatorn läser `segment` och `offentlig_sektor` före sin egen
    # tolkning (leads/profil.kundval). En ändring här kompilerar om profilen
    # vid nästa körning, eftersom de ingår i profilens indatahash.
    if payload.produkter is not None:
        merged["produkter"] = [p.model_dump() for p in payload.produkter]
    if payload.segment is not None:
        merged["segment"] = [s.model_dump() for s in payload.segment]
    if payload.offentlig_sektor is not None:
        merged["offentlig_sektor"] = payload.offentlig_sektor

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
        "eskalering": eskalering.normalisera(saved.get("eskalering")),
        "automation": automation.normalisera(saved.get("automation")),
        "crm_synk": _crm_synk_val(saved),
        "signatur": normalisera_signatur(saved.get("signatur")),
    }


def _crm_synk_val(settings: dict) -> dict:
    val = settings.get("crm_synk") if isinstance(settings.get("crm_synk"), dict) else {}
    leverantor = val.get("leverantor")
    return {
        "leverantor": leverantor if leverantor in ("hubspot", "pipedrive") else None,
        "integration_id": val.get("integration_id") or None,
    }


@router.get("/api/leads/profil")
async def get_iris_profil(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Iris-profilen — hur Iris tolkat kundens affärskontext och filter.

    Kompileras om när indata ändrats (hashen i app/leads/profil.py), så
    kunden ser alltid tolkningen av det som faktiskt gäller i nästa körning.
    Utan LLM-nyckel blir profilen regelbaserad och säger det själv."""
    return {"profil": await sakerstall_profil(request.app.state.storage, tenant["tenant_id"])}


@router.post("/api/leads/profil/tolka-om")
async def tolka_om_iris_profil(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Tvingar en ny tolkning — samma indata kan ge en bättre tolkning när
    modellen eller prompten förbättrats."""
    await _kraev_leads_budget(request.app.state.storage, tenant["tenant_id"])
    return {"profil": await sakerstall_profil(request.app.state.storage, tenant["tenant_id"], tvinga=True)}


@router.get("/api/leads/jev/statistik")
async def get_jev_statistik(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Jevs triage och klassning mot kodens nivå — underlaget för att slå på
    läge "pa" (app/leads/jev.py). Läser bara redan sparade bedömningar."""
    from ..leads import jev

    rader = await request.app.state.storage.list_prospects(tenant["tenant_id"], limit=500)
    return jev.statistik(rader)


@router.get("/api/leads/korningar")
async def lista_korningar(
    request: Request, tenant: dict = Depends(require_tenant), limit: int = 20
) -> dict:
    """Kundens körningar ur liggaren (migration 080, INV-JOB-003): det som
    går att följa, lämna och återvända till. `korning` är motorns tillstånd
    (app/leads/korning.py) för Iris-körningar; listjobb (scope 'lista') har
    inget tillstånd men syns med status och felorsak. Nyast först."""
    rader = await request.app.state.storage.list_leads_korningar(
        tenant["tenant_id"], limit=max(1, min(limit, 100))
    )
    return {"korningar": [_utan_kandidater(r) for r in rader]}


def _utan_kandidater(rad: dict) -> dict:
    """Körningens kandidatpool (namn, roller, telefon från registret) är
    motorns arbetsminne, inte kundens vy: den lämnar aldrig API:t."""
    k = rad.get("korning")
    if isinstance(k, dict) and "kandidater" in k:
        return {**rad, "korning": {f: v for f, v in k.items() if f != "kandidater"}}
    return rad


@router.get("/api/leads/korningar/{job_id}")
async def hamta_korning(
    request: Request, job_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """EN körning. 404 när raden inte finns — inte ett tomt svar, så UI:t
    kan skilja "borta" från "inte startad än"."""
    rad = await request.app.state.storage.get_leads_korning(tenant["tenant_id"], job_id)
    if rad is None:
        raise HTTPException(status_code=404, detail="Körningen finns inte.")
    return _utan_kandidater(rad)


@router.get("/api/leads/queue")
async def list_review_queue(
    request: Request, tenant: dict = Depends(require_tenant), limit: int = 100
) -> dict:
    """Utkast som väntar på granskning. Tom lista är ett giltigt svar och
    betyder att agenten inte har något att visa — inte att något är fel.

    `signatur` följer med så att arbetsytan kan rendera signaturblocket med
    logotypen i utkastvyn — brödtexten bär bara textversionen (signatur.py),
    och utan logotyp-URL:en hade granskaren inte sett det mottagaren ser."""
    storage = request.app.state.storage
    items = await storage.list_review_queue(tenant["tenant_id"], limit=min(limit, 200))
    settings = await storage.get_agent_settings(tenant["tenant_id"], agent_type="leads")
    sig = normalisera_signatur(settings.get("signatur"))
    svar: dict = {"items": items}
    if sig:
        svar["signatur"] = {**sig, "text": bygg_signaturtext(sig)}
    return svar


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

    # Statusbyte härifrån är alltid en människas val (statusloggen, 086).
    if "status" in fields:
        fields["status_kalla"] = "manuell"
    updated = await request.app.state.storage.update_prospect(
        tenant["tenant_id"], prospect_id, **fields
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")
    if "status" in fields:
        asyncio.create_task(
            crm_synk.synka_prospekt(
                request.app.state.storage,
                tenant["tenant_id"],
                updated,
                handelse="status",
                text=fields["status"],
            )
        )
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


async def _korningens_profil(storage, tenant_id: str, overrides: dict | None) -> tuple[dict, dict]:
    """Iris-profilen och den effektiva ICP:n för EN körning.

    Profilen (app/leads/profil.py) är kundens instruktionsfil: onboarding +
    affärskontext + fritext, tolkad en gång. Filtrera-panelens värden läggs
    ovanpå för just den här körningen — det sparade rörs aldrig."""
    settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
    profil = await sakerstall_profil(storage, tenant_id)
    icp = normalize_icp(_med_overrides(settings.get("icp"), overrides) or {})
    korningens = {
        **slå_ihop(profil, icp),
        "version": profil.get("version"),
        # Läses av jev.triage: False = Jev bedömer men väljer aldrig bort.
        "jev_bortval": automation.normalisera(settings.get("automation"))["jev_bortval"],
    }
    return korningens, som_icp(korningens, icp)


async def _skapa_prospekt_ur_kandidat(storage, tenant_id: str, bolag: dict, origin: str) -> dict:
    if bolag.get("kalla") == "gemini":
        # En sökträff bär modellens PÅSTÅENDEN om kontakt, ort och storlek.
        # Provkörningen 2026-10-05: en gissad info@-adress på en påhittad
        # domän räknades som kontaktväg och gav ett utkast, och gissad ort och
        # storlek gav poäng 100. Researchen hämtar kontakten ur bolagets egna
        # sidor (leads_agent._uppgradera_kontakt) och orten ur källmaterialet.
        bolag = {
            k: v for k, v in bolag.items()
            if k not in ("contact_name", "contact_email", "contact_role", "contact_level",
                         "contact_form_url", "ort", "postnr", "anstallda")
        }
    prospect = await storage.create_prospect(
        tenant_id,
        company_name=bolag["company_name"],
        # `contact_name` glömdes tidigare helt här — hitta_bolag()
        # kunde hitta en namngiven person men prospektraden fick
        # ändå bara e-postadressen, aldrig namnet.
        contact_name=bolag.get("contact_name"),
        contact_email=bolag.get("contact_email"),
        origin=origin,
        profil={
            k: bolag[k]
            for k in (
                "orgnr",
                "website",
                "ort",
                "postnr",
                "anstallda",
                # Fallback-trappans nivå (migration 058) — se
                # app/leads/discovery.py:KONTAKTNIVAER.
                "contact_role",
                "contact_level",
                "contact_form_url",
                # Registerkällan (merinfo, migration 081).
                "contact_phone",
                "sni",
                "omsattning",
            )
            if bolag.get(k) is not None
        },
    )
    if bolag.get("jev_triage"):
        await storage.spara_bedomning(
            tenant_id, prospect["id"], bedomning={"jev": {"triage": bolag["jev_triage"]}}
        )
    if bolag.get("website"):
        await _registrera_webb(storage, tenant_id, prospect["id"], bolag["website"])
    # Registersidan (merinfo) är det enda källmaterialet för ett bolag utan
    # webbplats. Utan den här raden fick researchen inget att läsa och skrev
    # "ingen information kunde hittas" i lägesbeskrivningen (provkörningen på
    # Alunix 2026-10-04: fem av fem leads).
    if bolag.get("source_name") == "merinfo" and bolag.get("source_url"):
        try:
            await storage.create_prospect_source(
                tenant_id,
                prospect_id=prospect["id"],
                source_url=bolag["source_url"],
                source_type="business_register",
                lawful_basis=_LAGLIG_GRUND_LISTKALLA,
            )
        except Exception:  # noqa: BLE001 — proveniens får inte fälla körningen
            logger.exception("Kunde inte registrera registerkällan för %s", prospect["id"])
    return prospect


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
    # 'iris' (migration 086): skiljer Iris egna fynd från en CSV-import, så
    # automationsreglerna per typ träffar rätt (app/leads/automation.py).
    origin_fynd = "test" if payload.is_test else "iris"
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
        # Uppslaget är modellens svar. Bär sajten inte bolagets namn hör den
        # till någon annan, och researchen hade då läst fel bolags sidor.
        if webb and existens.styrk(
            {"company_name": bolagsnamn, "website": webb, "kalla": "gemini"}, await mat_webbplats(webb)
        ):
            logger.info("Uppslagen webbplats för %s gick inte att styrka och används inte.", bolagsnamn)
            webb = None
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
        # Profilen ersätter kravet på en ifylld målgrupp (Alunix 2026-09-29:
        # körningen vägrade starta utan stad). Den finns alltid efter
        # onboarding; kompileras vid behov.
        profil, sok_icp = await _korningens_profil(storage, tenant_id, overrides)
        try:
            # Prospekt, listrader och CRM-kunder (app/leads/upptagna.py): Iris
            # hämtar aldrig ett bolag som redan ligger i en lista.
            uteslut_namn = {p["company_name"] for p in skapade} | await upptagna.hamta(storage, tenant_id)
            async with samla_anrop(storage, tenant_id, is_test=bool(payload.is_test), input_text="bolagssökning"):
                fynd = await hitta_bolag(sok_icp, saknas, uteslut_namn=uteslut_namn, profil=profil)
        except DiscoveryError as fel:
            if not skapade:
                raise HTTPException(status_code=503, detail=_FEL_SOKNING) from fel
            fynd = []
        from ..leads.forfilter import forfiltrera

        for bolag in fynd:
            if forfiltrera(profil, bolag, exclude_domains=sok_icp.get("exclude_domains")):
                continue
            # Sista kontrollen före skrivningen, se _fyll_pa.
            if upptagna.upptagen(await upptagna.hamta(storage, tenant_id), bolag.get("company_name"), bolag.get("orgnr")):
                continue
            skapade.append(await _skapa_prospekt_ur_kandidat(storage, tenant_id, bolag, origin_fynd))

    if not skapade:
        raise HTTPException(status_code=422, detail=_FEL_INGA_TRAFFAR)
    return skapade


async def _validera_batch_kan_starta(storage, tenant: dict, payload: LeadsBatchRequest) -> None:
    """Snabba avvisningar — inget LLM. Det som tar tid hör hemma i jobbet.

    Sedan 2026-09-30 stoppar INTE en tom målgrupp (Alunix: "den ska inte
    kunna stoppas på det sättet"). Iris-profilen tolkas ur affärskontexten,
    så det enda som stoppar är att Iris inte vet vad kunden säljer alls."""
    namn = [n.strip() for n in payload.company_names if n and n.strip()]
    if namn:
        return
    if tenant["tenant_id"] == DEFAULT_TENANT_ID:
        befintliga = await storage.list_prospects(tenant["tenant_id"], limit=payload.limit * 2)
        if any(p.get("origin") == "example" for p in befintliga):
            return
    if await las_kundtext(storage, tenant["tenant_id"]):
        return
    settings = await storage.get_agent_settings(tenant["tenant_id"], agent_type="leads")
    overrides = (
        payload.overrides.model_dump(exclude_none=True)
        if payload.overrides and payload.overrides.har_nagot()
        else None
    )
    if not icp_ar_tomt(normalize_icp(_med_overrides(settings.get("icp"), overrides) or {})):
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
    batch_id: str | None = None,
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
                    "batch_id": batch_id,
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
                    batch_id=batch_id,
                )
            )
        jobs.append({"job_id": job_id, "prospect_id": prospect["id"]})
    return jobs


#: Ett lås per körning (Sebbes krav 2026-10-06: flera användare på samma
#: konto kör agenter samtidigt, och leads_workers > 1 låter två barn i SAMMA
#: körning rapportera parallellt). Motorns tillstånd uppdateras med
#: läs-ändra-skriv (_las_korning → mutera → _spara_korning), och utan låset
#: skriver den sist sparande över den andras rapport: `pagaende` når aldrig
#: noll och körningen står i 'processing' för evigt (INV-JOB-003-slutet).
#: Låsen är per PROCESS — workers är asyncio-tasks i samma process
#: (app/main.py) — och rensas aldrig per körning: ett Lock per körning under
#: processens livstid är några hundra byte, och en rensning som poppar ett
#: lås någon fortfarande väntar på hade släppt in två skrivare igen. Yttre
#: nyckeln är event-loopen (weakref: en död testloop städar sina lås själv) —
#: ett asyncio.Lock är bundet till sin loop, och i driften finns bara en.
#: Fler REPLIKER av api-processen kräver ett Redis-lås i stället — höj inte
#: replikantalet utan att bygga det.
_KORNINGSLAS: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, asyncio.Lock]]" = (
    weakref.WeakKeyDictionary()
)


def _korningslas(batch_id: str) -> asyncio.Lock:
    # setdefault är atomärt nog här: ingen await mellan uppslag och insättning.
    tabell = _KORNINGSLAS.setdefault(asyncio.get_running_loop(), {})
    return tabell.setdefault(batch_id, asyncio.Lock())


async def _spara_korning(app_state, tenant_id: str, batch_id: str, k: dict) -> None:
    """Liggaren får motorns tillstånd efter varje steg (migration 080,
    INV-JOB-003). Redis-posten är snabbvägen; den här raden är det kunden
    kan återvända till efter en omladdning, en timme eller en deploy.
    Batchraden står i 'processing' tills motorn säger `klar`."""
    await app_state.storage.set_leads_job_status(
        tenant_id,
        job_id=batch_id,
        status="completed" if k.get("klar") else "processing",
        scope="batch",
        korning=k,
        is_test=bool(k.get("is_test")),
    )


async def _las_korning(app_state, tenant_id: str, batch_id: str) -> tuple[dict, dict | None]:
    """Körningens tillstånd: Redis-posten först (snabbvägen), annars liggaren
    (INV-JOB-003). Efter en deploy eller TTL är Redis tom medan raden i
    Postgres står i 'processing' med tillståndet; utan den här reservvägen
    låg en sådan körning kvar där för evigt."""
    post = await app_state.jobs.get(batch_id) or {}
    resultat = dict(post.get("result") or {})
    k = resultat.get("korning")
    if not k:
        rad = await app_state.storage.get_leads_korning(tenant_id, batch_id)
        k = (rad or {}).get("korning")
        if k:
            resultat.update(korning=k, jobs=k.get("jobs") or [], count=len(k.get("jobs") or []))
    return resultat, k


async def _markera_korning_fallen(app_state, tenant_id: str, batch_id: str, fel: BaseException) -> None:
    """En motor som kastar lämnar annars raden i 'processing' utan felorsak:
    exakt det spårlösa slutet 080 finns för att ta bort. Kastar aldrig."""
    try:
        await app_state.storage.set_leads_job_status(
            tenant_id, job_id=batch_id, status="failed", scope="batch", error=_jobbfeltext(fel)
        )
    except Exception:  # noqa: BLE001
        logger.exception("Kunde inte skriva felorsaken för körning %s", batch_id)


async def _ateruppta_korning(app_state, payload: dict) -> bool:
    """Återtag av ett batchjobb vars liggarrad står i 'processing' med
    tillstånd (deploy eller krasch mitt i motorn): fortsätt där liggaren
    står i stället för att söka om från början med dubbel researchkostnad.
    False = inget att återuppta, kör vägen som vanligt."""
    tenant = {"tenant_id": payload["tenant_id"], "tenant_name": payload.get("tenant_name")}
    try:
        rad = await app_state.storage.get_leads_korning(tenant["tenant_id"], payload["job_id"])
    except Exception:  # noqa: BLE001 — en trasig liggarläsning får inte stoppa kön
        logger.exception("Kunde inte läsa körningen %s för återupptagning.", payload["job_id"])
        return False
    k = (rad or {}).get("korning")
    if not k or k.get("klar"):
        return False
    try:
        await _fyll_pa(app_state, tenant, payload["job_id"])
    except Exception as fel:  # noqa: BLE001
        logger.exception("Återupptagningen av körning %s föll", payload["job_id"])
        await _markera_korning_fallen(app_state, tenant["tenant_id"], payload["job_id"], fel)
    return True


async def _styrning(app_state, tenant_id: str, batch_id: str) -> str | None:
    """'paus' | 'avbruten' | None, ur liggaren (inte Redis-posten, som bär
    motorns egen kopia av tillståndet och kan vara äldre än kundens knapptryck)."""
    rad = await app_state.storage.get_leads_korning(tenant_id, batch_id)
    return ((rad or {}).get("korning") or {}).get("styrning")


_STYRNING = {"pausa": "paus", "aterupta": None, "avbryt": "avbruten"}
AVBRUTEN_KORNING = "Körningen avbröts innan researchen startade."


@router.post("/api/leads/korningar/{job_id}/{atgard}")
async def styr_korning(
    request: Request,
    job_id: str,
    atgard: Literal["pausa", "aterupta", "avbryt"],
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Pausar, återupptar eller avbryter en pågående Iris-körning.

    Paus: inga nya prospekt köas; de som redan forskas blir klara och räknas
    in. Avbryt: dessutom hoppar köade men ej startade prospekt över sin
    research (ingen kostnad), och körningen avslutas med slutorsak
    'avbruten' när det sista barnet rapporterat. 409 när körningen inte är
    en pågående Iris-körning (klar, föll, eller ett listjobb)."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    if await storage.get_leads_korning(tenant_id, job_id) is None:
        raise HTTPException(status_code=404, detail="Körningen finns inte.")
    if not await storage.set_korning_styrning(tenant_id, job_id, _STYRNING[atgard]):
        raise HTTPException(status_code=409, detail="Körningen pågår inte och kan inte styras.")
    if atgard != "pausa":
        # Väck motorn: återupptagningsvägen fyller på igen, eller avslutar
        # direkt när inget barn är kvar i flykten.
        post = {"kind": "batch", "job_id": job_id, "tenant_id": tenant_id,
                "tenant_name": tenant["tenant_name"]}
        leadsstrom = getattr(request.app.state, "leadsstrom", None)
        if leadsstrom is not None:
            await leadsstrom.enqueue(post)
        else:
            asyncio.create_task(_ateruppta_korning(request.app.state, post))
    return {"job_id": job_id, "styrning": _STYRNING[atgard]}


async def _fyll_pa(app_state, tenant: dict, batch_id: str) -> None:
    """Köar research tills körningen har N leverbara leads (INV-LEADS-N-001).

    Läser körningens tillstånd ur batchjobbets resultat, köar så många
    kandidater som behövs, kör en ny sökrunda i nästa geo-ring när poolen är
    tom, och avslutar ärligt när målet är nått eller det inte går längre.
    Se app/leads/korning.py.

    Hela påfyllningen håller körningens lås: en väckning som kommer medan en
    annan worker redan fyller på ska läsa det tillstånd den påfyllningen
    skrev, inte en kopia från före den — annars köas samma kandidat två
    gånger. Priset är att en barnrapport för samma körning väntar ut en
    pågående sökrunda; andra körningar har egna lås och går parallellt."""
    async with _korningslas(batch_id):
        await _fyll_pa_last(app_state, tenant, batch_id)


async def _fyll_pa_last(app_state, tenant: dict, batch_id: str) -> None:
    jobs = app_state.jobs
    storage = app_state.storage
    tenant_id = tenant["tenant_id"]
    resultat, k = await _las_korning(app_state, tenant_id, batch_id)
    if not k or k.get("klar"):
        return
    if k.get("kalla") == "lista":
        # Körning ur en lista (Flytta till Iris): kandidaterna är givna, ingen
        # sökrunda och ingen påfyllning. Klar när sista barnet rapporterat.
        if k["pagaende"] == 0:
            # Avbruten: barnen har hoppat över sin research själva (_run_batch_prospect).
            iris_korning.avsluta(
                k, "avbruten" if await _styrning(app_state, tenant_id, batch_id) == "avbruten" else "klar"
            )
            k["sammanfattning"] = iris_korning.sammanfatta(k)
        resultat.update(korning=k, jobs=k["jobs"], count=len(k["jobs"]))
        await jobs.complete(batch_id, resultat)
        await _spara_korning(app_state, tenant_id, batch_id, k)
        return
    profil, sok_icp = await _korningens_profil(storage, tenant_id, k.get("overrides"))
    orsak = None
    styr = None
    while k["levererade"] + k["pagaende"] < k["mal"]:
        # Läses varje varv, inte en gång: en sökrunda kan ta minuter och
        # kunden ska kunna stoppa mellan två köade prospekt.
        styr = await _styrning(app_state, tenant_id, batch_id)
        if styr:
            break
        if k["undersokta"] + k["pagaende"] >= k["tak"]:
            orsak = "tak"
            break
        if not k["kandidater"]:
            if k["rundor"] >= iris_korning.MAX_RUNDOR:
                # "Slut på kandidater" förutsätter att sidorna gick att hämta.
                # Föll hämtningarna hos tjänsten (kredit, kvot, 429) och inget
                # levererades är det sökningen som föll — kunden ska se rött,
                # inte ett grönt "Klar" med noll leads (Sebbe 2026-10-06).
                tjanstefel = int((k.get("skrap") or {}).get("tjanstefel") or 0)
                orsak = "sokningen_foll" if tjanstefel and k["levererade"] == 0 else "slut_pa_kandidater"
                break
            if not iris_korning.har_malgrupp(profil, sok_icp):
                # Ingenting att sikta på: varken bransch, segment, kriterium
                # eller målgruppstext. En sådan sökning är "hitta vilket bolag
                # som helst", och det var den som gav påhittade bolag och en
                # slagsida mot bygg i provkörningen 2026-10-05.
                orsak = "ingen_malgrupp"
                break
            # Prospekt, listrader och CRM-kunder (app/leads/upptagna.py) plus
            # det körningen redan prövat.
            uteslut = await upptagna.hamta(storage, tenant_id) | {
                str(t.get("namn") or "") for t in k["tratt"]
            }
            # Kredittaket gäller hela körningen (plan 2026-10-05): varje runda
            # får det som återstår, och summan står i liggaren (Körningar).
            skrap = sidhamtning.starta(
                storage, tenant_id, tak=sidhamtning.STANDARD_TAK - sidhamtning.betalda(k.get("skrap"))
            )
            try:
                # Sökningen och Jev-triagen loggas som en egen post (Fas 7).
                async with samla_anrop(storage, tenant_id, is_test=bool(k.get("is_test")), input_text=f"sökrunda {k['rundor'] + 1}"):
                    await iris_korning.sokrunda(profil, sok_icp, k, uteslut=uteslut)
            except DiscoveryError:
                logger.warning("Sökrundan i körning %s misslyckades.", batch_id)
                if k["rundor"] >= iris_korning.MAX_RUNDOR:
                    orsak = "sokningen_foll"
                    break
            finally:
                k["skrap"] = sidhamtning.summera(k.get("skrap"), skrap)
            if skrap.slut and not k["kandidater"]:
                orsak = "kredittak"
                break
            continue
        try:
            await kontrollera_leads_budget(storage, tenant_id)
        except LeadsBudgetExceededError:
            orsak = "budget"
            break
        kandidat = k["kandidater"].pop(0)
        # Sista kontrollen mot listorna (Antons krav 2026-10-06): mängden
        # lästes när sökrundan började, och ett listbygge som körts sedan dess
        # kan ha tagit samma bolag. Läses om precis före skrivningen.
        if upptagna.upptagen(
            await upptagna.hamta(storage, tenant_id), kandidat.get("company_name"), kandidat.get("orgnr")
        ):
            k["tratt"].append({"namn": kandidat.get("company_name"), "steg": "dubblett",
                               "skal": "Finns redan: bolaget står redan i en lista eller som lead"})
            continue
        prospect = await _skapa_prospekt_ur_kandidat(
            storage, tenant_id, kandidat, "test" if k.get("is_test") else "iris"
        )
        barn = await _lagg_prospektjobb(
            app_state,
            tenant,
            [prospect],
            scope=k["scope"],
            overrides=k.get("overrides"),
            is_test=bool(k.get("is_test")),
            limit=1,
            batch_id=batch_id,
        )
        k["jobs"].extend({**b, "company_name": prospect.get("company_name")} for b in barn)
        k["pagaende"] += len(barn)
        # Spara INNAN nästa await: utan Redis startar jobbet som create_task
        # och kan rapportera tillbaka innan loopen är klar — då hade det läst
        # ett tillstånd utan sig själv.
        resultat.update(korning=k, jobs=k["jobs"], count=len(k["jobs"]))
        await jobs.complete(batch_id, resultat)
        await _spara_korning(app_state, tenant_id, batch_id, k)
    if k["pagaende"] == 0 and styr != "paus":
        if styr == "avbruten":
            iris_korning.avsluta(k, "avbruten")
        else:
            if not orsak and k["levererade"] < k["mal"]:
                # Samma sanningsregel som i loopen: tjänstefel utan leverans
                # är "sökningen föll", inte "slut på kandidater".
                tjanstefel = int((k.get("skrap") or {}).get("tjanstefel") or 0)
                orsak = "sokningen_foll" if tjanstefel and k["levererade"] == 0 else "slut_pa_kandidater"
            iris_korning.avsluta(k, "klar" if k["levererade"] >= k["mal"] else (orsak or "slut_pa_kandidater"))
        k["sammanfattning"] = iris_korning.sammanfatta(k)
        await _spara_listspar(storage, tenant_id, k)
    resultat.update(korning=k, jobs=k["jobs"], count=len(k["jobs"]))
    await jobs.complete(batch_id, resultat)
    await _spara_korning(app_state, tenant_id, batch_id, k)


async def _spara_listspar(storage, tenant_id: str, k: dict) -> None:
    """Bolagen som inte blev Iris-leads men hör hemma i en lista (plan
    2026-10-05): en färdig lista per körning, "Utan webbplats", så att kunden
    kan skapa utkast med ett mer generellt erbjudande senare. Körs en gång;
    kastar aldrig — listan får inte fälla en körning som redan levererat."""
    if k.get("listspar_lista"):
        return
    try:
        # Ett bolag som redan står i en lista (eller är kundens CRM-kund) ska
        # inte komma tillbaka i nästa körnings "Utan webbplats".
        sedda = await upptagna.hamta(storage, tenant_id)
        rader: list[dict] = []
        for rad in k.get("listspar") or []:
            if not upptagna.upptagen(sedda, rad.get("company_name"), rad.get("orgnr")):
                sedda.add(upptagna.nyckel(rad.get("company_name")))
                rader.append(rad)
        if not rader:
            return
        lista = await storage.create_lead_list(
            tenant_id,
            titel=f"Utan webbplats, Iris {datetime.now(timezone.utc):%Y-%m-%d}",
            icp={},
            antal=min(len(rader), 200),
            is_test=bool(k.get("is_test")),
        )
        for rad in rader:
            await storage.add_lead_list_item(tenant_id, list_id=lista["id"], **rad)
        await storage.set_lead_list_status(tenant_id, lista["id"], status="klar")
        k["listspar_lista"] = lista["id"]
    except Exception:  # noqa: BLE001
        logger.exception("Listspåret för körningen gick inte att spara.")


async def _rapportera_till_korning(
    app_state, tenant: dict, batch_id: str, *, job_id: str, namn: str, leverbar: bool,
    skal: str | None, skrap: dict | None = None, undersokt: bool = True, fyll: bool = True,
) -> None:
    """Ett prospektjobb är klart: räkna in det och fyll på. Kastar aldrig —
    en trasig motor får inte fälla ett researchjobb som redan är sparat.

    Idempotent per `job_id` (`korning.rapporterade`): ett barn som körts två
    gånger (återtag efter deploy) räknas en gång. `fyll=False` sparar bara
    utfallet; anroparen väcker motorn själv (_vacka_korning). Läs-ändra-skriv
    under körningens lås: med leads_workers > 1 rapporterar två barn annars
    över varandra och den enas utfall försvinner."""
    try:
        async with _korningslas(batch_id):
            resultat, k = await _las_korning(app_state, tenant["tenant_id"], batch_id)
            if not k:
                return
            rapporterade = k.setdefault("rapporterade", [])
            if job_id not in rapporterade:
                rapporterade.append(job_id)
                iris_korning.registrera_utfall(k, namn=namn, leverbar=leverbar, skal=skal, undersokt=undersokt)
                if skrap:
                    k["skrap"] = sidhamtning.summera(k.get("skrap"), skrap)
                resultat["korning"] = k
                await app_state.jobs.complete(batch_id, resultat)
                await _spara_korning(app_state, tenant["tenant_id"], batch_id, k)
    except Exception as fel:  # noqa: BLE001 — se docstringen
        logger.exception("Kunde inte rapportera till körning %s", batch_id)
        await _markera_korning_fallen(app_state, tenant["tenant_id"], batch_id, fel)
        return
    if fyll:
        await _vacka_korning(app_state, tenant, batch_id)


async def _vacka_korning(app_state, tenant: dict, batch_id: str) -> None:
    """Låt motorn fylla på (eller avsluta). Kastar aldrig."""
    try:
        await _fyll_pa(app_state, tenant, batch_id)
    except Exception as fel:  # noqa: BLE001
        logger.exception("Påfyllningen av körning %s föll", batch_id)
        await _markera_korning_fallen(app_state, tenant["tenant_id"], batch_id, fel)


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
    registrera_aktiv(job_id)
    try:
        req = _payload_till_request(payload)
        demo = tenant["tenant_id"] == DEFAULT_TENANT_ID
        if req.scope != "sok" and not req.company_names and not demo:
            # Iris-motorn: N = leverbara leads, inte kandidater.
            k = iris_korning.ny_korning(
                mal=req.limit, scope=req.scope, overrides=payload.get("overrides"), is_test=req.is_test
            )
            await app_state.jobs.complete(job_id, {"fase": "research", "jobs": [], "count": 0, "korning": k})
            # 'processing' med tillståndet, inte 'completed': sökjobbet är
            # klart men KÖRNINGEN har just börjat (migration 080). Raden
            # blir completed först när motorn säger `klar`.
            await _spara_korning(app_state, tenant["tenant_id"], job_id, k)
            await _fyll_pa(app_state, tenant, job_id)
            return
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
            tenant["tenant_id"], job_id=job_id, status="failed", scope="batch", error=_http_feltext(fel)
        )
    except DiscoveryError as fel:
        # En sökning som avvisades för att krediten är slut ska inte be kunden
        # "försöka igen" — samma klassning som resten av jobbvägarna. (Bär
        # DiscoveryError leverantörens svarstext, se app/leads/discovery.py.)
        await _larma_vid_kreditslut(app_state, tenant["tenant_id"], fel)
        feltext = kundtext_for(fel) or _FEL_SOKNING
        await app_state.jobs.fail(job_id, feltext)
        await app_state.storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="failed", scope="batch", error=feltext
        )
    except Exception as fel:  # noqa: BLE001 — jobbet ska bli failed, inte tyst dö
        logger.exception("Batchsökning misslyckades (%s)", job_id)
        await _larma_vid_kreditslut(app_state, tenant["tenant_id"], fel)
        # Felorsaken i liggaren (080): det var exakt den här raden som
        # saknades när Antons körning 2026-09-30 dog utan spår.
        await app_state.jobs.fail(job_id, _jobbfeltext(fel))
        await app_state.storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="failed", scope="batch", error=_jobbfeltext(fel)
        )
    finally:
        avregistrera_aktiv(job_id)


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
        tenant["tenant_id"], job_id=job_id, status="queued", scope="batch", is_test=payload.is_test
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


def _leverbarhet(rad: dict, result: dict, regler: dict) -> str | None:
    """None = leverbart, annars skälet (tratten). Antons krav 2026-10-01,
    kodat 2026-10-02 (plan del C): kvalificerat, över kundens tröskel, en
    kontaktperson MED roll, en kontaktväg (telefon eller arbetsmejl) och en
    lägesbeskrivning. Det är vad en körnings N räknar (INV-LEADS-N-001)."""
    from ..leads.discovery import ar_arbetsmejl

    if not result.get("qualified"):
        return (result.get("disqualifiers") or ["Uppfyllde inte kriterierna"])[0]
    if eskalering.under_troskel(regler, qualified=True, icp_fit=result.get("icp_fit")):
        return f"Under tröskeln: poäng {result.get('score_total')} av {regler['kvalificeringstroskel']} krävda"
    if not (rad.get("contact_name") and rad.get("contact_role")):
        return "Ingen kontaktperson med roll"
    mejl = rad.get("contact_email")
    if not (rad.get("contact_phone") or (mejl and ar_arbetsmejl(mejl, webb=rad.get("website")))):
        return "Ingen kontaktväg: varken telefon eller arbetsadress"
    if not str(result.get("lagesbeskrivning") or rad.get("lagesbeskrivning") or "").strip():
        return "Ingen lägesbeskrivning"
    return None


async def _run_batch_prospect(
    app_state, job_id: str, tenant: dict, *, prospect_id: str, scope: str,
    overrides: dict | None = None,
    is_test: bool = False,
    batch_id: str | None = None,
) -> None:
    run_research_step, run_outreach_draft = _valj_leads_kedja()
    utfall: dict = {"namn": "", "leverbar": False, "skal": "Researchen misslyckades."}

    storage = app_state.storage
    if batch_id and await _styrning(app_state, tenant["tenant_id"], batch_id) == "avbruten":
        await app_state.jobs.fail(job_id, AVBRUTEN_KORNING)
        await storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status="failed", scope=scope,
            prospect_id=prospect_id, error=AVBRUTEN_KORNING,
        )
        await _rapportera_till_korning(
            app_state, tenant, batch_id, job_id=job_id, namn="", leverbar=False, skal=None,
            undersokt=False,
        )
        return
    # Ordningen i finally (INV-JOB-003): körningen räknar in barnet FÖRST,
    # sedan blir barnets liggarrad completed/failed, sist fyller motorn på.
    # Dör processen mellan stegen tar återtaget vid: rapporten är idempotent
    # per job_id, och ett återtaget barn som redan står completed väcker bara
    # körningen (se hantera_leads_jobb).
    slutstatus: str | None = None
    await app_state.jobs.start(job_id)
    await storage.set_leads_job_status(
        tenant["tenant_id"], job_id=job_id, status="processing", scope=scope, prospect_id=prospect_id
    )
    registrera_aktiv(job_id)
    skrap = sidhamtning.starta(storage, tenant["tenant_id"], tak=sidhamtning.RESEARCH_TAK)
    try:
        # `overrides` togs emot av funktionen men skickades aldrig vidare, så
        # varje jobb i batchen kördes mot den SPARADE ICP:n oavsett vad
        # formuläret angav — och svaret ekade ändå tillbaka överskrivningarna
        # som om de gällt. Ett tyst fel: utfallet såg rimligt ut, det svarade
        # bara på fel fråga.
        context_pack, missing = await build_context_pack(
            storage, tenant["tenant_id"], overrides=overrides
        )
        # Samma sammanslagna målgrupp som kontextpaketet, till kodgrinden för
        # storlek och bemanning (leads/kvalificeringsgrind.py). Utan den mätte
        # grinden mot den sparade ICP:n medan modellen läste formulärets.
        installningar = await storage.get_agent_settings(tenant["tenant_id"], agent_type="leads")
        korningens_icp = normalize_icp(_med_overrides(installningar.get("icp"), overrides) or {})
        result = await run_research_step(
            storage,
            tenant["tenant_id"],
            prospect_id=prospect_id,
            tenant_name=tenant["tenant_name"],
            context_pack=context_pack,
            brief="",
            is_test=is_test,
            icp=korningens_icp,
        )
        result["onboarding_missing"] = list(missing)
        result["prospect_id"] = prospect_id

        # Leverbart (INV-LEADS-N-001, skärpt 2026-10-02): se _leverbarhet.
        _rad = await storage.get_prospect(tenant["tenant_id"], prospect_id) or {}
        _regler = eskalering.normalisera(installningar.get("eskalering"))
        utfall["namn"] = str(_rad.get("company_name") or "")
        _skal = _leverbarhet(_rad, result, _regler)
        if _skal:
            utfall["skal"] = _skal
            # Ett bolag som inte är leverbart är inget lead: nivå C döljer det
            # för kunden (list_prospects), oavsett om skälet är kriterierna,
            # tröskeln eller kontakten.
            await storage.spara_bedomning(
                tenant["tenant_id"], prospect_id,
                bedomning={"niva": "C", "qualified": False, "disqualifiers": [_skal]},
            )
        else:
            utfall.update(leverbar=True, skal=None)

        # Kundens eskaleringsregel (leads/eskalering.py). Här och inte i
        # researchstegen: då gäller den både V1 och V2, och ett utkast som
        # kunden själv begär för ett enskilt bolag stoppas inte — den som
        # klickar ÄR människan regeln lämnar över till.
        regler = eskalering.normalisera(installningar.get("eskalering"))
        if (
            scope == "research_and_draft"
            and not result.get("stopped_early")
            and eskalering.under_troskel(
                regler, qualified=bool(result.get("qualified")), icp_fit=result.get("icp_fit")
            )
        ):
            result["stopped_early"] = "under_troskel"

        if scope == "research_and_draft" and result.get("stopped_early"):
            # Grinden föll — bolaget kvalificerar inte, ligger under kundens
            # tröskel, eller saknar kontaktväg. Ett utkast är 4–7 LLM-anrop
            # till, för ett mejl som inte ska skickas automatiskt.
            if result["stopped_early"] == "inget_underlag":
                result["draft_note"] = (
                    "Hoppar över utkastet: bolagets sidor gick inte att hämta, så det finns "
                    "inget att bedöma eller skriva om."
                )
            elif result["stopped_early"] == "ej_kvalificerad":
                result["draft_note"] = "Hoppar över utkastet: bolaget uppfyller inte målgruppens kriterier."
            elif result["stopped_early"] == "under_troskel":
                result["draft_note"] = (
                    "Hoppar över utkastet: träffsäkerheten ligger under din tröskel på "
                    f"{regler['kvalificeringstroskel']} procent, så bolaget blir inget lead."
                )
            else:
                result["draft_note"] = (
                    "Hoppar över utkastet: ingen kontaktperson eller kontaktväg "
                    "hittades. Komplettera kontakten i registret och kör Processa om."
                )
        elif scope == "research_and_draft" and _skal:
            # Utkast skrivs bara för ett LEVERBART lead (_leverbarhet): en
            # namngiven kontaktperson med roll, en kontaktväg och en
            # lägesbeskrivning. Kontrollen räknade förut bara in körningens
            # utfall, och ett bolag som stod som "bortvalt: ingen
            # kontaktperson med roll" fick ändå status Redo och ett utkast
            # till en funktionsadress (provkörningen 2026-10-05).
            result["draft_note"] = f"Research klar. Inget utkast: {_skal[:1].lower()}{_skal[1:].rstrip('.')}."
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
            from ..leads.discovery import ar_arbetsmejl, vd_mottagare

            if email and not ar_arbetsmejl(email, webb=prospect.get("website")):
                email = None
            # Bara VD, och bara en adress som bär VD:ns namn (Antons regel 3,
            # discovery.vd_mottagare). En funktionsadress eller en annan roll
            # ger inget utkast; telefonen till VD står kvar på leadet.
            vd_epost = vd_mottagare(prospect) if email else None
            if email and not vd_epost:
                result["draft_note"] = (
                    "Research klar. Inget utkast: e-postadressen går inte att knyta till bolagets VD"
                    + (", ring VD i stället." if prospect.get("contact_phone") else ".")
                )
            elif email and not result.get("citat"):
                # Underlagsgolvet: utan ett enda ordagrant citat ur bolagets
                # egna sidor finns inget att öppna mejlet med, och utkastet blir
                # "Jag såg att ni ligger i Göteborg" (provkörningen 2026-10-05).
                result["draft_note"] = (
                    "Research klar. Inget utkast: för tunt underlag för ett personligt mejl. "
                    "Bolagets sidor sa för lite om verksamheten."
                )
            elif not email:
                # Kontaktformulär är inte en mottagare. Hoppa till nästa bolag.
                result["draft_note"] = (
                    "Research klar. Ingen arbetsadress hittades: leadet levereras "
                    "med telefon, ring kontaktpersonen."
                    if prospect.get("contact_phone")
                    else "Research klar. Hoppar över utkastet: inget arbetsmejl "
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
                            # Kallmejlets starkaste krok — vad som ändrats hos
                            # dem just nu. Saknades här (och i researchvyn) till
                            # 2026-09-04; se _utkastens_researchvy i
                            # leads_research_v2.py för mätningen som visade vad
                            # det kostade.
                            "trigger_events": result.get("trigger_events")
                            or ur_final.get("trigger_events"),
                            # Iris-profilen: VARFÖR bolaget valdes och vilken
                            # ingång kunden vill ha — plus mätta fakta om
                            # webbplatsen som utkastet får citera.
                            "motivering": result.get("motivering"),
                            "vinklar": result.get("vinklar"),
                            "uppfyllda_kriterier": result.get("uppfyllda_kriterier"),
                            "webbsignaler": result.get("webbsignaler"),
                            # Underlaget som gör mejlet personligt (2026-10-06).
                            "citat": (result.get("citat") or [])[:6],
                            "lagesbeskrivning": result.get("lagesbeskrivning"),
                            "mottagare": {
                                "namn": prospect.get("contact_name"),
                                "roll": prospect.get("contact_role"),
                            },
                            "vald_produkt": result.get("produkt"),
                        },
                        ensure_ascii=False,
                    )
                    # Den valda produkten i stället för hela produktbeskrivningen:
                    # Snajps utkast räknade upp alla tre agenterna och erbjöd ingen.
                    vald = result.get("produkt")
                    erbjudande = (
                        f"{vald['namn']}: {vald['nytta']}\n{result.get('offer_summary') or ''}".strip()
                        if vald
                        else offer[:2000]
                    )
                    draft = await run_outreach_draft(
                        storage,
                        tenant["tenant_id"],
                        thread_id=thread["id"],
                        prospect_email=vd_epost,
                        tenant_name=tenant["tenant_name"],
                        company_name=prospect.get("company_name") or "",
                        offer_summary=erbjudande,
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
                    # Researchen är sparad, så jobbet blir completed — men
                    # anteckningen bar tidigare f"...: {fel}", alltså
                    # leverantörens råa engelska JSON rakt in i kundens
                    # jobbruta, och ett kreditslut i utkaststeget larmade
                    # ingen. Nu: ärlig kvottext + larm, annars en fast mening.
                    logger.exception("Utkastet i leads-jobb %s kunde inte skrivas", job_id)
                    await _larma_vid_kreditslut(app_state, tenant["tenant_id"], fel)
                    result["draft_note"] = (
                        "Research klar, men utkastet kunde inte skrivas: "
                        + (kundtext_for(fel) or _FEL_UTKAST)
                    )

        await app_state.jobs.complete(job_id, result)
        slutstatus = "completed"
    except Exception as error:  # noqa: BLE001 — ett trasigt prospekt fäller inte batchen
        logger.exception("Leads-jobb %s (prospekt %s) misslyckades", job_id, prospect_id)
        await _larma_vid_kreditslut(app_state, tenant["tenant_id"], error)
        # Kvotklassens text står ensam: prospekt-id:t framför en mening om att
        # AI-kapaciteten är slut säger kunden ingenting, och kreditslutet
        # gäller alla prospekt lika.
        kundtext = kundtext_for(error)
        await app_state.jobs.fail(
            job_id, kundtext or f"Prospekt {prospect_id}: {_jobbfeltext(error)}"
        )
        slutstatus = "failed"
    finally:
        avregistrera_aktiv(job_id)
    # Här och inte i finally: avbröts tasken (deploy, SIGTERM) finns inget
    # utfall att rapportera. Förr rapporterades då "Researchen misslyckades"
    # och återtaget rapporterade en gång till, så `pagaende` räknades ned två
    # gånger för samma barn.
    if slutstatus is not None:
        if batch_id:
            await _rapportera_till_korning(
                app_state,
                tenant,
                batch_id,
                job_id=job_id,
                fyll=False,
                namn=utfall["namn"],
                leverbar=utfall["leverbar"],
                skal=utfall["skal"],
                skrap=skrap.som_dict(),
            )
        await storage.set_leads_job_status(
            tenant["tenant_id"], job_id=job_id, status=slutstatus, scope=scope, prospect_id=prospect_id
        )
        if batch_id:
            await _vacka_korning(app_state, tenant, batch_id)


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

    settings_rad = await storage.get_agent_settings(tenant["tenant_id"], agent_type="leads")
    overrides = (
        payload.overrides.model_dump(exclude_none=True)
        if payload.overrides and payload.overrides.har_nagot()
        else None
    )
    icp = normalize_icp(_med_overrides(settings_rad.get("icp"), overrides) or {})
    # Grinden står EFTER sammanslagningen: formulärets överskrivningar (t.ex.
    # must_have=[titeln]) räknas, inte bara den sparade ICP:n. Utan den
    # beställdes en lista på en tom målgrupp, discovery sökte på ingenting
    # och kunden fick en "fel"-lista minuter senare i stället för ett tydligt
    # nej direkt — och en budget-dragning för en körning som inte kunde lyckas.
    if not _har_sokbar_malgrupp(icp):
        raise HTTPException(status_code=422, detail=_FEL_INGEN_MALGRUPP_LISTA)
    await _kraev_leads_budget(storage, tenant["tenant_id"])

    lista = await storage.create_lead_list(
        tenant["tenant_id"],
        titel=payload.titel,
        icp=icp,
        antal=payload.antal,
        is_test=payload.is_test,
    )
    job_id = await request.app.state.jobs.create(tenant_id=tenant["tenant_id"], status="queued")
    await storage.set_leads_job_status(
        tenant["tenant_id"], job_id=job_id, status="queued", scope="lista", is_test=payload.is_test
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


#: Kolumner som följer med när en rad kopieras in i en kombinerad lista.
_LISTRADSFALT = (
    "item_typ", "company_name", "website", "ort", "contact_name", "contact_role",
    "contact_email", "contact_level", "contact_phone", "orgnr", "source_name",
    "source_url", "signal", "signal_detalj",
)


def _har_kontaktvag(rad: dict, filter: str) -> bool:
    tel, mejl = bool(rad.get("contact_phone")), bool(rad.get("contact_email"))
    return {"alla": True, "telefon": tel, "mejl": mejl, "bada": tel and mejl}[filter]


def _dedupnyckel(rad: dict) -> str:
    """orgnr när det finns (migration 081), annars bolagsnamnet casefold:
    samma bolag i två listor ska bli EN rad i den kombinerade."""
    orgnr = "".join(ch for ch in str(rad.get("orgnr") or "") if ch.isdigit())
    return f"orgnr:{orgnr}" if orgnr else f"namn:{str(rad.get('company_name') or '').casefold().strip()}"


_FEL_CRM_LISTA = "En CRM-kundlista är kundens befintliga kunder. Den prospekteras inte och kombineras inte."


def _kraev_ej_crm(lista: dict) -> None:
    """CRM-kundlistan (migration 098) finns för att UTESLUTA bolag, inte för
    att bearbeta dem: den lyfts aldrig till Iris eller in i en annan lista."""
    if lista.get("kalla") == "crm":
        raise HTTPException(status_code=409, detail=_FEL_CRM_LISTA)


@router.post("/api/leads/listor/kombinera", status_code=201)
async def kombinera_leadslistor(
    request: Request, payload: KombineraListorRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Bygger en skräddarsydd lista ur flera färdiga (migration 082). Ingen
    sökning, ingen LLM, ingen budgetdragning: bara kopiering med dedup och
    filter. Källistorna står orörda. 404 om någon källa saknas, 409 om någon
    inte är klar, 422 om filtret inte lämnar en enda rad."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    kallor: list[dict] = []
    for lid in payload.list_ids:
        kraev_uuid(lid, "listan")
        lista = await storage.get_lead_list(tenant_id, lid)
        if not lista:
            raise HTTPException(status_code=404, detail="En av källistorna finns inte.")
        if lista.get("status") != "klar":
            raise HTTPException(status_code=409, detail=f"Listan {lista['titel']!r} är inte klar än.")
        _kraev_ej_crm(lista)
        kallor.append(lista)

    rader: list[dict] = []
    sedda: set[str] = set()
    dubbletter = 0
    for kalla in kallor:
        for rad in await storage.list_lead_list_items(tenant_id, kalla["id"]):
            if not _har_kontaktvag(rad, payload.kontaktfilter):
                continue
            nyckel = _dedupnyckel(rad)
            if nyckel in sedda:
                dubbletter += 1
                continue
            sedda.add(nyckel)
            rader.append(rad)
    if not rader:
        raise HTTPException(status_code=422, detail="Inga rader matchade filtret i de valda listorna.")

    # ICP:n på den kombinerade listan är unionen av källornas, så vyn kan visa
    # branscher och orter utan att läsa källistorna.
    icp: dict = {}
    for kalla in kallor:
        for f, v in (kalla.get("icp") or {}).items():
            if isinstance(v, list):
                icp.setdefault(f, [])
                icp[f] += [x for x in v if x not in icp[f]]
            elif f not in icp:
                icp[f] = v
    ny = await storage.create_lead_list(
        tenant_id,
        titel=payload.titel,
        icp=icp,
        # ponytail: antal är check-begränsat 1–200; en kombinerad lista kan
        # bära fler rader än så, kolumnen säger då taket, item_count sanningen.
        antal=min(len(rader), 200),
        is_test=any(bool(k.get("is_test")) for k in kallor),
        kalla="kombinerad",
        kallistor=[k["id"] for k in kallor],
        kontaktfilter=payload.kontaktfilter,
    )
    nya: list[dict] = []
    for rad in rader:
        nya.append(
            await storage.add_lead_list_item(
                tenant_id, list_id=ny["id"], **{f: rad.get(f) for f in _LISTRADSFALT}
            )
        )
    await storage.set_lead_list_status(tenant_id, ny["id"], status="klar")
    ny["status"] = "klar"
    return {"list": ny, "items": nya, "dubbletter_bort": dubbletter}


@router.get("/api/leads/listor")
async def lista_leadslistor(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    # Lat städning FÖRE läsningen: en lista som hängt sedan en krasch ska
    # visas med sitt ärliga fel, inte som "byggs" med skräprader.
    await _stada_lat(request.app.state, tenant["tenant_id"])
    return {"lists": await request.app.state.storage.list_lead_lists(tenant["tenant_id"])}


@router.get("/api/leads/listor/{list_id}")
async def hamta_leadslista(
    request: Request, list_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(list_id, "listan")
    storage = request.app.state.storage
    await _stada_lat(request.app.state, tenant["tenant_id"])
    lista = await storage.get_lead_list(tenant["tenant_id"], list_id)
    if not lista:
        raise HTTPException(status_code=404, detail="Listan finns inte.")
    return {"list": lista, "items": await storage.list_lead_list_items(tenant["tenant_id"], list_id)}


#: Art. 14-grunden för en listträff som blir prospekt: raden kom ur publika
#: källor (platsannons, nyhet, bolagets egen sajt) och bär källänken vidare.
_LAGLIG_GRUND_LISTKALLA = (
    "Berättigat intresse för B2B-prospektering; uppgiften hämtad ur en "
    "publik källa (GDPR art. 6.1 f), källänk bevarad."
)

#: source_name (discovery-federationens ursprung) → prospect_sources
#: check-villkor (migration 010). Okänt ursprung faller till 'other' —
#: aldrig till en mer specifik typ än belägget bär.
_LISTKALLA_TILL_SOURCE_TYPE = {
    "merinfo": "business_register",
    "jobtech": "job_signal",
    "nyheter": "public_news",
    "rss": "public_news",
}


@router.post("/api/leads/listor/{list_id}/items/{item_id}/prospekt")
async def listrad_till_prospekt(
    request: Request,
    list_id: str,
    item_id: str,
    tenant: dict = Depends(require_tenant),
) -> dict:
    """Lyfter EN listrad in i prospektregistret — vägen från leadslista till
    Email studio.

    Hela poängen är återbruk: ett prospekt har redan utkastkedjan
    (`POST /leads/outreach/draft`), granskningskön, godkännandet och
    sändvägen. Listan behöver därför ingen egen mejlpipeline — bara den här
    bron. INV-SEC-004 består: list-JOBBET har fortfarande inget sändverktyg;
    det som kan mejlas är prospektet, efter människans godkännande, precis
    som alla andra prospekt.

    LLM-fri med flit: befordran kostar ingenting och kan köras på hela
    listan. Utkastet (som kostar) skapas först när kunden öppnar bolaget.

    Dedupe mot registret på bolagsnamn (casefold) — samma jämförelse som
    batchens uteslutningsmängd i `_samla_korningens_prospekt`. En rad som
    redan finns återanvänds i stället för att dubbleras; svaret säger vilket
    via `skapad`, så knappen kan köras om utan att fråga.

    Origin följer listan: en testlistas rader blir `origin='test'` (skyddade
    av send-guardens spärr noll), en riktig listas blir `'import'` — samma
    värde som migration 039 reserverade för exakt den här klassen av inflöde.
    """
    kraev_uuid(list_id, "listan")
    kraev_uuid(item_id, "raden")
    tenant_id = tenant["tenant_id"]
    storage = request.app.state.storage

    lista = await storage.get_lead_list(tenant_id, list_id)
    if not lista:
        raise HTTPException(status_code=404, detail="Listan finns inte.")
    rad = next(
        (
            r
            for r in await storage.list_lead_list_items(tenant_id, list_id)
            if str(r.get("id")) == item_id
        ),
        None,
    )
    if rad is None:
        raise HTTPException(status_code=404, detail="Raden finns inte i listan.")
    _kraev_ej_crm(lista)

    prospect, skapad = await _befordra_listrad(storage, tenant_id, lista, rad)
    return {"prospect": prospect, "skapad": skapad}


def _listans_origin(lista: dict) -> str:
    """Härkomsten för en listas rader: 'test' skyddas av spärr noll, en
    CSV-import blir 'import', allt annat 'lista' (migration 086)."""
    if lista.get("is_test"):
        return "test"
    return "import" if lista.get("kalla") == "import" else "lista"


async def _befordra_listrad(storage, tenant_id: str, lista: dict, rad: dict) -> tuple[dict, bool]:
    """Listrad → prospekt (dedup på bolagsnamn casefold). Telefon och orgnr
    (migration 081) följer med via profil-allowlisten. Returnerar
    (prospekt, skapad). 422 om raden saknar bolagsnamn."""
    namn = (rad.get("company_name") or "").strip()
    if not namn:
        raise HTTPException(status_code=422, detail="Raden saknar bolagsnamn.")

    befintliga = await storage.list_prospects(tenant_id, limit=500)
    for p in befintliga:
        if str(p.get("company_name") or "").casefold() == namn.casefold():
            return p, False

    prospect = await storage.create_prospect(
        tenant_id,
        company_name=namn,
        contact_name=rad.get("contact_name"),
        contact_email=rad.get("contact_email"),
        origin=_listans_origin(lista),
        profil={
            k: rad[k]
            for k in ("website", "ort", "contact_role", "contact_level", "contact_phone", "orgnr")
            if rad.get(k) is not None
        },
    )

    website = rad.get("website")
    if website:
        await _registrera_webb(storage, tenant_id, prospect["id"], website)
    source_url = rad.get("source_url")
    if source_url:
        källnamn = str(rad.get("source_name") or "").casefold()
        source_type = next(
            (typ for nyckel, typ in _LISTKALLA_TILL_SOURCE_TYPE.items() if nyckel in källnamn),
            "other",
        )
        try:
            await storage.create_prospect_source(
                tenant_id,
                prospect_id=prospect["id"],
                source_url=source_url,
                source_type=source_type,
                lawful_basis=_LAGLIG_GRUND_LISTKALLA,
            )
        except Exception:  # noqa: BLE001 — proveniens får inte fälla befordran
            logger.exception("Kunde inte registrera listkälla för %s", prospect["id"])

    return prospect, True


@router.post("/api/leads/listor/{list_id}/till-iris", status_code=202)
async def listan_till_iris(
    request: Request, list_id: str, payload: TillIrisRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Flyttar listans rader (eller de valda) till Iris: prospekt skapas med
    telefon och orgnr, och en riktig körning köas med research per bolag —
    lägesbeskrivning, poäng och nivå — och utkast när scope säger det. Det
    ersätter "utkast till alla med mejladress", som skrev utkast ur radens
    metadata utan research (minnesregeln "Aldrig mall som utkast").

    Körningen bär `korning.kalla='lista'`: ingen sökrunda, ingen påfyllning,
    och den syns i Iris › Körningar som vilken körning som helst (INV-JOB-003).
    Känd gräns tills planens del C: `leverbar` kräver arbetsmejl, så en rad
    med bara telefon får research och bedömning men inget utkast — tratten
    i Körningar säger varför."""
    _require_live_llm()
    kraev_uuid(list_id, "listan")
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    lista = await storage.get_lead_list(tenant_id, list_id)
    if not lista:
        raise HTTPException(status_code=404, detail="Listan finns inte.")
    _kraev_ej_crm(lista)
    rader = await storage.list_lead_list_items(tenant_id, list_id)
    if payload.item_ids:
        valda = {str(x) for x in payload.item_ids}
        rader = [r for r in rader if str(r.get("id")) in valda]
    if not rader:
        raise HTTPException(status_code=422, detail="Inga rader att flytta.")
    await _kraev_leads_budget(storage, tenant_id)

    prospekt: list[dict] = []
    nya = 0
    sedda: set[str] = set()
    for rad in rader:
        try:
            p, skapad = await _befordra_listrad(storage, tenant_id, lista, rad)
        except HTTPException:
            continue  # rad utan bolagsnamn
        if p["id"] in sedda:
            continue
        sedda.add(p["id"])
        prospekt.append(p)
        nya += int(skapad)
    if not prospekt:
        raise HTTPException(status_code=422, detail="Ingen rad gick att flytta.")

    is_test = payload.is_test or bool(lista.get("is_test"))
    scope = payload.scope
    if scope is None:
        regler = automation.normalisera(
            (await storage.get_agent_settings(tenant_id, agent_type="leads")).get("automation")
        )
        typ = "import" if lista.get("kalla") == "import" else "lista"
        scope = "research_and_draft" if regler["per_typ"][typ]["utkast_auto"] else "research"
    app_state = request.app.state
    batch_id = await app_state.jobs.create(tenant_id=tenant_id, status="processing")
    k = iris_korning.ny_korning(mal=len(prospekt), scope=scope, overrides=None, is_test=is_test)
    k.update(kalla="lista", list_id=list_id, list_titel=lista.get("titel"))
    # Barnen är kända innan de köas: jobs och pagaende skrivs FÖRE kön, så
    # ett barn som rapporterar direkt (create_task-vägen) inte läser ett
    # tillstånd utan sig själv. job_id:t är kosmetiskt i vyn (React-nyckel).
    k["jobs"] = [
        {"job_id": f"prospekt:{p['id']}", "prospect_id": p["id"], "company_name": p.get("company_name")}
        for p in prospekt
    ]
    k["pagaende"] = len(prospekt)
    await app_state.jobs.complete(batch_id, {"korning": k, "jobs": k["jobs"], "count": len(k["jobs"]), "fase": "research"})
    await _spara_korning(app_state, tenant_id, batch_id, k)
    await _lagg_prospektjobb(
        app_state, tenant, prospekt,
        scope=scope, overrides=None, is_test=is_test, limit=len(prospekt), batch_id=batch_id,
    )
    return {"batch_id": batch_id, "prospekt": len(prospekt), "nya": nya, "scope": scope}


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

    registrera_aktiv(job_id, lista["id"])
    await storage.set_lead_list_status(tenant_id, lista["id"], status="byggs")
    sidhamtning.starta(storage, tenant_id)
    try:
        from ..leads.discovery import hamta_kontaktvag, sla_upp_webbplats

        icp = lista.get("icp") or {}
        from ..leads.sources import merinfo

        # Listorna är Iris kalla motsvarighet, inte en kopia (Sebbe
        # 2026-10-06): inget bolag som redan är ett Iris-prospekt, står i en
        # annan lista eller är kundens egen CRM-kund.
        uteslut = await upptagna.hamta(storage, tenant_id)
        traffar = None
        if merinfo.aktiv():
            # Registerkällan med kundens profil, så Jev kan rangordna mot
            # kundens målgrupp och kriterier. Profilen skickas inte till den
            # gamla kedjan: där ändrar den vilka källor som körs.
            try:
                from ..leads.profil import sakerstall_profil, slå_ihop

                profil = slå_ihop(await sakerstall_profil(storage, tenant_id), icp)
            except Exception:  # noqa: BLE001 — utan profil rangordnar koden ensam
                logger.warning("Profilen gick inte att läsa för listan %s.", lista["id"])
                profil = None
            # Pulsen flyttar 300-sekundersklockan (app/jobs/store.py) vid
            # varje hämtad sida: en lista på 40 listsidor + 90 bolagssidor
            # tar längre än så, och utan puls visade UI:t "Tidsgräns
            # överskriden" medan jobbet fortfarande byggde listan.
            async with samla_anrop(storage, tenant_id, input_text="listsökning (register)"):
                traffar = await merinfo.sok(
                    icp, int(lista["antal"]), uteslut=uteslut, profil=profil,
                    puls=lambda: app_state.jobs.start(job_id), lage="lista",
                )
        if traffar is None:
            async with samla_anrop(storage, tenant_id, input_text="listsökning"):
                traffar = await hitta_bolag(icp, int(lista["antal"]), uteslut_namn=uteslut)
        traffar = [t for t in traffar if not upptagna.upptagen(uteslut, t.get("company_name"), t.get("orgnr"))]
        rader: list[dict] = []
        geografi = (icp.get("geography") or [None])[0] if isinstance(icp.get("geography"), list) else icp.get("geography")
        for traff in traffar:
            # Kontaktskörden (LLM-fri, openleads ground-truth-mönster):
            # källträffar från annonser/nyheter bär sällan kontaktväg, men
            # ingressen lovar en per rad — hämta info@/kontakt@ ur bolagets
            # egen sajt med regex, aldrig gissad, aldrig privat. Första
            # skarpa listan (pixelgranskningen 2026-09-02) hade fem rader
            # med "—" i kontaktkolumnen; det är det här strecket som stängs.
            #
            # Saknas SAJTEN slås den upp först (grounded Gemini, EN fråga per
            # rad utan adress) — kundkravet är en kontaktväg per rad, och en
            # rad utan sajt hade annars aldrig ens nått regex-skörden. Bara
            # för rader utan adress: raderna som redan bär en kostar inget.
            # Registerraden (merinfo) bär redan namn, roll och telefon; ett
            # webbplatsuppslag per rad vore ett Gemini-anrop för en kontaktväg
            # som redan finns.
            if not traff.get("contact_email") and not traff.get("website") and not traff.get("contact_phone"):
                try:
                    webb = await sla_upp_webbplats(
                        traff.get("company_name") or "", geografi=geografi
                    )
                except Exception as fel:  # noqa: BLE001 — uppslag får inte fälla listan
                    # ...utom när AI-leverantören säger nej för hela kontot:
                    # då fäller varje återstående rad på samma sätt, och att
                    # svälja det ger en lista som ser klar ut men saknar det
                    # kunden betalade för. Fall fort, ärligt, med larm.
                    if kundtext_for(fel):
                        raise
                    webb = None
                if webb:
                    traff = {**traff, "website": webb}
            if not traff.get("contact_email") and traff.get("website"):
                kontakt = await hamta_kontaktvag(traff["website"])
                if kontakt["contact_email"]:
                    traff = {**traff, **kontakt}
            rader.append(traff)

        # Raderna skrivs FÖRST när hela bygget lyckats. Tidigare skrevs varje
        # rad direkt i loopen, och ett fel på rad fyra lämnade tre skräprader
        # under en lista som aldrig blev klar (testaren 2026-09-13). Nu når
        # ett fel i sökningen eller skörden aldrig tabellen, och städaren
        # (app/jobs/stadare.py) hittar inga rader att ta bort under ett
        # pågående bygge.
        #
        # Sista kontrollen mot Iris (Antons krav 2026-10-06): mängden lästes
        # före sökningen, och en Iris-körning under bygget kan ha tagit samma
        # bolag. Läses om här, och samma bolag två gånger i listan stryks.
        sista = await upptagna.hamta(storage, tenant_id)
        unika: list[dict] = []
        for traff in rader:
            if upptagna.upptagen(sista, traff.get("company_name"), traff.get("orgnr")):
                continue
            sista |= upptagna.bolagsnycklar([traff])
            unika.append(traff)
        rader = traffar = unika
        for traff in rader:
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
                contact_phone=traff.get("contact_phone"),
                orgnr=traff.get("orgnr"),
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
    except Exception as fel:  # noqa: BLE001 — listan ska bli 'fel', inte tyst dö
        if not isinstance(fel, DiscoveryError):
            logger.exception("Listbygget misslyckades (%s)", job_id)
        await _larma_vid_kreditslut(app_state, tenant_id, fel)
        # felorsak läses direkt ur lead_lists av listvyn — jobbläsvägens
        # översättning når den aldrig, så den skrivs kundfärdig här. Aldrig
        # str(fel): en Python-stack eller leverantörens JSON i listvyn är
        # varken ärligt eller begripligt.
        felorsak = kundtext_for(fel) or (
            _FEL_SOKNING if isinstance(fel, DiscoveryError) else _FEL_LISTBYGGE
        )
        # Rader från ett tidigare, avbrutet försök (före 2026-09-13 skrevs de
        # en och en) tas bort — en misslyckad lista visar ingen halv tabell.
        try:
            await storage.rensa_lead_list_items(tenant_id, lista["id"])
        except Exception:  # noqa: BLE001 — statusen ska skrivas även om rensningen hickar
            logger.exception("Kunde inte rensa raderna för den misslyckade listan %s", lista["id"])
        await storage.set_lead_list_status(tenant_id, lista["id"], status="fel", felorsak=felorsak)
        await app_state.jobs.fail(job_id, felorsak)
        await storage.set_leads_job_status(
            tenant_id, job_id=job_id, status="failed", scope="lista", error=felorsak
        )
    finally:
        avregistrera_aktiv(job_id, lista["id"])


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
            # Ett barn som hann bli completed men dog innan motorn fyllt på:
            # utan väckningen stod körningen still tills städaren fällde den.
            if payload.get("batch_id"):
                await _vacka_korning(
                    app_state,
                    {"tenant_id": tenant_id, "tenant_name": payload.get("tenant_name")},
                    payload["batch_id"],
                )
            return
        if liggarstatus == "processing" and payload.get("kind") == "batch":
            if await _ateruppta_korning(app_state, payload):
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
        batch_id=payload.get("batch_id"),
    )


#: nyttolastens `kind` -> liggarens scope (prospektjobb bär sitt eget `scope`).
_KIND_TILL_SCOPE = {"batch": "batch", "draft": "draft", "lista": "lista"}


async def ge_upp_leadsjobb(app_state, payload: dict) -> None:
    """Strömmen har gett upp en post (MAX_LEVERANSER, app/jobs/stream.py).

    Tidigare kvitterades posten tyst: Redis-jobbet, liggaren och listraden
    stod kvar i processing/byggs för evigt, och kunden såg en snurra som
    aldrig tog slut. En post som kraschat sin hanterare tre gånger ska i
    stället sluta ÄRLIGT — failed överallt, med en mening som säger vad som
    hänt, och en lista utan halvfärdiga rader.

    Kastar aldrig: anroparen kvitterar posten efteråt oavsett.
    """
    job_id = payload.get("job_id")
    tenant_id = payload.get("tenant_id")
    if not job_id or not tenant_id:
        return
    storage = app_state.storage
    try:
        if await storage.get_leads_job_status(tenant_id, job_id) == "completed":
            return
        await faila_jobb_om_oppet(app_state.jobs, job_id, UPPGIVET_JOBB)
        await storage.set_leads_job_status(
            tenant_id,
            job_id=job_id,
            status="failed",
            scope=payload.get("scope") or _KIND_TILL_SCOPE.get(payload.get("kind"), "research"),
            prospect_id=payload.get("prospect_id"),
            error=UPPGIVET_JOBB,
        )
        batch_id = payload.get("batch_id")
        if batch_id and payload.get("prospect_id"):
            # Barn i en Iris-körning: räknas in som bortvalt, annars går
            # `pagaende` aldrig till noll och körningen står i 'processing'
            # för evigt (INV-JOB-003).
            prospekt = await storage.get_prospect(tenant_id, payload["prospect_id"]) or {}
            await _rapportera_till_korning(
                app_state,
                {"tenant_id": tenant_id, "tenant_name": payload.get("tenant_name")},
                batch_id,
                job_id=job_id,
                namn=prospekt.get("company_name") or payload["prospect_id"],
                leverbar=False,
                skal="Researchen gavs upp efter upprepade försök.",
            )
        list_id = payload.get("list_id")
        if payload.get("kind") == "lista" and list_id:
            lista = await storage.get_lead_list(tenant_id, list_id)
            if lista and lista.get("status") != "klar":
                await storage.rensa_lead_list_items(tenant_id, list_id)
                await storage.set_lead_list_status(
                    tenant_id, list_id, status="fel", felorsak=UPPGIVET_LISTA
                )
        await storage.log_platform_event(
            level="error",
            source="leads",
            message=f"Leadsströmmen gav upp jobbet {job_id} efter upprepade leveranser",
            tenant_id=tenant_id,
            detail={"job_id": job_id, "kind": payload.get("kind"), "list_id": list_id},
        )
    except Exception:  # noqa: BLE001 — se docstringen
        logger.exception("Kunde inte markera det uppgivna leads-jobbet %s som misslyckat", job_id)
