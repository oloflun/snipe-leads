"""SNI-koder — branschnischen, med svenskt klartextnamn.

SNI 2007 är SCB:s näringsgrensindelning. Den fullständiga tabellen har drygt
800 koder; den här filen har de som faktiskt förekommer bland svenska
småföretag. Det är ett medvetet urval, inte en ofullständig kopia.

## Varför en uppslagstabell alls

UI:t ska kunna visa "43.220 — VVS-arbeten" i stället för "43.220". En kund som
väljer bransch ur en lista av rena sifferkoder väljer fel, och ett felvalt
targetingfilter upptäcks först när mejlen gått till fel bransch.

## Vad som händer med en kod vi inte känner till

Den släpps igenom och visas som sig själv. Tabellen är ett hjälpmedel för
läsbarhet, inte en vitlista — SCB har 800 koder och vi har ~40. Att neka en
giltig SNI-kod bara för att den saknas här hade gjort filen till en spärr den
aldrig var tänkt att vara. FORMATET valideras däremot strikt (`validera_kod`),
eftersom ett trasigt format tyder på ett inmatningsfel och inte på en nisch vi
råkar sakna.
"""

from __future__ import annotations

import re

#: Koden som SCB skriver den: två siffror, punkt, tre siffror. Vissa register
#: skriver den utan punkt eller med bara två decimaler — `normalisera_kod`
#: tar hand om det innan valideringen.
_KOD_MONSTER = re.compile(r"^\d{2}\.\d{3}$")

#: Urvalet: bygg, hantverk, fordon, handel, restaurang, IT, konsult, tjänster,
#: vård och tillverkning. Det som en småföretagsnisch i Umeå eller Göteborg
#: rimligen faller inom.
SNI_NAMN: dict[str, str] = {
    # Tillverkning och livsmedel
    "10.710": "Bagerier och tillverkning av färska bakverk",
    "16.230": "Tillverkning av byggnadssnickerier",
    "25.620": "Metallbearbetning",
    "31.090": "Tillverkning av övriga möbler",
    "33.120": "Reparation av maskiner",
    # Bygg och installation
    "41.200": "Byggande av bostadshus och andra byggnader",
    "43.120": "Mark- och grundarbeten",
    "43.210": "Elinstallationer",
    "43.220": "VVS-arbeten",
    "43.290": "Andra bygginstallationer",
    "43.320": "Byggnadssnickeriarbeten",
    "43.330": "Golv- och väggbeläggningsarbeten",
    "43.341": "Måleriarbeten",
    "43.910": "Takarbeten",
    "43.990": "Övrig specialiserad bygg- och anläggningsverksamhet",
    # Fordon och handel
    "45.200": "Underhåll och reparation av motorfordon",
    "46.900": "Övrig partihandel",
    "47.111": "Livsmedelshandel med brett sortiment",
    "47.190": "Övrig detaljhandel med brett sortiment",
    "47.520": "Detaljhandel med järnhandelsvaror och byggmaterial",
    "47.910": "Detaljhandel via postorder och internet",
    # Transport
    "49.410": "Vägtransport, godstrafik",
    "52.100": "Magasinering och varulagring",
    # Besöksnäring
    "55.101": "Hotell och konferensanläggningar",
    "56.100": "Restaurangverksamhet",
    "56.210": "Cateringverksamhet",
    # IT och information
    "58.290": "Utgivning av annan programvara",
    "62.010": "Dataprogrammering",
    "62.020": "Datakonsultverksamhet",
    "62.030": "Datordrifttjänster",
    "63.110": "Databehandling, hosting och därmed sammanhängande tjänster",
    # Finans, juridik, konsult
    "68.310": "Fastighetsförmedling",
    "69.201": "Redovisning och bokföring",
    "69.202": "Revision",
    "70.220": "Konsultverksamhet avseende företags organisation",
    "71.121": "Teknisk konsultverksamhet inom bygg- och anläggningsteknik",
    "71.129": "Övrig teknisk konsultverksamhet",
    "73.110": "Reklambyråverksamhet",
    "74.101": "Industri- och produktdesignverksamhet",
    "74.102": "Grafisk formgivning",
    "74.201": "Fotografverksamhet",
    # Företagstjänster
    "78.200": "Personaluthyrning",
    "80.100": "Säkerhetsverksamhet",
    "81.210": "Lokalvård",
    "81.300": "Skötsel och underhåll av grönytor",
    "82.110": "Kombinerade kontorstjänster",
    # Vård och personliga tjänster
    "86.230": "Tandläkarverksamhet",
    "86.900": "Övrig hälso- och sjukvård",
    "95.110": "Reparation av datorer och kringutrustning",
    "96.021": "Hår- och skönhetsvård",
}


class OgiltigSniKodError(ValueError):
    """Formatfel i en SNI-kod. Se modulens docstring om varför formatet
    valideras men inte innehållet."""


def normalisera_kod(rå: object) -> str:
    """'43220', '43.22' och ' 43.220 ' blir alla '43.220'.

    Register skriver koden olika. Att normalisera före jämförelsen är enda
    sättet att slippa ett filter som missar hälften av träffarna för att
    källan råkade utelämna en punkt.
    """
    text = str(rå or "").strip()
    siffror = "".join(tecken for tecken in text if tecken.isdigit())
    if not siffror:
        return text
    # Två decimaler är en giltig SNI-nivå (43.22); vi fyller ut till tre så
    # att jämförelsen sker på en enda form.
    if len(siffror) == 4:
        siffror += "0"
    if len(siffror) == 5:
        return f"{siffror[:2]}.{siffror[2:]}"
    return text


def validera_kod(rå: object) -> str:
    kod = normalisera_kod(rå)
    if not _KOD_MONSTER.match(kod):
        raise OgiltigSniKodError(
            f"{rå!r} är inte en giltig SNI-kod. Formatet är två siffror, punkt, "
            "tre siffror — till exempel 43.220 för VVS-arbeten."
        )
    return kod


def namn_for_kod(rå: object) -> str:
    """Klartextnamnet, eller koden själv om vi inte känner den."""
    kod = normalisera_kod(rå)
    return SNI_NAMN.get(kod, kod)


def beskriv_kod(rå: object) -> str:
    """'43.220 — VVS-arbeten'. Raden UI:t visar."""
    kod = normalisera_kod(rå)
    namn = SNI_NAMN.get(kod)
    return f"{kod} — {namn}" if namn else kod


def matchar_sni(
    prospektets_kod: object,
    *,
    inkludera: list[str] | tuple[str, ...] = (),
    exkludera: list[str] | tuple[str, ...] = (),
) -> bool:
    """Positiv och negativ branschfiltrering i ett anrop.

    Exkludering vinner alltid över inkludering. En kund som både bett om
    "bygg" och undantagit "takarbeten" menar det senare som ett undantag från
    det förra, inte som en motsägelse.

    Saknar prospektet SNI-kod och kunden HAR satt inkluderingskrav blir svaret
    False: ett okänt bolag uppfyller inte ett krav, det slipper det inte.
    """
    kod = normalisera_kod(prospektets_kod)

    if kod and any(kod == normalisera_kod(e) for e in exkludera):
        return False

    if not inkludera:
        return True

    if not kod:
        return False

    return any(kod == normalisera_kod(i) for i in inkludera)
