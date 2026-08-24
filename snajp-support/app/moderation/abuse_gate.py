"""Vad agenten inte ska behöva ta emot — och den viktiga gränsdragningen.

Delad av alla tre agenterna sedan 2026-08-24; se `app/moderation/__init__.py`
för varför den flyttade hit från `app/leads/`.

## Detta är INTE ett svordomsfilter

En kund som skriver "det här är ju för jävligt, jag har väntat i tre veckor"
är arg på en verklig sak och ska få hjälp. Att avvisa den personen för ordvalet
är att straffa den som har mest rätt att vara upprörd, och det är precis den
kunden ett supportärende finns för.

Gränsen går vid RIKTAD förolämpning, hot och kränkningar mot person eller
grupp. Alltså inte hur hårt någon uttrycker sig, utan vad uttrycket riktas mot.

Fyra nivåer, fyra svar:

| Nivå       | Vad det är                              | Vad som händer            |
|------------|-----------------------------------------|---------------------------|
| `oro`         | Stress inför en deadline eller följd  | Inget. Svara som vanligt, men lugnt och konkret. |
| `frustration` | Kraftuttryck om SITUATIONEN          | Inget. Svara som vanligt. |
| `riktad`      | Förolämpning riktad mot agenten/person | Ett lugnt påpekande, sedan hjälp |
| `allvarlig`   | Hot, sexuella påhopp, hets mot folkgrupp | Avbryt och eskalera till människa |

## `oro` är ett TONLÄGE, inte en ny eskaleringsnivå

En kund som skriver "momsdeklarationen ska in på fredag och jag får inte ihop
det" är inte arg och inte otrevlig. Den är rädd att missa något med en följd —
en försening, en avgift, ett vite. Behandlas det som `inget` svarar agenten
neutralt och sakligt på en fråga som bar en ton, och det läses som likgiltighet
just när det kostar mest.

Nivån ändrar därför BARA `ton_instruktion`. `ska_eskalera` är fortfarande sant
enbart för `allvarlig`, och `replik` är None. En orolig kund ska få ett lugnare
svar, inte hamna i en kö.

Ordningen mot `frustration`: frustration vinner. En kund som är BÅDE stressad
och arg är arg, och det är den känslan svaret ska möta först.

## Varför listorna är korta

En lång ordlista blir ett filter som fäller fel, och varje falskt utslag är en
kund som får en tillrättavisning i stället för hjälp. Listorna nedan täcker det
grova och entydiga. Gråzonen ska hellre gå igenom till en människa än stoppas
av ett reguljärt uttryck.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

INGET = "inget"
ORO = "oro"
FRUSTRATION = "frustration"
RIKTAD = "riktad"
ALLVARLIG = "allvarlig"

#: Ord som signalerar TIDSPRESS eller en följd kunden är rädd för. Matchas som
#: prefix, precis som frustrationsstammarna — svenskan böjer dem ("deadline",
#: "deadlinen", "försenad", "förseningen").
#:
#: TVÅ ORD SOM STOD HÄR OCH PLOCKADES BORT IGEN, så att de inte läggs tillbaka:
#:
#:   "hjälp"  — står i nästan varje supportmeddelande ("kan ni hjälpa mig?").
#:              Med den i listan var i princip allt oro, och en tonnivå som
#:              alltid slår är ingen tonnivå.
#:   "missa"  — prefixmatchningen gjorde "missade" till oro, och "vi missade
#:              leveransen förra veckan" är dåtid, inte tidspress. Den som
#:              RISKERAR att missa något skriver oftast ut vad: en deadline,
#:              ett förfallodatum, en fredag. De orden står kvar.
_ORO = {
    "deadline", "deadlines", "bråttom", "brådskande", "akut", "hinner", "hinna",
    "försen", "forsen", "riskerar", "vite", "påminnelseavgift",
    "förfaller", "forfaller", "inkasso", "stressad", "stressar",
    "panik", "orolig", "oroar", "urgent", "asap",
}

#: Uttryck där oron är en TIDPUNKT snarare än ett ord. En kund som skriver
#: "ska in på fredag" bär samma stress utan att använda något av orden ovan.
_ORO_MONSTER = (
    re.compile(r"\b(ska|måste|behöver)\s+(vara\s+)?(in|inne|klart|klar|lämnas|skickas)\b"),
    re.compile(r"\b(idag|imorgon|i\s+morgon)\b.*\b(senast|innan|före)\b"),
    re.compile(r"\bsenast\s+(idag|imorgon|i\s+morgon|på\s+\w+dag|den\s+\d)"),
)

#: Kraftuttryck om situationen. Fälls ALDRIG — de finns med enbart för att
#: kunna skiljas från de riktade, och för att tonen i svaret ska kunna möta
#: en upprörd kund i stället för att låtsas att inget sagts.
_FRUSTRATION = {
    "jävla", "jävlar", "jävligt", "helvete", "fan", "fanken", "skit",
    "skitdåligt", "förbannat", "as", "korkat", "kass", "kasst", "värdelöst",
    "damn", "hell", "crap", "bullshit",
}

#: Riktade förolämpningar. Kräver att ordet syftar på någon, inte på en sak.
_RIKTADE = {
    "idiot", "idioter", "korkad", "korkade", "dum", "dumma", "dummer",
    "efterbliven", "hjärndöd", "imbecill", "pucko", "tönt", "mongo",
    "stupid", "moron", "idiotic",
}

#: Det som avbryter samtalet. Hot, sexuella påhopp och kränkningar mot
#: folkgrupp. Listan innehåller medvetet inga slurord i klartext — de matchas
#: via mönster nedan, så att filen går att läsa högt i ett möte.
_ALLVARLIGA_MONSTER = (
    # Hot om våld, riktat mot mottagaren.
    re.compile(r"\b(jag\s+ska\s+(döda|slå|mörda|hitta|spöa)|ta\s+livet\s+av\s+dig)\b"),
    re.compile(r"\b(kill\s+you|i\s+will\s+find\s+you)\b"),
    # Uppmaning till självskada.
    re.compile(r"\b(ta\s+livet\s+av\s+dig|dö\s+bort|kys\b|kill\s+yourself)\b"),
    # Sexuella påhopp.
    re.compile(r"\b(knulla\s+dig|sug\s+min|fuck\s+you)\b"),
    # Kränkningar mot folkgrupp. STAMMAR, inte hela ord: svenskan böjer dem
    # (blatte/blattar/blattarna), och ett filter som bara fångar grundformen
    # fångar i praktiken ingenting — plural är det vanligaste bruket.
    re.compile(r"\b(blatt|svartskall|neger|negrer|n[i1]gg|judesvin|bögjävel)\w*\b"),
)

#: "skit-" är en FÖRSTÄRKNING i svenskan och pekar åt båda hållen: skitdålig är
#: negativt, skitbra är positivt. Frustrationsstammarna matchas därför som
#: prefix (så att skitprodukt fångas), med undantag för de sammansättningar där
#: förstärkningen är positiv. Utan undantaget hade en nöjd kund som skriver
#: "skitbra, tack!" klassats som frustrerad, och agenten hade svarat urskuldande
#: på ett beröm.
_POSITIVA_SAMMANSATTNINGAR = {
    "skitbra", "skitkul", "skitsnygg", "skitgott", "skitroligt", "skitfin",
    "skitduktig", "skitsmart", "skitnice",
}

#: Ord som bara är riktade när de står nära ett personligt pronomen eller
#: agentens namn. "Det här är dumt" är frustration; "du är dum" är riktat.
_PERSONMARKOR = re.compile(
    r"\b(du|dig|ni|er|din|ditt|dina|agenten|boten|roboten|you|your)\b"
)


@dataclass(frozen=True)
class AbuseBeslut:
    niva: str
    trafford_term: str | None
    #: Text som läggs FÖRE det vanliga svaret. Aldrig i stället för det, utom
    #: på nivå `allvarlig`.
    replik: str | None

    @property
    def ska_eskalera(self) -> bool:
        return self.niva == ALLVARLIG

    @property
    def ska_svara_normalt(self) -> bool:
        return self.niva != ALLVARLIG


def _normalisera(text: str) -> str:
    """Gemener, och bokstäver med diakriter kvar.

    Medvetet INGEN aggressiv avkodning av l33tspeak eller mellanslag mellan
    bokstäver. Den sortens normalisering fäller "s k i t b r a" och gör filtret
    till en gissningslek. Den som verkligen vill runda ett filter gör det ändå;
    priset ska inte betalas av kunder som skriver normalt.
    """
    return unicodedata.normalize("NFC", text or "").casefold()


def _ord(text: str) -> list[str]:
    return re.findall(r"\w+", text, flags=re.UNICODE)


def check_abuse(meddelande: str) -> AbuseBeslut:
    """Bedömer ETT kundmeddelande. Gör ingen I/O och fattar inga beslut om
    ärendet — anroparen avgör vad nivån ska leda till."""
    text = _normalisera(meddelande)

    for monster in _ALLVARLIGA_MONSTER:
        traff = monster.search(text)
        if traff:
            return AbuseBeslut(
                niva=ALLVARLIG,
                trafford_term=traff.group(0),
                replik=(
                    "Jag avslutar det här samtalet. En kollega tar över och hör av "
                    "sig till dig. Har du ett ärende som behöver lösas kommer det "
                    "att lösas — men inte så här."
                ),
            )

    orden = set(_ord(text))

    riktade = orden & _RIKTADE
    if riktade and _PERSONMARKOR.search(text):
        return AbuseBeslut(
            niva=RIKTAD,
            trafford_term=sorted(riktade)[0],
            replik=(
                "Jag hjälper dig gärna, men jag vill inte bli tilltalad så. "
                "Berätta vad som hänt så tar vi det därifrån."
            ),
        )

    if _frustrationsord(orden):
        # INGEN tillrättavisning. Den här kunden är arg på en sak, inte på
        # agenten, och har oftast rätt att vara det. Nivån returneras enbart
        # så att svaret kan möta känslan i stället för att ignorera den.
        #
        # Ligger FÖRE oro-kontrollen: en kund som är både stressad och arg är
        # arg, och det är den känslan svaret ska möta först.
        return AbuseBeslut(
            niva=FRUSTRATION,
            trafford_term=sorted(_frustrationsord(orden))[0],
            replik=None,
        )

    oroande = _oroord(orden)
    if oroande:
        return AbuseBeslut(niva=ORO, trafford_term=sorted(oroande)[0], replik=None)
    for monster in _ORO_MONSTER:
        traff = monster.search(text)
        if traff:
            return AbuseBeslut(niva=ORO, trafford_term=traff.group(0), replik=None)

    return AbuseBeslut(niva=INGET, trafford_term=None, replik=None)


def _frustrationsord(orden: set[str]) -> set[str]:
    """Prefixmatchning mot frustrationsstammarna, minus de positiva
    sammansättningarna. Se _POSITIVA_SAMMANSATTNINGAR om varför."""
    traffar = set()
    for ord_ in orden:
        if ord_ in _POSITIVA_SAMMANSATTNINGAR:
            continue
        if ord_ in _FRUSTRATION or any(
            ord_.startswith(stam) and len(stam) >= 4 for stam in _FRUSTRATION
        ):
            traffar.add(ord_)
    return traffar


def _oroord(orden: set[str]) -> set[str]:
    """Prefixmatchning mot orostammarna. Samma mekanik som `_frustrationsord`.

    Minsta stamlängd 5 och inte 4: med 4 hade "akut" fångat "akutmottagning"
    och en del annat. Orden i `_ORO` som är kortare än 5 tecken matchas därför
    bara exakt.

    Också SUFFIX, till skillnad från `_frustrationsord`, för stammar på minst
    6 tecken. Svenskan förstärker genom att sätta något FÖRE ordet —
    "jättebråttom", "superbråttom" — och en ren prefixmatchning missar precis
    de fall där oron är som tydligast. Sexteckensgränsen håller ändå
    kortformerna ("akut", "vite") från att fångas mitt inne i andra ord.
    """
    traffar = set()
    for ord_ in orden:
        if ord_ in _ORO or any(
            (ord_.startswith(stam) and len(stam) >= 5)
            or (ord_.endswith(stam) and len(stam) >= 6)
            for stam in _ORO
        ):
            traffar.add(ord_)
    return traffar


def ton_instruktion(beslut: AbuseBeslut) -> str:
    """Raden som läggs till i prompten så att svaret möter läget.

    Skriven som en instruktion om TONFALL, inte om innehåll: agenten ska
    fortfarande svara på sakfrågan och fortfarande grunda svaret i
    kunskapsbasen. Det enda som ändras är hur den låter.
    """
    if beslut.niva == ORO:
        return (
            "## Tonläge\n"
            "Kunden är stressad — det finns en tidsgräns eller en följd som "
            "oroar. Kunden är INTE arg på dig. Svara lugnt och konkret: säg "
            "vad som gäller och vad nästa steg är, i den ordningen. Undvik "
            "brasklappar och långa förbehåll — de läser som undanflykter när "
            "någon har bråttom. Lova ingenting om en tidpunkt du inte vet."
        )
    if beslut.niva == FRUSTRATION:
        return (
            "## Tonläge\n"
            "Kunden är tydligt frustrerad. Bekräfta det i EN mening, utan att "
            "ursäkta dig överdrivet och utan att kommentera ordvalet. Gå sedan "
            "rakt på vad du kan göra åt saken. Ingen glättighet, inga "
            "utropstecken."
        )
    if beslut.niva == RIKTAD:
        return (
            "## Tonläge\n"
            "Kunden har riktat en förolämpning mot dig. Påpeka det lugnt och i "
            "en enda mening, utan att moralisera, och hjälp sedan till som "
            "vanligt. Bli inte avmätt eller passiv-aggressiv."
        )
    return ""
