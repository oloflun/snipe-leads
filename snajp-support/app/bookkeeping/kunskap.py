"""Bokföringskunskapen som DATA, versionerad i repot.

## Varför en datamodul och inte modellens minne

Chatten får förklara begrepp — det står i CHATT_SYSTEMPROMPT — men en
förklaring ur modellens minne är olika varje gång och går inte att granska.
Texterna här är skrivna av oss, ligger i git, och ändras genom en diff någon
läser. Samma arbetsdelning som `kontoplan.py`: modellen väljer VILKET ämne
frågan gäller, koden levererar texten.

Kunskapsbasen är EGEN för bokföringen. Den delar ingenting med supportagentens
kunskapsbas (`app/kb_articles.py`, `ss_knowledge_base`) — de svarar på olika
frågor åt olika mottagare, och ett delat index hade gjort supportens
demoartiklar till bokföringsråd.

## Om delmängden

Samma tak som kontoplanen: ämnena nedan täcker det ett litet bolags frågor
faktiskt handlar om. Saknas ett ämne ska det LÄGGAS TILL som en datarad här —
inte improviseras av modellen vid körning, och `sok_amne` returnerar därför
None i stället för närmaste gissning.

## Vad texterna INTE får innehålla

Belopp som fastställs årligen (traktamentsschabloner, milersättningens exakta
nivå framåt) skrivs med hänvisning till Skatteverket i stället för med en
siffra som tyst blir fel vid årsskiftet. Stabila lagfästa tal (300 kr-taket
för representationsmoms, arkiveringstiden) får stå. Talen i texterna blir
grundade tal under INV-BOOK-003 när verktyget sparar sitt svar i
`context.resultat` — det är korrekt: de är hämtade ur ett verktygsresultat.

Och ingenting här är rådgivning. Texterna förklarar begrepp och regler på
allmän nivå; gränsen mot "vad ska JAG göra i min deklaration" dras av
CHATT_SYSTEMPROMPT och ska synas i tonen även här.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Amne:
    id: str
    rubrik: str
    text: str
    #: Ord en fråga om ämnet kan innehålla. Matchas gemener, delsträng.
    nyckelord: tuple[str, ...]


_AMNEN = (
    Amne(
        "momssatser",
        "Momssatserna 25, 12 och 6 procent",
        "Sverige har tre momssatser. 25 % är huvudregeln och gäller de flesta "
        "varor och tjänster. 12 % gäller bland annat livsmedel, restaurang- och "
        "cateringtjänster samt hotell. 6 % gäller bland annat böcker, "
        "tidningar, persontransporter och entré till kultur- och "
        "idrottsevenemang. Vissa områden är momsfria, till exempel sjukvård, "
        "tandvård, bank- och försäkringstjänster och uthyrning av bostäder — "
        "då dras ingen moms av på inköp som hör till den verksamheten. "
        "Ingående moms är momsen på det företaget köper, utgående moms är "
        "momsen på det företaget säljer.",
        ("moms", "momssats", "25", "12", "6", "momsfri", "momsfritt"),
    ),
    Amne(
        "momsdeklaration",
        "Momsdeklaration och redovisningsperioder",
        "Momsen redovisas till Skatteverket per månad, per kvartal eller per "
        "helår, beroende på omsättningens storlek — Skatteverket beslutar "
        "vilken period som gäller för bolaget. Moms att betala är utgående "
        "moms minus ingående moms för perioden; är den ingående större får "
        "bolaget i stället tillbaka mellanskillnaden. I bokföringen förs "
        "momsen över till redovisningskontot för moms (2650) när perioden "
        "stäms av.",
        ("momsdeklaration", "deklarera moms", "redovisningsperiod", "moms att betala", "2650"),
    ),
    Amne(
        "periodisering",
        "Periodisering: rätt kostnad på rätt period",
        "Periodisering betyder att en intäkt eller kostnad bokförs på den "
        "period den hör till, inte den period fakturan råkade betalas. En "
        "hyra som betalas i december men gäller januari är en förutbetald "
        "kostnad; ett utfört arbete som ännu inte fakturerats är en upplupen "
        "intäkt. Mindre företag som följer K2 får låta bli att periodisera "
        "poster under 5 000 kr och återkommande utgifter som är ungefär lika "
        "stora varje år. Periodiseringskontona ingår inte i Snajps förenklade "
        "kontoplan — ett underlag som spänner över flera perioder flaggas i "
        "stället för granskning.",
        ("periodisering", "förutbetald", "upplupen", "avgränsning", "interimspost"),
    ),
    Amne(
        "representation",
        "Representation och vad som får dras av",
        "Kostnad för måltider vid representation är inte avdragsgill "
        "inkomstskattemässigt sedan 2017. Däremot får momsen dras av på ett "
        "underlag upp till 300 kr exklusive moms per person och tillfälle, "
        "förutsatt att representationen har ett omedelbart samband med "
        "verksamheten. Enklare förtäring — kaffe, bulle, en enklare smörgås — "
        "är fortfarande avdragsgill upp till skäligt belopp. I Snajps "
        "kontoplan bokförs avdragsgill representation på 6071.",
        ("representation", "kundmiddag", "restaurang med kund", "6071", "avdragsgill middag"),
    ),
    Amne(
        "resor_och_traktamente",
        "Tjänsteresor och traktamente",
        "Resor i tjänsten är avdragsgilla: biljetter bokförs på 5810, kost "
        "och logi i Sverige på 5831. Traktamente är en skattefri "
        "schablonersättning vid tjänsteresa med övernattning utanför den "
        "vanliga verksamhetsorten; beloppen fastställs årligen av "
        "Skatteverket, så kontrollera aktuell nivå där. Betalar bolaget "
        "faktiska måltider i stället reduceras traktamentet.",
        ("tjänsteresa", "traktamente", "resa", "hotell", "logi", "biljett"),
    ),
    Amne(
        "milersattning",
        "Milersättning för egen bil i tjänsten",
        "Den som kör egen privat bil i tjänsten kan få skattefri "
        "milersättning enligt en schablon per mil som fastställs av "
        "Skatteverket — kontrollera aktuellt belopp där, nivån har ändrats "
        "mellan åren. Ersättning över schablonen är skattepliktig lön. "
        "Underlaget är en körjournal: datum, resmål, ärende och antal mil.",
        ("milersättning", "egen bil", "körjournal", "mil"),
    ),
    Amne(
        "hemmakontor",
        "Arbetsrum hemma",
        "Avdrag för arbetsrum i den egna bostaden är mycket restriktivt. Det "
        "kräver i regel att rummet är särskilt inrättat för verksamheten och "
        "inte kan användas som bostadsutrymme, eller att arbetsgivaren "
        "saknar arbetsplats att erbjuda. Ett vanligt skrivbord i vardagsrummet "
        "räcker inte. Kostnader som el och bredband kan dras av bara till den "
        "del de hör till verksamheten. Frågan är ofta en gränsdragning en "
        "redovisningskonsult bör titta på.",
        ("hemmakontor", "arbetsrum", "hemma", "bostad"),
    ),
    Amne(
        "telefon_och_bil",
        "Telefon och bil i företaget",
        "Mobiltelefon och abonnemang som används i verksamheten bokförs på "
        "6212 och datakommunikation på 6230; används de privat i mer än "
        "ringa omfattning kan det bli en skattepliktig förmån. För bil "
        "gäller två spår: en förmånsbil beskattas hos föraren enligt "
        "schablon, medan den som kör privat bil i tjänsten i stället får "
        "milersättning. Drivmedel för företagets personbilar bokförs på 5611.",
        ("telefon", "mobil", "abonnemang", "bil", "förmånsbil", "drivmedel"),
    ),
    Amne(
        "fakturor",
        "Leverantörs- och kundfakturor",
        "En faktura ska bland annat innehålla fakturadatum, fakturanummer i "
        "löpande följd, säljarens och köparens namn och adress, säljarens "
        "momsregistreringsnummer, vad som sålts, beskattningsunderlag per "
        "momssats och momsbeloppet. Leverantörsskulder bokförs på 2440 och "
        "kundfordringar på 1510. Betalningsvillkor avtalas; 30 dagar är "
        "vanligt mellan företag. Vid sen betalning får säljaren ta ut "
        "dröjsmålsränta, lagstadgad påminnelseavgift (60 kr) och mellan "
        "företag en förseningsersättning på 450 kr.",
        ("faktura", "fakturakrav", "betalningsvillkor", "påminnelse", "dröjsmålsränta", "kundfordran", "leverantörsskuld"),
    ),
    Amne(
        "bankavstamning",
        "Bankavstämning",
        "Bankavstämning betyder att kontoutdraget från banken jämförs med "
        "bokföringens poster på företagskontot (1930): varje transaktion på "
        "utdraget ska ha ett underlag, och varje bokfört underlag ska synas "
        "på utdraget. Oparade transaktioner är det som ska utredas — ett "
        "kvitto som aldrig laddades upp, eller ett uttag som inte hör till "
        "verksamheten. Snajps avstämning läser kontoutdraget, jämför mot "
        "periodens underlag och kastar filen; den bokför ingenting.",
        ("bankavstämning", "kontoutdrag", "stämma av", "avstämning", "1930"),
    ),
    Amne(
        "verifikationer",
        "Bokföringslagen: verifikationer, löpande bokföring och arkivering",
        "Varje affärshändelse ska ha en verifikation som visar när den "
        "inträffat, vad den avser, belopp och motpart. Kontanta in- och "
        "utbetalningar ska bokföras senast följande arbetsdag, övriga "
        "affärshändelser så snart det kan ske. Räkenskapsinformation ska "
        "arkiveras i sju år. Sedan den 1 juli 2024 behöver papperskvitton "
        "inte sparas om innehållet överförts digitalt utan risk att "
        "uppgifter förändras — det digitala underlaget blir då originalet. "
        "Verifikationskedjan innebär att det ska gå att följa en post från "
        "underlag till rapport och tillbaka.",
        ("verifikation", "bokföringslagen", "arkivering", "spara kvitton", "löpande bokföring", "verifikationskedja"),
    ),
    Amne(
        "omvand_byggmoms",
        "Omvänd byggmoms",
        "Vid försäljning av byggtjänster mellan byggföretag gäller omvänd "
        "skattskyldighet: säljaren fakturerar utan moms och skriver köparens "
        "momsregistreringsnummer samt en upplysning om omvänd "
        "skattskyldighet på fakturan, och köparen redovisar både utgående "
        "och ingående moms på förvärvet. Kontona för omvänd byggmoms ingår "
        "inte i Snajps förenklade kontoplan — sådana underlag flaggas för "
        "granskning i stället för att konteras fel.",
        ("omvänd byggmoms", "byggmoms", "omvänd skattskyldighet", "byggtjänst"),
    ),
    Amne(
        "eu_handel",
        "EU-handel och VAT-nummer",
        "Vid försäljning av varor till ett momsregistrerat företag i ett "
        "annat EU-land faktureras utan svensk moms, förutsatt att köparens "
        "giltiga VAT-nummer anges på fakturan och varan transporteras till "
        "det andra landet; köparen redovisar förvärvsmoms. Vid inköp från "
        "EU redovisar det svenska bolaget momsen självt på samma sätt. "
        "EU-försäljningen rapporteras dessutom i en periodisk "
        "sammanställning till Skatteverket. VAT-nummer kan kontrolleras i "
        "EU-kommissionens VIES-tjänst.",
        ("eu", "vat", "vat-nummer", "unionsinternt", "periodisk sammanställning", "utland"),
    ),
    Amne(
        "import",
        "Import från länder utanför EU",
        "Vid import från länder utanför EU deklareras varorna hos "
        "Tullverket, och ett momsregistrerat bolag redovisar importmomsen "
        "själv i momsdeklarationen i stället för att betala den till "
        "Tullverket. Underlaget är tullräkningen eller tulldeklarationen, "
        "inte bara leverantörens faktura — spara båda.",
        ("import", "tull", "tullverket", "importmoms", "utanför eu"),
    ),
    Amne(
        "k_regelverk",
        "K1, K2 och K3 i korthet",
        "K-regelverken styr hur årsbokslut och årsredovisning upprättas. K1 "
        "är förenklat årsbokslut för de minsta enskilda firmorna. K2 är ett "
        "förenklat regelverk med schabloner för mindre aktiebolag och "
        "ekonomiska föreningar. K3 är huvudregelverket, med fler "
        "bedömningar och upplysningar, och är obligatoriskt för större "
        "företag. Valet påverkar bland annat hur periodisering och "
        "avskrivningar hanteras — vilket regelverk som passar bolaget är en "
        "fråga för en redovisningskonsult.",
        ("k1", "k2", "k3", "regelverk", "årsredovisning", "årsbokslut"),
    ),
    Amne(
        "avdragsratt",
        "Avdragsrätt i allmänhet",
        "Huvudregeln är att utgifter för att förvärva och behålla intäkter "
        "är avdragsgilla i verksamheten. Privata levnadskostnader är det "
        "inte, och gränsdragningen är den vanligaste stötestenen: en dator "
        "som används i verksamheten är avdragsgill, en middag med en vän är "
        "det inte. Vissa kostnader är aldrig avdragsgilla, till exempel "
        "böter och skattetillägg. Om ett enskilt inköp får dras av i just "
        "ert fall är en bedömning för en redovisningskonsult.",
        ("avdrag", "avdragsgill", "avdragsrätt", "dra av"),
    ),
)

KUNSKAP: dict[str, Amne] = {a.id: a for a in _AMNEN}


def sok_amne(fraga: str) -> Amne | None:
    """Ämnet en fråga gäller, eller None.

    Exakt id först, sedan nyckelord mot frågans ORD — ett enordsnyckelord
    måste matcha ett helt ord ("bil" träffar inte "mobil"), ett flerords-
    nyckelord matchar som delsträng. None och inte närmaste gissning — samma
    regel som `foresla_konto`: anroparen svarar hellre med de kända ämnena än
    med fel text.
    """
    normerad = (fraga or "").strip().lower()
    if not normerad:
        return None
    if normerad in KUNSKAP:
        return KUNSKAP[normerad]
    ord_i_fragan = set(re.findall(r"[a-z0-9åäöé-]+", normerad))

    # Pass 1: exakta träffar — hela nyckelordet som eget ord, eller en fras
    # som delsträng. Pass 2: prefixträffar för böjningsformer ("momsen",
    # "mobilen"), bara för nyckelord på minst fyra tecken så att "bil" inte
    # träffar "biljett" — och där vinner det LÄNGSTA matchande nyckelordet,
    # inte det första ämnet: "momsdeklarationen" ska nå "momsdeklaration"
    # (15 tecken), inte fastna på "moms" (4) i ämnet före.
    for amne in _AMNEN:
        for nyckel in amne.nyckelord:
            if (" " in nyckel and nyckel in normerad) or nyckel in ord_i_fragan:
                return amne

    basta: tuple[int, Amne] | None = None
    for amne in _AMNEN:
        for nyckel in amne.nyckelord:
            if " " in nyckel or len(nyckel) < 4:
                continue
            if any(ordet.startswith(nyckel) for ordet in ord_i_fragan):
                if basta is None or len(nyckel) > basta[0]:
                    basta = (len(nyckel), amne)
    return basta[1] if basta else None
