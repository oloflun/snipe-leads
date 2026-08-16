"""Produktdatan leads-agenten säljer FÖR Livrustning — inte för Snajp.

Motsvarar `business_contexts` för workspacet (TENANTS.md steg 5). Backenden
läser den som ett `context_docs`-dokument med `kind='product_marketing'`, vilket
är vad `build_context_pack` faktiskt bygger paketet av. Se
`app/leads/business_context.py` om varför de två källorna inte är synkade.

Källor: livrustning.se (startsida, /kurser, /hjartsakerzon, /kvalitetspolicy,
/intigritetspolicy) hämtade 2026-08-05 via `livrustning_kb.py`, samt kundens
köpvillkor för hjartstartarbutiken.com.

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

Livrustning AB (org.nr 556824-9022) utbildar i hjärt-lungräddning, första
hjälpen, brand och krisstöd, och säljer hjärtstartare. Utbildningarna hålls
antingen hos kunden, i egna kurslokaler i centrala Stockholm, eller digitalt.
De digitala kurserna (eHLR och eFörstaHjälpen) genomförs när och var deltagaren
vill, vilket gör att kunden slipper samla alla på samma plats samtidigt.

Utöver kurserna levererar de helhetsåtagandet Hjärtsäker zon enligt svensk
standard SS280000 — hjärtstartare, skyltning, placering, registrering och
utbildning av personalen som ett paket.

Hjärtstartare säljs via webbutiken hjartstartarbutiken.com. Livrustning är en
OBEROENDE leverantör och säljer flera fabrikat, inte ett eget.

TILL VEM

Arbetsgivare som behöver uppfylla kravet på första hjälpen-beredskap, samt
bostadsrättsföreningar, skolor och föreningar. Verksamhet finns i Stockholm,
Umeå och Nerja i Spanien, men utbildning sker över hela landet.

VAD SOM SKILJER DEM FRÅN KONKURRENTERNA

Mer än 30 års erfarenhet och cirka 60 000 utbildade personer sedan 90-talet,
med ungefär 2 000 per år. Det gör dem till en av de största leverantörerna i
Sverige inom livräddning.

De har under många år haft Sveriges nöjdaste kursdeltagare i HLR och första
hjälpen enligt Reco.se, baserat på över 780 omdömen.

Att de är oberoende av fabrikat är ett säljargument i sig: en kund som köper
hjärtstartare av en leverantör som bara säljer ett märke får det märket
rekommenderat oavsett behov.

De är aktiv medlem i Branschrådet för Hjärtstartare i Sverige.

De lämnar 100 % nöjdhetsgaranti på utbildningarna.

VANLIGA INVÄNDNINGAR

"Vi har redan en hjärtstartare." Utrustning utan utbildad personal används
sällan i skarpt läge, och elektroder och batteri har utgångsdatum. Hjärtsäker
zon-åtagandet omfattar just det som glöms bort efter inköpet.

"Vi hinner inte samla alla." Det är precis vad de digitala kurserna löser.

"Det är för dyrt." Nöjdhetsgarantin flyttar risken till Livrustning.

"Vi har företagshälsovård som sköter det." Vanligt hos större bolag. Kontrollera
vad avtalet faktiskt täcker — HLR ingår inte alltid.

FÅR INTE PÅSTÅS I ETT UTSKICK

Ingen garantitid får nämnas. Underlaget innehåller två motstridiga uppgifter:
produktgarantin i webbutiken är 1 år mot tillverkningsfel, medan Hjärtsäker
zon-paketet anges med 8 år på livrustning.se. Vilken som gäller när är inte
utrett med kunden. Båda står kvar i kunskapsbasen med sin kontext, och tills
kunden bekräftat vilken som gäller i vilken situation ska agenten inte
formulera något om garanti alls.

Inga siffror om mottagarens verksamhet får hittas på. Antal anställda,
omsättning, lokaler eller tidigare inköp nämns bara om uppgiften finns i
researchunderlaget.
"""

#: Kontaktuppgifterna som måste stå i varje utskicks sidfot (send_guard regel 1).
AVSANDARE = {
    "foretagsnamn": "Livrustning AB",
    "orgnr": "556824-9022",
    "postadress": "Rudsjövägen 112, 131 47 Nacka",
    "epost": "kontakt@livrustning.se",
    "telefon": "070-733 32 54",
}
