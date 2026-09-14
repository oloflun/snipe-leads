"""Bankens kontoutdrag, och avstämningen mot det som är bokfört.

## Varför det här INTE är "ett filformat till"

Ett kvitto är ett UNDERLAG: det bär ett belopp, en moms och en motpart, och
resultatet av att läsa det är ett verifikat. Ett kontoutdrag är motsatsen — det
bär inga underlag alls, bara betalningar som redan skett. Att lägga `text/csv`
i `LASBARA_MIMETYPER` hade skickat det genom avläsningen och producerat
nonsensverifikat för varje rad i en fil med hundra rader.

Frågan ett kontoutdrag svarar på är en annan: *stämmer det jag bokfört med det
som faktiskt rörde kontot?* Det är en AVSTÄMNING, och den har egen matte.

## Vad modulen gör, och vad den avsiktligt inte gör

Gör: läser filen, normaliserar raderna, och matchar dem mot underlagen för
perioden på belopp och datum. Rapporterar tre högar — matchade, banktransaktioner
utan underlag, och underlag utan banktransaktion.

Gör INTE: skriver ingenting. Ingen tabell, inget verifikat, ingen status som
ändras. Avstämningen är en LÄSNING, och det är hela skälet till att den kunde
byggas utan att röra lagret.

Det är också varför den är ofarlig att köra om: två körningar på samma fil ger
samma svar och lämnar inga spår.

## Matchningen är avsiktligt trubbig

Ett belopp och ett datum inom ett fönster. Ingen textmatchning mot motpart:
bankens beskrivning ("KORTKOP 240814 CIRCLE K 12345") liknar sällan kvittots
motpartsnamn tillräckligt för att en fuzzy-matchning ska bli annat än
gissningar, och en felaktig matchning är värre än ingen — den döljer ett
saknat underlag.

Fönstret finns för att kortköp bokförs hos banken en till tre dagar efter
inköpsdatumet på kvittot. Det är den vanligaste orsaken till att en korrekt
avstämning ser felaktig ut.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from .math import BeloppsfelError, till_decimal
from .underlag import normalisera_datum

#: Tak per fil. Ett års kontoutdrag för ett litet bolag ligger långt under.
MAX_BYTES = 2 * 1024 * 1024

#: Hur många dagar en bankrad får ligga från underlagets datum och ändå räknas
#: som samma affär. Tre dagar täcker helgen mellan ett fredagsköp och måndagens
#: bokföring hos banken.
DAGSFONSTER = 3


class KontoutdragsfelError(ValueError):
    """Filen gick inte att läsa som ett kontoutdrag."""


@dataclass(frozen=True)
class Banktransaktion:
    datum: date
    text: str
    #: Negativt = pengar ut. Bankens eget tecken behålls.
    belopp: Decimal


@dataclass
class Avstamning:
    matchade: list[dict[str, Any]] = field(default_factory=list)
    saknar_underlag: list[dict[str, Any]] = field(default_factory=list)
    saknar_banktransaktion: list[dict[str, Any]] = field(default_factory=list)

    def as_report(self) -> list[str]:
        rader = []
        if self.saknar_underlag:
            rader.append(
                f"{len(self.saknar_underlag)} banktransaktion"
                f"{'er' if len(self.saknar_underlag) != 1 else ''} saknar underlag."
            )
        if self.saknar_banktransaktion:
            rader.append(
                f"{len(self.saknar_banktransaktion)} underlag saknar motsvarande "
                "banktransaktion."
            )
        if not rader:
            rader.append("Allt stämmer: varje banktransaktion har ett underlag och tvärtom.")
        return rader


#: Kolumnnamn vi känner igen, gemener. Svenska banker exporterar med olika
#: rubriker och ibland på engelska; listan är uppräknad i stället för gissad,
#: av samma skäl som kontoplanen är det — ett gissat kolumnval blir ett tyst
#: fel i en siffra någon deklarerar på.
_DATUMKOLUMNER = (
    "bokföringsdatum",
    "bokforingsdatum",
    "transaktionsdatum",
    "datum",
    "date",
    "bokfört",
    "valutadatum",
)
_TEXTKOLUMNER = ("text", "beskrivning", "specifikation", "meddelande", "description", "referens")
_BELOPPSKOLUMNER = ("belopp", "amount", "summa", "transaktionsbelopp")


def _hitta(rubriker: list[str], kandidater: tuple[str, ...]) -> str | None:
    normaliserade = {r.strip().lower().lstrip("﻿"): r for r in rubriker}
    for kandidat in kandidater:
        if kandidat in normaliserade:
            return normaliserade[kandidat]
    # Delsträngsmatchning som andra försök: "Belopp (SEK)" ska hittas av "belopp".
    for nyckel, original in normaliserade.items():
        if any(kandidat in nyckel for kandidat in kandidater):
            return original
    return None


def las_kontoutdrag(data: bytes) -> list[Banktransaktion]:
    """CSV in, transaktioner ut.

    Avgränsaren SNIFFAS och antas inte: svenska banker exporterar med semikolon
    (eftersom kommat är decimaltecken), men engelskspråkiga exporter från samma
    banker använder komma. Ett hårdkodat antagande gör att den ena filen tyst
    läses som EN kolumn, alltså noll transaktioner och en avstämning som säger
    att allt stämmer.

    Teckenkodningen prövas i tur och ordning. Windows-1252 är vanligast i
    exporter från svenska banker, och en UTF-8-läsning av den filen ger å/ä/ö
    som skräp i motpartstexten — läsbart nog att passera, fel nog att irritera.
    """
    if not data:
        raise KontoutdragsfelError("filen är tom")
    if len(data) > MAX_BYTES:
        raise KontoutdragsfelError(
            f"filen är {len(data) // 1024 // 1024} MB, taket är {MAX_BYTES // 1024 // 1024} MB"
        )

    text: str | None = None
    for kodning in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = data.decode(kodning)
            break
        except UnicodeDecodeError:
            continue
    if text is None:  # pragma: no cover — latin-1 avkodar allt
        raise KontoutdragsfelError("filens teckenkodning gick inte att läsa")

    prov = text[:4096]
    try:
        dialekt = csv.Sniffer().sniff(prov, delimiters=";,\t")
        avgransare = dialekt.delimiter
    except csv.Error:
        # Sniffern misslyckas på filer med en enda kolumn eller udda citattecken.
        # Semikolon är det vanligaste i svenska exporter; välj det före komma.
        avgransare = ";" if prov.count(";") >= prov.count(",") else ","

    lasare = csv.DictReader(io.StringIO(text), delimiter=avgransare)
    rubriker = [r for r in (lasare.fieldnames or []) if r]
    if not rubriker:
        raise KontoutdragsfelError("filen saknar rubrikrad")

    kol_datum = _hitta(rubriker, _DATUMKOLUMNER)
    kol_belopp = _hitta(rubriker, _BELOPPSKOLUMNER)
    kol_text = _hitta(rubriker, _TEXTKOLUMNER)

    if kol_datum is None or kol_belopp is None:
        raise KontoutdragsfelError(
            "hittar ingen datum- och beloppskolumn. Rubrikerna var: "
            + ", ".join(rubriker[:8])
        )

    transaktioner: list[Banktransaktion] = []
    for rad in lasare:
        rat_datum = (rad.get(kol_datum) or "").strip()
        rat_belopp = (rad.get(kol_belopp) or "").strip()
        if not rat_datum or not rat_belopp:
            continue

        datum = normalisera_datum(rat_datum)
        if datum is None:
            continue
        try:
            # Minustecknet behålls: riktningen är information, inte brus.
            negativ = rat_belopp.lstrip().startswith("-")
            belopp = till_decimal(rat_belopp.lstrip().lstrip("-"))
        except (BeloppsfelError, ValueError):
            continue

        transaktioner.append(
            Banktransaktion(
                datum=datum,
                text=(rad.get(kol_text) or "").strip() if kol_text else "",
                belopp=-belopp if negativ else belopp,
            )
        )

    if not transaktioner:
        raise KontoutdragsfelError(
            "hittade inga läsbara rader. Kontrollera att filen är ett "
            "kontoutdrag och inte en sammanställning."
        )
    return transaktioner


def stam_av(
    transaktioner: list[Banktransaktion], underlag: list[dict[str, Any]]
) -> Avstamning:
    """Matchar banktransaktioner mot underlag på belopp och datum.

    Beloppet jämförs på ABSOLUTVÄRDE. Ett kvitto bär bruttot som ett positivt
    tal med en `riktning`, medan banken bär tecknet i beloppet — att jämföra
    dem som de står hade gett noll träffar på varje kostnad.

    Varje underlag kan matchas EN gång. Utan den bokföringen matchar två
    likadana kvitton på 250 kr mot samma bankrad, och avstämningen påstår att
    ett underlag saknas när det i själva verket finns två.
    """
    kvar = [
        u
        for u in underlag
        if u.get("datum") and u.get("brutto") is not None
    ]
    anvanda: set[int] = set()
    resultat = Avstamning()

    for tx in transaktioner:
        träff_index: int | None = None
        for i, u in enumerate(kvar):
            if i in anvanda:
                continue
            u_datum = normalisera_datum(str(u["datum"]))
            if u_datum is None:
                continue
            if abs(till_decimal(u["brutto"])) != abs(tx.belopp):
                continue
            if abs((u_datum - tx.datum).days) > DAGSFONSTER:
                continue
            träff_index = i
            break

        if träff_index is None:
            resultat.saknar_underlag.append(
                {
                    "datum": tx.datum.isoformat(),
                    "text": tx.text,
                    "belopp": f"{tx.belopp:f}",
                }
            )
        else:
            anvanda.add(träff_index)
            u = kvar[träff_index]
            resultat.matchade.append(
                {
                    "datum": tx.datum.isoformat(),
                    "text": tx.text,
                    "belopp": f"{tx.belopp:f}",
                    "underlag_id": u.get("id"),
                    "motpart": u.get("motpart"),
                }
            )

    for i, u in enumerate(kvar):
        if i not in anvanda:
            resultat.saknar_banktransaktion.append(
                {
                    "underlag_id": u.get("id"),
                    "datum": str(u.get("datum")),
                    "motpart": u.get("motpart"),
                    "brutto": f"{till_decimal(u['brutto']):f}",
                }
            )

    return resultat
