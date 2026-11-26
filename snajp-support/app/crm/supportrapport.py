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
"""

from __future__ import annotations

import re
from typing import Any

from . import adaptrar, lagring

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
    return ny or korning


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
