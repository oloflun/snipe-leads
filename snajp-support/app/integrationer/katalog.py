"""Verktygskatalogen: en tenants aktiva integrationer som körbara verktyg.

Katalogen är det modellen får VÄLJA ur. Den får aldrig något mer: inga URL:er,
inga rubriker, inga hemligheter — bara namn, beskrivning och argumentschema.
Resten ligger bakom `Verktyg.kor`, som koden anropar.

En trasig integration (ogiltig konfig, oläsbar hemlighet, MCP-server nere)
hoppas över med ett felbesked i `Katalog.fel`. Den ska aldrig fälla ett ärende
— kunden får då ett svar ur kunskapsbasen som om integrationen inte fanns,
och felet syns i spårloggen och i portalens provkörning.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from . import http_verktyg, lagring, mcp_klient
from .hemligheter import IngenNyckelError, OlasbarHemlighetError
from .modell import HttpKonfig, KonfigFel, McpKonfig, las_konfig, slug
from .resultat import Verktygsresultat

logger = logging.getLogger("snajp-support.integrationer.katalog")

#: (argument, kontext, simulera) -> resultat
Korare = Callable[[dict[str, Any] | None, dict[str, Any], bool], Awaitable[Verktygsresultat]]


@dataclass
class Verktyg:
    namn: str
    beskrivning: str
    parametrar: dict[str, Any]
    skrivande: bool
    integration_id: str
    integration_namn: str
    typ: str
    kor: Korare = field(repr=False)

    def for_modellen(self) -> dict[str, Any]:
        return {
            "namn": self.namn,
            "beskrivning": self.beskrivning,
            "system": self.integration_namn,
            "argument": self.parametrar,
            "andrar_data": self.skrivande,
        }


@dataclass
class Katalog:
    verktyg: list[Verktyg] = field(default_factory=list)
    fel: list[str] = field(default_factory=list)

    def hitta(self, namn: str) -> Verktyg | None:
        return next((v for v in self.verktyg if v.namn == namn), None)

    def __bool__(self) -> bool:
        return bool(self.verktyg)

    def som_text(self) -> str:
        return json.dumps([v.for_modellen() for v in self.verktyg], ensure_ascii=False, indent=1)


def _unikt(namn: str, tagna: set[str]) -> str:
    namn = namn[:64]
    if namn not in tagna:
        return namn
    for i in range(2, 100):
        kandidat = f"{namn[:60]}_{i}"
        if kandidat not in tagna:
            return kandidat
    raise RuntimeError("för många verktyg med samma namn")  # pragma: no cover


def _http_korare(forfragan: Any, hemligheter: dict[str, str], verktygsnamn: str) -> Korare:
    async def kor(argument: dict[str, Any] | None, kontext: dict[str, Any], simulera: bool) -> Verktygsresultat:
        resultat = await http_verktyg.kor(
            forfragan, argument=argument, hemligheter=hemligheter, kontext=kontext, simulera=simulera
        )
        resultat.verktyg = verktygsnamn
        return resultat

    return kor


def _mcp_korare(
    konfig: McpKonfig, hemligheter: dict[str, str], verktygsnamn: str, serverns_namn: str, skrivande: bool
) -> Korare:
    async def kor(argument: dict[str, Any] | None, kontext: dict[str, Any], simulera: bool) -> Verktygsresultat:
        return await mcp_klient.anropa_verktyg(
            konfig,
            hemligheter,
            verktygsnamn=verktygsnamn,
            serverns_namn=serverns_namn,
            argument=argument,
            skrivande=skrivande,
            simulera=simulera,
        )

    return kor


def mcp_verktyget_tillats(konfig: McpKonfig, verktyg: mcp_klient.McpVerktyg) -> bool:
    """Tom tillåtelselista = allt utom det servern själv märker destruktivt."""
    if konfig.tillatna_verktyg:
        return verktyg.namn in konfig.tillatna_verktyg
    return verktyg.destruktivt is not True


def mcp_verktyget_skriver(konfig: McpKonfig, verktyg: mcp_klient.McpVerktyg) -> bool:
    """Skrivande om admin säger det, eller om servern själv säger att verktyget
    inte är skrivskyddat. Omärkt räknas som läsande — de flesta servrar märker
    inte sina läsverktyg, och att simulera dem i testchatten gjorde testchatten
    oanvändbar för just det den ska visa."""
    return (
        verktyg.namn in konfig.skrivande_verktyg
        or verktyg.skrivskyddat is False
        or verktyg.destruktivt is True
    )


async def bygg_katalog(storage: Any, tenant_id: str) -> Katalog:
    katalog = Katalog()
    try:
        rader = await lagring.lista(storage, tenant_id, bara_aktiva=True)
    except Exception:  # noqa: BLE001 — en trasig läsning får inte fälla ärendet
        logger.exception("Kunde inte läsa integrationerna för %s", tenant_id)
        katalog.fel.append("Integrationerna gick inte att läsa.")
        return katalog

    tagna: set[str] = set()
    for rad in rader:
        namn = rad["namn"]
        try:
            konfig = las_konfig(rad["typ"], rad["konfig"])
            hemligheter = lagring.dekryptera_hemligheter(rad)
        except KonfigFel as fel:
            katalog.fel.append(f"{namn}: ogiltig konfiguration ({fel})")
            continue
        except (IngenNyckelError, OlasbarHemlighetError) as fel:
            katalog.fel.append(f"{namn}: {fel}")
            continue

        if isinstance(konfig, HttpKonfig):
            for forfragan in konfig.verktygsforfragningar():
                verktygsnamn = _unikt(forfragan.verktygsnamn, tagna)
                tagna.add(verktygsnamn)
                katalog.verktyg.append(
                    Verktyg(
                        namn=verktygsnamn,
                        beskrivning=forfragan.description or forfragan.name,
                        parametrar=forfragan.json_schema(set(hemligheter)),
                        skrivande=forfragan.ar_skrivande,
                        integration_id=rad["id"],
                        integration_namn=namn,
                        typ="http",
                        kor=_http_korare(forfragan, hemligheter, verktygsnamn),
                    )
                )
            continue

        try:
            serverns = await mcp_klient.lista_verktyg_cachat(
                f"{rad['id']}:{rad.get('updated_at')}", konfig, hemligheter
            )
        except mcp_klient.McpFel as fel:
            katalog.fel.append(f"{namn}: {fel}")
            continue
        for mv in serverns:
            if not mcp_verktyget_tillats(konfig, mv):
                continue
            verktygsnamn = _unikt(f"mcp_{slug(namn, max_langd=20)}_{mv.namn}", tagna)
            tagna.add(verktygsnamn)
            skrivande = mcp_verktyget_skriver(konfig, mv)
            katalog.verktyg.append(
                Verktyg(
                    namn=verktygsnamn,
                    beskrivning=mv.beskrivning,
                    parametrar=mv.schema,
                    skrivande=skrivande,
                    integration_id=rad["id"],
                    integration_namn=namn,
                    typ="mcp",
                    kor=_mcp_korare(konfig, hemligheter, verktygsnamn, mv.namn, skrivande),
                )
            )
    return katalog
