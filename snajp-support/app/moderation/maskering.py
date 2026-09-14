"""Maskerar personnummer innan kundens text lämnar huset.

## Varför

Innehållet i ett supportmejl är OKONTROLLERAT. En konsument som skriver till en
kundtjänst skriver vad hen tycker är relevant, och det inkluderar
personnummer — "mitt personnummer är 19850101-1234, kan ni kolla min order?".
Vi kan inte styra det och ska inte låtsas att vi kan.

Hela mejltexten skickas till modelleverantören. Det är den enskilt största
öppna risken i [DPIA:n](../../../docs/dpia_supportagenten.md), R1, och den kan
i grunden bara stängas i AVTAL — vilken leverantör, på vilken nivå, med vilket
åtagande om att innehållet inte används för produktförbättring.

Den här modulen stänger den inte. Den gör den mindre: den tar bort den
vanligaste och mest identifierande formen av känslig uppgift innan anropet
går. Ett maskerat mejl som ändå råkar innehålla en hälsouppgift i löptext är
fortfarande ett problem — läs inte det här som att R1 är löst.

## Varför Luhn OCH datumkontroll, och inte bara ett mönster

Ett mönster som matchar tio siffror maskerar ordernummer, fakturanummer och
telefonnummer. Då blir texten obegriplig för modellen, svaren sämre, och
någon tar bort maskeringen — vilket är hur en spärr dör.

Ett svenskt person- och samordningsnummer måste uppfylla två saker samtidigt:
de sex första siffrorna ska vara ett giltigt datum (samordningsnummer har
dag + 60), och hela numret ska passera Luhn. Kombinationen gör falska utslag
sällsynta nog att maskeringen kan stå på i drift.

Falskt NEGATIVT är fortfarande möjligt — ett personnummer skrivet med
mellanslag mellan varje siffra går igenom. Den luckan är känd och accepterad:
alternativet är ett grovt mönster som fäller allt, och det hade blivit
avstängt.
"""

from __future__ import annotations

import re
from datetime import date

#: Vad ett maskerat nummer ersätts med. Läsbart för modellen — den ska förstå
#: ATT kunden uppgav ett personnummer, bara inte vilket, så att svaret kan
#: hänvisa till det ("vi ser numret du uppgav") utan att bära det.
PLATSHALLARE = "[personnummer]"

#: 10 eller 12 siffror, med valfri avskiljare. `+` används för den som fyllt
#: 100 år och hör alltså med.
_KANDIDAT = re.compile(r"(?<!\d)(\d{2})?(\d{6})([-+]?)(\d{4})(?!\d)")


def _luhn_ok(siffror: str) -> bool:
    """Luhn över de tio sista siffrorna, som Skatteverket definierar den."""
    tio = siffror[-10:]
    if len(tio) != 10 or not tio.isdigit():
        return False
    summa = 0
    for i, tecken in enumerate(tio):
        varde = int(tecken) * (2 if i % 2 == 0 else 1)
        summa += varde - 9 if varde > 9 else varde
    return summa % 10 == 0


def _datum_ok(sex: str) -> bool:
    """De sex första siffrorna ska vara ett giltigt datum.

    Samordningsnummer har dagen + 60, så 850161 är giltigt och betyder den
    första. Utan den regeln maskeras inte samordningsnummer alls, och de bärs
    just av personer som ofta har mest att förlora på en läcka.
    """
    ar, manad, dag = int(sex[0:2]), int(sex[2:4]), int(sex[4:6])
    if dag > 60:
        dag -= 60
    if not (1 <= manad <= 12 and 1 <= dag <= 31):
        return False
    try:
        # Århundradet är okänt här; 2000 duger för att pröva dag-i-månad.
        date(2000 + ar, manad, dag)
    except ValueError:
        return False
    return True


def ar_personnummer(text: str) -> bool:
    """Om strängen ensam är ett person- eller samordningsnummer."""
    traff = _KANDIDAT.fullmatch(text.strip())
    if not traff:
        return False
    return _ar_traff_giltig(traff)


def _ar_traff_giltig(traff: re.Match) -> bool:
    sekel, sex, _, sista = traff.groups()
    if not _datum_ok(sex):
        return False
    return _luhn_ok((sekel or "") + sex + sista)


def maskera_personnummer(text: str) -> str:
    """Byter ut varje person- och samordningsnummer mot `PLATSHALLARE`.

    Idempotent: platshållaren innehåller inga siffror, så en andra körning
    hittar ingenting att maskera.
    """
    if not text:
        return text

    def ersatt(traff: re.Match) -> str:
        return PLATSHALLARE if _ar_traff_giltig(traff) else traff.group(0)

    return _KANDIDAT.sub(ersatt, text)


def antal_maskerade(text: str) -> int:
    """Hur många nummer som skulle maskeras. För loggning och mätning —
    ANTALET får loggas, aldrig numren."""
    return sum(1 for traff in _KANDIDAT.finditer(text or "") if _ar_traff_giltig(traff))
