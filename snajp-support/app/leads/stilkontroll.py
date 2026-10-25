"""Stilkontrollen: AI- och robotmarkörer i ett kallt mejl, i kod.

Skrivstilen (`agent-core/prompts/leads-skrivstil.md`) säger HUR mejlet ska
låta, och den når modellen i varje utkaststeg. En regel som bara står i en
prompt är en riktning, inte en garanti (samma läxa som gissningsgrinden), så
de markörer som går att känna igen mekaniskt prövas här efteråt:

  tankstreck i brödtext, "Jag ser/såg att", "vi har skapat/utvecklat",
  "X är en AI-agent som", effektivisera/effektivitet/optimera, "i dagens",
  superlativ om oss, utropstecken, två meningar i rad med samma första ord,
  meningar över 25 ord, kolonuppräkningar i löptext, en hälsningsfras
  skriven av modellen (signaturen läggs på i kod), ett mejl som slutar med en
  fråga i stället för en handling och en brödtext över 90 ord.

Batchkontrollen fångar regel 7: två mejl i samma körning får inte ha samma
ingång eller samma uppmaning.

Kontrollen FÄLLER inget. Ett fynd tvingar utkastet till mänsklig granskning
(`leads_tools._queue_outreach_draft_impl`), och skälet står på köposten så
att granskaren ser det. Resultatet har samma form som textkvalitetslagret
(`textkvalitet.Kontrollresultat`), och texten ändras aldrig.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from functools import lru_cache

from ..textkvalitet import Anmarkning, Kontrollresultat
from .grounding_gate import _maska_idiom
from .text_delta import split_sentences

MAX_ORD = 25
#: Skrivstilen: 60–100 ord i brödtexten. Piloten och avslutet står i varje
#: mejl, men provkörningen 2026-10-25 gav 105–150 ord: för långt (Anton).
MAX_ORD_MEJL = 100

_HALSNING = re.compile(
    r"^\s*(?:med\s+vänlig(?:a)?\s+hälsning(?:ar)?|vänliga\s+hälsningar|bästa\s+hälsningar|"
    r"hälsningar|mvh|ha\s+en\s+(?:bra|fin|trevlig)\s+(?:dag|helg))\b",
    re.IGNORECASE | re.MULTILINE,
)
_TILLTAL = re.compile(r"^\s*(?:hej|hejsan|hallå|goddag|god\s+morgon)\b[^.?!\n]*,?\s*$", re.IGNORECASE)
#: Foten (utskicksfot.bygg_fot) börjar med en egen rad "--".
_FOT = re.compile(r"^--\s*$", re.MULTILINE)

#: (kod, mönster, beskrivning). Beskrivningen är det granskaren läser.
_MARKORER: tuple[tuple[str, re.Pattern[str], str], ...] = (
    # Ett tankstreck i intervall ("15–20 minuter") står utan blanksteg och
    # träffas inte; ett med blanksteg runt sig är ett tankstreck i löptext.
    ("tankstreck", re.compile(r"—|\s[–-]\s"), "tankstreck i brödtexten"),
    ("jag_ser_att", re.compile(r"\bjag\s+(?:ser|såg|märkte|noterade|har\s+sett)\s+att\b", re.IGNORECASE),
     "börjar i vår iakttagelse (\"Jag ser att …\")"),
    ("vi_har_skapat", re.compile(r"\bvi\s+har\s+(?:skapat|utvecklat|byggt|tagit\s+fram)\b", re.IGNORECASE),
     "\"vi har skapat/utvecklat\""),
    ("ar_en_ai_agent", re.compile(r"\bär\s+en\s+(?:\w+\s+)?(?:AI-?\s?)?(?:agent|assistent)\s+som\b", re.IGNORECASE),
     "\"X är en AI-agent som …\""),
    ("effektivisera", re.compile(r"\b(?:effektivisera\w*|effektivitet\w*|optimera\w*)", re.IGNORECASE),
     "effektivisera/effektivitet/optimera"),
    ("i_dagens", re.compile(r"\bi\s+dagens\b", re.IGNORECASE), "\"i dagens …\""),
    ("utropstecken", re.compile(r"!"), "utropstecken"),
    ("antagande_om_dem",
     re.compile(r"\b(?:kan\s+jag\s+tänka\s+mig|vet\s+jag\s+att|är\s+jag\s+säker\s+på|jag\s+utgår\s+från|jag\s+gissar)\b",
                re.IGNORECASE),
     "ett antagande om mottagaren"),
)
#: Ingången som mall (Anton 2026-10-12, två gånger): en allmän mening om
#: branschen med en etikett på ("För företag som ert …", "… som ni gör",
#: "liksom ni", "ett byggföretag som ert") läses som ett massutskick, oavsett
#: hur specifik resten är. De goda ingångarna (Witekk, Tingstad, Consenso) är
#: skrivna TILL mottagaren om deras verksamhet: "Med er roll inom …", "Att
#: hitta nya företagsuppdrag i Göteborg, parallellt med villor …".
_MALL_INGANG = re.compile(
    r"(?:\bför\s+(?:ett\s+|en\s+)?\w*(?:företag|bolag|byrå|firma|verksamhet)\w*\s+som\s+(?:ert|er|ditt|din|dig)\b"
    r"|\b(?:lik)?som\s+(?:ni|du)(?:\s+(?:gör|är|har|jobbar|arbetar))?\s*[,.]"
    r"|\bsom\s+(?:ert|er)\b"
    r"|\bi\s+er\s+(?:situation|bransch)\b"
    r"|\bför\s+er\s+som\b)",
    re.IGNORECASE,
)
#: En allmän ingång: "man", "den som" och "ett företag som" gör meningen till
#: en sanning om vem som helst. Ingången skrivs i andra person om just dem.
_GENERELL_INGANG = re.compile(
    r"(?:\bman\b|\bden\s+som\b|\bde\s+som\b|\b(?:ett|en)\s+\w*(?:företag|bolag|byrå|firma|verksamhet)\s+som\b"
    r"|\bföretag\s+i\s+er\b|\bmånga\s+\w*(?:företag|bolag)\b)",
    re.IGNORECASE,
)
#: Slentrianöppningen (Anton 2026-10-15): efter att "För företag som ert" och
#: "som ni gör" fälldes blev "Med er/ert/era …", "När ni …" och "Ni som …" de
#: nya mallorden, i mejl efter mejl. Ingången börjar i deras löfte eller i en
#: fråga till dem, aldrig i en av de här öppningarna.
_SLENTRIAN = re.compile(r"^(?:med\s+(?:er|ert|era|din|ditt|dina)|när\s+(?:ni|du)|(?:ni|du)\s+som)\b", re.IGNORECASE)
#: Uppräkningen av deras utbud (Anton 2026-10-15: "en generisk upprabbling av
#: deras verksamhet"): "Med ert breda utbud av fordon, utrustning och service
#: för snöskotrar …", "Med er verksamhet som säljer båtar, motorer och
#: trailers …". En lista om tre led eller fler i ingångens första halva är en
#: återberättelse av sajten, inte en mening till dem; samma lista sist, i
#: momentet ("när kundfrågorna om båtar, motorer och trailers blir många",
#: Båtladan, Antons bästa utkast), är en detalj i spänningen och står kvar.
_UTBUD = re.compile(r"\b(?:bred(?:a|t)?\s+utbud|utbud\s+av|allt\s+från)\b", re.IGNORECASE)
_TRELEDSLISTA = re.compile(r"[\wåäöÅÄÖ-]+(?:\s+[\wåäöÅÄÖ-]+)?,\s+[\wåäöÅÄÖ-]+(?:\s+[\wåäöÅÄÖ-]+)?,?\s+(?:och|samt|eller)\s+[\wåäöÅÄÖ-]+")
#: Du och ni om samma mottagare (skrivreglerna: "blanda aldrig"). Båthuset
#: 2026-10-12: "Hej Monica" och "era kunder", sedan "du lägger" och "vi bokar
#: … åt er". Pronomenen som TILLTALAR, inte ägandeformen "er egen information".
_DU = re.compile(r"\b(?:du|dig)\b", re.IGNORECASE)
_NAMNGIVEN = re.compile(r"^\s*(?:hej|hejsan|hallå)\s+[A-ZÅÄÖ][\wåäöé-]+\s*[,!]", re.IGNORECASE)
_NI = re.compile(r"\bni\b|\båt\s+er\b|\bhos\s+er\b|\btill\s+er\b|\bert\b|\bera\b", re.IGNORECASE)
#: Mallord som omkörningen 2026-10-15 gav i fem av elva ingångar efter att
#: skrivstilen talat om bolagets "löfte": "… är ert löfte, men att svara på
#: återkommande kundfrågor tar tid från det arbetet". Löftet ska synas i deras
#: egna ord, inte benämnas; och "tar tid från det arbetet/kärnverksamheten"
#: kunde stå i vilket mejl som helst.
_MALLORD = re.compile(
    r"\b(?:ert|ditt|deras)\s+löfte\b|\blöfte\s+till\b|\bstår\s+(?:ni|du)\s+för\b|\bnågot\s+(?:ni|du)\s+står\s+för\b"
    r"|\btar\s+tid\s+från\s+(?:det\s+arbetet|det\s+(?:ni|du)\s+gör\s+bäst|er\s+kärn\w*|ert\s+kärn\w*)"
    r"|\bkärnverksamhet\w*|\bkärnuppdrag\w*|\båterkommande\s+(?:kund)?frågor\s+tar\s+tid\b"
    # Körningarna 2026-10-15/16 (189 utkast): "det är svårt att", "tar tid från
    # att" och "kräver fullt fokus" stod i fem till nio ingångar var.
    # ", inte på att hitta nästa …" är tillåtet igen sedan 2026-10-25 (Anton:
    # "helt okej om den förekommer ibland"), men bara med deras eget hantverk
    # som det de fokuserar på ("på måleriet"), aldrig ett allmänt "varje
    # projekt", och inte i varje mejl (samma_grepp i mot_andra).
    r"|\bdet\s+är\s+svårt\s+att\b|\bär\s+det\s+svårt\s+att\b"
    r"|\b(?:ta|tar)\s+tid\s+från\s+att\b|\bkräver\s+(?:fullt|ditt|ert)\s+fokus\b"
    r"|\b(?:fokus\w*|koncentrera\s+(?:er|dig))\s+på\s+(?:varje\s+(?:enskilt\s+)?(?:projekt|detalj)|projekt(?:et|en)?\b"
    r"|arbetet|uppdrag(?:et|en)?\b|verksamheten|jobbet|det\s+(?:ni|du)\s+gör)"
    r"|\bägna\s+(?:er|dig)\s+åt\s+(?:varje\s+(?:enskilt\s+)?projekt|projekt(?:et|en)?\b|arbetet|jobbet)",
    re.IGNORECASE,
)
#: Fokusgreppet ("… kräver att ni kan fokusera på måleriet, inte på att hitta
#: nästa uppdrag"): rätt ibland, fel i varje mejl (Anton 2026-10-25; 5 av 12 i
#: provkörningen samma natt, och 4 av 11 i omkörningen med synonymer).
_FOKUSGREPP = re.compile(
    r"\b(?:fokus\w*\s+på|koncentrera\s+(?:er|dig)\s+på|ägna\s+(?:er|dig)\s+åt)\b", re.IGNORECASE
)


def fokusgrepp(text: str) -> bool:
    """Bär ingångens två första meningar fokusgreppet?"""
    return bool(_FOKUSGREPP.search(_ingangsstycke(text)))
#: Fler än så här av de senaste ingångarna i körningen får inte redan bära greppet.
FOKUSGREPP_TAK = 1
#: Avslutet som order (Anton 2026-10-25: "en svag CTA som läses som botmejl
#: och massutskick ... måste förbjudas helt"): sista meningen börjar med
#: "Svara", eller mejlet ber om ett citerat kodord ("svara 'pilot'"). "… eller
#: svara på mejlet så bokar vi en genomgång" mitt i en inbjudan är tillåtet.
_SVARA_ORDER = re.compile(r"^svara\b", re.IGNORECASE)
_SVARA_KODORD = re.compile(r"\bsvara\s+(?:med\s+)?[\"”“'‘’][^\"”“'‘’]{1,20}[\"”“'‘’]", re.IGNORECASE)
#: Ingången som kritik (Anton 2026-10-25): deras löfte ställt mot ett
#: misslyckande ("Du lovar …, men frågor … hinner sällan besvaras", "Ni lovar
#: … Men den tiden försvinner snabbt"). En utmaning i deras sorts arbete är
#: rätt; ett påstående om att just de brister träffar en öm tå.
_KRITISK_INGANG = re.compile(
    r"\b(?:ni|du)\s+lovar\b[^?]*\bmen\b"
    r"|\b(?:hinner|hinns|besvaras|blir)\s+(?:\w+\s+)?sällan\b|\bsällan\s+(?:hinner|hinns|besvaras)\b"
    r"|\bförsvinner\b|\bblir\s+(?:liggande|lidande)\b|\bhalkar\s+efter\b",
    re.IGNORECASE,
)
#: Registerfakta i ingången: ett antal (siffra eller ord) följt av anställda,
#: platschefer, kontor, år …, eller ett grundningsår. "Med 20-25 anställda och
#: fem platschefer" är fakta mottagaren redan vet. En tid ("15–20 minuter"),
#: ett klockslag eller ett telefonnummer är inte det.
_REGISTERFAKTA = re.compile(
    r"(?:\b(?:\d+|en|ett|två|tre|fyra|fem|sex|sju|åtta|nio|tio|tolv|femton|tjugo|trettio|fyrtio|femtio|hundra)"
    r"\s*(?:[-–]\s*\d+)?\s+(?:anställda|medarbetare|platschefer|arbetsledare|montörer|kontor|fordon|bilar|"
    r"maskiner|miljoner|mkr|msek|års?)\b"
    r"|\b(?:sedan|grundat|grundades|grundade|startade|etablerade?|etablerat)\s+(?:år\s+)?(?:19|20)\d\d\b)",
    re.IGNORECASE,
)
#: Siffror som ord, så att "fem" i mejlet täcker "5" i villkoren och tvärtom.
_TALORD = {
    "1": "en", "2": "två", "3": "tre", "4": "fyra", "5": "fem", "6": "sex", "7": "sju", "8": "åtta",
    "9": "nio", "10": "tio", "12": "tolv", "15": "femton", "20": "tjugo", "25": "tjugofem",
    "30": "trettio", "40": "fyrtio", "50": "femtio", "60": "sextio", "70": "sjuttio", "80": "åttio",
    "90": "nittio", "100": "hundra",
}
_TAL = re.compile(r"\d+(?:[.,]\d+)?")
_SUPERLATIV = re.compile(
    r"(?<![a-zåäö])(?:marknadsledande|branschledande|världsledande|revolutionerande|"
    r"banbrytande|unik|unika|unikt|överlägsen|oslagbar|bäst|bästa)(?![a-zåäö])",
    re.IGNORECASE,
)
#: Kolon följt av en uppräkning i samma mening. Inte klockslag (10:30) och
#: inte ett PS.
#: Kolonet följs av blanksteg: "brf:er och allmännyttan" är ingen uppräkning
#: (facitutkastet Fiskebäck 2026-10-12).
_KOLONLISTA = re.compile(r"(?<!\d):\s(?!\d)[^.?!\n]*(?:,|\soch\s|\ssamt\s)")


def _brodtext(text: str) -> str:
    """Mejlet utan kodens tillägg: allt från foten och från signaturens
    hälsning och nedåt bort. Används när en köad text ska jämföras."""
    text = _FOT.split(text or "", maxsplit=1)[0]
    traff = re.search(r"^\s*Vänliga hälsningar,\s*$", text, re.MULTILINE)
    return text[: traff.start()] if traff else text


def _meningar(text: str) -> list[str]:
    ut = []
    for start, slut in split_sentences(text):
        for rad in text[start:slut].split("\n"):
            rad = rad.strip()
            if rad and not _TILLTAL.match(rad) and re.search(r"[A-Za-zÅÄÖåäö]", rad):
                ut.append(rad)
    return ut


def _norm(mening: str) -> str:
    return re.sub(r"\s+", " ", mening).strip().casefold()


def ingang(text: str) -> str:
    """Första meningen efter tilltalet."""
    meningar = _meningar(_brodtext(text))
    return _norm(meningar[0]) if meningar else ""


def uppmaning(text: str) -> str:
    """Sista meningen i brödtexten: handlingen mejlet slutar med (skrivstilen,
    omgång 3). Förr den sista frågan, men igenkänningsfrågan står nu tidigt."""
    meningar = _meningar(_brodtext(text))
    return _norm(meningar[-1]) if meningar else ""


def kontrollera(text: str) -> Kontrollresultat:
    """Markörerna i ett mejl. Alla fynd är allvarliga: de tvingar granskning."""
    text = text or ""
    fynd: list[Anmarkning] = []

    def lagg(kod: str, beskrivning: str) -> None:
        fynd.append(Anmarkning(kod, f"Stil: {beskrivning}", allvarlig=True))

    if _HALSNING.search(text):
        lagg("halsningsfras", "hälsningsfras skriven av modellen (signaturen läggs på i kod)")
    brod = _brodtext(text)
    for kod, monster, beskrivning in _MARKORER:
        traff = monster.search(brod)
        if traff:
            lagg(kod, f"{beskrivning}: \"{traff.group(0).strip()}\"")
    superlativ = _SUPERLATIV.search(_maska_idiom(brod.lower()))
    if superlativ:
        lagg("superlativ", f"superlativ: \"{superlativ.group(0)}\"")

    meningar = _meningar(brod)
    if meningar:
        mall = _MALL_INGANG.search(meningar[0])
        if mall:
            lagg("mall_ingang", f"ingången är en allmän mening med en etikett på (\"{mall.group(0).strip()}\")")
        generell = _GENERELL_INGANG.search(meningar[0])
        if generell and not mall:
            lagg("generell_ingang", f"ingången är allmän (\"{generell.group(0).strip()}\"), inte skriven till dem")
        fakta = _REGISTERFAKTA.search(meningar[0])
        if fakta:
            lagg("registerfakta_i_ingangen", f"registerfakta i ingången (mottagaren vet redan): \"{fakta.group(0)}\"")
        slentrian = _SLENTRIAN.search(meningar[0])
        if slentrian:
            lagg("slentrian_ingang", f"ingången börjar med en slentrianöppning (\"{slentrian.group(0)} …\"); börja i deras löfte eller med en fråga till dem")
        utbud = _UTBUD.search(meningar[0])
        lista = _TRELEDSLISTA.search(meningar[0])
        if utbud or (lista and lista.start() < len(meningar[0]) / 2):
            traff = (utbud or lista).group(0)
            lagg("uppraknad_ingang", f"ingången räknar upp vad de säljer (\"{traff}\") i stället för vad de lovar sina kunder")
        mallord = _MALLORD.search(" ".join(meningar[:2]))
        if mallord:
            lagg("mallord_i_ingangen", f"ingången bär ett mallord (\"{mallord.group(0)}\"); säg det med deras egna, konkreta ord")
        kopia = kopierat_exempel(meningar[0])
        if kopia:
            lagg("kopierat_exempel", f"ingången lånar ord ur skrivstilens exempel (\"{kopia}\")")
        kritik = _KRITISK_INGANG.search(" ".join(meningar[:2]))
        if kritik:
            lagg("kritisk_ingang", f"ingången läses som kritik av dem (\"{kritik.group(0)[:40]}\"); beskriv en utmaning i deras sorts arbete")
    tilltal = "\n".join(meningar)
    du, ni = _DU.search(tilltal), _NI.search(tilltal)
    if du and ni:
        lagg("du_och_ni", f"blandar du och ni om samma mottagare (\"{du.group(0)}\" och \"{ni.group(0)}\")")
    elif _NAMNGIVEN.match(text) and re.search(r"\bni\b", tilltal, re.IGNORECASE) and not du:
        # "Hej Per," och sedan "ni" rakt igenom (2026-10-15): till en
        # namngiven mottagare skrivs mejlet i du-form.
        lagg("ni_till_person", "hälsar med förnamn men skriver \"ni\"; till en namngiven mottagare används \"du\"")
    for forra, mening in zip(meningar, meningar[1:]):
        a, b = (re.match(r"[\wÅÄÖåäö]+", m) for m in (forra, mening))
        if a and b and a.group(0).casefold() == b.group(0).casefold():
            lagg("samma_start", f"två meningar i rad börjar med \"{b.group(0)}\"")
            break
    # Skrivstilens regel 4 och strukturen (Antons omgång 3): mejlet slutar med
    # en enkel handling, aldrig en fråga, och brödtexten är högst 90 ord.
    if meningar and meningar[-1].endswith("?"):
        lagg("slutar_med_fraga", f"slutar med en fråga i stället för en handling: \"{meningar[-1][:60]}\"")
    svara = next((m for m in meningar[-1:] if _SVARA_ORDER.match(m)), None) or next(
        (m for m in meningar if _SVARA_KODORD.search(m)), None
    )
    if svara:
        lagg("svara_sa_avslut", f"avslutet är en order (\"{svara[:50]}\"); skriv en vardaglig inbjudan")
    antal_ord = sum(len(m.split()) for m in meningar)
    if antal_ord > MAX_ORD_MEJL:
        lagg("for_langt", f"brödtexten är {antal_ord} ord (högst {MAX_ORD_MEJL})")
    for mening in meningar:
        if len(mening.split()) > MAX_ORD:
            lagg("lang_mening", f"mening över {MAX_ORD} ord: \"{mening[:60]}…\"")
            break
    for mening in meningar:
        if not mening.upper().startswith("PS") and _KOLONLISTA.search(mening):
            lagg("kolonlista", f"kolonuppräkning i löptext: \"{mening[:60]}…\"")
            break
    return Kontrollresultat(text=text, anmarkningar=fynd)


#: Fyra ord i rad ur skrivstilens exempel räcker för att en ingång ska vara
#: lånad (Anton 2026-10-15): Lycka Service fick "Att hitta nya
#: företagsuppdrag …" och Törnqvist "… inte bara snabba affärer" ordagrant ur
#: tabellen fel/rätt. Regel 7 sa det redan; nu prövas den.
_LANAD_ORDFOLJD = 4


def _ord(text: str) -> list[str]:
    return re.findall(r"[a-zåäöé0-9]+", text.casefold())


@lru_cache(maxsize=1)
def _exempelfoljder() -> frozenset[tuple[str, ...]]:
    """Ordföljderna i skrivstilens citerade exempel (allt inom citattecken
    med minst sex ord). Läses ur filen, så att ett nytt exempel täcks direkt."""
    from ..agent.leads_systemprompt import skrivstil

    foljder: set[tuple[str, ...]] = set()
    for citat in re.findall(r"\"([^\"\n]{30,})\"", skrivstil()):
        ord_ = _ord(citat)
        if len(ord_) >= 6:
            foljder.update(tuple(ord_[i : i + _LANAD_ORDFOLJD]) for i in range(len(ord_) - _LANAD_ORDFOLJD + 1))
    return frozenset(foljder)


#: Ord som står i nästan varje mejl i den här domänen och därför inte gör en
#: ordföljd lånad ("både privatpersoner och företag" är deras egna ord lika ofta).
_VANLIGA_ORD = frozenset({
    "företag", "företagen", "kunder", "kunderna", "privatpersoner", "verksamhet", "verksamheten",
    "uppdrag", "uppdragen", "arbetet", "kundfrågor", "frågor", "frågorna",
})


def _sarskiljande(foljd: tuple[str, ...]) -> bool:
    """Minst två ord i följden bär innehåll (sex bokstäver eller fler, inte
    domänens vardagsord): "inte bara snabba affärer" ja, "en utmaning att
    hitta" och "något som får vänta" nej."""
    return sum(1 for o in foljd if len(o) >= 6 and o not in _VANLIGA_ORD) >= 2


