"""Utkast till listspårets bolag ("Utan webbplats") — ett generellt erbjudande.

## Varför den här vägen finns

Antons regel 8 (CLAUDE.md, 2026-10-05): bolag som inte blir Iris-leads (utan
webbplats, parkerad domän, ingen kontaktmejl på sajten) kastas inte, utan
hamnar i körningens lista "Utan webbplats" för utkast med ett mer generellt
erbjudande. Ingen dyr research körs på dem. Sebbe 2026-10-07: "Bygg utkast
till listan Utan webbplats också".

Iris utkastkedja (run_outreach_draft) går inte att återanvända: den kräver
citat ur bolagets egen sajt (underlagsgolvet) och faktagrinden fäller allt
som inte står i researchen. Här finns ingen sajt. Därför ett eget, billigt
steg: ETT modellanrop per bolag, byggt på det registret vet (namn, ort,
bransch) och kundens erbjudande, med svenska humanizern i samma anrop.

## Vad mejlet får säga

- Hälsningen är alltid "Hej," — registrets personer blir aldrig ett leads
  kontakt (regel 1), så inget namn.
- Bolaget kallas "ni". Ingenting påstås om bolaget utöver registerfakta.
- Kundens erbjudande i en eller två meningar, en låg-friktions-uppmaning.
- Ingen signatur och ingen avregistreringsrad: de läggs på i kod när utkastet
  köas (leads_tools._queue_outreach_draft_impl), när en adress finns.

## När skickas det

Utkastet sparas på listraden (lead_list_items.utkast, migration 106). Det
köas först när kunden lagt in en mejladress som tillhör VD (regel 5) — då
med signatur, logga och lagstadgad fot, och via granskningskön som alla
andra utkast.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..config import get_settings
from .tilltal import kortnamn

logger = logging.getLogger("snajp-support.listutkast")

#: Variantnamnet språkgrinden kräver. Sant här: humanizer-svenska SKILL.md
#: ligger i samma anrop som skrivningen (se _systemprompt).
HUMANIZER = "snajp:humanizer-svenska"

_UPPDRAG = """Du skriver ett kort, kallt första mejl på svenska från {avsandare} till ett litet svenskt bolag.

Bolaget har ingen webbplats som säger något om dem. Allt du vet står under "Bolaget" nedan, och det är det ENDA du får påstå om dem. Erbjudandet står under "Erbjudandet"; det är det enda du får påstå om {avsandare}.

Regler:
- Inled med exakt "Hej," på egen rad. Inget namn.
- Tilltala bolaget med "ni" och "er" genomgående, även i uppmaningen ("Hör av er").
- Nämn bolagets namn högst en gång, utan bolagsform (AB).
- 45–80 ord i brödtexten. Ren text, inga listor, ingen markdown.
- Välj EN sak ur erbjudandet, den som rimligast hjälper ett bolag i deras bransch och storlek. Räkna aldrig upp flera produkter eller funktioner.
- Struktur: öppna med en konkret, vardaglig fråga eller iakttagelse om hur det brukar se ut i deras typ av verksamhet (till exempel var nya kunder kommer ifrån, eller mejlen som ska besvaras efter arbetsdagen), utan att påstå något om just dem; sedan EN till två meningar om den valda saken; sist EN låg-friktions-uppmaning (ett kort samtal eller ett exempel).
- Förbjudna fraser: "förenkla er vardag", "effektivitet", "avgörande", "stor skillnad", "frigöra tid", "i dagens", "vi på {avsandare}", "Till er som". Inga allmänna påståenden om branschen.
- Hitta aldrig på kunder, case, siffror, resultat eller något om bolaget.
- Avsluta med "Vänliga hälsningar," på egen rad. Ingen signatur, inget namn, ingen avregistreringsrad: de läggs på automatiskt.
- Ämnesraden: kort och konkret, med bolagets namn eller ort, utan utropstecken. Aldrig produktkategorin ("AI-agenter", "AI för …") som ämne.

Skriv först utkastet, och tillämpa sedan humanizern nedan på din egen text innan du svarar.

