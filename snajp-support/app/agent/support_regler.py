"""Support-agentens regler per kund: eskalering, ton, ämnesområde, faktakontroll.

## Varifrån modellen kommer

Ebbot-researchen 2026-09-18 (bd snipe-1fl). Två iakttagelser styrde:

  * Ebbots ramverk är per kund: persona, ton och överlämningsregler ställs in
    av varje kund och inte globalt. Vår agent hyrs ut på samma sätt, så
    trösklarna som låg hårdkodade i `support_agent.py` flyttas hit och läses
    ur `agent_configs.settings` för agent_type "support".
  * Ebbots chatt loopade: två otydliga förtydliganden i följd ("fattar du
    inte?") gav samma svar tre gånger, utan motfråga och utan överlämning.
    Därför finns ett TAK för misslyckade rundor i följd, och en kund som
    säger att svaret missade räknas som en misslyckad runda.

## Var reglerna verkställs

I KOD, i `support_agent.run_support_agent`. Modellen levererar signaler
(triage: ber kunden om en människa, ligger frågan inom ämnesområdet, säger
kunden att svaret missade; research: behövs ett förtydligande) — men beslutet
att lämna över fattas här, av samma skäl som påhoppsgrinden: det ska inte gå
att prata bort.

## Läs tolerant, skriv strikt

Samma kontrakt som Iris regler (`leads/eskalering.py`): `normalisera` kastar
aldrig, okänt eller trasigt blir standardvärdet. Skrivvägen är pydantic i
`api/schemas.py`. Standardvärdena är DAGENS beteende före flytten — en kund
som aldrig rört inställningarna märker ingen skillnad utöver de nya
triggerna (uttrycklig begäran om människa, frustration).
"""

from __future__ import annotations

import re
from typing import Any, TypedDict


class Eskaleringsregler(TypedDict):
    #: Misslyckade rundor i följd som tolereras innan överlämning. En runda
    #: är misslyckad när agenten måste ställa en motfråga, eller när kunden
    #: säger att förra svaret missade. 2 = dagens beteende (två motfrågor,
    #: sedan en människa).
    max_misslyckade: int
    #: Sentiment under den här gränsen (0–100) lämnas över. 30 = dagens 0.3.
    sentimentgrans: int
    #: "erbjud": säg att frågan ligger utanför och erbjud en människa.
    #: "eskalera": lämna över direkt.
    utanfor_amnet: str
    #: Räknas "fattar du inte?" som en misslyckad runda?
    frustration_raknas: bool


class SupportInstallningar(TypedDict):
    eskalering: Eskaleringsregler
    #: Nyckel i TONLAGEN. "standard" = kanalens eller adminprofilens ton.
    tonlage: str
    #: Nyckel i FAKTAKONTROLL.
    faktakontroll: str
    #: Kundens egen beskrivning av vad agenten ska hjälpa till med. KUNDSKRIVEN
    #: text: når prompten bara wrappad och i user-position (INV-SEC-009).
    amnesomrade: str


STANDARD_ESKALERING: Eskaleringsregler = {
    "max_misslyckade": 2,
    "sentimentgrans": 30,
    "utanfor_amnet": "erbjud",
    "frustration_raknas": True,
}

MAX_MISSLYCKADE_TAK = 5
AMNESOMRADE_TAK = 600

UTANFOR_AMNET_VAL = ("erbjud", "eskalera")

#: Tonlägen kunden väljer mellan. Texten är VÅR (ett enumval mappat till en
#: fast mening), så den kan aldrig bära en instruktion kunden skrivit.
TONLAGEN: dict[str, str] = {
    "standard": "",
    "formell": (
        "Skriv sakligt och korrekt. Inga vardagliga uttryck, inga emojier och "
        "inga utropstecken."
    ),
    "personlig": (
        "Skriv varmt och personligt, som en kunnig kollega. Visa gärna med en "
        "kort mening att du förstått kundens situation innan du svarar."
    ),
    "kortfattad": (
        "Skriv så kort det går utan att tappa sakinnehåll: kärnan i svaret "
        "först, inga inledande artighetsfraser."
    ),
}

#: Faktakontrollens nivåer (se support_faktagrind.py för vad varje nivå
#: kontrollerar). Ebbots tre nivåer, men verkställda i kod mot kunskapsbasen
#: i stället för av en andra modell.
FAKTAKONTROLL = ("tillatande", "forsiktig", "strikt")

STANDARD: SupportInstallningar = {
    "eskalering": STANDARD_ESKALERING,
    "tonlage": "standard",
    "faktakontroll": "forsiktig",
    "amnesomrade": "",
}


