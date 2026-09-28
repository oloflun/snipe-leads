"""Flaggan "rollkopplingen är oklar" — underlag för intresseavvägningen.

## Varför den finns

Den rättsliga grunden för att kontakta en person i ett kallmejl är
berättigat intresse, och intresseavvägningen (docs/intresseavvagning_kallmejl.md)
lutar sig mot att kontakten sker i personens YRKESROLL. En namngiven person
utan känd yrkesroll är därmed en svagare grund — inte nödvändigtvis fel, men
något en människa ska kunna hitta och bedöma i efterhand.

Flaggan är en LÄSTIDSHÄRLEDNING ur fält som redan finns (`contact_name`,
`contact_role`, adresstypen) och lagras inte: en lagrad kopia av en härledning
glider isär med sina källfält, och den här ska aldrig kunna visa något annat
än vad raden faktiskt säger. Själva BEDÖMNINGEN byggs medvetet inte i kod —
beställningen 2026-09-20 var flaggning som underlag, inte en automatiserad
intresseavvägning.

## Vad som flaggas

En rad flaggas när det finns en PERSON i den (namngiven kontakt eller en
personlig mejladress i formen fornamn.efternamn@) men ingen yrkesroll är
belagd. Funktionsadresser utan namn (info@, kundtjanst@) flaggas inte — där
kontaktas en funktion, inte en identifierbar person, och det är just
personkopplingen som gör rollfrågan juridiskt intressant.
"""

from __future__ import annotations

from typing import Any

from .sources.base import Prospect


def rollkoppling_oklar(rad: dict[str, Any]) -> bool:
    """True när raden bär en person utan belagd yrkesroll."""
    roll = str(rad.get("contact_role") or "").strip()
    if roll:
        return False
    namngiven = bool(str(rad.get("contact_name") or "").strip())
    epost = str(rad.get("contact_email") or "").strip()
    personlig_adress = bool(
        epost and Prospect(company_name="", contact_email=epost).epost_ar_personlig
    )
    return namngiven or personlig_adress


def med_rollflagga(rad: dict[str, Any]) -> dict[str, Any]:
    """Raden plus flaggan, utan att röra originalet."""
    return {**rad, "rollkoppling_oklar": rollkoppling_oklar(rad)}