def kopierat_exempel(mening: str) -> str | None:
    """Första särskiljande ordföljden i meningen som står ordagrant i ett
    exempel, eller None."""
    ord_ = _ord(mening)
    foljder = _exempelfoljder()
    for i in range(len(ord_) - _LANAD_ORDFOLJD + 1):
        foljd = tuple(ord_[i : i + _LANAD_ORDFOLJD])
        if foljd in foljder and _sarskiljande(foljd):
            return " ".join(foljd)
    return None


def amne_fynd(subject: str, *, bolag: str | None, produkt: str | None, andra: Sequence[str] = ()) -> list[Anmarkning]:
    """Ämnesraden (Anton 2026-10-15: "pinsamma ämnesrader, nämn INTE företagens
    namn i ämnesraden"). "Åkes Motor och era kundfrågor", "Pilot för Iris,
    Törnqvist Etc." och "Kundfrågor för …" i nästan varje mejl. Ämnesraden bär
    inget bolagsnamn, ingen produkt och börjar inte som ett annat mejls."""
    from .tilltal import kortnamn

    amne = " ".join(str(subject or "").split())
    fynd: list[Anmarkning] = []
    if not amne:
        return fynd
    kort = kortnamn(bolag).casefold() if bolag else ""
    if kort and (kort in amne.casefold() or _forsta_namnled(kort) in _ord(amne)):
        fynd.append(Anmarkning("namn_i_amnet", f"Stil: bolagets namn står i ämnesraden: \"{amne}\"", allvarlig=True))
    stam = produktstam(produkt)
    if stam and stam in amne.casefold():
        fynd.append(Anmarkning("produkt_i_amnet", f"Stil: produkten står i ämnesraden: \"{amne}\"", allvarlig=True))
    borjan = " ".join(_ord(amne)[:2])
    if borjan and any(" ".join(_ord(a)[:2]) == borjan for a in andra if a):
        fynd.append(Anmarkning("samma_amne", f"Stil: ämnesraden börjar som ett annat mejls: \"{amne}\"", allvarlig=True))
    if len(_ord(amne)) > 8:
        fynd.append(Anmarkning("langt_amne", f"Stil: ämnesraden är över åtta ord: \"{amne}\"", allvarlig=True))
    return fynd


