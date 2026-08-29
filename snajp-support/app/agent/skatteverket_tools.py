"""Skatteverket-uppslaget som ETT verktyg, delat av alla agenter.

## Varför ett verktyg och inte ett anrop i varje körning

Agenten ska ha Skatteverket TILLGÄNGLIGT, inte anropa det. De allra flesta
turer behöver ingen registeruppgift — en fråga om vad ingående moms betyder
besvaras ur `kunskap.py` och ska inte kosta ett myndighetsanrop, en väntan på
nätverket, och en rad i Skatteverkets auditlogg som bevaras i fem år.

Ett verktyg ger exakt den formen: modellen kallar på det när frågan faktiskt
gäller bolagets egen registrering, och annars inte alls. Samma avvägning som
`bookkeeping_chat_tools.py` gör för sina fyra dataset — modellen väljer VAD,
koden gör.

## Ett verktyg, alla agenter

Verktyget ligger här och inte i `bookkeeping_chat_tools.py` för att det inte
hör till bokföringen: samma uppgift är relevant för supportagenten (en kund
som frågar varför de inte fått ett momsbeslut) och för onboarding. Bokföringen
är först i prioritet, inte ensam om behovet.

Kontexterna skiljer sig åt mellan agenterna, så verktyget läser fältet
`skatteverket` via `getattr` i stället för att kräva en gemensam bastyp. En
kontext utan fältet får samma svar som en kontext utan inloggning — verktyget
finns, uppgiften går inte att hämta, och modellen får veta varför.

## Ingen orgnr-parameter. Läs `SkatteverketAtkomst` innan du lägger till en.

Modellen får VÄLJA UPPGIFT, aldrig identitet. Orgnr och token kommer ur
kontexten, satt av servern (INV-SEC-002). Två oberoende skäl står i
`leads/skatteverket.py:SkatteverketAtkomst`: tokenen gäller ändå bara den
inloggades eget bolag, och de allmänna villkoren §7.1 tillåter bara uppslag
"av, eller för" mottagaren själv. Ett orgnr-argument hade sett ut som en
enrichment-funktion för prospekt, vilket är precis det avtalet förbjuder.

## Varför resultatet sparas i kontexten när den kan ta emot det

INV-BOOK-003 (`bookkeeping/beloppsgrind.py`) jämför svarets belopp mot turens
verktygsresultat. Skatteverkets svar bär tal — datum, `momstypKod`,
`avslutsorsakKod` — och saknas de i `context.resultat` blir grinden strängare
än den ska vara: sanna siffror från det här verktyget fälls som ogrundade.
Det står utskrivet i `bookkeeping_chat_tools.py`:s docstring som en fälla för
nya verktyg, och det här är ett nytt verktyg.
"""

from __future__ import annotations

import json
from typing import Any

from agents import RunContextWrapper, function_tool

from ..leads.skatteverket import TILLATNA_UPPGIFTER, sla_upp


async def _sla_upp_skatteverket_impl(kontext: Any, uppgift: str) -> str:
    """Den testbara delen. Se modulens docstring för varför den tar HELA
    kontexten och inte ett orgnr."""
    atkomst = getattr(kontext, "skatteverket", None)
    resultat = await sla_upp(atkomst, uppgift)

    # `spara` finns på BokforingChattContext och är INV-BOOK-003:s enda indata.
    # Andra kontexter saknar den, och då räcker det att returnera texten.
    spara = getattr(kontext, "spara", None)
    if callable(spara):
        return spara(resultat)
    return json.dumps(resultat, ensure_ascii=False, default=str)


@function_tool
async def sla_upp_skatteverket(ctx: RunContextWrapper[Any], uppgift: str) -> str:
    """Slår upp kundens EGEN registrering hos Skatteverket.

    Använd bara när frågan gäller vad som faktiskt är registrerat för bolaget —
    till exempel vilken momsperiod eller redovisningsmetod som gäller, eller om
    bolaget är godkänt för F-skatt. Allmänna frågor om vad moms eller F-skatt
    ÄR besvaras utan det här verktyget.

    Svaret gäller alltid det inloggade bolaget. Du kan inte slå upp något annat
    företag, och du ska inte fråga kunden efter ett organisationsnummer.

    Fältet `galler_nu` säger om registreringen gäller i dag. Lita på det —
    ett svar kan innehålla en registrering som redan avslutats.

    Args:
        uppgift: 'fskatt', 'moms' eller 'arbetsgivarregistrerad'.
    """
    return await _sla_upp_skatteverket_impl(ctx.context, uppgift)


#: Läggs till i varje agents verktygslista. Egen konstant så att en agent som
#: INTE ska ha uppslaget syns som ett medvetet undantag i koden.
SKATTEVERKET_TOOLS = [sla_upp_skatteverket]

__all__ = ["SKATTEVERKET_TOOLS", "TILLATNA_UPPGIFTER", "sla_upp_skatteverket"]
