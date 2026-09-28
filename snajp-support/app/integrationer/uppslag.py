"""Integrationsuppslaget i support-kedjan: modellen väljer, koden anropar.

## Var det sitter

Efter KB-sökningen och före research-steget i `run_support_agent`. Steget
körs BARA när tenanten har aktiva integrationer, och kostar då ett LLM-anrop
per runda. En tenant utan integrationer får exakt samma kedja som förut.
Stegordningstesterna (EXPECTED_ORDER_*) vilar på det.

## Samma princip som resten av kedjan

"Modellen resonerar, koden agerar" (support_agent.py). Modellen returnerar
JSON med vilka verktyg den vill anropa och med vilka argument, inget mer.
Koden:

  1. validerar verktygsnamnet mot katalogen (ett påhittat namn är ett fel,
     inte ett anrop),
  2. håller taken: högst tre anrop per runda, högst två rundor, högst ETT
     ändrande anrop per ärende,
  3. simulerar ändrande anrop i testchatten,
  4. kör anropen parallellt, och
  5. lämnar resultatet som opålitligt innehåll i användarposition. Svaren
     kommer från externa system och kan bära en promptinjektion.

## Faktakällan

Ett lyckat anrops data blir en tillåten faktakälla, precis som
kunskapsbasen. `Underlag.kallor` läggs till i faktagrindens underlag
(support_faktagrind.kontrollera, snipe-1fl), så att ett korrekt återgivet
leveransdatum inte fälls som ett påstående utan stöd.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ..agentcore.packs import PlaybookStep, RunLedger
from ..leads.untrusted_content import wrap_untrusted_content
from .katalog import Katalog, Verktyg, bygg_katalog
from .resultat import Verktygsresultat, kapa

logger = logging.getLogger("snajp-support.integrationer.uppslag")

MAX_RUNDOR = 2
MAX_ANROP_PER_RUNDA = 3
MAX_SKRIVANDE_PER_ARENDE = 1
#: Per anrop, i PROMPTEN (resultatet självt kan vara upp till 16 kB). Tre
#: anrop à 3 000 tecken är ungefär vad kunskapsbasblocket tar.
MAX_TECKEN_I_PROMPTEN = 3000

#: Den sanktionerade formen: befintlig skill + overlay (skill-låset,
#: INV-SKILL-005, gör en ny skill till ett baslinjebyte för varje kund).
#: cs:customer-research § 2 är skillens egen text om att söka i CRM och
#: supportplattform — exakt vad steget gör. Skopad, för att inte betala
#: 10 kB skilltext per runda för en lista med verktygsval.
INTEGRATIONSSTEG = PlaybookStep(
    skill="cs:customer-research",
    requires=("skill:cs:ticket-triage",),
    scope=("§ 2. Search Available Sources",),
    rationale=(
        "Steget väljer bara vilka av kundens system som ska frågas; skillens "
        "källordning (CRM, supportplattform) är det enda som gäller här."
    ),
    overlay="support-integrationsuppslag",
    temperature=0.0,
    condition="tenant_har_integrationer",
)

Steg = Callable[..., Awaitable[dict[str, Any]]]

#: Läggs till research-stegets uppgift när uppslaget gav något. Utan raden
#: bedömer steget bara kunskapsbasen, och en fråga som kundens system besvarat
#: ("var är min order?") blir en kunskapslucka och en överlämning.
RESEARCH_TILLAGG = (
    " Uppgifterna från kundens system räknas som underlag: kb_supports_answer "
    "ska vara true även när de (och inte kunskapsbasen) besvarar frågan."
)

#: Läggs till utkaststegets uppgift när uppslaget gav något.
UTKAST_TILLAGG = (
    " Uppgifterna från kundens system räknas som kunskapsbas i det här svaret: "
    "återge dem exakt. Misslyckades ett anrop, säg rakt ut att uppgiften inte går "
    "att hämta just nu i stället för att gissa, och påstå aldrig att en ändring "
    "är gjord om systemets svar inte visar det."
)


@dataclass
class Underlag:
    #: Klart att lägga i case_context (tom sträng = inget att tillföra).
    block: str = ""
    #: Rå data ur lyckade anrop, åt faktagrinden.
    kallor: list[str] = field(default_factory=list)
    #: En post per anrop, utan svarsdata (se Verktygsresultat.for_logg).
    logg: list[dict[str, Any]] = field(default_factory=list)
    #: Integrationer som inte gick att använda (trasig konfig, server nere).
    katalogfel: list[str] = field(default_factory=list)
    rundor: int = 0

    def __bool__(self) -> bool:
        return bool(self.block)


def _uppgift(runda: int) -> str:
    return (
        "Välj vilka av kundens system (verktygen i listan) som behöver frågas för "
        "att besvara ärendet, enligt reglerna ovan. Returnera JSON: "
        '"anrop" (lista med {"verktyg": exakt namn ur listan, "argument": objekt}, '
        f"högst {MAX_ANROP_PER_RUNDA}, tom lista om inget behövs), "
        '"klar" (bool, false bara om du behöver svaren för att välja ett anrop till), '
        '"motivering" (svenska, en mening). '
        # Uppmätt 2026-09-19 i development: "Which carrier is delivering it?"
        # efter ett ordersvar gav inget nytt uppslag ("transportören angavs
        # redan i föregående svar") och lämnades över, eftersom agentens egna
        # tidigare svar med flit aldrig räknas som källa.
        "Är meddelandet en följdfråga om något som kom ur kundens system, fråga "
        "systemet igen med identifierarna (ordernummer, kundnummer) ur samtalet: "
        "det du själv skrev i ett tidigare svar räknas inte som underlag nu."
        + (
            " Det här är runda 2: välj bara anrop som bygger på svaren nedan och inte "
            "redan är gjorda."
            if runda > 1
            else ""
        )
    )


def _normalisera_val(svar: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Modellens `anrop` som (namn, argument). Allt som inte har formen tappas."""
    ut: list[tuple[str, dict[str, Any]]] = []
    for post in svar.get("anrop") or []:
        if not isinstance(post, dict):
            continue
        namn = str(post.get("verktyg") or post.get("namn") or "").strip()
        argument = post.get("argument")
        if argument is None:
            argument = {}
        if not namn or not isinstance(argument, dict):
            continue
        ut.append((namn, argument))
    return ut