def _forsta_namnled(kort: str) -> str:
    """Bolagsnamnets första led när det är särskiljande ("båtladan",
    "yngvessons"), annars tomt: "bygg", "nya" och korta led säger inget."""
    led = _ord(kort)
    forsta = led[0] if led else ""
    return forsta if len(forsta) >= 6 and forsta not in _VANLIGA_LED else "\0"


_VANLIGA_LED = frozenset({"svensk", "svenska", "sverige", "nordic", "norrlands", "byggservice", "service"})


def konstruktion(text: str) -> str:
    """Ingångens tre första ord: konstruktionen, inte orden efter."""
    return " ".join(ingang(text).split()[:3])


def erbjudande_fynd(text: str, *, villkor: str | None, produkt: str | None) -> list[Anmarkning]:
    """Erbjudandet intakt (Anton 2026-10-12): kedjans omskrivningar tappade
    "fem leads utan kostnad" och lämnade en vag fråga. Varje siffra i villkoren
    (som siffra eller ord) och produktens namn ska stå kvar i brödtexten."""
    brod = _brodtext(text or "").casefold()
    fynd: list[Anmarkning] = []
    saknade: list[str] = []
    for tal in _TAL.findall(villkor or ""):
        ord_ = _TALORD.get(tal, "")
        if tal not in brod and not (ord_ and re.search(rf"\b{ord_}\b", brod)):
            saknade.append(tal)
    if saknade:
        fynd.append(Anmarkning("erbjudande_siffror", f"Stil: villkorens siffror saknas i mejlet: {', '.join(saknade)}",
                               allvarlig=True))
    namn = produktstam(produkt)
    if namn and namn not in brod:
        fynd.append(Anmarkning("erbjudande_produkt", f"Stil: produkten \"{namn}\" nämns inte", allvarlig=True))
    elif namn:
        # Agenten före löftet (Båthuset 2026-10-12: "Vi lovar att du lägger
        # minst 50 % mindre tid …" och Supportagenten först i sista meningen):
        # mottagaren ska veta VAD som lovas innan siffrorna kommer.
        ingang_slut = brod.find("\n\n", brod.find(ingang(text)[:20]) if ingang(text) else 0)
        siffror = [m.start() for t in _TAL.findall(villkor or "") for m in re.finditer(rf"\b{re.escape(t)}\b", brod)
                   if m.start() > ingang_slut]
        if siffror and brod.find(namn, max(ingang_slut, 0)) > min(siffror):
            fynd.append(Anmarkning("agent_efter_loftet",
                                   f"Stil: \"{namn}\" namnges först efter löftet; säg vad agenten gör innan siffrorna",
                                   allvarlig=True))
    return fynd