def normalisera_eskalering(ratt: Any) -> Eskaleringsregler:
    """Sparat värde → fullständiga eskaleringsregler. Kastar aldrig."""
    regler: Eskaleringsregler = dict(STANDARD_ESKALERING)  # type: ignore[assignment]
    if not isinstance(ratt, dict):
        return regler
    tak = ratt.get("max_misslyckade")
    if isinstance(tak, (int, float)) and not isinstance(tak, bool):
        regler["max_misslyckade"] = max(0, min(MAX_MISSLYCKADE_TAK, int(tak)))
    grans = ratt.get("sentimentgrans")
    if isinstance(grans, (int, float)) and not isinstance(grans, bool):
        regler["sentimentgrans"] = max(0, min(100, int(grans)))
    if ratt.get("utanfor_amnet") in UTANFOR_AMNET_VAL:
        regler["utanfor_amnet"] = ratt["utanfor_amnet"]
    if isinstance(ratt.get("frustration_raknas"), bool):
        regler["frustration_raknas"] = ratt["frustration_raknas"]
    return regler


def normalisera(settings: Any) -> SupportInstallningar:
    """Hela `agent_configs.settings` för support → fullständiga inställningar."""
    rad = settings if isinstance(settings, dict) else {}
    tonlage = rad.get("tonlage")
    faktakontroll = rad.get("faktakontroll")
    amnesomrade = rad.get("amnesomrade")
    return {
        "eskalering": normalisera_eskalering(rad.get("eskalering")),
        "tonlage": tonlage if tonlage in TONLAGEN else "standard",
        "faktakontroll": faktakontroll if faktakontroll in FAKTAKONTROLL else "forsiktig",
        "amnesomrade": (
            amnesomrade.strip()[:AMNESOMRADE_TAK] if isinstance(amnesomrade, str) else ""
        ),
    }


# -- Orsakskoder -----------------------------------------------------------

#: Varför ett samtal lämnades över. Koden sparas i ss_chat_state och i
#: agentens resultat; texten är vad medarbetaren ser. Fritextmotiveringen på
#: ärendet (`escalation_reason`) är oförändrad — den bär detaljen.
ORSAKER: dict[str, str] = {
    "kund_bad_om_manniska": "Kunden bad om att få prata med en människa.",
    "utanfor_amnesomradet": "Frågan ligger utanför det agenten är inställd att hjälpa till med.",
    "utanfor_kunskapsbasen": "Kunskapsbasen saknar svar på en tydlig fråga.",
    "fortydligandetak": "Agenten fick inte ihop ett svar trots förtydliganden.",
    "sakerhet": "Känsligt ärende: pengar, juridik, personuppgifter eller missnöje.",
    "pahopp": "Samtalet avbröts efter hot eller påhopp.",
    "modellbedomning": "Eskaleringsbedömningen krävde en människa.",
    "medarbetare_tog_over": "En medarbetare tog över samtalet.",
}


# -- Signaler som avgörs i kod ---------------------------------------------

#: Kunden ber uttryckligen om en människa. Fram till 2026-09-18 var regexen
#: bara en väckarklocka för eskaleringssteget, och modellen kunde rösta nej.
#: Sedan Ebbot-researchen är den en TRIGGER: en kund som ber om en människa
#: får en, utan övertalningsförsök. Ett falskt utslag kostar en överlämning;
#: ett missat kostar en kund som bad om en människa och fick en bot.
_BER_OM_MANNISKA = re.compile(
    r"\b(prata|tala|snacka|chatta)\s+med\s+(en\s+)?(människa|person|någon|"
    r"handläggare|anställd|medarbetare|kollega|er\s+personal|kundtjänst)|"
    r"\b(riktig|levande|verklig)\s+(människa|person)\b|"
    r"\bmänsklig\s+(hjälp|kontakt|support|handläggare)\b|"
    r"\bkoppla\s+(mig|vidare|in\s+en)\b|"
    r"\bringa?\s+(upp\s+)?mig\b",
    re.IGNORECASE,
)

#: Nekande ord strax före en träff ("jag behöver INTE prata med någon").
_NEKANDE_FORE = re.compile(r"\b(inte|ej|ingen|inga|slippa|slipper|utan\s+att)\b", re.IGNORECASE)


def ber_om_manniska(text: str) -> bool:
    """Ber texten uttryckligen om en människa? Nekade formuleringar räknas inte."""
    for traff in _BER_OM_MANNISKA.finditer(text or ""):
        fore = (text or "")[max(0, traff.start() - 30) : traff.start()]
        if not _NEKANDE_FORE.search(fore):
            return True
    return False


#: Ett kort jakande svar. Läses BARA när agenten i förra repliken erbjöd en
#: människa (ss_chat_state.erbjod_manniska) — då är "ja" en begäran, annars
#: är det ett svar på något annat.
_JAKANDE = re.compile(
    r"^\s*(ja|japp|jajamän|jo|gärna|ja\s+tack|ja\s+gärna|ok(ej|ay)?|absolut|visst|"
    r"gör\s+det|det\s+vill\s+jag|snälla|yes)\b",
    re.IGNORECASE,
)


def jakande_svar(text: str) -> bool:
    """Är meddelandet ett kort ja? Långa meddelanden är nya frågor, även när
    de börjar med "ja" ("Ja, men hur lång är leveranstiden?")."""
    kort = (text or "").strip()
    return len(kort) <= 40 and bool(_JAKANDE.match(kort)) and "?" not in kort
