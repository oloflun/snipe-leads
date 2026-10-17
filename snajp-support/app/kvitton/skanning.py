"""Skanningen — från inkorg till sparade kvitton, med dublettkontroll.

## Kedjan, i ordning

    hämta mejl → är det en kvittokandidat? → har vi läst just det mejlet?
    → kvittohanteraren läser det utifrån grundprompten (`hanterare.hantera`)
    → ett bk_underlag per underlag i mejlet → kasta mejlet

Mejlets INNEHÅLL sparas aldrig: precis som uppladdningsvägen
(`bookkeeping/underlag.py`) skrivs de avlästa fälten plus ett fingeravtryck,
och texten och bilagorna släpps när anropet är klart. Ett mejl vi inte har
är ett mejl som inte kan läcka.

## Dubbletterna — två spärrar, olika hårda

1. FINGERAVTRYCKET (hårt nej): sha256 över kontots adress + mejlets id.
   Samma mejl skannat två gånger blir aldrig två kvitton — det hoppas över
   utan kostnad, före varje modellanrop. Ett mejl som lästs men inte gav
   något underlag minns i `kvitto_mejl_lasta` (migration 096) av samma skäl.
2. INNEHÅLLET (mjuk flagga): grundpromptens avsnitt 7 — samma leverantör och
   dokumentnummer, eller samma belopp inom 3 dagar — prövas av
   `granskning.verifiera` mot ALLA tidigare underlag. Flaggan ger
   granskning, aldrig ett tyst kast: en människa avgör.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .hanterare import Inkommande, anvand_deterministisk, hantera, spara
from .mejl import Mejlkonto
from .systemprompt import hamta_profil
from .tolkning import ar_kvittokandidat


def mejlfingeravtryck(kontoadress: str, mejl_id: str) -> str:
    return hashlib.sha256(f"mejl:{kontoadress}:{mejl_id}".encode()).hexdigest()


@dataclass
class Skanningsresultat:
    """Vad en körning gjorde, mejl för mejl — indata till inkorgsvyn."""

    genomlasta: int = 0
    nya_kvitton: int = 0
    hoppade_dubbletter: int = 0
    handelser: list[dict[str, Any]] = field(default_factory=list)
    #: Modellens steg över hela skanningen, för agent_runs-loggen.
    steg: list[dict[str, Any]] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0


# Bakåtkompatibelt namn — äldre tester och skript importerade det härifrån.
_anvand_deterministisk = anvand_deterministisk


async def skanna_inkorg(
    storage: Any, tenant_id: str, konto: Mejlkonto, *, max_antal: int = 50
) -> Skanningsresultat:
    """Hela kedjan. Returnerar en händelse per genomläst mejl, i inkorgens
    ordning, så att gränssnittet kan visa exakt vad agenten gjorde."""
    resultat = Skanningsresultat()
    mejlen = await konto.hamta_mejl(max_antal=max_antal)
    profil = await hamta_profil(storage, tenant_id)

    for mejl in mejlen:
        resultat.genomlasta += 1
        handelse: dict[str, Any] = {
            "mejl_id": mejl.id,
            "avsandare": mejl.avsandare,
            "amne": mejl.amne,
            "datum": mejl.datum,
        }

        if not ar_kvittokandidat(mejl):
            handelse["utfall"] = "ej_kvitto"
            resultat.handelser.append(handelse)
            continue

        fingeravtryck = mejlfingeravtryck(konto.adress, mejl.id)
        if await storage.get_bk_underlag_by_sha256(
            tenant_id, fingeravtryck
        ) is not None or await storage.ar_kvittomejl_last(tenant_id, fingeravtryck):
            handelse["utfall"] = "redan_last"
            resultat.hoppade_dubbletter += 1
            resultat.handelser.append(handelse)
            continue

        hantering = await hantera(
            storage, tenant_id, Inkommande.fran_mejl(mejl), konto=konto, profil=profil
        )
        resultat.tokens_in += hantering.trace.total_tokens_in
        resultat.tokens_out += hantering.trace.total_tokens_out
        resultat.steg.append(
            {
                "mejl_id": mejl.id,
                "klass": hantering.resultat["klass"],
                "underlag": len(hantering.resultat["underlag"]),
                "verktyg": hantering.verktygsanrop,
                "steg": hantering.trace.skills_used,
            }
        )
        handelse["klass"] = hantering.resultat["klass"]

        underlagen = hantering.resultat["underlag"]
        if not underlagen:
            await storage.markera_kvittomejl_last(
                tenant_id, fingeravtryck, klass=hantering.resultat["klass"]
            )
            handelse["utfall"] = "ej_kvitto"
            resultat.handelser.append(handelse)
            continue

        avsandare = f"{mejl.avsandare} <{mejl.avsandaradress}>".strip()
        sparade = []
        for nr, u in enumerate(underlagen):
            # Första underlaget bär mejlets fingeravtryck (det spärren ovan
            # frågar efter); fler underlag i samma mejl får ett eget.
            sha = fingeravtryck if nr == 0 else mejlfingeravtryck(konto.adress, f"{mejl.id}#{nr + 1}")
            sparade.append(
                await spara(
                    storage,
                    tenant_id,
                    u,
                    hantering.resultat,
                    sha256=sha,
                    filnamn=mejl.amne or "kvittomejl",
                    mimetyp="message/rfc822",
                    kalla="mejl",
                    mejl_id=mejl.id,
                    mejl_amne=mejl.amne,
                    mejl_avsandare=avsandare,
                    reservdatum=mejl.datum,
                )
            )
        resultat.nya_kvitton += len(sparade)

        forsta = sparade[0]
        rad = forsta.rad
        handelse["utfall"] = "kvitto" if forsta.status == "klar" else "kvitto_granska"
        handelse["kvitto_id"] = rad["id"]
        handelse["belopp"] = None if rad.get("brutto") is None else f"{rad['brutto']:f}"
        handelse["belopp_original"] = rad.get("belopp_original")
        handelse["kategori"] = rad.get("kategori")
        handelse["motpart"] = rad.get("motpart")
        handelse["status"] = forsta.status
        handelse["granskningsstatus"] = forsta.granskningsstatus
        handelse["flaggor"] = (rad.get("granskning") or {}).get("flaggor") or []
        handelse["antal_underlag"] = len(sparade)
        resultat.handelser.append(handelse)

    return resultat
