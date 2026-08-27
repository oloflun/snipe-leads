"""Sändvägen för supportsvar — godkända utkast och autosvar.

Fram till 2026-08-28 fanns ingen: `drafts.py` satte mejlets status till `sent`
och loggade "Utskick simulerat", och kunden såg "skickat" på ett svar som
aldrig lämnade databasen. Den här modulen är den enda platsen som får avgöra
om ett supportsvar faktiskt skickas, och dess kontrakt är att ALDRIG låta
"skickat" vara en lögn:

  * Skickas mejlet på riktigt returneras en notering som säger det.
  * Skickas det inte (simulering, torrkörning, testmejl) returneras en
    notering som säger DET — statusflödet får fortsätta, för i de lägena är
    simuleringen avsiktlig och känd.
  * MISSLYCKAS en riktig sändning kastas `SandningsFel`, och anroparen får
    inte sätta någon status alls. Godkännandevägen översätter till 502;
    autosvarsvägen faller ned till ett vanligt utkast i granskningskön.

## Varför testmejl aldrig skickas

"Hämta testmail" skriver ärenden med påhittade men VERKLIGA adresser
(anna.lindqvist@mail.se — mail.se är en riktig domän). Raderna är märkta
`provider='mock'` av connectorn, och den märkningen är spärren: ett godkänt
testärende övar granskningsflödet, det mejlar inte en främling.

## Avsändaridentiteten

Samma globala konto som leads-utskicken (SMTP_* i config, ETT konto i v1).
Det betyder att svaret INTE kommer från tenantens egen supportadress — tråden
i kundens mejlklient bryts. Det är en känd v1-begränsning, dokumenterad i
stället för gömd: per-tenant-avsändare kräver credentials som inte är
modellerade än (samma Del F-lucka som send_provider.py beskriver).
"""

from __future__ import annotations

import logging
from typing import Any

from ..leads.send_provider import SendProvider, get_send_provider

logger = logging.getLogger("snajp-support.sender")

#: Noteringarna som hamnar i beslutsloggen. Konstanter för att tester och
#: läsare ska kunna skilja lägena åt utan att tolka fritext.
NOT_SIMULERAT = "Utskick simulerat — ingen SMTP-konfiguration i den här miljön."
NOT_TESTMEJL = "Testmejl (provider=mock) — skickas aldrig till mottagaradressen."
NOT_MOTTAGARE_SAKNAS = "Mejlraden saknar avsändaradress — inget kunde skickas."


class SandningsFel(RuntimeError):
    """En RIKTIG sändning misslyckades. Anroparen får inte markera något som
    skickat — det är hela skillnaden mot noteringarna ovan."""


def _svarsamne(amne: str | None) -> str:
    text = (amne or "").strip()
    if not text:
        return "Re: ert ärende"
    # Ett "Re: Re: Re:" ser maskinellt ut; ett enda prefix räcker.
    return text if text.lower().startswith("re:") else f"Re: {text}"


async def skicka_supportsvar(
    email: dict[str, Any] | None,
    *,
    content: str,
    provider: SendProvider | None = None,
) -> str:
    """Skicka ett supportsvar till mejlets avsändare, om det ska skickas.

    Returnerar noteringen för beslutsloggen. Kastar `SandningsFel` enbart när
    en riktig sändning försöktes och misslyckades.
    """
    provider = provider or get_send_provider()

    if email is None or not (email.get("from_email") or "").strip():
        # Ingen mottagare är inte ett sändfel — det är en rad som inte GÅR att
        # svara på per mejl. Godkännandet ska ändå kunna slutföras (svaret
        # ligger i konversationen), men loggen ska säga sanningen.
        logger.warning("Supportsvar utan mottagaradress — inget skickas.")
        return NOT_MOTTAGARE_SAKNAS

    if (email.get("provider") or "") == "mock":
        return NOT_TESTMEJL

    if not provider.levererar:
        return NOT_SIMULERAT

    mottagare = str(email["from_email"]).strip()
    amne = _svarsamne(email.get("subject"))
    try:
        await provider.send(to=mottagare, subject=amne, body=content)
    except Exception as fel:
        # Loggen får detaljerna; anroparen får ett svenskt besked utan
        # serverns interna feltext (den kan bära adresser och kontonamn).
        logger.exception("Supportsvar till %s kunde inte skickas.", mottagare)
        raise SandningsFel(
            "Svaret kunde inte skickas — ingenting har markerats som skickat. "
            "Försök igen om en stund."
        ) from fel

    return f"Skickat till {mottagare} via SMTP."


__all__ = [
    "NOT_MOTTAGARE_SAKNAS",
    "NOT_SIMULERAT",
    "NOT_TESTMEJL",
    "SandningsFel",
    "skicka_supportsvar",
]
