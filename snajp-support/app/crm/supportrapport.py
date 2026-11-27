"""Synkens två nivåer: det kunden ser och det supporten får (migration 163).

Antons svar 2026-11-26: förloppet visas för kunden, felen i enkla ord, med
beskedet att de gått vidare till supporten. Alla felkoder och hela rapporten
blir ett supportärende.

## Kundens nivå: `enkelt`

En kort lista över vad som hände, grupperad efter sort och fält, utan koder,
radnummer och källans id: "3 bolag har ett telefonnummer som inte gick att
läsa". Appen sätter orden; här avgörs bara sorten.

## Supportens nivå: `bygg`

Hela rapporten: räknarna, anslutningens inställningar och gällande mappning,
och varje felrad med kod. Den sparas på körningen när den avslutas, och
supportsystemet hämtar den över /api/admin/crm/supportrapporter.

Ett värde som inte gick att tolka står i rapporten med sin FORM, inte med
innehållet: `070-123 45` blir `999-999 99`. Formen räcker för att se varför
det föll (riktnummer saknas, fel antal siffror), och en felskriven adress
eller ett felskrivet nummer är fortfarande en persons uppgift.

Det som hoppas över med flit (privatpersoner, mappningens egna undantag, det
som redan är borta) är inga fel och ger ingen rapport.

## Ärendet: `skapa_arende`

En rapport blir av sig själv ett plattformsärende (migration 156), samma
tabell som Hjälprutans felrapporter, och numret skrivs på körningen så att
kunden ser det under CRM › Synk. Synken startas av en nyckel och har ingen
användare: rapportören är den fasta identiteten `SYSTEMRAPPORTOR`, som ingen
kund är och som Hjälprutans lista därför aldrig visar för någon.

Ärendets text bär räknarna och felkodernas namn, aldrig ett värde, ett namn
på en post eller källans id: det som behövs står i rapporten, och ärendet
pekar dit. En kund utan arbetsyta (bara API) får inget ärende; rapporten
väntar då i `GET /api/admin/crm/supportrapporter?utan_arende=true`.

Samma anslutning som faller natt efter natt ger ETT ärende: ett öppet ärende
från synken för samma kund och samma anslutning får körningen som en intern
händelse i stället. Av med `CRM_SUPPORTARENDEN=0`.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Any

from ..config import get_settings
from ..notifications.prioriterat_mejl import skicka_felrapport
from . import adaptrar, lagring

logger = logging.getLogger("snajp-support.crm.supportrapport")

#: Synkens identitet som rapportör. Fast och dokumenterad: samma värde i varje
#: miljö, och ingen användare kan ha det.
SYSTEMRAPPORTOR = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://snajp.se/crm/synk"))
SYSTEMRAPPORTOR_NAMN = "Snajp CRM, synken"
_SIDA = "/crm/synk"
#: Högst så här många felkoder står i ärendets text; resten står i rapporten.
_MAX_KODER = 40

#: Mejlen om nya ärenden körs efter svaret. Referenserna håller uppgifterna
#: vid liv (asyncio.create_task är svag), som i plattformsarenden.py.
_pagaende: set[asyncio.Task] = set()

#: Skäl som är avsedda och inte fel.
MED_FLIT = ("privatperson", "hoppas_over_enligt_mappningen", "redan_borta")

#: Sorterna kunden får se. Appen har en mening för var och en.
_SORT_FOR_ORSAK = {
    "saknar_namn": "saknar_uppgift", "saknar_namn_och_epost": "saknar_uppgift",
    "orgnr_tillhor_annat_bolag": "dubblett", "finns_redan": "dubblett",
    "behandlingen_ar_begransad": "begransad",
    "privatperson": "privatperson", "hoppas_over_enligt_mappningen": "undantagen", "redan_borta": "redan_borta",
}


def form(varde: Any) -> str | None:
    """Värdets form utan dess innehåll: bokstäver blir a, siffror 9."""
    if varde is None:
        return None
    text = re.sub(r"[^\W\d_]", "a", str(varde)[:80])
    return re.sub(r"\d", "9", text)


def ar_fel(rad: dict[str, Any]) -> bool:
    """En felrad som supporten ska se: allt utom det som hoppats över med flit."""
    return bool(rad.get("faltfel")) or rad.get("orsak") not in (None, *MED_FLIT)


def behovs(korning: dict[str, Any]) -> bool:
    return korning.get("status") == "failed" or any(ar_fel(r) for r in korning.get("fel") or [])


def enkelt(korning: dict[str, Any]) -> list[dict[str, Any]]:
    """[{sort, objekt, falt, antal}] för kunden, störst först. `falt` finns
    bara för sorten `ogiltigt_varde`: vilket fält som inte gick att läsa."""
    antal: dict[tuple[str, str, str | None], int] = {}
    for rad in korning.get("fel") or []:
        objekt = rad.get("objekt") or "bolag"
        if rad.get("orsak"):
            nyckel = (_SORT_FOR_ORSAK.get(rad["orsak"], "annat"), objekt, None)
            antal[nyckel] = antal.get(nyckel, 0) + 1
        for faltfel in rad.get("faltfel") or []:
            sort = "saknar_uppgift" if faltfel.get("kod") == "saknas" else "ogiltigt_varde"
            nyckel = (sort, objekt, faltfel.get("falt"))
            antal[nyckel] = antal.get(nyckel, 0) + 1
    ut = [{"sort": sort, "objekt": objekt, "falt": falt, "antal": n} for (sort, objekt, falt), n in antal.items()]
    return sorted(ut, key=lambda r: (-r["antal"], r["sort"], r["falt"] or ""))


def bygg(tenant_namn: str | None, anslutning: dict[str, Any] | None, korning: dict[str, Any]) -> dict[str, Any]:
    """Hela rapporten. Rör ingen lagring."""
    rader, koder = [], {}
    for rad in korning.get("fel") or []:
        if not ar_fel(rad):
            continue
        if rad.get("orsak"):
            koder[rad["orsak"]] = koder.get(rad["orsak"], 0) + 1
        faltfel = []
        for f in rad.get("faltfel") or []:
            koder[f["kod"]] = koder.get(f["kod"], 0) + 1
            faltfel.append({"falt": f.get("falt"), "kod": f.get("kod"),
                            **({"form": form(f["varde"])} if f.get("varde") not in (None, "(sparas inte)") else {})})
        rader.append({k: rad[k] for k in ("objekt", "index", "externt_id", "namn", "orsak", "krockar_med") if rad.get(k) is not None}
                     | ({"faltfel": faltfel} if faltfel else {}))
    rapport: dict[str, Any] = {
        "version": 1,
        "skapad": lagring.nu(),
        "kund": tenant_namn,
        "korning": {
            "id": korning["id"], "lage": korning["lage"], "status": korning["status"], "error": korning.get("error"),
            "startad_av": korning.get("startad_av"), "created_at": korning.get("created_at"),
            "completed_at": korning.get("completed_at"), "raknare": {k: korning.get(k, 0) for k in lagring.RAKNARE},
        },
        "koder": dict(sorted(koder.items(), key=lambda kv: (-kv[1], kv[0]))),
        "rader": rader,
        # Felloggen sparar högst MAX_FEL rader. Räknarna säger hur många det var.
        "avkortad": len(korning.get("fel") or []) >= lagring.MAX_FEL,
    }
    if anslutning:
        rapport["anslutning"] = {
            "id": anslutning["id"], "namn": anslutning["namn"], "system": anslutning["system"],
            "konfliktregel": anslutning.get("konfliktregel"), "saknade": anslutning.get("saknade"),
            "standardrelation": anslutning.get("standardrelation"),
            "privatpersoner": bool(anslutning.get("privatpersoner")),
            "egen_mappning": anslutning.get("mappning") or {},
            "gallande_mappning": adaptrar.gallande_mappning(anslutning["system"], anslutning.get("mappning")),
        }
    return rapport


async def lamna(
    storage: Any, tenant_id: str, anslutning: dict[str, Any] | None, korning: dict[str, Any]
) -> dict[str, Any]:
    """Bygger och sparar rapporten om körningen har fel. Returnerar körningen."""
    if not behovs(korning) or korning.get("support_lamnad_at"):
        return korning
    tenant_namn = None
    try:
        tenant = await storage.get_tenant(tenant_id)
        tenant_namn = (tenant or {}).get("name")
    except Exception:  # noqa: BLE001 — namnet är en bekvämlighet i rapporten, inte ett villkor
        pass
    ny = await lagring._upp(storage, tenant_id, "crm_synkkorningar", korning["id"], {
        "supportrapport": bygg(tenant_namn, anslutning, korning), "support_lamnad_at": lagring.nu()})
    ny = ny or korning
    if get_settings().crm_supportarenden and not ny.get("support_arende"):
        nummer = await skapa_arende(storage, tenant_id, ny, ny.get("supportrapport") or {}, anslutning=anslutning)
        if nummer:
            ny = {**ny, "support_arende": nummer}
    return ny


# -- Ärendet -----------------------------------------------------------------


def arendets_gjorde(anslutning: dict[str, Any] | None, korning: dict[str, Any]) -> str:
    namn = (anslutning or {}).get("namn") or "API:t utan anslutning"
    return f"Synk från {namn} ({korning.get('lage') or 'delta'})"


def arendets_hande(tenant_id: str, korning: dict[str, Any], rapport: dict[str, Any]) -> str:
    """Räknarna och felkoderna, störst först. Bara koder och tal: ingen rad
    ur rapporten, inget värde och ingen form av ett värde."""
    rader = [f"Körning {korning['id']}, status {korning.get('status')}."]
    if re.fullmatch(r"[a-z0-9_]{1,60}", str(korning.get("error") or "")):
        rader.append(f"Körningen föll: {korning['error']}.")
    rader.append(f"Totalt {korning.get('totalt', 0)}, skapade {korning.get('skapade', 0)}, "
                 f"uppdaterade {korning.get('uppdaterade', 0)}, hoppade {korning.get('hoppade', 0)}.")
    koder = sorted((rapport.get("koder") or {}).items(), key=lambda kv: (-kv[1], kv[0]))
    if koder:
        rader.append("Felkoder, störst först:")
        rader += [f"- {kod}: {antal}" for kod, antal in koder[:_MAX_KODER]
                  if re.fullmatch(r"[a-z0-9_]{1,60}", str(kod))]
        if len(koder) > _MAX_KODER:
            rader.append(f"- och {len(koder) - _MAX_KODER} koder till, i rapporten")
    if rapport.get("avkortad"):
        rader.append(f"Felloggen är avkortad till {lagring.MAX_FEL} rader; räknarna gäller hela körningen.")
    rader.append(f"Hela rapporten: GET /api/admin/crm/supportrapporter/{tenant_id}/{korning['id']}")
    return "\n".join(rader)


def _antal_poster(korning: dict[str, Any]) -> str:
    """Antalet poster som föll, ur felloggen. Loggen har taket MAX_FEL: står
    den full är talet ett golv, och då säger texten "minst"."""
    fel = korning.get("fel") or []
    antal = sum(1 for rad in fel if ar_fel(rad))
    return f"minst {antal}" if len(fel) >= lagring.MAX_FEL else str(antal)


async def _arbetsyta(storage: Any, tenant_id: str) -> str | None:
    """Kundens arbetsyta, bara id. Oskopad systemläsning som `tillgang.grund`:
    `workspaces` bär workspace-RLS och en tenant-skopad anslutning ser noll
    rader. Den tidigast skapade vinner när flera delar kund."""
    if lagring._ar_postgres(storage) and hasattr(storage, "pool"):
        async with storage.pool.acquire() as conn:
            rad = await conn.fetchrow(
                "select id from workspaces where ss_tenant_id = $1::text::uuid order by created_at limit 1",
                str(tenant_id))
        return None if rad is None else str(rad["id"])
    return getattr(storage, "_crm_arbetsytor", {}).get(str(tenant_id))


async def _hjalpens_tenant(storage: Any) -> str | None:
    """Hjälpens egen kund (`HJALP_TENANT_SLUG`): mejlet om en ny felrapport
    bär den, inte rapportörens kund."""
    slug = get_settings().hjalp_tenant_slug
    for tenant in await storage.list_tenants():
        if tenant.get("slug") == slug:
            return str(tenant["id"])
    return None


async def _mejla(storage: Any, nummer: str, arende_id: str) -> None:
    """Mejlet till Snajp om ett NYTT ärende. Får aldrig fälla något."""
    try:
        hjalp = await _hjalpens_tenant(storage)
        if hjalp is None:
            logger.info("Mejlet om synkärende %s hoppades över: hjälpens kund finns inte.", nummer)
            return
        await skicka_felrapport(nummer=nummer, arende_id=arende_id, tenant_id=hjalp)
    except Exception:  # noqa: BLE001 — mejlet får aldrig fälla ärendet
        logger.warning("Mejlet om synkärende %s kunde inte skickas.", nummer, exc_info=True)


async def skapa_arende(
    storage: Any, tenant_id: str, korning: dict[str, Any], rapport: dict[str, Any], *,
    anslutning: dict[str, Any] | None = None,
) -> str | None:
    """Gör rapporten till ett plattformsärende och skriver numret på körningen.

    Ett öppet ärende från synken för samma kund och samma anslutning
    återanvänds med en intern händelse. None när inget ärende skapades: kunden
    saknar arbetsyta, körningen har inga fel, eller något föll. Ett fel här
    fäller aldrig synken."""
    try:
        if not behovs(korning):
            return None
        arbetsyta = await _arbetsyta(storage, tenant_id)
        if arbetsyta is None:
            logger.info("Synkens rapport fick inget ärende: kunden saknar arbetsyta (tenant %s, körning %s).",
                        tenant_id, korning["id"])
            return None
        tenant = await storage.get_tenant(tenant_id) or {}
        slug = tenant.get("slug")
        if not slug:
            logger.info("Synkens rapport fick inget ärende: kunden saknar slug (tenant %s).", tenant_id)
            return None
        if anslutning is None and korning.get("anslutning_id"):
            anslutning = await lagring.hamta_anslutning(storage, tenant_id, korning["anslutning_id"])
        gjorde = arendets_gjorde(anslutning, korning)
        meddelande = f"Samma anslutning föll igen i körning {korning['id']}: {_antal_poster(korning)} poster"

        # Det öppna ärendet söks med en riktad fråga (inte bland en lista med
        # tak), och händelsen skrivs villkorat på statusen som lästes. Byter
        # någon status emellan, eller stänger ärendet, söks det om: ett
        # stängt ärende ger då ett nytt, ett annat läge får händelsen.
        for _ in range(3):
            oppet = await storage.hitta_oppet_plattformsarende(
                rapportor_user_id=SYSTEMRAPPORTOR, kund_workspace_id=arbetsyta, kund_tenant_slug=slug, gjorde=gjorde)
            if oppet is None:
                break
            andrat = await storage.andra_plattformsarende(
                oppet["id"], status=oppet["status"], kraver_status=(oppet["status"],),
                handelse={"typ": "synk", "synlig_for_kund": False, "aktor": "system", "meddelande": meddelande})
            if andrat is not None:
                await satt_arende(storage, tenant_id, korning["id"], oppet["nummer"])
                return oppet["nummer"]
        else:
            logger.warning("Synkens ärende bytte status under skrivningen tre gånger (tenant %s, körning %s).",
                           tenant_id, korning["id"])
            return None

        from ..api.schemas import PlattformsarendeRequest

        falt = PlattformsarendeRequest(
            rapportor_user_id=SYSTEMRAPPORTOR, rapportor_namn=SYSTEMRAPPORTOR_NAMN, kund_workspace_id=arbetsyta,
            kund_tenant_slug=slug, vy="crm", roll="system", besok_av_admin=False, sida=_SIDA, gjorde=gjorde,
            hande=arendets_hande(tenant_id, korning, rapport)[:4000], vantade="Att alla poster kom in.",
        ).model_dump()
        # Synken skapade ärendet, inte en kund: den första händelsen säger det
        # och är intern, som de som följer.
        arende = await storage.skapa_plattformsarende(falt, aktor="system", synlig_for_kund=False)
        await satt_arende(storage, tenant_id, korning["id"], arende["nummer"])
        uppgift = asyncio.create_task(_mejla(storage, arende["nummer"], arende["id"]))
        _pagaende.add(uppgift)
        uppgift.add_done_callback(_pagaende.discard)
        return arende["nummer"]
    except Exception as fel:  # noqa: BLE001 — ärendet får aldrig fälla synken
        logger.warning("Synkens supportärende kunde inte skapas (%s, tenant %s, körning %s).",
                       type(fel).__name__, tenant_id, korning.get("id"))
        return None


async def lista(storage: Any, *, bara_utan_arende: bool = False, limit: int = 200) -> list[dict[str, Any]]:
    """Rapporterna hos alla kunder, nyast först. Bara för adminvägen: läser
    per kund, eftersom radskyddet inte släpper en läsning tvärs över kunder."""
    ut: list[dict[str, Any]] = []
    for tenant in await storage.list_tenants():
        tenant_id = str(tenant["id"])
        for korning in await lagring.lista_korningar(storage, tenant_id, limit=200):
            if not korning.get("support_lamnad_at") or (bara_utan_arende and korning.get("support_arende")):
                continue
            rapport = korning.get("supportrapport") or {}
            ut.append({"tenant_id": tenant_id, "kund": tenant.get("name"), "korning_id": korning["id"],
                       "lamnad_at": korning["support_lamnad_at"], "arende": korning.get("support_arende"),
                       "status": korning["status"], "error": korning.get("error"),
                       "anslutning": (rapport.get("anslutning") or {}).get("namn"),
                       "system": (rapport.get("anslutning") or {}).get("system"),
                       "koder": rapport.get("koder") or {}, "antal_rader": len(rapport.get("rader") or [])})
    ut.sort(key=lambda r: r["lamnad_at"], reverse=True)
    return ut[:limit]


async def satt_arende(storage: Any, tenant_id: str, korning_id: str, nummer: str) -> dict[str, Any] | None:
    korning = await lagring.hamta_korning(storage, tenant_id, korning_id)
    if korning is None or not korning.get("support_lamnad_at"):
        return None
    return await lagring._upp(storage, tenant_id, "crm_synkkorningar", korning_id, {"support_arende": nummer})
