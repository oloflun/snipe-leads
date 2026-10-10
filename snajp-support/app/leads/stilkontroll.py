"""Stilkontrollen: AI- och robotmarkörer i ett kallt mejl, i kod.

Skrivstilen (`agent-core/prompts/leads-skrivstil.md`) säger HUR mejlet ska
låta, och den når modellen i varje utkaststeg. En regel som bara står i en
prompt är en riktning, inte en garanti (samma läxa som gissningsgrinden), så
de markörer som går att känna igen mekaniskt prövas här efteråt:

  tankstreck i brödtext, "Jag ser/såg att", "vi har skapat/utvecklat",
  "X är en AI-agent som", effektivisera/effektivitet/optimera, "i dagens",
  superlativ om oss, utropstecken, två meningar i rad med samma första ord,
  meningar över 25 ord, kolonuppräkningar i löptext och en hälsningsfras
  skriven av modellen (signaturen läggs på i kod).

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
)
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
    """Sista frågan i mejlet, annars sista meningen."""
    meningar = _meningar(_brodtext(text))
    fragor = [m for m in meningar if m.endswith("?")]
    return _norm((fragor or meningar or [""])[-1])


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
    for forra, mening in zip(meningar, meningar[1:]):
        a, b = (re.match(r"[\wÅÄÖåäö]+", m) for m in (forra, mening))
        if a and b and a.group(0).casefold() == b.group(0).casefold():
            lagg("samma_start", f"två meningar i rad börjar med \"{b.group(0)}\"")
            break
    for mening in meningar:
        if len(mening.split()) > MAX_ORD:
            lagg("lang_mening", f"mening över {MAX_ORD} ord: \"{mening[:60]}…\"")
            break
    for mening in meningar:
        if not mening.upper().startswith("PS") and _KOLONLISTA.search(mening):
            lagg("kolonlista", f"kolonuppräkning i löptext: \"{mening[:60]}…\"")
            break
    return Kontrollresultat(text=text, anmarkningar=fynd)


def mot_andra(text: str, andra: Sequence[str]) -> list[Anmarkning]:
    """Batchkontrollen för ETT mejl mot de andra i samma körning."""
    fynd = []
    egen_ingang, egen_uppmaning = ingang(text), uppmaning(text)
    if egen_ingang and any(ingang(t) == egen_ingang for t in andra):
        fynd.append(Anmarkning("samma_ingang", "Stil: samma ingång som ett annat mejl i körningen", allvarlig=True))
    if egen_uppmaning and any(uppmaning(t) == egen_uppmaning for t in andra):
        fynd.append(Anmarkning("samma_uppmaning", "Stil: samma uppmaning som ett annat mejl i körningen", allvarlig=True))
    return fynd


def kontrollera_batch(texter: Sequence[str]) -> list[list[Anmarkning]]:
    """Batchkontrollen över en hel körning: per mejl, fynden mot de andra."""
    return [mot_andra(t, [*texter[:i], *texter[i + 1 :]]) for i, t in enumerate(texter)]
