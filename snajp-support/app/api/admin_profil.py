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

from ..agentcore.instruktioner import las_instruktioner
from ..agentcore.strukturera import strukturera as strukturera_text
from ..leads.soul import SOUL_KIND
from .deps import kraev_uuid, require_master_key
from .schemas import InstruktionRequest, TenantProfilRequest

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])


async def _dokument_ur(payload: InstruktionRequest | TenantProfilRequest) -> tuple[str, str, str]:
    """(dokument, kalla, anmarkning). Tre vägar, i prioritetsordning:

      1. Ett redigerat dokument skickades med  -> ta det ordagrant, 'manuell'.
      2. strukturera=True                      -> modellen får forma råtexten.
      3. annars                                -> råtexten sparas som den är.

    Väg 1 måste komma först. Den som redigerat modellens utkast för hand och
    får det omstrukturerat igen tappar sina ändringar — och lär sig att inte
    redigera.
    """
    if isinstance(payload, InstruktionRequest):
        rav, redigerad = payload.ravtext, payload.strukturerad_md
    else:
        rav, redigerad = (payload.instruktioner_rav or ""), payload.instruktioner_md

    if redigerad is not None and redigerad.strip():
        return redigerad.strip(), "manuell", ""
    if not payload.strukturera:
        return rav.strip(), "manuell", ""
    resultat = await strukturera_text(rav)
    return resultat.dokument, resultat.kalla, resultat.anmarkning


# -- Globala agentinstruktioner ------------------------------------------
#
# Det som förr bara gick att ändra genom att redigera agent-core/AGENTS.md och
# deploya om. Filen finns kvar som fallback: har ingen skrivit någon global
# instruktion är den fortfarande sanningen, alltså exakt beteendet före 049.


@router.get("/instruktioner")
async def hamta_instruktioner(request: Request) -> dict:
    storage = request.app.state.storage
    aktiv = await storage.get_global_instructions()
    # `aktiv_text` är vad agenten FAKTISKT skulle läsa just nu, fil-fallbacken
    # inräknad. Utan den svarar vyn på "vad står i tabellen" när frågan är
    # "vad läser agenten", och de två är olika så länge fallbacken finns.
    lager = await las_instruktioner(storage)
    return {
        "instruktioner": {
            "ravtext": (aktiv or {}).get("ravtext", ""),
            "strukturerad_md": (aktiv or {}).get("strukturerad_md", ""),
            "kalla": (aktiv or {}).get("kalla", ""),
            "uppdaterad": (aktiv or {}).get("created_at"),
            "aktiv_text": lager.global_md,
            "fran_fil": lager.global_fran_fil,
            "hash": lager.hash[:12],
            "historik": await storage.list_global_instructions(limit=20),
        }
    }


@router.post("/instruktioner/forhandsgranska")
async def forhandsgranska_instruktioner(request: Request, payload: InstruktionRequest) -> dict:
    """Strukturera UTAN att spara.

    Egen endpoint och inte en flagga på PUT: den som vill se vad modellen gör
    av sina anteckningar ska kunna göra det utan att den aktiva instruktionen
    byts mitt under en pågående körning.
    """
    resultat = await strukturera_text(payload.ravtext)
    return {
        "dokument": resultat.dokument,
        "kalla": resultat.kalla,
        "anmarkning": resultat.anmarkning,
    }


@router.put("/instruktioner")
async def spara_instruktioner(request: Request, payload: InstruktionRequest) -> dict:
    storage = request.app.state.storage
    dokument, kalla, anmarkning = await _dokument_ur(payload)

    rad = await storage.save_global_instructions(
        ravtext=payload.ravtext, strukturerad_md=dokument, kalla=kalla
    )
    await storage.log_platform_event(
        level="info",
        source="admin.instruktioner",
        message="Globala agentinstruktioner uppdaterade.",
        detail={"kalla": kalla, "tecken": len(dokument)},
    )
    return {
        "instruktioner": {
            "id": rad["id"],
            "kalla": kalla,
            "strukturerad_md": dokument,
            "anmarkning": anmarkning,
        }
    }


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
        dokument, _kalla, anmarkning = await _dokument_ur(payload)
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

    return {"sparat": andrade, "anmarkning": anmarkning}
