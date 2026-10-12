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

from ..textkvalitet import Anmarkning, Kontrollresultat
from .grounding_gate import _maska_idiom
from .text_delta import split_sentences

MAX_ORD = 25
#: Skrivstilen: tre stycken och 50–90 ord i brödtexten.
MAX_ORD_MEJL = 90

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
#: Ingången som mall (Anton 2026-10-12): "För företag som ert, som …" stod i
#: mejl efter mejl och läses som ett massutskick, oavsett vad som följer.
_MALL_INGANG = re.compile(
    r"^(?:för\s+(?:ett\s+)?(?:företag|bolag|verksamheter)\s+som\s+(?:ert|er|ditt|dig|din)\b|för\s+er\s+som\b)",
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
_KOLONLISTA = re.compile(r"(?<!\d):(?!\d)[^.?!\n]*(?:,|\soch\s|\ssamt\s)")


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
        if _MALL_INGANG.match(meningar[0]):
            lagg("mall_ingang", f"ingången är en mall: \"{meningar[0][:60]}\"")
        fakta = _REGISTERFAKTA.search(meningar[0])
        if fakta:
            lagg("registerfakta_i_ingangen", f"registerfakta i ingången (mottagaren vet redan): \"{fakta.group(0)}\"")
    for forra, mening in zip(meningar, meningar[1:]):
        a, b = (re.match(r"[\wÅÄÖåäö]+", m) for m in (forra, mening))
        if a and b and a.group(0).casefold() == b.group(0).casefold():
            lagg("samma_start", f"två meningar i rad börjar med \"{b.group(0)}\"")
            break
    # Skrivstilens regel 4 och strukturen (Antons omgång 3): mejlet slutar med
    # en enkel handling, aldrig en fråga, och brödtexten är högst 90 ord.
    if meningar and meningar[-1].endswith("?"):
        lagg("slutar_med_fraga", f"slutar med en fråga i stället för en handling: \"{meningar[-1][:60]}\"")
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


def mot_andra(text: str, andra: Sequence[str]) -> list[Anmarkning]:
    """Batchkontrollen för ETT mejl mot de andra i samma körning."""
    fynd = []
    egen_ingang, egen_uppmaning = ingang(text), uppmaning(text)
    if egen_ingang and any(ingang(t) == egen_ingang for t in andra):
        fynd.append(Anmarkning("samma_ingang", "Stil: samma ingång som ett annat mejl i körningen", allvarlig=True))
    elif egen_ingang and any(konstruktion(t) == konstruktion(text) for t in andra if ingang(t)):
        fynd.append(Anmarkning("samma_konstruktion", "Stil: ingången är byggd som ett annat mejl i körningen",
                               allvarlig=True))
    if egen_uppmaning and any(uppmaning(t) == egen_uppmaning for t in andra):
        fynd.append(Anmarkning("samma_uppmaning", "Stil: samma uppmaning som ett annat mejl i körningen", allvarlig=True))
    return fynd


def kontrollera_batch(texter: Sequence[str]) -> list[list[Anmarkning]]:
    """Batchkontrollen över en hel körning: per mejl, fynden mot de andra."""
    return [mot_andra(t, [*texter[:i], *texter[i + 1 :]]) for i, t in enumerate(texter)]