def _nyckel(namn: str, argument: dict[str, Any]) -> str:
    return f"{namn}:{json.dumps(argument, sort_keys=True, ensure_ascii=False, default=str)}"


def _block(resultat: list[Verktygsresultat]) -> str:
    poster = []
    for r in resultat:
        post = r.for_modellen()
        if "data" in post:
            post["data"] = kapa(str(post["data"]), MAX_TECKEN_I_PROMPTEN)
        poster.append(post)
    return (
        "## Uppgifter från kundens system\n"
        "Hämtade just nu ur kundens egna system. Lyckade svar är fakta om just "
        "den här kunden och får användas i svaret precis som kunskapsbasen. Ett "
        "misslyckat eller simulerat anrop betyder att uppgiften INTE är känd: säg "
        "det hellre än att gissa, och lova aldrig att en ändring är gjord om "
        "svaret inte visar det.\n\n"
        + wrap_untrusted_content(
            json.dumps(poster, ensure_ascii=False, indent=1), source="tenant:integration"
        )
    )


async def hamta(
    storage: Any,
    tenant_id: str,
    *,
    steg: Steg,
    ledger: RunLedger,
    trace: Any,
    case_context: str,
    kontext: dict[str, Any],
    is_test: bool,
    katalog: Katalog | None = None,
) -> Underlag:
    """Kör uppslaget. Kastar aldrig för integrationsfel.

    Ett fel i LLM-anropet självt (kvot, kreditslut) får däremot bubbla, precis
    som i kedjans andra steg: det är samma fel som skulle fälla nästa steg,
    och chat.py har redan den ärliga kundtexten för det.

    `kontext` är kodens egna värden för platshållarna (kund.email, arende.id
    …, se modell.KONTEXTNAMN).
    """
    if katalog is None:
        katalog = await bygg_katalog(storage, tenant_id)
    underlag = Underlag(katalogfel=list(katalog.fel))
    if not katalog:
        return underlag

    katalogtext = wrap_untrusted_content(katalog.som_text(), source="tenant:integration-katalog")
    resultat: list[Verktygsresultat] = []
    gjorda: set[str] = set()
    skrivande_gjorda = 0

    for runda in range(1, MAX_RUNDOR + 1):
        tidigare = (
            "\n\n## Svar från rundan före\n"
            + wrap_untrusted_content(
                json.dumps([r.for_modellen() for r in resultat], ensure_ascii=False, indent=1),
                source="tenant:integration",
            )
            if resultat
            else ""
        )
        svar = await steg(
            INTEGRATIONSSTEG,
            ledger,
            trace,
            task=_uppgift(runda),
            case_context=(
                f"{case_context}\n\n## Tillgängliga verktyg i kundens system\n{katalogtext}{tidigare}"
            ),
        )
        underlag.rundor = runda

        att_kora: list[tuple[Verktyg, dict[str, Any]]] = []
        nekade: list[Verktygsresultat] = []
        for namn, argument in _normalisera_val(svar)[:MAX_ANROP_PER_RUNDA]:
            verktyg = katalog.hitta(namn)
            if verktyg is None:
                nekade.append(Verktygsresultat(verktyg=namn, ok=False, fel="Verktyget finns inte."))
                continue
            nyckel = _nyckel(namn, argument)
            if nyckel in gjorda:
                continue
            gjorda.add(nyckel)
            if verktyg.skrivande:
                if skrivande_gjorda >= MAX_SKRIVANDE_PER_ARENDE:
                    nekade.append(
                        Verktygsresultat(
                            verktyg=namn,
                            ok=False,
                            skrivande=True,
                            fel="Högst en ändring per ärende görs automatiskt. Resten tar en kollega.",
                        )
                    )
                    continue
                skrivande_gjorda += 1
            att_kora.append((verktyg, argument))

        if att_kora:
            nya = await asyncio.gather(
                *(v.kor(argument, kontext, is_test) for v, argument in att_kora),
                return_exceptions=True,
            )
            for (verktyg, _), utfall in zip(att_kora, nya):
                if isinstance(utfall, BaseException):
                    # kor() kastar inte enligt kontraktet — hamnar vi här är
                    # det en bugg, och den ska synas i loggen men inte fälla
                    # kundens svar.
                    logger.error("Verktyget %s kastade: %r", verktyg.namn, utfall)
                    utfall = Verktygsresultat(
                        verktyg=verktyg.namn, ok=False, skrivande=verktyg.skrivande,
                        fel="Anropet gick inte att genomföra.",
                    )
                resultat.append(utfall)
        resultat.extend(nekade)

        if svar.get("klar", True) is not False or not att_kora:
            break

    if resultat:
        underlag.block = _block(resultat)
        underlag.kallor = [r.data for r in resultat if r.ok and not r.simulerad and r.data]
        underlag.logg = [r.for_logg() for r in resultat]
    return underlag


def kontextvarden(
    *,
    kund_email: str | None,
    kund_namn: str | None,
    kund_telefon: str | None = None,
    kund_id: str | None,
    arende_id: str | None,
    kategori: str | None,
    kanal: str | None,
    tenant_namn: str | None,
) -> dict[str, Any]:
    """Platshållarnas kontextvärden ur ärendet (modell.KONTEXTNAMN)."""
    return {
        "kund.email": kund_email,
        "kund.namn": kund_namn,
        "kund.telefon": kund_telefon,
        "kund.id": kund_id,
        "arende.id": arende_id,
        "arende.kategori": kategori,
        "kanal": kanal,
        "tenant.namn": tenant_namn,
    }
