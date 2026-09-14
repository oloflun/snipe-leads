"""Vad som krävs för att flytta ett prospekt från 'test'/'example' till 'manual'.

## Varför en egen, ren funktion

Kontrollen behövs på två ställen: endpointen
`POST /api/leads/prospects/{id}/befordra` (app/api/leads.py) och skriptet som
kopierar demo-prospekt till ett riktigt konto
(scripts/konvertera_testkund.py --prospekt). Skriver man kontrollen två gånger
är det två tillfällen att skriva den olika — och det är precis den sortens
glapp som gör att ett påhittat exempelbolag slinker igenom det ena stället
fast det stoppas i det andra.

Funktionen tar bara emot de fält den behöver, ingen databas och ingen
tenant-koppling. Skriptet kör mot psycopg2-rader, endpointen mot
storage-dictar — båda har orgnr/website/contact_email som strängar, och det
är allt den här funktionen frågar efter.
"""

from __future__ import annotations

import re

from .orgnr import OgiltigtOrgnrError, validera_format

#: RFC 2606: reserverade toppdomäner som aldrig kan gå att registrera på
#: riktigt. exempelbolag.py bygger alla sina webbplatser under `.example`
#: (se _webbplats där); `.invalid` och `.test` läggs till här av samma skäl
#: även om ingen kodväg genererar dem i dag — en importerad rad skulle kunna
#: bära dem, och kontrollen ska stoppa dem också.
_RESERVERADE_TOPPDOMANER = (".example", ".invalid", ".test")

#: Enkel adressform, inte en fullständig RFC 5322-parser. Syftet är att fånga
#: ett tomt eller uppenbart trasigt fält, inte att avgöra om adressen faktiskt
#: tar emot post (det gör mejlservern vid själva sändningen).
_EPOST_MONSTER = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _webbplats_ar_exempel(webbplats: str) -> bool:
    stam = webbplats.strip().lower().rstrip("/")
    for prefix in ("https://", "http://"):
        if stam.startswith(prefix):
            stam = stam[len(prefix):]
    return any(stam.endswith(toppdoman) for toppdoman in _RESERVERADE_TOPPDOMANER)


def saknade_falt(
    *, orgnr: str | None, website: str | None, contact_email: str | None
) -> list[str]:
    """Listan över vad som saknas för att prospektet ska få bli 'manual'.

    Tom lista betyder godkänt. Var sträng beskriver EN brist och är skriven
    för att visas direkt för kunden, inte för en logg.
    """
    brister: list[str] = []

    try:
        validera_format(orgnr)
    except OgiltigtOrgnrError:
        brister.append(
            "Organisationsnummer saknas eller är ogiltigt. Ange ett riktigt "
            "org.nr, till exempel 556824-9022."
        )

    webbplats = (website or "").strip()
    if not webbplats or _webbplats_ar_exempel(webbplats):
        brister.append(
            "Webbplatsen saknas eller är en exempeladress (t.ex. .example). "
            "Ange bolagets riktiga webbplats."
        )

    epost = (contact_email or "").strip()
    if not epost or not _EPOST_MONSTER.match(epost):
        brister.append("E-postadress saknas eller ser inte ut som en giltig adress.")

    return brister