Svara med ETT JSON-objekt och ingenting annat: {{"subject": "...", "body": "..."}}"""


def _bolagsfakta(rad: dict[str, Any]) -> str:
    falt = [
        ("Namn", kortnamn(rad.get("company_name"))),
        ("Ort", rad.get("ort")),
        ("Bransch och register", rad.get("signal")),
        ("Detalj", rad.get("signal_detalj")),
    ]
    return "\n".join(f"- {k}: {str(v).strip()[:300]}" for k, v in falt if v and str(v).strip())


def _systemprompt(avsandare: str) -> str:
    from ..agentcore.registry import load_skill_md

    return _UPPDRAG.format(avsandare=avsandare) + "\n\n## humanizer-svenska\n\n" + load_skill_md(HUMANIZER)


def _sim_utkast(rad: dict[str, Any], avsandare: str) -> dict[str, str]:
    """Deterministiskt utkast för testsviten och den lokala stacken."""
    namn = kortnamn(rad.get("company_name")) or "er"
    ort = str(rad.get("ort") or "").strip()
    return {
        "subject": f"En fråga till {namn}" + (f" i {ort}" if ort else ""),
        "body": (
            "Hej,\n\n"
            f"Jag hör av mig till er på {namn} med en kort fråga.\n\n"
            f"{avsandare} hjälper mindre bolag att få fler kunder utan mer eget arbete.\n\n"
            "Hör av er om ni vill se ett exempel.\n\n"
            "Vänliga hälsningar,"
        ),
    }


def _tolka(text: str) -> dict[str, str] | None:
    rad = text.strip()
    staket = re.search(r"```(?:json)?\s*(.*?)```", rad, re.S)
    try:
        data = json.loads(staket.group(1) if staket else rad)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    amne = str(data.get("subject") or "").strip()
    brod = str(data.get("body") or "").strip()
    if not amne or not brod:
        return None
    return {"subject": amne[:200], "body": brod[:4000]}


async def skriv_listutkast(rad: dict[str, Any], *, avsandare: str, erbjudande: str) -> dict[str, Any]:
    """{subject, body, anmarkning?} för EN listrad. Kastar RuntimeError om
    modellen inte gav ett användbart svar.

    `anmarkning` sätts när textkvalitetslagret flaggat något allvarligt;
    utkastet sparas ändå, och köningen tvingar det då till granskning.
    """
    settings = get_settings()
    if settings.is_simulation():
        utkast = _sim_utkast(rad, avsandare)
    else:
        import asyncio

        from ..agent.llm import get_llm_client, tankande_kwargs
        from ..kvotfel import ar_kreditslut, ar_kvotfel

        # Omtag vid kvotfel (429 från Vertex när en hel lista skrivs), med
        # växande paus. Kreditslut tas aldrig om: det är permanent tills vi
        # agerat, och tre avvisningar till är bara väntan.
        for forsok in range(4):
            try:
                svar = await get_llm_client().chat.completions.create(
                    model=settings.model,
                    temperature=0.6,
                    messages=[
                        {"role": "system", "content": _systemprompt(avsandare)},
                        {
                            "role": "user",
                            "content": f"## Bolaget\n{_bolagsfakta(rad)}\n\n## Erbjudandet\n{erbjudande[:2000]}",
                        },
                    ],
                    **tankande_kwargs(),
                )
                break
            except Exception as fel:
                if forsok == 3 or ar_kreditslut(fel) or not ar_kvotfel(fel):
                    raise
                await asyncio.sleep(5 * 2**forsok)
        tolkat = _tolka(svar.choices[0].message.content or "")
        if tolkat is None:
            raise RuntimeError("Modellen gav inget användbart utkast.")
        utkast = tolkat

    from ..textkvalitet import kontrollera, putsa

    utkast["body"], _ = putsa(utkast["body"])
    # Den avslutande hälsningsfrasen slutar med komma tills signaturen läggs
    # på vid köningen; kontrollen läser texten före den, annars är varje
    # utkast "slutar mitt i en mening".
    fore_halsning = re.sub(r"\n+[^\n]*hälsningar,?\s*$", "", utkast["body"], flags=re.IGNORECASE)
    allvarliga = kontrollera(fore_halsning, sprak="sv").allvarliga
    if allvarliga:
        utkast["anmarkning"] = "; ".join(a.beskrivning for a in allvarliga)
    return utkast
