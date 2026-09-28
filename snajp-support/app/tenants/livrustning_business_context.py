"""Produktdatan leads-agenten säljer FÖR Livrustning — inte för Snajp.

Motsvarar `business_contexts` för workspacet (TENANTS.md steg 5). Backenden
läser den som ett `context_docs`-dokument med `kind='product_marketing'`, vilket
är vad `build_context_pack` faktiskt bygger paketet av. Se
`app/leads/business_context.py` om varför de två källorna inte är synkade.

Källa: Livrustnings nya webbplats (livrustning.vercel.app, ersätter
livrustning.se vid lansering), läst 2026-09-19 — samma underlag som
`livrustning_kb.py`. Den gamla versionen byggde på Wix-sajten och påstod att
Livrustning säljer hjärtstartare via en webbutik. Det gör de inte längre, och
supportagenten läser den här texten också (support_agent.py, affärskontexten).

ÄNDRA INGA SIFFROR ELLER TIDSRAMAR HÄR utan att stämma av med kunden. Texten
går in i varje utskick agenten skriver, och grundningsgrinden mäter utkastets
påståenden mot den — ett tal som ändras här blir ett tal agenten påstår för
kundens räkning.
"""

from __future__ import annotations

#: Går in som `product_marketing`. Skriven som löpande text och inte som
#: punktlistor, eftersom den läses av en modell som ska formulera om den —
#: en punktlista tenderar att kopieras rakt in i mejlet.
PRODUCT_MARKETING = """\
VAD LIVRUSTNING SÄLJER

Livrustning AB (org.nr 556824-9022) utbildar i HLR, första hjälpen och brand.
Instruktörerna kommer till kundens arbetsplats på ett datum kunden väljer.
Fyra upplägg: Säkerhetsdag (4 timmar, brand, HLR och första hjälpen i fyra
stationer), eHLR-Event (2 timmar, hela personalen i HLR med hjärtstartare,
obegränsat antal deltagare, personligt intyg till alla), eHLR och
eFörstaHjälpen (digitalt lärande plus praktisk träning, ett års access för
repetition) och klassiska kurser på plats i små grupper (max 12 deltagare,
20 för brand). Priset sätts per offert utifrån antal deltagare, utbildning och
ort.

De hjälper också arbetsplatser att bli en Hjärtsäker zon enligt SS 280000:
utbildning, rutiner, placering och skyltning, registrering i Sveriges
Hjärtstartarregister, repetition och diplom. Livrustning säljer INTE
hjärtstartare.

TILL VEM

Arbetsplatser som vill att hela personalen ska kunna rädda liv — gärna som
programpunkt på en kick-off eller planeringsdag. De digitala kurserna passar
verksamheter där alla inte kan vara på samma plats samtidigt. Bas i
Stockholm, Umeå och Nerja i Spanien; utbildning över hela Sverige.

VAD SOM SKILJER DEM FRÅN KONKURRENTERNA

Över 30 års erfarenhet och cirka 2 000 utbildade deltagare per år — en av
Sveriges ledande leverantörer av kurser i HLR och första hjälpen.
Rekommenderade på Reco.se fem år i rad, med Sveriges nöjdaste kursdeltagare
enligt Reco.se under flera år. 100 % nöjdhetsgaranti. Allt kursinnehåll följer
gällande lagstiftning och Svenska HLR-rådets riktlinjer. Alla utbildas på en
gång, samma dag, i stället för några i taget under flera år.

VANLIGA INVÄNDNINGAR

"Vi hinner inte samla alla." eHLR-Event tar två timmar, och de digitala
kurserna kräver inte att alla är på samma plats.

"Det är för dyrt." Nöjdhetsgarantin flyttar risken till Livrustning, och
offerten utgår från hur många ni faktiskt är.

"Vi har företagshälsovård som sköter det." Vanligt hos större bolag.
Kontrollera vad avtalet faktiskt täcker — HLR ingår inte alltid.

FÅR INTE PÅSTÅS

Inga priser, garantitider eller kundnamn. Kundlistan på nya sajten är inte
godkänd av Livrustning. Inga siffror om mottagarens verksamhet får hittas på —
antal anställda, omsättning, lokaler eller tidigare inköp nämns bara om
uppgiften finns i researchunderlaget.
"""

#: Kontaktuppgifterna som måste stå i varje utskicks sidfot (send_guard regel 1).
AVSANDARE = {
    "foretagsnamn": "Livrustning AB",
    "orgnr": "556824-9022",
    "postadress": "Hökaren 49, 907 88 Täfteå",
    "epost": "kontakt@livrustning.se",
    "telefon": "070-733 32 54",
}
