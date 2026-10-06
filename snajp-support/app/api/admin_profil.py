"""Adminens SKRIVYTA mot agentprofilen — instruktioner, ton, röst, affärskontext.

## Varför en egen fil bredvid admin.py

`admin.py` bär regeln "ingen endpoint här skriver", och den regeln är värd att
behålla: en läsvy som råkar skriva är en dålig upptäckt att göra i drift. Så
läsningen ligger kvar där och skrivningen ligger här, bakom samma
master-nyckel men i en fil vars namn säger vad den gör.

## Varför skrivningen behövdes alls

`agent_configs.instructions_md` och `.tone` fanns sedan migration 010 utan
någon skrivväg — i någon yta — och utan läsväg heller. Följden märktes först
hos en kund: instruktionsändringar gav identiska svar, därför att texten
aldrig lämnade databasen. Migration 049 gav fälten sin läsväg
(`app/agentcore/instruktioner.py`); det här är skrivvägen.

## Vad som INTE går att skriva härifrån

Ärenden, mejl, prospekt, körningar, fakturering. Det är historik och
transaktioner — de uppstår ur något som hänt och ska inte gå att redigera i
efterhand. Här ändras bara det som formar FRAMTIDA körningar.

## Varför instruktionsfälten är admin-only

Det är en säkerhetsgräns, inte en rollfråga. Instruktionerna går i
SYSTEMposition i prompten; kundskriven text (SOUL, affärskontext) går i
USERposition, wrappad som opålitligt innehåll. Skillnaden är hela INV-SEC-009:
en kund ska kunna be om en ton och inte kunna be om att reglerna ignoreras.

Flyttas ett av instruktionsfälten till kundens egen yta MÅSTE det samtidigt
flyttas till USERposition. De två besluten är ett beslut.

## Spårning

Varje skrivning loggar en rad i `platform_events` med kund och fältnamn. Utan
det är en ändring som ingen kan spåra precis den sortens misstag den gamla
"ingen skrivning"-regeln fanns för att förhindra.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..agentcore.baka_in import baka_in
from ..agentcore.instruktioner import MAX_TECKEN, MAX_TECKEN_GRUNDPROMPT, las_instruktioner
from ..agentcore.overlays import load_global_instructions as load_global_instructions_fil
from ..leads.soul import SOUL_KIND
from .deps import kraev_uuid, require_master_key
from .schemas import (
    InstruktionRequest,
    TenantAktivRequest,
    TenantProfilRequest,
    TenantStatusRequest,
)

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])

#: 'alla' = det gemensamma lagret (agent-core/AGENTS.md); 'support' och 'leads'
#: = agentens grundprompt (agent-core/prompts/). Migration 099.
AGENTTYPER = ("alla", "support", "leads")


async def _dokument_ur(
    payload: InstruktionRequest | TenantProfilRequest, *, bas: str, tak: int
) -> tuple[str, str, str]:
    """(dokument, kalla, anmarkning). Tre vägar, i prioritetsordning:

      1. Ett färdigt dokument skickades med (granskad förhandsvisning eller
         handredigering)                       -> ta det ordagrant.
      2. strukturera=True                      -> feedbacken BAKAS IN i `bas`.
      3. annars                                -> texten sparas som den är.

    Väg 2 ersatte före 2026-10-06 hela dokumentet med modellens omformning av
    feedbacken ensam (strukturera.py). En inklistrad mall blev då fem rader
    och sanningsreglerna försvann. Nu läggs feedbacken in i det dokument som
    redan gäller (agentcore/baka_in.py), och allt den inte gäller står kvar.
    """
    if isinstance(payload, InstruktionRequest):
        rav = payload.feedback if payload.feedback is not None else payload.ravtext
        redigerad = payload.strukturerad_md
    else:
        rav, redigerad = (payload.instruktioner_rav or ""), payload.instruktioner_md

    if redigerad is not None and redigerad.strip():
        return redigerad.strip()[:tak], ("bakad" if rav.strip() else "manuell"), ""
    if not payload.strukturera:
        return rav.strip()[:tak], "manuell", ""
    bakning = await baka_in(bas, rav, tak=tak)
    return bakning.dokument[:tak], bakning.kalla, bakning.anmarkning


def _fil_text(agent: str) -> str:
    """Den incheckade texten som gäller när ingen version är sparad."""
    if agent == "support":
        from ..agent.support_systemprompt import _mall

        return _mall()
    if agent == "leads":
        from ..agent.leads_systemprompt import fil_mall

        return fil_mall()
    return load_global_instructions_fil()


def _tak(agent: str) -> int:
    return MAX_TECKEN if agent == "alla" else MAX_TECKEN_GRUNDPROMPT


async def _basdokument(storage, agent: str) -> tuple[str, dict | None]:
    """(dokumentet som gäller nu, den aktiva raden eller None)."""
    rad = await storage.get_global_instructions(agent)
    if rad and (rad.get("strukturerad_md") or "").strip():
        return rad["strukturerad_md"], rad
    return _fil_text(agent), rad


def _agent(agent: str) -> str:
    if agent not in AGENTTYPER:
        raise HTTPException(status_code=422, detail=f"Okänd agent: {agent}. Giltiga: {', '.join(AGENTTYPER)}.")
    return agent


# -- Globala agentinstruktioner ------------------------------------------
#
# Det som förr bara gick att ändra genom att redigera agent-core/AGENTS.md och
# deploya om. Filen finns kvar som fallback: har ingen skrivit någon global
# instruktion är den fortfarande sanningen, alltså exakt beteendet före 049.


@router.get("/instruktioner")
async def hamta_instruktioner(request: Request, agent: str = "alla") -> dict:
    """Instruktionerna för `agent` ('alla' = det gemensamma lagret, 'support'
    och 'leads' = agentens grundprompt), som agenten läser dem just nu."""
    agent = _agent(agent)
    storage = request.app.state.storage
    aktiv = await storage.get_global_instructions(agent)
    # `aktiv_text` är vad agenten FAKTISKT skulle läsa just nu, fil-fallbacken
    # inräknad. Utan den svarar vyn på "vad står i tabellen" när frågan är
    # "vad läser agenten", och de två är olika så länge fallbacken finns.
    aktiv_text, _ = await _basdokument(storage, agent)
    lager = await las_instruktioner(storage)
    return {
        "instruktioner": {
            "agent": agent,
            "ravtext": (aktiv or {}).get("ravtext", ""),
            "feedback": (aktiv or {}).get("feedback", ""),
            "strukturerad_md": (aktiv or {}).get("strukturerad_md", ""),
            "kalla": (aktiv or {}).get("kalla", ""),
            "uppdaterad": (aktiv or {}).get("created_at"),
            "aktiv_text": aktiv_text,
            "fran_fil": not (aktiv and (aktiv.get("strukturerad_md") or "").strip()),
            "hash": lager.hash[:12] if agent == "alla" else "",
            "tak": _tak(agent),
            "historik": await storage.list_global_instructions(limit=20, agent_type=agent, med_text=True),
        }
    }


@router.post("/instruktioner/forhandsgranska")
async def forhandsgranska_instruktioner(request: Request, payload: InstruktionRequest) -> dict:
    """Baka in feedbacken UTAN att spara, och visa varje ändring med skäl.

    Egen endpoint och inte en flagga på PUT: den som vill se vad modellen gör
    av sin feedback ska kunna göra det utan att den aktiva instruktionen byts
    mitt under en pågående körning. Det dokument som visas här är det som
    sparas, om admin godkänner det (PUT med strukturerad_md).
    """
    agent = _agent(payload.agent)
    bas, _ = await _basdokument(request.app.state.storage, agent)
    feedback = payload.feedback if payload.feedback is not None else payload.ravtext
    return (await baka_in(bas, feedback, tak=_tak(agent))).som_dict()


@router.put("/instruktioner")
async def spara_instruktioner(request: Request, payload: InstruktionRequest) -> dict:
    storage = request.app.state.storage
    agent = _agent(payload.agent)
    bas, _ = await _basdokument(storage, agent)
    dokument, kalla, anmarkning = await _dokument_ur(payload, bas=bas, tak=_tak(agent))

    rad = await storage.save_global_instructions(
        ravtext=payload.ravtext,
        strukturerad_md=dokument,
        kalla=kalla,
        agent_type=agent,
        feedback=(payload.feedback or "").strip(),
    )
    await storage.log_platform_event(
        level="info",
        source="admin.instruktioner",
        message=f"Agentinstruktioner uppdaterade ({agent}).",
        detail={"agent": agent, "kalla": kalla, "tecken": len(dokument), "fore": len(bas)},
    )
    # Fas R2 (INV-CACHE-001): globala instruktioner gäller för ALLA tenants
    # på en gång (se app/agentcore/instruktioner.py) — bumpa den GLOBALA
    # konfigräknaren, inte en enskild tenants, så varenda cachad svarspost
    # hos varenda tenant blir omatchbar. Se app/cache/versioner.py.
    from ..cache import versioner

    await versioner.bumpa_config_global()
    return {
        "instruktioner": {
            "id": rad["id"],
            "agent": agent,
            "kalla": kalla,
            "strukturerad_md": dokument,
            "anmarkning": anmarkning,
        }
    }


@router.post("/instruktioner/{instruktion_id}/aterstall")
async def aterstall_instruktioner(request: Request, instruktion_id: str) -> dict:
    """Gör en tidigare version aktiv igen, som en ny rad (kalla='aterstalld').

    En ny rad i stället för att flytta `aktiv`: historiken ska visa att en
    återställning skett och när, och en körning som läste den mellanliggande
    versionen ska fortfarande gå att spåra (INV-AUDIT-001)."""
    kraev_uuid(instruktion_id, "Versionen")
    storage = request.app.state.storage
    gammal = await storage.get_global_instruction(instruktion_id)
    if not gammal:
        raise HTTPException(status_code=404, detail="Versionen finns inte.")
    agent = gammal.get("agent_type") or "alla"
    rad = await storage.save_global_instructions(
        ravtext=gammal.get("ravtext") or "",
        strukturerad_md=gammal.get("strukturerad_md") or "",
        kalla="aterstalld",
        agent_type=agent,
        feedback=f"Återställd version från {gammal.get('created_at')}",
    )
    await storage.log_platform_event(
        level="info",
        source="admin.instruktioner",
        message=f"Agentinstruktioner återställda ({agent}).",
        detail={"agent": agent, "fran": instruktion_id},
    )
    from ..cache import versioner

    await versioner.bumpa_config_global()
    return {"instruktioner": {"id": rad["id"], "agent": agent, "kalla": "aterstalld"}}


# -- Kundprofilen: allt som styr EN kunds agent, på ett ställe -------------


@router.get("/tenants/{tenant_id}/profil")
async def hamta_profil(request: Request, tenant_id: str, agent_type: str = "support") -> dict:
    """Varje fält som formar kundens agent, plus VAR det hamnar i prompten.

    `position` följer med i svaret och är inte dekoration: den är skillnaden
    mellan en regel agenten lyder och en text agenten läser som data. Står den
    inte i svaret måste den som bygger vyn slå upp den i koden, och den som
    inte gör det ritar två fält som ser likadana ut och beter sig olika.
    """
    kraev_uuid(tenant_id, "Kunden")
    storage = request.app.state.storage
    tenant = await storage.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Kunden finns inte.")

    config = await storage.get_agent_config(tenant_id, agent_type=agent_type)
    soul = await storage.get_latest_context_doc(tenant_id, kind=SOUL_KIND)
    affarskontext = await storage.get_latest_context_doc(tenant_id, kind="product_marketing")
    installningar = await storage.get_agent_settings(tenant_id, agent_type=agent_type)
    lager = await las_instruktioner(
        storage, tenant_id, agent_type=agent_type, tenant_namn=tenant.get("name") or ""
    )

    return {
        "profil": {
            "tenant": {
                "id": str(tenant["id"]),
                "slug": tenant.get("slug"),
                "name": tenant.get("name"),
            },
            "agent_type": agent_type,
            "instruktioner_rav": config.get("instructions_rav", ""),
            "instruktioner_md": config.get("instructions_md", ""),
            "tone": config.get("tone", ""),
            "taxonomy": list(config.get("taxonomy") or []),
            "language_policy": config.get("language_policy", "sv_default"),
            "status": config.get("status", "draft"),
            "pinned_pack_version": config.get("pinned_pack_version"),
            "soul": (soul or {}).get("content", ""),
            "affarskontext": (affarskontext or {}).get("content", ""),
            "installningar": installningar,
            "kb_artiklar": len(await storage.list_kb(tenant_id)),
            "instruktionshash": lager.hash[:12],
            "global_fran_fil": lager.global_fran_fil,
            "position": {
                "instruktioner_md": "system",
                "tone": "user (ärendekontext)",
                "soul": "user (opålitligt innehåll)",
                "affarskontext": "user (opålitligt innehåll)",
                "kunskapsbas": "user (enda faktakällan för svar)",
            },
        }
    }


@router.put("/tenants/{tenant_id}/profil")
async def spara_profil(request: Request, tenant_id: str, payload: TenantProfilRequest) -> dict:
    """Sparar de fält som SKICKATS med. None betyder "rör inte".

    Skillnaden mot tom sträng bärs hela vägen ner i lagringslagret: tom sträng
    nollställer, None låter bli. Utan den kan ett formulär som sparar en
    sektion i taget inte undvika att radera de andra — och det felet syns
    först när en kunds röstdokument är borta.
    """
    kraev_uuid(tenant_id, "Kunden")
    storage = request.app.state.storage
    if not await storage.get_tenant(tenant_id):
        raise HTTPException(status_code=404, detail="Kunden finns inte.")

    andrade: list[str] = []
    anmarkning = ""

    if payload.instruktioner_rav is not None or payload.instruktioner_md is not None:
        # Kundens instruktion bakas in i den som redan gäller, samma väg som
        # det globala lagret: en ny anteckning ska inte radera de gamla.
        befintlig = (await storage.get_agent_config(tenant_id, agent_type=payload.agent_type)).get(
            "instructions_md"
        ) or ""
        dokument, _kalla, anmarkning = await _dokument_ur(payload, bas=befintlig, tak=MAX_TECKEN)
        await storage.set_agent_instructions(
            tenant_id,
            agent_type=payload.agent_type,
            instructions_md=dokument,
            instructions_rav=payload.instruktioner_rav or "",
            tone=payload.tone,
        )
        andrade.append("instruktioner")
        if payload.tone is not None:
            andrade.append("tone")
    elif payload.tone is not None:
        # Bara tonen ändrades. Instruktionerna läses tillbaka och skrivs
        # oförändrade — set_agent_instructions är en upsert, så tom sträng
        # här hade raderat dem.
        nuvarande = await storage.get_agent_config(tenant_id, agent_type=payload.agent_type)
        await storage.set_agent_instructions(
            tenant_id,
            agent_type=payload.agent_type,
            instructions_md=nuvarande.get("instructions_md", ""),
            instructions_rav=nuvarande.get("instructions_rav", ""),
            tone=payload.tone,
        )
        andrade.append("tone")

    if payload.soul is not None:
        await storage.save_context_doc(
            tenant_id, kind=SOUL_KIND, content=payload.soul, source="admin"
        )
        andrade.append("soul")

    if payload.affarskontext is not None:
        await storage.save_context_doc(
            tenant_id, kind="product_marketing", content=payload.affarskontext, source="admin"
        )
        andrade.append("affarskontext")

    if andrade:
        await storage.log_platform_event(
            level="info",
            source="admin.profil",
            message=f"Agentprofil ändrad: {', '.join(andrade)}.",
            tenant_id=tenant_id,
            detail={"agent_type": payload.agent_type, "falt": andrade},
        )
        # Fas R2 (INV-CACHE-001): bara instruktioner/ton/SOUL påverkar en
        # cachad repliks GRUND (de går i system-/kontextposition för varje
        # körning) — bumpa bara då. `affarskontext` ändrar case_context för
        # de FULLA körningarna men rörs medvetet inte här: uppdraget som
        # införde bumpen skopade den till instruktioner/ton/SOUL, och en
        # svarscache-post existerar ändå bara för förstakontaktsfrågor utan
        # kundspecifik kontext (se svarscache.lookup_behorig).
        if {"instruktioner", "tone", "soul"} & set(andrade):
            from ..cache import versioner

            await versioner.bumpa_config(tenant_id)

    return {"sparat": andrade, "anmarkning": anmarkning}


@router.put("/tenants/{tenant_id}/aktiv")
async def satt_tenant_aktiv(
    request: Request, tenant_id: str, payload: TenantAktivRequest
) -> dict:
    """Stänger av eller återaktiverar en kund — trial-konverteringens manuella väg.

    Beslutet 2026-09-20: ingen automatisk konvertering när provperioden går
    ut. En människa stänger av, med bekräftelse i adminytan, och det här är
    skrivningen bakom den knappen. Avstängningen ÄR `ss_tenants.active`:
    `validate_api_key` avvisar nycklar för en inaktiv tenant, så alla tre
    agenterna, den inloggade arbetsytan, portalen och den publika chatten
    låses ute i samma ögonblick — med 401, inte 403, så en avstängd kunds
    nyckel inte går att skilja från en ogiltig utifrån.

    Ingenting raderas. Data, inställningar och historik står orörda, och en
    återaktivering öppnar allt igen — avstängning är en förhandling, inte en
    gallring (gallringen har sin egen väg, scripts/gallra.py).
    """
    kraev_uuid(tenant_id, "Kunden")
    storage = request.app.state.storage
    tenant = await storage.set_tenant_active(tenant_id, active=payload.active)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Kunden finns inte.")

    await storage.log_platform_event(
        # warning vid avstängning: det är händelsen någon kan behöva förklara
        # i efterhand, och den ska inte drunkna bland info-raderna.
        level="info" if payload.active else "warning",
        source="admin.avstangning",
        message=(
            f"Kontot återaktiverat: {tenant.get('name') or tenant_id}."
            if payload.active
            else f"Kontot avstängt: {tenant.get('name') or tenant_id}."
        ),
        tenant_id=tenant_id,
        detail={"active": payload.active, "orsak": payload.orsak or ""},
    )
    return {"tenant": tenant}


#: Besked per läge i händelseloggen. Pausen är en warning av samma skäl som
#: avstängningen: det är händelsen någon kan behöva förklara i efterhand.
_STATUS_BESKED = {
    "aktiv": ("info", "Kontot återaktiverat"),
    "pausad": ("warning", "Kontot pausat"),
    "avstangd": ("warning", "Kontot avstängt"),
}


@router.put("/tenants/{tenant_id}/status")
async def satt_tenant_status(
    request: Request, tenant_id: str, payload: TenantStatusRequest
) -> dict:
    """Sätter kontots läge från adminytans paketflik (migration 080).

    Spärren är fortfarande `ss_tenants.active` och skrivs i samma sats
    (storage.set_tenant_status): 'pausad' och 'avstangd' låser ute lika hårt,
    med 401 via validate_api_key precis som den gamla aktiv-vägen. Skillnaden
    är AVSIKTEN — en paus ska öppnas igen, en avstängning är ett avslut — och
    den skillnaden bär adminytan och händelseloggen, inte någon grind.

    Ingenting raderas, oavsett läge. Data, inställningar och historik står
    orörda, och 'aktiv' öppnar allt igen.
    """
    kraev_uuid(tenant_id, "Kunden")
    storage = request.app.state.storage
    tenant = await storage.set_tenant_status(tenant_id, status=payload.status)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Kunden finns inte.")

    niva, besked = _STATUS_BESKED[payload.status]
    await storage.log_platform_event(
        level=niva,
        source="admin.kundstatus",
        message=f"{besked}: {tenant.get('name') or tenant_id}.",
        tenant_id=tenant_id,
        detail={"status": payload.status, "orsak": payload.orsak or ""},
    )
    return {"tenant": tenant}
