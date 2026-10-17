"""Pröva en listas bolag mot Iris igen (Antons beställning 2026-10-08).

En lista byggd före den nya kontaktsökningen (leadsregel 12–17) har bolag som
fastnade på "ingen kontaktmejl" fast adressen fanns på sajten. Här hämtas
registrets bolagssida och sajten på nytt, samma sökning och fördelning som en
körning (discovery.hamta_person_kontakt, sources/merinfo.fordela) körs, och
utfallet blir:

* mejl → Iris-prospekt (research startas av anroparen),
* bara telefon → ringlistan,
* annars står raden kvar med sitt nya skäl.

Ett bolag finns på ETT ställe (Antons krav 2026-10-08): en flyttad rad
raderas aldrig men märks `signal='flyttad'` och visas inte längre i listan,
och prospektet skapas genom storage.create_prospect, som returnerar ett
befintligt prospekt i stället för att skapa ett till.

Används av POST /api/leads/listor/{id}/omprova och scripts/omklassa_listspar.py.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .platshallare import AVVECKLAT

logger = logging.getLogger(__name__)

#: Märkningen i signal_detalj, per spår.
MARKERING = {"iris": "Iris", "ring": "ringlistan"}
_MARKERAD = " → flyttad till "
#: Prospektets profilkolumner (migration 031, 058, 081).
PROSPEKTFALT = (
    "orgnr", "website", "ort", "postnr", "anstallda", "omsattning", "sni",
    "contact_role", "contact_level", "contact_phone",
)


def ar_markerad(signal_detalj: str | None) -> bool:
    return _MARKERAD in (signal_detalj or "")


def ny_signal_detalj(signal_detalj: str | None, spar: str, dag: str) -> str:
    """Skälet som stod kvar, plus vart bolaget flyttades och när."""
    return f"{(signal_detalj or '').strip()}{_MARKERAD}{MARKERING[spar]} {dag}".strip()


def kandidat_ur_rad(rad: dict[str, Any], bolag: dict[str, Any] | None) -> dict[str, Any]:
    """Listraden med registrets bolagsfakta (merinfo.tolka_bolag) i
    kandidatens form, som körningen ser den."""
    from .sources import merinfo

    k = merinfo.till_kandidat(bolag, {}, None) if bolag and bolag.get("company_name") else {}
    return {
        **k,
        "company_name": rad["company_name"],
        "orgnr": rad.get("orgnr") or k.get("orgnr"),
        "ort": rad.get("ort") or k.get("ort"),
        "website": rad.get("website") or k.get("website"),
        "source_name": rad.get("source_name") or k.get("source_name"),
        "source_url": rad.get("source_url") or k.get("source_url"),
        # Webbpoolens bedömning (migration 108) följer med till prospektet.
        **{f: rad[f] for f in ("lan", "webbniva", "webbrevision") if rad.get(f) is not None},
    }


def planera(
    rad: dict[str, Any], kandidat: dict[str, Any], kontakt: dict[str, Any] | None
) -> tuple[str, str | None, dict[str, Any] | None]:
    """(spår, skäl, kandidaten på spåret). Spåret är merinfo.fordela:s, eller
    "redan_flyttad" för en rad som redan märkts. Kandidaten (bara iris och
    ring) är den som blir prospekt."""
    from .sources import merinfo

    if ar_markerad(rad.get("signal_detalj")) or rad.get("signal") == "flyttad":
        return "redan_flyttad", None, None
    if kandidat.get("avvecklas"):
        # Antons beslut 2026-10-08: ett bolag som avvecklas blir aldrig ett lead.
        return "ej_kvalificerad", AVVECKLAT, None
    spar, skal = merinfo.fordela(kandidat, kontakt)
    if spar not in MARKERING:
        return spar, skal, None
    k = merinfo.iris_kandidat(kandidat, kontakt) if spar == "iris" else merinfo.ringrad(kandidat, kontakt)
    return spar, skal, k


#: Källorna Processa om kan pröva för en rad (sparas i lead_list_items.kallor,
#: migration 110). Anton 2026-10-10: omprövningen ska "endast svepa källor som
#: den förra agenten inte använde", så att så många källor som möjligt täcks.
KALLOR = ("register", "katalog", "webbplats", "webbuppslag")


async def sok(
    rad: dict[str, Any], bolag: dict[str, Any] | None, *, betald: bool
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Kandidaten med webbplats och kontaktsökningens svar. `kandidat["kallor"]`
    är radens källor efter omprövningen (de tidigare plus de nya).

    * register: registrets bolagssida (anroparen läser den, `bolag`),
    * katalog: hitta.se på org.nr (leads/katalog.py), en gång per rad,
    * webbplats: kontaktsökningen på sajten; alltid när en sajt finns (sidorna
      är cachade och gratis att läsa om),
    * webbuppslag: grounded Gemini-uppslaget av webbplatsen (betald), en gång
      per rad och bara när inget annat gav en sajt.

    En parkerad eller trasig sajt ur registret avslutar inte sökningen: de
    andra vägarna till webbplatsen prövas (Anton 2026-10-10)."""
    from . import discovery, katalog
    from .platshallare import ar_platshallare
    from .sources import merinfo

    tidigare = {str(x) for x in rad.get("kallor") or []}
    nya: set[str] = {"register"} if bolag else set()
    kandidat = kandidat_ur_rad(rad, bolag)
    if "katalog" not in tidigare:
        kandidat = await katalog.berika(kandidat)
        nya.add("katalog")
    uppslag = betald and "webbuppslag" not in tidigare
    webb = await merinfo._webbplats(kandidat, betald=uppslag)
    skal = await ar_platshallare(webb) if webb else None
    if skal and skal != AVVECKLAT:
        alt = await merinfo._webbplats({**kandidat, "website": None}, betald=uppslag)
        if alt and discovery.normalisera_webbplats(alt) != discovery.normalisera_webbplats(webb)                 and not await ar_platshallare(alt):
            webb, skal = alt, None
    if uppslag:
        nya.add("webbuppslag")
    if skal:
        # Platshållaren är skälet (för webbpoolen det akuta), inte bara ett hinder.
        kandidat["webbrevision"] = {**(kandidat.get("webbrevision") or {}), "platshallare": skal}
        kandidat["avvecklas"] = skal == AVVECKLAT
        webb = None
    kandidat = {**kandidat, "website": webb}
    kontakt = None
    if webb:
        nya.add("webbplats")
        kontakt = await discovery.hamta_person_kontakt(
            webb, kandidat.get("vd_namn"), bolagsadress_racker=True, bolagsnamn=kandidat["company_name"]
        )
    kandidat["kallor"] = sorted(tidigare | nya)
    return kandidat, kontakt


