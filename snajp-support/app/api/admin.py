"""Admin master control — läsning över alla kunder.

Varför en egen router: `require_tenant` avvisar master-nyckeln mot kunddata
med 403 (deps.py). Det är rätt designat — en administrativ nyckel ska inte
kunna smyga in som en kund — men det betyder att överblicken behöver en egen
väg. **Allt här ligger bakom `require_master_key`.**

Ingen endpoint här skriver. En admin-vy som kan ändra kunddata är en vy som
förr eller senare gör det av misstag.

Regeln gäller den här FILEN, inte adminytan som helhet. Agentprofilen —
instruktioner, ton, röstdokument, affärskontext — går att skriva från
`api/admin_profil.py`, bakom samma master-nyckel och med en rad i
platform_events per ändring. Den delningen är hela poängen: en fil vars namn
säger att den skriver, och en som inte gör det. Lägg aldrig en skrivning här.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from .deps import require_master_key

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])


@router.get("/tenants")
async def list_tenants(request: Request) -> dict:
    """Alla tenants med nyckeltal. Raden skickas vidare HEL: `active`,
    `products` (workspaces.products, None om ingen arbetsyta kunde läsas) och
    `test_runs` bär adminvyns paket- och hälsobedömning. Plocka inte ut fält
    här — en vy som inte får `test_runs` visar en testyta i full användning
    som tyst."""
    return {"tenants": await request.app.state.storage.list_tenants_with_stats()}


@router.get("/tenants/{tenant_id}/runs")
async def list_tenant_runs(request: Request, tenant_id: str, limit: int = 50) -> dict:
    runs = await request.app.state.storage.list_agent_runs_all(
        tenant_id=tenant_id, limit=min(limit, 200)
    )
    return {"runs": runs}


@router.get("/runs")
async def list_runs(
    request: Request,
    tenant_id: str | None = None,
    agent_type: str | None = None,
    limit: int = 50,
) -> dict:
    runs = await request.app.state.storage.list_agent_runs_all(
        tenant_id=tenant_id, agent_type=agent_type, limit=min(limit, 200)
    )
    return {"runs": runs}


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: str) -> dict:
    storage = request.app.state.storage
    run = await storage.get_agent_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Körningen finns inte.")
    # Spår av version 2 (Fas 7) bär systemlagren som hashar; texterna står en
    # gång per hash i prompt_lager. Spårvyn får dem bredvid körningen.
    logg = run.get("step_log") if isinstance(run.get("step_log"), list) else []
    hashar = sorted(
        {
            lager["hash"]
            for steg in logg
            if isinstance(steg, dict)
            for lager in steg.get("lager") or []
            if lager.get("position") == "system" and lager.get("hash")
        }
    )
    return {"run": {**run, "lagertexter": await storage.get_prompt_lager(hashar)}}


# -- Insyn (Fas 7): allt agenten läser, visat som flöde --------------------
#
# Läsning, som resten av filen. Visningen byggs ur samma funktioner som
# bygger prompten (app/agentcore/insyn.py) — aldrig ur en egen beskrivning.


@router.get("/tenants/{tenant_id}/insyn")
async def tenant_insyn(request: Request, tenant_id: str, agent: str = "leads", kanal: str = "chat") -> dict:
    from ..agentcore import insyn

    if agent not in ("leads", "support"):
        raise HTTPException(status_code=422, detail="agent måste vara leads eller support.")
    if not await request.app.state.storage.get_tenant(tenant_id):
        raise HTTPException(status_code=404, detail="Kunden finns inte.")
    return {"insyn": await insyn.oversikt(request.app.state.storage, tenant_id, agent, kanal=kanal)}


@router.get("/skills/fil")
async def skill_fil(skill: str, fil: str) -> dict:
    """Hela skillfilen och om den är orörd mot manifestet. Läser bara filer
    registret känner till (parse_skill_name + registrets läsväg), så en
    sökväg utanför agent-core/skills/ går inte att be om."""
    from ..agentcore import insyn
    from ..agentcore.registry import SkillRegistryError

    if ".." in fil or fil.startswith(("/", "\\")):
        raise HTTPException(status_code=422, detail="Ogiltig sökväg.")
    try:
        return {"fil": insyn.skillfil(skill, fil)}
    except SkillRegistryError as fel:
        raise HTTPException(status_code=404, detail=str(fel)) from fel


@router.post("/tenants/{tenant_id}/insyn/kb-prov")
async def kb_prov(request: Request, tenant_id: str, payload: dict) -> dict:
    """Vilka kunskapsartiklar en fråga hade hämtat. POST bara för att frågan
    kan vara lång och inte hör hemma i en url eller en åtkomstlogg; anropet
    skriver ingenting och gör inget språkmodellanrop. Därför här i
    läsroutern och inte i admin_profil.py, vars hela poäng är att den skriver."""
    from ..agentcore import insyn

    fraga = str((payload or {}).get("fraga") or "").strip()[:2000]
    if not fraga:
        raise HTTPException(status_code=422, detail="Skriv en fråga.")
    return {"prov": await insyn.kb_prov(request.app.state.storage, tenant_id, fraga)}


@router.get("/prospects/{prospect_id}/kedja")
async def prospect_kedja(request: Request, prospect_id: str, tenant_id: str) -> dict:
    """En körnings flöde för ett bolag: utfall per nod, in- och utdata,
    grindarnas utslag och var kedjan stannade. `tenant_id` krävs: prospekten
    läses alltid inom sin kund (RLS), även av admin."""
    from ..agentcore import insyn

    ut = await insyn.kedja(request.app.state.storage, tenant_id, prospect_id)
    if ut is None:
        raise HTTPException(status_code=404, detail="Bolaget finns inte hos kunden.")
    return {"kedja": ut}


@router.get("/events")
async def list_events(
    request: Request,
    level: str | None = None,
    tenant_id: str | None = None,
    limit: int = 100,
) -> dict:
    """Notiscentret. Fel över alla kunder, senast först."""
    events = await request.app.state.storage.list_platform_events(
        level=level, tenant_id=tenant_id, limit=min(limit, 500)
    )
    return {"events": events}


@router.get("/tenants/{tenant_id}/inbox")
async def tenant_inbox(request: Request, tenant_id: str, limit: int = 50) -> dict:
    return {
        "emails": await request.app.state.storage.list_emails(
            tenant_id, limit=min(limit, 200), is_test=None
        )
    }


@router.get("/tenants/{tenant_id}/leads-underlag")
async def tenant_leads_underlag(request: Request, tenant_id: str, limit: int = 200) -> dict:
    """Vad varje lead faktiskt vilar på: källor, hämtat material och bedömning.

    Svarar på frågan "finns bolaget?" för redan sparade leads (scripts/
    granska_leads_underlag.py). Bara bolagsuppgifter, aldrig kontaktpersoner:
    granskningen gäller bolaget, och svaret skrivs ut i en terminal.
    """
    storage = request.app.state.storage
    ut: list[dict] = []
    for p in await storage.list_prospects(tenant_id, limit=min(limit, 500)):
        webb = p.get("website")
        cache = await storage.get_sidcache(tenant_id, webb) if webb else None
        kallor = sorted(await storage.list_prospect_source_urls(tenant_id, str(p["id"])))
        ut.append(
            {
                "id": str(p["id"]),
                "company_name": p.get("company_name"),
                "website": webb,
                "origin": p.get("origin"),
                "status": p.get("status"),
                "niva": p.get("niva"),
                "score_total": p.get("score_total"),
                "kallor": kallor,
                "register": any("merinfo.se" in k for k in kallor),
                "hamtat_tecken": len((cache or {}).get("innehall") or ""),
                "hamtfel": (cache or {}).get("fel"),
                "created_at": p.get("created_at"),
                # Bara nyckel och utfall ("kp:träff"): räcker för att se vilka
                # regler ett lead bedömdes med, utan att motiveringen skrivs ut.
                "bedomning": [
                    f"{r.get('nyckel')}:{r.get('utfall')}"
                    for r in (p.get("score_breakdown") or [])
                    if isinstance(r, dict)
                ],
            }
        )
    return {"leads": ut}


@router.get("/tenants/{tenant_id}/drafts")
async def tenant_drafts(request: Request, tenant_id: str, limit: int = 50) -> dict:
    """Kundens utkast. Går via samma granskningskö som kunden själv ser —
    admin har ingen egen, andra sanning om vad som väntar."""
    return {
        "queue": await request.app.state.storage.list_review_queue(
            tenant_id, limit=min(limit, 200)
        )
    }


@router.get("/usage")
async def usage(request: Request) -> dict:
    """Förbrukning per kund. Samma siffror som /tenants, men utan
    ärendemängden — det här är fakturerings- och kostnadsvyn, och att blanda
    in aktivitetsmått där gör det oklart vad man tittar på."""
    tenants = await request.app.state.storage.list_tenants_with_stats()
    return {
        "usage": [
            {
                "tenant_id": t["id"],
                "slug": t.get("slug"),
                "name": t.get("name"),
                "runs": t.get("runs", 0),
                "tokens_in": t.get("tokens_in", 0),
                "tokens_out": t.get("tokens_out", 0),
                "last_activity": t.get("last_activity"),
            }
            for t in tenants
        ]
    }


@router.get("/sandvag")
async def sandvagsdiagnos(request: Request, vard: str = "", port: int = 0) -> dict:
    """Kan den här containern över huvud taget skicka mejl — och hur?

    Läser vilken provider som är vald OCH provar en TCP-anslutning ut mot
    SMTP-porten. Ingen inloggning, inget mejl, inga uppgifter behövs.

    ## Varför den finns

    Hostingplattformarna blockerar utgående SMTP på sina billiga planer, och
    felet syns först vid det första riktiga utskicket — som ett
    "Network is unreachable" långt inne i en agentkörning. Det har kostat oss
    en kväll två gånger: Render 2026-07-30 (commit 0d3ac1d) och Railway
    2026-08-27. Frågan "släpper plattformen igenom porten?" ska gå att ställa
    på en sekund, inifrån containern, innan någon felsöker ett lösenord som
    inte är fel.

    Att den ligger bakom master-nyckeln är avsiktligt: svaret avslöjar
    plattformens nätverkspolicy och vilken sändväg vi kör, vilket ingen kund
    har ett ärende till.
    """
    import asyncio

    from ..leads.send_provider import get_send_provider

    settings = get_settings()
    provider = get_send_provider()
    målvärd = (vard or settings.smtp_host or "smtp.gmail.com").strip()
    målport = port or settings.smtp_port or 587

    async def prova(p: int) -> dict:
        try:
            anslutning = asyncio.open_connection(målvärd, p)
            läsare, skrivare = await asyncio.wait_for(anslutning, timeout=8)
            hälsning = ""
            try:
                data = await asyncio.wait_for(läsare.read(120), timeout=5)
                hälsning = data.decode(errors="replace").strip()[:80]
            except Exception:  # noqa: BLE001 — banner är en bonus, inte svaret
                pass
            skrivare.close()
            return {"port": p, "oppen": True, "banner": hälsning}
        except Exception as fel:  # noqa: BLE001
            return {
                "port": p,
                "oppen": False,
                "fel": type(fel).__name__,
                "errno": getattr(fel, "errno", None),
            }

    resultat = [await prova(p) for p in dict.fromkeys([målport, 587, 465, 2525])]
    nagon_oppen = any(r["oppen"] for r in resultat)

    return {
        "provider": type(provider).__name__,
        "levererar": getattr(provider, "levererar", False),
        "vard": målvärd,
        "portar": resultat,
        "smtp_mojligt": nagon_oppen,
        "slutsats": (
            "SMTP går ut härifrån."
            if nagon_oppen
            else "Plattformen blockerar utgående SMTP — använd RESEND_API_KEY (HTTPS)."
        ),
    }


@router.post("/sandvag/prov")
async def sandvagsprov(request: Request, till: str) -> dict:
    """Skicka ETT provmejl genom den konfigurerade sändvägen.

    Finns för att svara på frågan som `/sandvag` inte kan svara på: att porten
    är öppen (eller att vi kör HTTPS) betyder inte att ett mejl faktiskt
    kommer FRAM. Nyckeln kan vara ogiltig, domänen overifierad hos Resend,
    kvoten slut — och alla tre visar sig först vid ett riktigt utskick.

    Utan den här endpointen är enda sättet att pröva sändvägen i en ny miljö
    att godkänna ett riktigt kundsvar och hoppas. Det är fel ordning: vägen
    ska vara bevisad innan en kunds mejl är insatsen.

    ## Varför brödtexten är låst

    Anroparen väljer bara MOTTAGARE, aldrig innehåll. En master-nyckel som kan
    skicka fritt formulerad text till valfri adress är en öppen relä om
    nyckeln någonsin läcker; en som bara kan skicka den här fasta lappen är
    det inte. Begränsningen kostar ingenting — ett provmejl behöver inte säga
    något annat än att det kom fram.
    """
    from ..leads.send_provider import get_send_provider

    provider = get_send_provider()
    if not getattr(provider, "levererar", False):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Sändvägen är {type(provider).__name__} — den skickar ingenting. "
                "Sätt RESEND_API_KEY (eller SMTP_*) först."
            ),
        )

    adress = (till or "").strip()
    if "@" not in adress:
        raise HTTPException(status_code=422, detail="Ogiltig mottagaradress.")

    try:
        await provider.send(
            to=adress,
            subject="Snajp: sändvägen fungerar",
            body=(
                "Det här är ett provmejl från Snajps backend.\n\n"
                "Kommer det fram är sändvägen bevisad hela vägen: nyckeln är "
                "giltig, avsändardomänen är verifierad och leverantören "
                "accepterade utskicket.\n\n"
                f"Skickat via {type(provider).__name__}.\n"
            ),
        )
    except Exception as fel:  # noqa: BLE001 — felet ÄR svaret här
        raise HTTPException(
            status_code=502,
            detail=f"{type(fel).__name__}: {str(fel)[:400]}",
        ) from fel

    return {"skickat": True, "till": adress, "provider": type(provider).__name__}
