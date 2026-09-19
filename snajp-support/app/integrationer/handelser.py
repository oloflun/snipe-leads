"""Händelser: kodutlösta anrop till kundens system (inte modellutlösta).

## Varför

"Integrera med ärendehanteringssystemet" betyder i praktiken oftast en sak:
när agenten lämnar över ska ärendet hamna där kundens människor redan
arbetar. Det kan vara Zendesk, Freshdesk, HubSpot eller ett eget system, och
det ska ske med hela samtalet, så att ingen behöver be kunden börja om. Det
är Ebbots överlämningslöfte, i kundens eget verktyg i stället för i vår
portal.

Det är inte ett beslut för modellen. När ett ärende eskalerar anropar koden
varje aktiv HTTP-integration som har en förfrågan bunden till händelsen
(`handelser: {"arende_eskalerat": "<förfrågans name>"}`), med mallvärden
koden själv fyller i (modell.HANDELSER).

## Aldrig på bekostnad av svaret

`skicka` kastar aldrig. Ett misslyckat anrop blir en rad i platform_events
(syns i admin), och kunden får sitt svar oavsett. Det är samma prioritering
som det prioriterade mejlet i support_agent: databasen är sanningen om att
ärendet eskalerat, allt annat är knuffar.

I testchatten simuleras anropen (de är skrivande per definition), så att en
administratör som provar agenten inte skapar ärenden i sin skarpa Zendesk.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from . import http_verktyg, lagring
from .hemligheter import IngenNyckelError, OlasbarHemlighetError
from .modell import HANDELSER, HttpKonfig, KonfigFel, las_konfig
from .resultat import Verktygsresultat

logger = logging.getLogger("snajp-support.integrationer.handelser")

#: Hur mycket av samtalet som följer med. Ett ärendesystem vill ha hela
#: samtalet, men ett samtal på hundratals repliker är inte ett ärende längre.
MAX_MEDDELANDEN = 60


async def samtalet(storage: Any, tenant_id: str, customer_id: str) -> list[dict[str, Any]]:
    """Kundens samtal, äldst först, över alla ärenden (varje chattmeddelande
    är ett eget ärende i vår modell, se support_agent._render_conversation)."""
    try:
        historik = await storage.get_customer_history(tenant_id, customer_id)
    except Exception:  # noqa: BLE001
        return []
    meddelanden: list[dict[str, Any]] = []
    for arende in reversed(historik):  # historiken är nyast först
        try:
            rader = await storage.get_messages(tenant_id, arende["conversation_id"])
        except Exception:  # noqa: BLE001
            continue
        for rad in rader:
            text = (rad.get("content") or "").strip()
            if not text:
                continue
            forfattare = rad.get("author")
            if rad.get("direction") == "inbound":
                fran = "kund"
            elif forfattare == "human":
                fran = "medarbetare"
            else:
                fran = "agent"
            meddelanden.append({"fran": fran, "text": text, "tid": rad.get("created_at")})
    return meddelanden[-MAX_MEDDELANDEN:]


def samtalstext(meddelanden: list[dict[str, Any]]) -> str:
    etikett = {"kund": "Kunden", "agent": "Agenten", "medarbetare": "Medarbetare"}
    return "\n".join(f"{etikett.get(m['fran'], m['fran'])}: {m['text']}" for m in meddelanden)


async def eskaleringsdata(
    storage: Any,
    tenant_id: str,
    *,
    customer_id: str,
    orsak: str | None,
    orsakskod: str | None,
    arendelank: str | None,
) -> dict[str, Any]:
    """`handelse.*`-värdena för arende_eskalerat (se modell.HANDELSER)."""
    meddelanden = await samtalet(storage, tenant_id, customer_id)
    senaste = next((m["text"] for m in reversed(meddelanden) if m["fran"] == "kund"), "")
    return {
        "orsak": orsak or "",
        "orsakskod": orsakskod or "",
        "samtal": samtalstext(meddelanden),
        "meddelanden": meddelanden,
        "senaste_meddelande": senaste,
        "arendelank": arendelank or "",
        "tidpunkt": datetime.now(timezone.utc).isoformat(),
    }


async def _logga_fel(storage: Any, tenant_id: str, handelse: str, integration: str, resultat: Verktygsresultat) -> None:
    try:
        await storage.log_platform_event(
            level="warning",
            source="integration",
            message=f"{integration}: {handelse} kunde inte skickas ({resultat.fel})"[:300],
            tenant_id=tenant_id,
            detail=resultat.for_logg(),
        )
    except Exception:  # noqa: BLE001 — eventloggning får inte fälla något
        logger.warning("kunde inte logga integrationsfelet till platform_events")


_pagaende: set[asyncio.Task[Any]] = set()


async def har_handelse(storage: Any, tenant_id: str, handelse: str) -> bool:
    """Har kunden någon aktiv förfrågan bunden till händelsen?

    Billig kontroll före `eskalering_i_bakgrunden`, så att en kund utan
    integrationer inte får en bakgrundstask per överlämning för ingenting.
    """
    try:
        rader = await lagring.lista(storage, tenant_id, bara_aktiva=True)
    except Exception:  # noqa: BLE001
        return False
    for rad in rader:
        if rad["typ"] == "http" and handelse in ((rad.get("konfig") or {}).get("handelser") or {}):
            return True
    return False


def eskalering_i_bakgrunden(
    storage: Any,
    tenant_id: str,
    *,
    kontext: dict[str, Any],
    customer_id: str,
    orsak: str | None,
    orsakskod: str | None,
    arendelank: str | None,
    is_test: bool,
) -> asyncio.Task[Any]:
    """arende_eskalerat utan att kunden väntar på det.

    Kundens svar är redan sparat när det här anropas; ett ärendesystem som
    svarar långsamt (15 s tidsgräns) ska inte bli kundens latens. Tasken hålls
    i en mängd tills den är klar, annars kan den skräpsamlas mitt i körningen.
    """

    async def kor() -> None:
        try:
            data = await eskaleringsdata(
                storage,
                tenant_id,
                customer_id=customer_id,
                orsak=orsak,
                orsakskod=orsakskod,
                arendelank=arendelank,
            )
            await skicka(storage, tenant_id, "arende_eskalerat", kontext=kontext, data=data, is_test=is_test)
        except Exception:  # noqa: BLE001 — skicka kastar inte, men datainsamlingen kan
            logger.exception("Eskaleringshändelsen kunde inte skickas (tenant %s)", tenant_id)

    task = asyncio.create_task(kor())
    _pagaende.add(task)
    task.add_done_callback(_pagaende.discard)
    return task


async def skicka(
    storage: Any,
    tenant_id: str,
    handelse: str,
    *,
    kontext: dict[str, Any],
    data: dict[str, Any],
    is_test: bool = False,
) -> list[Verktygsresultat]:
    """Kör varje aktiv förfrågan bunden till `handelse`. Kastar aldrig."""
    if handelse not in HANDELSER:
        raise ValueError(f"Okänd händelse {handelse!r}")  # programmeringsfel, inte driftfel
    try:
        rader = await lagring.lista(storage, tenant_id, bara_aktiva=True)
    except Exception:  # noqa: BLE001
        logger.exception("Kunde inte läsa integrationerna för händelsen %s", handelse)
        return []

    varden = dict(kontext)
    varden.update({f"handelse.{k}": v for k, v in data.items()})
    utfall: list[Verktygsresultat] = []
    for rad in rader:
        if rad["typ"] != "http":
            continue
        try:
            konfig = las_konfig("http", rad["konfig"])
            hemligheter = lagring.dekryptera_hemligheter(rad)
        except (KonfigFel, IngenNyckelError, OlasbarHemlighetError):
            continue
        assert isinstance(konfig, HttpKonfig)
        forfragan_namn = konfig.handelser.get(handelse)
        if not forfragan_namn:
            continue
        forfragan = next((r for r in konfig.requests if r.name == forfragan_namn), None)
        if forfragan is None:
            continue
        resultat = await http_verktyg.kor(
            forfragan,
            argument={},
            hemligheter=hemligheter,
            kontext=varden,
            simulera=is_test,
        )
        resultat.verktyg = f"{rad['namn']}:{handelse}"
        if not resultat.ok:
            await _logga_fel(storage, tenant_id, handelse, rad["namn"], resultat)
        utfall.append(resultat)
    return utfall