async def sok_alla(
    par: list[tuple[dict[str, Any], dict[str, Any] | None]],
    *,
    betald: bool = False,
    samtidigt: int = 8,
    forlopp: Any = None,
) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    """sok() för alla rader, högst `samtidigt` åt gången. En trasig sajt ger
    kandidaten utan kontakt (fördelningen säger då "prövas om")."""
    sparr = asyncio.Semaphore(samtidigt)
    klara = 0

    async def en(rad: dict[str, Any], bolag: dict[str, Any] | None):
        nonlocal klara
        async with sparr:
            try:
                return await sok(rad, bolag, betald=betald)
            except Exception:  # noqa: BLE001 — en sajt får inte fälla resten
                logger.exception("Omprövningen föll för %s", rad.get("company_name"))
                return kandidat_ur_rad(rad, bolag), None
            finally:
                klara += 1
                if forlopp:
                    forlopp(klara, len(par))

    return await asyncio.gather(*(en(r, b) for r, b in par))


async def hamta_bolag(rad: dict[str, Any]) -> dict[str, Any] | None:
    """Registrets bolagssida för raden (cachad 30 dygn i sidhämtningen)."""
    from .sources import merinfo

    url = rad.get("source_url")
    if not url or "merinfo" not in str(rad.get("source_name") or url):
        return None
    try:
        md = await merinfo.hamta(url, fas="bolag")
    except Exception:  # noqa: BLE001
        logger.exception("Registersidan kunde inte hämtas för %s", rad.get("company_name"))
        return None
    return merinfo.tolka_bolag(md, url) if md else None
