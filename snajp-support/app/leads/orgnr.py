"""Svenskt organisationsnummer — validering, och vad valideringen INTE bevisar.

## Vad kontrollsiffran faktiskt säger

Ett organisationsnummer är tio siffror där den sista är en kontrollsiffra
beräknad med Luhn-algoritmen (modulo 10). Kontrollen fångar **skrivfel**: en
felskriven siffra och de flesta omkastningar av två intilliggande siffror ger
fel kontrollsiffra.

Den säger INGENTING om att bolaget existerar, är aktivt, eller heter det
användaren påstår. `556000-0001` kan vara giltigt enligt Luhn och ändå aldrig
ha registrerats. Att veta det kräver Näringslivsregistret, och den licensen har
vi inte — samma gräns som `sources/registry.py` beskriver.

Det är därför funktionen heter `validera_format` och inte `verifiera_bolag`.
Ett namn som lovar mer än koden håller är hur nästa person bygger ett
antagande på en kontroll som inte gjordes.

## Varför tredje siffran måste vara minst 2

Det är så man skiljer ett organisationsnummer från ett personnummer. Hos
Skatteverket har juridiska personer alltid en tredje siffra ≥ 2, eftersom
den siffran hos en fysisk person är en månad (01–12).

Kontrollen finns här av ett integritetsskäl, inte ett formellt: utan den kan
någon skriva in sitt personnummer i ett fält vi behandlar som företagsdata,
och då lagrar vi en känslig personuppgift i en kolumn som aldrig var avsedd
för det och som inte har det skyddet.
"""

from __future__ import annotations

import re

#: Första siffran anger juridisk form. Används för att kunna säga något
#: begripligt tillbaka, inte för att neka — listan är inte uttömmande.
_GRUPPER = {
    "2": "stat, landsting eller kommun",
    "5": "aktiebolag",
    "6": "enkelt bolag",
    "7": "ekonomisk förening eller bostadsrättsförening",
    "8": "ideell förening eller stiftelse",
    "9": "handelsbolag eller kommanditbolag",
}


class OgiltigtOrgnrError(ValueError):
    """Formatfel. Meddelandet går rakt ut till användaren och ska säga vad som
    är fel, inte bara att något är det."""


def _siffror(rå: object) -> str:
    return "".join(t for t in str(rå or "") if t.isdigit())


def normalisera(rå: object) -> str:
    """'556824-9022', '5568249022' och '16556824-9022' blir alla '5568249022'.

    Prefixet 16 förekommer i myndighetsregister (sekelmarkör) och ska bort
    innan kontrollsiffran räknas — annars faller giltiga nummer.
    """
    siffror = _siffror(rå)
    if len(siffror) == 12 and siffror.startswith("16"):
        siffror = siffror[2:]
    return siffror


def _luhn_stammer(siffror: str) -> bool:
    summa = 0
    # Luhn räknar från höger: varannan siffra dubbleras, med start på den
    # NÄST sista. Kontrollsiffran själv ingår i summan.
    for index, tecken in enumerate(reversed(siffror)):
        värde = int(tecken)
        if index % 2 == 1:
            värde *= 2
            if värde > 9:
                värde -= 9
        summa += värde
    return summa % 10 == 0


_PERSONNUMMER_SVAR = (
    "Det där ser ut som ett personnummer, inte ett organisationsnummer. "
    "Skriv inte in ditt personnummer här — vi behöver bolagets nummer, det som "
    "står på fakturor och registreringsbeviset."
)


def _neka_personnummer(siffror: str) -> None:
    """Två former att fånga.

    TOLV siffror som börjar på 19 eller 20 är ett personnummer med sekel. Tio
    siffror vars TREDJE siffra är under 2 är ett personnummer utan sekel — hos
    en fysisk person är den siffran en månad (01–12), och juridiska personer
    har därför alltid ≥ 2 där.
    """
    if len(siffror) == 12 and siffror[:2] in ("19", "20"):
        raise OgiltigtOrgnrError(_PERSONNUMMER_SVAR)
    if len(siffror) == 10 and int(siffror[2]) < 2:
        raise OgiltigtOrgnrError(_PERSONNUMMER_SVAR)


def validera_format(rå: object) -> str:
    """Returnerar tio siffror utan bindestreck, eller höjer.

    Se modulens docstring: detta validerar FORMATET. Att bolaget finns är en
    annan fråga som kräver ett register vi inte har.
    """
    siffror = normalisera(rå)

    if not siffror:
        raise OgiltigtOrgnrError("Fyll i organisationsnumret.")

    # Personnummerkontrollen ligger FÖRE längdkontrollen. Ett tolvsiffrigt
    # personnummer (19850312-1234) hade annars fällts som "fel längd", och
    # användaren hade rättat längden i stället för att förstå att fältet inte
    # ska innehålla ett personnummer alls. Rätt fel är viktigare än att fel
    # över huvud taget ges.
    _neka_personnummer(siffror)

    if len(siffror) != 10:
        raise OgiltigtOrgnrError(
            f"Ett organisationsnummer har tio siffror, det här har {len(siffror)}. "
            "Skriv det som 556824-9022."
        )

    if not _luhn_stammer(siffror):
        raise OgiltigtOrgnrError(
            "Kontrollsiffran stämmer inte, vilket nästan alltid betyder ett "
            "skrivfel. Kontrollera numret mot ett fakturaunderlag eller "
            "registreringsbeviset."
        )

    return siffror


def formatera(rå: object) -> str:
    """'5568249022' → '556824-9022'. Formen folk känner igen."""
    siffror = normalisera(rå)
    return f"{siffror[:6]}-{siffror[6:]}" if len(siffror) == 10 else str(rå or "")


def juridisk_form(rå: object) -> str | None:
    """Vad första siffran antyder. None när vi inte känner igen den."""
    siffror = normalisera(rå)
    return _GRUPPER.get(siffror[:1]) if siffror else None


# -- Webbplatsen ------------------------------------------------------------


def harled_webbplats(epost: object) -> str:
    """Gissar bolagets webbplats ur en e-postadress.

    Finns för att slippa be kunden om en uppgift vi nästan alltid kan räkna
    fram. Fältet är ändå redigerbart — gissningen ska föreslå, aldrig bestämma.

    Publika e-postdomäner ger tom sträng: `anna@gmail.com` säger ingenting om
    var bolaget har sin sajt, och att föreslå `gmail.com` hade fått agenten att
    researcha Google.
    """
    text = str(epost or "").strip().lower()
    if "@" not in text:
        return ""
    domän = text.rsplit("@", 1)[-1].strip()

    publika = {
        "gmail.com", "hotmail.com", "outlook.com", "live.se", "live.com",
        "yahoo.com", "icloud.com", "telia.com", "bredband.net", "spray.se",
        "comhem.se", "me.com", "msn.com",
    }
    if not domän or domän in publika or "." not in domän:
        return ""
    return f"https://{domän}"
