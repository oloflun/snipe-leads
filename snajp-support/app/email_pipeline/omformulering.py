"""Omformulering av svarsutkast — Förbättra, Kortare, Mer personlig.

## Vad det här är

Granskaren i inkorgen har tre småknappar bredvid "Godkänn & skicka". Var och
en skriver om det AKTUELLA utkastet (inklusive granskarens egna redigeringar)
i en riktning, utan att skicka något och utan att röra det sparade utkastet:
resultatet landar i textrutan, och det som till slut skickas är som alltid
det granskaren ser och godkänner (drafts.approve med edited_content).

## Varför ingenting persisteras här

Godkännandevägen har redan ett kontrakt: det som skickas är innehållet i
rutan. En omformulering som skrev om det sparade utkastet hade skapat en
andra sanning — en granskare som ångrar sig kunde inte längre komma tillbaka
till originalet. Stateless in/ut håller kontraktet intakt.

## Varför inga nya fakta får tillkomma

Utkastet är grundat i kunskapsbasen av processorn (grundningsregeln i
email_pipeline/processor.py). En omformulering som fick lägga till innehåll
hade varit en väg RUNT den grindningen — därför är instruktionen till
modellen att enbart omforma, och kundmejlet skickas med som kontext för ton
och fullständighet, inte som källa till nya påståenden.

## Simuleringsläget

Utan LLM-nyckel (Settings.is_simulation) görs deterministiska texttransformer
i kod, av samma skäl som sim_triage finns: den lokala stacken och testsviten
ska kunna köra hela flödet utan modell, och beteendet ska gå att falsifiera.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from ..config import get_settings
from ..moderation.maskering import maskera_personnummer

logger = logging.getLogger("snajp-support.omformulering")

#: Lägena och deras instruktion till modellen. Nyckeln är API-kontraktet
#: (schemas.OmformuleraDraftRequest.lage) — läggs ett läge till ska schemat,
#: den här tabellen och knappraden i support-webb/InkorgVy ändras ihop.
LAGEN: dict[str, str] = {
    "forbattra": (
        "Förbättra utkastet: tydligare struktur, proffsigare och mer konkreta "
        "formuleringar, korrekt svenska. Svara på allt kunden faktiskt frågade "
        "om — men lägg ALDRIG till sakuppgifter, priser eller löften som inte "
        "redan står i utkastet."
    ),
    "kortare": (
        "Korta utkastet väsentligt — sikta på ungefär halva längden. Behåll "
        "varje sakuppgift som besvarar kundens fråga; det som ska bort är "
        "utfyllnad, upprepningar och onödiga artighetsfraser (en hälsning och "
        "en avslutning räcker)."
    ),
    "personligare": (
        "Gör utkastet varmare och mer personligt: tilltala kunden med förnamn "
        "om det är känt, knyt an till kundens konkreta situation med kundens "
        "egna ord, och låt tonen vara mänsklig snarare än mallad. Inga nya "
        "sakuppgifter."
    ),
}

_PROMPT = """Du skriver om ett svarsutkast från ett företags kundtjänst.

Uppdrag: {instruktion}

Regler, i den här ordningen:
1. Inga nya sakuppgifter, priser, datum eller löften — bara det som redan
   står i utkastet får förekomma, omformulerat.
2. Behåll utkastets språk (svenska förblir svenska).
3. Behåll formen: en hälsningsrad först, en avslutning med avsändaren sist.
4. Svara ENBART med den omskrivna mejltexten — ingen rubrik, ingen
   kommentar, inga citattecken runt svaret.

Kundens mejl (kontext för ton och vad som frågades — INTE en källa för nya
påståenden):
Ämne: {subject}
{body}

Utkastet att skriva om:
{draft}"""


def _mening_split(text: str) -> list[str]:
    """Grov meningsdelning för simuleringens kortare-läge."""
    return [m.strip() for m in re.split(r"(?<=[.!?])\s+", text.strip()) if m.strip()]


def _sim_omformulera(lage: str, content: str, *, kundnamn: str | None) -> str:
    """Deterministiska transformer när ingen modell finns.

    Medvetet enkla: de finns för att flödet ska gå att köra och testa
    end-to-end lokalt, inte för att imponera. Strukturen (hälsning först,
    signatur sist) bevaras genom att bara mittenpartiet röres.
    """
    rader = content.strip().splitlines()

    # Hälsningen (första raden som börjar med "hej") och signaturblocket
    # (från "vänliga hälsningar"-raden och nedåt) lämnas orörda.
    halsning: list[str] = []
    if rader and rader[0].strip().casefold().startswith("hej"):
        halsning = [rader.pop(0)]
        while rader and not rader[0].strip():
            rader.pop(0)

    signatur: list[str] = []
    for i, rad in enumerate(rader):
        if re.match(r"^\s*(med\s+)?vänlig(a)?\s+hälsning(ar)?,?\s*$", rad, re.IGNORECASE):
            signatur = rader[i:]
            rader = rader[:i]
            break
    kropp = "\n".join(rader).strip()

    if lage == "kortare":
        meningar = _mening_split(kropp)
        behall = max(1, (len(meningar) + 1) // 2)
        kropp = " ".join(meningar[:behall])
    elif lage == "personligare":
        fornamn = (kundnamn or "").strip().split()[0] if (kundnamn or "").strip() else ""
        if halsning and fornamn and fornamn.casefold() not in halsning[0].casefold():
            halsning = [f"Hej {fornamn}!"]
        if "tack för att du hör" not in kropp.casefold():
            kropp = f"Tack för att du hörde av dig! {kropp}"
    else:  # forbattra
        kropp = re.sub(r"[ \t]+", " ", kropp)
        kropp = re.sub(r"\n{3,}", "\n\n", kropp).strip()

    delar = [*halsning, "", kropp] if halsning else [kropp]
    if signatur:
        delar += ["", *signatur]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(delar)).strip()


async def omformulera_utkast(
    *,
    lage: str,
    content: str,
    email: dict[str, Any] | None,
) -> str:
    """Det omskrivna utkastet. Kastar ValueError på okänt läge.

    Faller tillbaka på originaltexten om modellen svarar tomt — en trasig
    omformulering ska ge granskaren texten hen redan hade, aldrig en tom ruta.
    """
    if lage not in LAGEN:
        raise ValueError(f"Okänt omformuleringsläge: {lage!r}")

    settings = get_settings()
    kundnamn = (email or {}).get("from_name")
    if settings.is_simulation():
        return _sim_omformulera(lage, content, kundnamn=kundnamn)

    from ..agent.llm import get_llm_client, tankande_kwargs

    # Samma maskeringsgräns som triagen: kundtexten lämnar huset, alltså
    # maskeras personnummer innan (DPIA R1). Utkastet är vår egen text men
    # kan citera kunden — maskeras det med.
    prompt = _PROMPT.format(
        instruktion=LAGEN[lage],
        subject=maskera_personnummer((email or {}).get("subject") or "(inget ämne)"),
        body=maskera_personnummer((email or {}).get("body_text") or "(saknas)"),
        draft=maskera_personnummer(content),
    )
    response = await get_llm_client().chat.completions.create(
        model=settings.model,
        temperature=0.4,
        messages=[{"role": "user", "content": prompt}],
        **tankande_kwargs(),
    )
    nytt = (response.choices[0].message.content or "").strip()
    return nytt or content
