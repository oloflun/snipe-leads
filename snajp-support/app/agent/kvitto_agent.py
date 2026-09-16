"""Kvitto-assistenten — chattagenten över kvittodatan.

Bygger på samma skelett som bokföringschatten (`bookkeeping_agent.py`):
Agents SDK, verktyg som hämtar, beloppsgrinden INV-BOOK-003 som fäller varje
svar med ett tal som inte kommer ur ett verktygsanrop i samma tur. Det som
skiljer är uppgiften: den svarar på VAD FÖRETAGET LAGT PENGAR PÅ, inte på
kontering och K-regelverk — och den ger fortfarande aldrig skatteråd.

Poleringssteget och kunskapsfångsten från bokföringschatten är MEDVETET
borttagna här: kvitto-assistenten är en billigare yta (2 modellanrop per tur
i stället för 5–7), och Gemini-kvoten har redan fällt en lansering en gång.
"""

from __future__ import annotations

import time
from typing import Any

from agents import Agent, ModelSettings, Runner

from ..agentcore.instruktioner import las_instruktioner
from ..bookkeeping.beloppsgrind import check_belopp
from ..moderation.abuse_gate import check_abuse, ton_instruktion
from .bookkeeping_agent import bygg_turhistorik, fallt_svar
from .kvitto_chat_tools import KVITTO_CHATT_TOOLS, KvittoChattContext
from .llm import get_agent_model

#: Skrivs till `agent_runs.agent_type`. Samma typ som resten av modulen —
#: kvittohanteringen ÄR bookkeeping-produkten i entitlement och migrationer.
AGENT_TYPE = "bookkeeping"

#: Integritetslöftet, formulerat så att det är SANT. Extraktionen använder en
#: extern AI-modell (Vertex AI/Gemini i drift), så "allt sker lokalt" vore en
#: vilseledande marknadsföringsclaim. Texten ägs här och renderas av båda
#: gränssnitten — samma mönster som FORBEHALL.
INTEGRITETSNOTIS = (
    "Dina mejl och kvitton säljs aldrig och delas aldrig med tredje part utöver "
    "den AI-tjänst som tolkar kvittotexten åt oss, under personuppgiftsbiträdesavtal "
    "inom vår GDPR-plan. Mejlens text sparas inte: agenten läser, plockar ut "
    "kvittofälten och släpper mejlet — det som lagras är fälten, avsändare och "
    "ämnesrad samt en kontrollsumma."
)

FORBEHALL = (
    "Förslag, inte bokföring. Kvittohanteraren läser av och sammanställer dina "
    "kvitton. Beloppen är avlästa maskinellt och ska granskas av en människa "
    "innan de används i bokföring eller deklaration."
)

CHATT_SYSTEMPROMPT = f"""Du är Snajps kvitto-assistent. Du svarar på svenska, kort och konkret,
om företagets kvitton och utlägg.

## Din grundregel, före allt annat
DU RÄKNAR ALDRIG. Varje siffra du skriver måste komma från ett verktygsanrop i
den HÄR turen. Du får inte addera, dra ifrån eller uppskatta. Behöver du ett
tal: hämta det. Finns det inte: säg att det inte finns.

Skriv belopp med "kr" efter siffran, till exempel "1 250 kr". Ett svar som bär
ett belopp du inte hämtat fälls av en kontroll innan kunden ser det.

## Dina verktyg
- hamta_kvittosammanfattning(fran, till) — antal, totalbelopp, moms och
  summan per kategori för en period.
- lista_kvitton(fran, till, status, kategori) — kvittona, med belopp,
  kategori, källa (mejl eller uppladdning) och status.

Du väljer själv period. Säger kunden "i mars" och året är underförstått:
använd innevarande år, och skriv ut vilken period du hämtat så att kunden kan
rätta dig.

## Flaggade kvitton
Ett kvitto med status granska_manuellt räknas INTE in i summorna — säg det
när det är relevant, och säg varför det flaggades (anmärkningen står i
listan): otydligt belopp, utländsk valuta eller möjlig dubblett.

## Vad du inte får råda om
Du får förklara vad som står i kvittodatan. Du får INTE säga om en kostnad är
avdragsgill, hur något ska deklareras eller hur en fråga från Skatteverket
ska hanteras — det är rådgivning som kräver en auktoriserad
redovisningskonsult. Hänvisa dit i stället, vänligt och utan omsvep.

## Dataskydd
Kvittona tillhör det inloggade företaget och bara det. Skriv aldrig ut ett
personnummer eller ett fullständigt kortnummer i ett svar. Frågor om radering
och registerutdrag hänvisas till kontakt@snajp.se.

## Ton
Skriv som en kunnig kollega: siffrorna exakta, språket levande. Variera dina
meningsöppningar, undvik "Jag förstår att…" och "Tack för din fråga!". Säg
"jag vet inte" när du inte vet.

{FORBEHALL}
"""


def build_kvitto_chat_agent(globalt_block: str = "") -> Agent:
    instruktioner = CHATT_SYSTEMPROMPT
    if globalt_block:
        instruktioner = f"{globalt_block}\n\n{CHATT_SYSTEMPROMPT}"
    return Agent[KvittoChattContext](
        name="Snajp-Kvitto-Chatt",
        instructions=instruktioner,
        model=get_agent_model(),
        tools=KVITTO_CHATT_TOOLS,
        model_settings=ModelSettings(temperature=0.5),
    )


_OMFORSOK_INSTRUKTION = (
    "STOPP. Ditt förra svar innehöll minst ett belopp som inte fanns i något "
    "verktygsresultat i den här turen, och det svaret kastades därför.\n\n"
    "Brister: {brister}\n\n"
    "Du MÅSTE anropa ett verktyg för att få siffran. Gissa inte och räkna inte. "
    "Anropa hamta_kvittosammanfattning eller lista_kvitton för den period frågan "
    "gäller, och svara med de tal verktyget gav dig. Finns talet inte att hämta: "
    "säg det rakt ut. Ett svar utan siffra är ett giltigt svar."
)


async def run_kvitto_chat_turn(
    storage,
    tenant_id: str,
    *,
    message: str,
    historik: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """En tur i kvittosamtalet. Grinden körs på den exakta text kunden ser."""
    lager = await las_instruktioner(storage, None)
    agent = build_kvitto_chat_agent(lager.global_block)
    context = KvittoChattContext(storage=storage, tenant_id=tenant_id)

    meddelanden = bygg_turhistorik(historik, message)

    abuse = check_abuse(message)
    ton = ton_instruktion(abuse)
    if ton:
        meddelanden.append({"role": "user", "content": [{"type": "input_text", "text": ton}]})

    start = time.monotonic()
    result = await Runner.run(agent, meddelanden, context=context, max_turns=8)
    svar = str(result.final_output or "").strip()

    verdikt = check_belopp(svar, context.resultat)
    if not verdikt.ok:
        meddelanden.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": _OMFORSOK_INSTRUKTION.format(
                            brister="; ".join(verdikt.as_report()) or "(inga angivna)"
                        ),
                    }
                ],
            }
        )
        result = await Runner.run(agent, meddelanden, context=context, max_turns=8)
        svar = str(result.final_output or "").strip()
        verdikt = check_belopp(svar, context.resultat)

    if not verdikt.ok:
        svar = fallt_svar()

    return {
        "reply": svar,
        "grundad": verdikt.ok,
        "brister": verdikt.as_report(),
        "verktygsanrop": len(context.resultat),
        "latency_ms": int((time.monotonic() - start) * 1000),
        "forbehall": FORBEHALL,
        "tonlage": abuse.niva,
    }
