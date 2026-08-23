"""Från fil till fält — utan att gissa, och utan att spara filen.

## Filen sparas aldrig

Ett kvitto eller en faktura kan innehålla personnummer och lönebelopp. Vi tar
emot bytes, läser ut text, och behåller ENDAST de utlästa fälten plus en
sha256 av originalet. Samma val som `agent/vision.py` gör idag för
supportchattens bilder, och av samma skäl: en fil vi inte har är en fil som
inte kan läcka, och den behöver ingen gallringsrutin.

ponytail: taket är namngivet. Ska originalet bevaras — bokföringslagen 7 kap.
kräver det av den som FÖR bokföringen — är det ett objektlager plus en
retentionspolicy, och ett eget beslut. Vi föreslår; kunden bokför i sitt eget
system och arkiverar där.

Hashen finns för att kunna svara på "har vi sett det här kvittot förut?" utan
att ha kvar det.

## Arbetsdelningen mot modellen

Koden hämtar TEXT ur filen (pypdf för PDF, vision-sidovagnen för bild).
Modellen läser texten och svarar med fält. Koden normaliserar fälten och
avvisar det som inte går att tolka — den fyller aldrig i ett tomt fält.
Grinden i `verifieringsgrind.py` gör resten.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from decimal import Decimal

from .math import BeloppsfelError, MOMSSATSER, till_decimal

#: Format vi kan läsa. Allt annat avvisas vid API-gränsen med sitt namn, i
#: stället för att tyst ge ett tomt underlag.
LASBARA_MIMETYPER: tuple[str, ...] = (
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
)

#: Tak per fil. En kvittobild är sällan över några MB, och ett tak som sätts
#: här är ett tak som inte behöver sättas i varje anropsväg.
MAX_BYTES = 12 * 1024 * 1024


class UnderlagsfelError(ValueError):
    """Filen går inte att läsa alls. Skilt från "fält saknas", som är
    grindens sak och hamnar i granskningskön."""


def sha256_av(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def kontrollera_fil(data: bytes, mimetyp: str) -> None:
    if mimetyp not in LASBARA_MIMETYPER:
        tillatna = ", ".join(LASBARA_MIMETYPER)
        raise UnderlagsfelError(f"{mimetyp} går inte att läsa (kan läsa: {tillatna})")
    if not data:
        raise UnderlagsfelError("filen är tom")
    if len(data) > MAX_BYTES:
        raise UnderlagsfelError(
            f"filen är {len(data) // 1024 // 1024} MB, taket är {MAX_BYTES // 1024 // 1024} MB"
        )


def las_pdf_text(data: bytes) -> str:
    """Textlagret i en PDF.

    En skannad PDF har inget textlager och ger tom sträng — det är inte ett
    fel utan ett svar, och anroparen ska då gå bildvägen i stället. Att
    returnera "" och låta grinden fälla på saknade fält vore att förlora
    informationen om VARFÖR, så vi säger det uttryckligen.
    """
    try:
        from pypdf import PdfReader
    except ImportError as orsak:  # pragma: no cover — beroendet står i requirements
        raise UnderlagsfelError("pypdf saknas i miljön") from orsak

    import io

    try:
        reader = PdfReader(io.BytesIO(data))
        delar = [sida.extract_text() or "" for sida in reader.pages]
    except Exception as orsak:  # noqa: BLE001 — pypdf kastar många olika typer
        raise UnderlagsfelError(f"PDF:en gick inte att läsa: {orsak}") from orsak

    return "\n".join(delar).strip()


#: Prompten till vision-sidovagnen. Skild från `vision._VISION_PROMPT`, som är
#: skriven för kundtjänstärenden — en bokföringsbild ska läsas som ett kvitto,
#: inte beskrivas som en bild.
BILDPROMPT = (
    "Det här är ett kvitto eller en faktura. Skriv av ALL text du ser, ordagrant, "
    "rad för rad. Hitta inte på något. Kan du inte läsa en rad, skriv [oläsligt] "
    "på den raden. Tolka inte och sammanfatta inte — skriv av."
)


async def las_bild_text(data_url: str) -> str:
    """Text ur en kvittobild via den befintliga vision-klienten.

    Återanvänder `agent.llm.get_vision_client` — samma underbiträde som redan
    står i personuppgiftsbiträdesavtalet (se vision.py). En andra
    bildtjänst hade krävt ett nytt avtal per kund.
    """
    from ..agent.llm import get_vision_client

    client = get_vision_client()
    if client is None:
        raise UnderlagsfelError(
            "ingen bildklient är konfigurerad — ladda upp kvittot som PDF eller "
            "mata in uppgifterna för hand"
        )

    from ..config import get_settings

    settings = get_settings()
    svar = await client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": BILDPROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
    return (svar.choices[0].message.content or "").strip()


# -- Normalisering av modellens fält ---------------------------------------

_DATUM_MONSTER = (
    "%Y-%m-%d",
    "%Y%m%d",
    "%d/%m/%Y",
    "%d.%m.%Y",
)


def normalisera_datum(varde: object) -> date | None:
    """Ett datum, eller None. Aldrig dagens datum som fallback.

    Ett kvitto som bokförs på fel dag hamnar i fel period, och fel period är
    fel momsdeklaration. Hellre en brist grinden fäller på.
    """
    if isinstance(varde, date) and not isinstance(varde, datetime):
        return varde
    if isinstance(varde, datetime):
        return varde.date()
    if not isinstance(varde, str) or not varde.strip():
        return None
    text = varde.strip()
    for monster in _DATUM_MONSTER:
        try:
            return datetime.strptime(text, monster).date()
        except ValueError:
            continue
    return None


def _fran_json_tal(varde: object) -> object:
    """DEN ENDA platsen där en float får bli ett belopp.

    `math.till_decimal` avvisar float, och det är rätt överallt utom här.
    Skälet: modellens svar går genom `json.loads`, och JSON-talet `1250.5`
    blir en Python-float innan vår kod ser det. Utan den här bron hade varje
    kvitto där modellen svarade med ett tal i stället för en sträng blivit ett
    underlag med "saknas: brutto" — alltså hade grinden eskalerat allt, och
    felet hade sett ut som att modellen inte kunde läsa kvitton.

    `Decimal(str(f))` och inte `Decimal(f)`: `str` ger den kortaste sträng som
    round-trippar tillbaka till samma float, alltså "0.1" och inte
    "0.1000000000000000055511151231257827". Konverteringen är exakt i den
    meningen som betyder något — den bevarar talet modellen skrev. Det farliga
    med float är ARITMETIKEN, och den sker aldrig på den här sidan.

    Uppströms ber prompten dessutom om strängar (se BILDPROMPT och
    playbookens utdatakontrakt). Det här är bältet, inte hängslena.
    """
    if isinstance(varde, float) and not isinstance(varde, bool):
        return str(varde)
    return varde


def normalisera_momssats(varde: object) -> Decimal | None:
    """25, "25", "25 %", "0.25" och Decimal("0.25") ger alla Decimal("0.25").

    Regeln som skiljer procent från andel: ett värde > 1 är procent. Den är
    entydig här och bara här — svenska satser är 6/12/25 som procent och
    0.06/0.12/0.25 som andel, och de två mängderna överlappar inte.

    En sats som inte finns i Sverige ger None, inte närmaste giltiga.
    """
    if varde is None:
        return None
    varde = _fran_json_tal(varde)
    if isinstance(varde, str):
        rensad = varde.replace("%", "").strip()
        if not rensad:
            return None
        varde = rensad
    try:
        tal = till_decimal(varde, falt="momssats")
    except BeloppsfelError:
        return None
    if tal > 1:
        tal = tal / Decimal(100)
    # Normalisera skalan så att Decimal("0.250") jämförs lika med Decimal("0.25").
    tal = tal.normalize()
    for sats in MOMSSATSER:
        if tal == sats:
            return sats
    return None


def normalisera_belopp(varde: object) -> Decimal | None:
    """Ett belopp, eller None. Går strängen inte att tolka blir det None —
    inte noll. Se `verifieringsgrind`: 0 kr är ett svar, tomt är det inte."""
    if varde is None:
        return None
    varde = _fran_json_tal(varde)
    if isinstance(varde, str):
        # "1 250,00 kr" -> "1250.00". Valutakod och tusenavskiljare bort.
        rensad = re.sub(r"(?i)\b(kr|sek|kronor)\b", "", varde).strip()
        if not rensad:
            return None
        varde = rensad
    try:
        return till_decimal(varde, falt="belopp")
    except BeloppsfelError:
        return None


def normalisera_falt(rat: dict) -> dict:
    """Modellens råa svar till fält grinden kan pröva.

    Fält som inte går att tolka UTELÄMNAS. De hamnar då i grindens lista över
    brister, med sitt namn, i stället för att bära ett gissat värde vidare.
    """
    normaliserat: dict = {}

    datum = normalisera_datum(rat.get("datum"))
    if datum is not None:
        normaliserat["datum"] = datum

    brutto = normalisera_belopp(rat.get("brutto"))
    if brutto is not None:
        normaliserat["brutto"] = brutto

    sats = normalisera_momssats(rat.get("momssats"))
    if sats is not None:
        normaliserat["momssats"] = sats

    motpart = rat.get("motpart")
    if isinstance(motpart, str) and motpart.strip():
        normaliserat["motpart"] = motpart.strip()

    riktning = rat.get("riktning")
    if riktning in ("intakt", "kostnad"):
        normaliserat["riktning"] = riktning

    kategori = rat.get("kategori")
    if isinstance(kategori, str) and kategori.strip():
        normaliserat["kategori"] = kategori.strip()

    return normaliserat