def produktstam(produkt: str | None) -> str:
    """Produktens kortform utan bestämd form: "Kvittohanteraren" → "kvittohanterare",
    "Supportagenten" → "supportagent", "Iris, leadsagenten" → "iris". Mejlet
    skriver "Vår Kvittohanterare" (outreach_playbook._produktnamn)."""
    namn = (produkt or "").split(",")[0].split("(")[0].strip().casefold()
    for suffix in ("aren", "eren", "en", "n"):
        if namn.endswith(suffix) and len(namn) > len(suffix) + 3:
            return namn[: -len(suffix)] + ("are" if suffix in ("aren", "eren") else "")
    return namn


def _gemensam_fras(a: str, b: str, n: int = 4) -> str | None:
    """Första ordföljden om n ord som två ingångar delar, eller None."""
    oa, ob = _ord(a), _ord(b)
    foljder = {tuple(ob[i : i + n]) for i in range(len(ob) - n + 1)}
    for i in range(len(oa) - n + 1):
        if tuple(oa[i : i + n]) in foljder:
            return " ".join(oa[i : i + n])
    return None


def mot_andra(text: str, andra: Sequence[str]) -> list[Anmarkning]:
    """Batchkontrollen för ETT mejl mot de andra i samma körning."""
    fynd = []
    egen_ingang, egen_uppmaning = ingang(text), uppmaning(text)
    if egen_ingang and any(ingang(t) == egen_ingang for t in andra):
        fynd.append(Anmarkning("samma_ingang", "Stil: samma ingång som ett annat mejl i körningen", allvarlig=True))
    elif egen_ingang and any(konstruktion(t) == konstruktion(text) for t in andra if ingang(t)):
        fynd.append(Anmarkning("samma_konstruktion", "Stil: ingången är byggd som ett annat mejl i körningen",
                               allvarlig=True))
    elif egen_ingang:
        # Samma fras i ingången som ett annat mejl, var den än står
        # (2026-10-15: "tar tid från det arbetet" sist i fem ingångar som
        # började olika).
        fras = next((f for t in andra if (f := _gemensam_fras(egen_ingang, ingang(t)))), None)
        if fras:
            fynd.append(Anmarkning("samma_fras", f"Stil: ingången delar frasen \"{fras}\" med ett annat mejl i körningen",
                                   allvarlig=True))
    if egen_uppmaning and any(uppmaning(t) == egen_uppmaning for t in andra):
        fynd.append(Anmarkning("samma_uppmaning", "Stil: samma uppmaning som ett annat mejl i körningen", allvarlig=True))
    if _FOKUSGREPP.search(_ingangsstycke(text)) and (
        sum(1 for t in andra[-12:] if _FOKUSGREPP.search(_ingangsstycke(t))) > FOKUSGREPP_TAK
    ):
        fynd.append(Anmarkning(
            "samma_grepp", "Stil: \"fokusera på …\" står redan i flera ingångar i körningen; bygg ingången på ett annat sätt",
            allvarlig=True,
        ))
    return fynd


def _ingangsstycke(text: str) -> str:
    """Ingångens två första meningar: greppet står ofta i den andra."""
    return " ".join(_meningar(_brodtext(text))[:2])


def kontrollera_batch(texter: Sequence[str]) -> list[list[Anmarkning]]:
    """Batchkontrollen över en hel körning: per mejl, fynden mot de andra."""
    return [mot_andra(t, [*texter[:i], *texter[i + 1 :]]) for i, t in enumerate(texter)]
