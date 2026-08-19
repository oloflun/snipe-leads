"""Exempelbolag: påhittade företag som passar kundens ICP.

## Varför de finns

`POST /api/leads/runs/batch` svarar 422 med "Inga prospekt att köra på" när
tenanten är tom. Det är korrekt men obrukbart som svar på en knapp som heter
*Starta körning*: en ny kund har per definition noll prospekt, och den enda
vägen framåt var att lägga in bolag för hand innan de sett agenten göra
någonting. Det är fel ordning — man vill se produkten arbeta innan man matar
den.

Exempelbolagen är därför en väg IN i produkten, inte en produkt i sig.

## Varför de genereras utan LLM

Modulen är ren och deterministisk. Två skäl, båda praktiska:

 1. Leads-ytorna kräver annars en riktig nyckel (`_require_live_llm`), och i
    simuleringsläge — vilket dev ofta står i — hade knappen svarat 503. En
    demonstrationsfunktion som bara fungerar när allt annat redan fungerar
    demonstrerar ingenting.
 2. Ett påhittat bolagsnamn ur en språkmodell kan råka vara ett RIKTIGT bolag.
    Namnen här byggs av ett ledord ur branschen plus ett suffix ur en fast
    lista, och märks dessutom `origin='example'` i databasen.

## Varför de aldrig kan mejlas

Raden får `origin = 'example'` (migration 039) och saknar mottagaradress.
`scheduler._kor_send_guard` slår upp origin och blockerar innan provider.send()
— alltså på samma ställe som de sex spärrarna, inte i UI:t. Ett exempelbolag
som mejlas är ett mejl till en adress som inte finns, i bästa fall; i värsta
fall till ett riktigt bolag med samma namn.
"""

from __future__ import annotations

import hashlib
from typing import Any

#: Namndelar. Sammansättningarna ska låta som svenska bolag men inte träffa
#: ett verkligt: därför ett neutralt ortsled + ett branschled + bolagsform.
_LED = (
    "Nord",
    "Väst",
    "Syd",
    "Öst",
    "Bergs",
    "Sjö",
    "Ek",
    "Lund",
    "Vik",
    "Hammar",
    "Alm",
    "Gran",
)

_EFTERLED = ("vik", "berg", "strand", "haga", "backe", "näs", "lid", "sund")

_BOLAGSFORM = ("AB", "Gruppen AB", "& Partner AB", "Sverige AB")

#: Fallback när ICP:t inte säger något om bransch. Medvetet breda svenska
#: SMB-branscher — det är den kundtyp produkten säljs till.
_DEFAULT_BRANSCHER = ("Bygg", "Tillverkning", "Logistik", "Fastighet", "Installation")

_DEFAULT_ROLLER = ("VD", "Inköpschef", "Platschef", "Marknadschef")


def _tal(fro: str, mod: int) -> int:
    """Deterministiskt heltal ur en sträng. Samma ICP ger samma lista igen."""
    return int(hashlib.sha256(fro.encode("utf-8")).hexdigest()[:8], 16) % mod


def _forsta(varde: Any, fallback: tuple[str, ...], index: int) -> str:
    if isinstance(varde, list) and varde:
        return str(varde[index % len(varde)]).strip() or fallback[index % len(fallback)]
    return fallback[index % len(fallback)]


def bygg_exempelbolag(icp: dict[str, Any] | None, *, antal: int) -> list[dict[str, str]]:
    """Bygger `antal` exempelbolag som ligger inom ICP:t.

    Returnerar dictar med `company_name`, `contact_name` och en `motivering`
    som förklarar VARFÖR bolaget passar — samma fråga en riktig kund kommer att
    ställa om ett riktigt prospekt, och den ska gå att svara på även här.
    """
    icp = icp or {}
    branscher = icp.get("industries") or list(_DEFAULT_BRANSCHER)
    geografi = icp.get("geography") or []
    roller = icp.get("roles") or list(_DEFAULT_ROLLER)
    storlek = icp.get("company_size") or {}
    min_anst = storlek.get("min")
    max_anst = storlek.get("max")

    bolag: list[dict[str, str]] = []
    for i in range(max(antal, 0)):
        bransch = _forsta(branscher, _DEFAULT_BRANSCHER, i)
        roll = _forsta(roller, _DEFAULT_ROLLER, i)
        ort = _forsta(geografi, ("Sverige",), i)

        fro = f"{bransch}|{ort}|{i}"
        namn = (
            f"{_LED[_tal(fro + 'a', len(_LED))]}"
            f"{_EFTERLED[_tal(fro + 'b', len(_EFTERLED))]} "
            f"{bransch.split()[0].capitalize()} "
            f"{_BOLAGSFORM[_tal(fro + 'c', len(_BOLAGSFORM))]}"
        )

        storleksrad = ""
        if min_anst is not None or max_anst is not None:
            storleksrad = f", {min_anst or 1}–{max_anst or 49} anställda"

        bolag.append(
            {
                "company_name": namn,
                "contact_name": roll,
                "motivering": (
                    f"Exempelbolag: {bransch.lower()} i {ort}{storleksrad}. "
                    f"Beslutsfattaren agenten skulle leta efter är {roll.lower()}. "
                    "Bolaget är påhittat och kan aldrig kontaktas."
                ),
            }
        )
    return bolag
