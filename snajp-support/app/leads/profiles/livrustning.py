"""ICP-FÖRSLAG för Livrustning AB — att godkänna, inte att lita på.

Underlag: `app/tenants/livrustning_kb.py` (hämtad från livrustning.se 2026-08-05)
och `lib/tenants/livrustning.ts`.

Livrustning AB, org.nr 556824-9022, Nacka. Utbildar i HLR, första hjälpen,
brand och krisstöd, och säljer hjärtstartare via hjartstartarbutiken.com.
30+ års erfarenhet, ~2 000 utbildade per år, ~60 000 totalt.

## Antagandet hela förslaget vilar på

Att deras nästa kund är en ARBETSGIVARE med tillräckligt många anställda för
att första hjälpen-beredskap är ett krav, men för få för att redan ha ett
företagshälsovårdsavtal som täcker det.

Det antagandet kan vara fel. Kunskapsbasen nämner uttryckligen även
bostadsrättsföreningar, skolor och föreningar som målgrupp för de digitala
kurserna — tre segment som inte alls fångas av ett SNI- och storleksfilter,
eftersom en BRF varken har anställda eller en meningsfull branschkod. Vill vi åt
dem krävs en annan urvalsmekanism än den här. Se AVVIKELSER nedan.

## Varför just 10–49 anställda

Under 10: AFS 1999:7 gäller fortfarande, men budgeten för en bokad
gruppututbildning gör det sällan. Digitala kurser passar bättre, och de säljs
inte med kallmejl utan med självbetjäning.

Över 49: bolaget har med stor sannolikhet redan ett företagshälsovårdsavtal där
HLR ingår. Då säljer Livrustning inte in ett behov utan mot en befintlig
leverantör, vilket är en annan och mycket längre affär.

## Varför branscherna ser ut som de gör

Alla valda SNI-koder har antingen förhöjd olycksrisk (bygg, tillverkning,
transport) eller många människor i samma lokal (restaurang, lokalvård,
tandvård). Båda gör första hjälpen-beredskap till något chefen redan tänkt på —
och ett kallmejl som landar i ett behov mottagaren redan känner är ett annat
mejl än ett som ska skapa behovet.
"""

from __future__ import annotations

from typing import Any

#: Förslaget. Skickas INTE automatiskt någonstans — se profiles/__init__.py.
LIVRUSTNING_ICP_FORSLAG: dict[str, Any] = {
    # Göteborgsområdet enligt uppdragets testkörning. Se AVVIKELSE 1: kunden
    # har ingen verksamhetsort där.
    "geo": ["goteborg"],
    "sni_codes": [
        # Bygg och anläggning — förhöjd olycksrisk, lagkrav på beredskap.
        "41.200",  # Byggande av bostadshus och andra byggnader
        "43.210",  # Elinstallationer
        "43.220",  # VVS-arbeten
        # Tillverkning och verkstad — maskiner, skärskador, klämrisk.
        "25.620",  # Metallbearbetning
        "33.120",  # Reparation av maskiner
        # Transport — ensamarbete och långa avstånd till vård.
        "49.410",  # Vägtransport, godstrafik
        # Många människor i samma lokal.
        "56.100",  # Restaurangverksamhet
        "56.210",  # Cateringverksamhet
        "81.210",  # Lokalvård
        "86.230",  # Tandläkarverksamhet
    ],
    "size": {
        "anstallda_min": 10,
        "anstallda_max": 49,
    },
    "exclude_domains": [
        # Konkurrenter och branschkollegor. Listan är avsiktligt kort och ska
        # fyllas på av kunden — vi vet inte vilka de själva räknar som
        # konkurrenter, och att gissa fel åt båda hållen kostar: en missad
        # kund, eller ett mejl till någon de träffar på Branschrådet.
        "livrustning.se",
        "hjartstartarbutiken.com",
    ],
    "roles": ["VD", "Platschef", "HR-ansvarig", "Skyddsombud", "Arbetsmiljöansvarig"],
    "must_have": [
        "Egna anställda som arbetar på plats, inte enbart distansarbete",
    ],
    "deal_breakers": [
        "Redan kund hos Livrustning",
        "Bemanningsföretag utan egen arbetsplats",
    ],
    "max_prospects_per_run": 10,
}


LIVRUSTNING_MOTIVERING = """\
FÖRSLAG — kräver ditt godkännande innan det skrivs in via PUT /api/leads/config.

Målgrupp: arbetsgivare i Göteborgsområdet med 10–49 anställda, i branscher med
förhöjd olycksrisk eller många människor i samma lokal.

AVVIKELSER SOM INTE SKA JÄMKAS IHOP
-----------------------------------

1. GEOGRAFIN STÄMMER INTE MED VERKSAMHETEN.
   Livrustning har verksamhet i Stockholm, Umeå och Nerja — inte i Göteborg.
   Kunskapsbasen säger "utbildar över hela landet", och de digitala kurserna
   är platsoberoende, så Göteborg är säljbart. Men en bokad utbildning PÅ PLATS
   i Göteborg innebär resa från Stockholm, och det påverkar både pris och
   leveranstid. Antingen ska mejlen leda med de digitala kurserna, eller så ska
   geografin flyttas till 'umea' — deras kurskontor ligger på Hökaren 49,
   907 88 Täfteå, vilket är Umeå kommun och därmed mitt i den regionen.
   Uppdraget bad om en körning mot Göteborgsfixturen, så förslaget följer det.
   Beslutet är ditt.

2. TRE MÅLGRUPPER FÅNGAS INTE ALLS AV DET HÄR FILTRET.
   Kunskapsbasen nämner bostadsrättsföreningar, skolor och föreningar som
   målgrupp för de digitala kurserna. En BRF har varken anställda eller en
   meningsfull SNI-kod, så ett filter byggt på storlek och bransch missar dem
   helt. Det är inte ett fel i filtret utan i valet av mekanism — de segmenten
   kräver en annan källa (t.ex. föreningsregister) och ett eget ICP.

3. GARANTITIDERNA ÄR FORTFARANDE MOTSTRIDIGA.
   Redan noterat i livrustning_kb.py: produktgarantin i webbutiken är 1 år mot
   tillverkningsfel, medan Hjärtsäker zon-paketet anges med 8 år på
   livrustning.se. BÅDA står kvar i underlaget med sin kontext. Ett utskick får
   därför inte nämna någon garantitid alls förrän kunden bekräftat vilken som
   gäller när — grundningsgrinden fäller ett påstående som inte entydigt går
   att belägga, och det är rätt beteende här.

OSÄKERHETEN JAG INTE KAN LÖSA
-----------------------------

Jag vet inte vilka Livrustning själva räknar som konkurrenter. exclude_domains
innehåller därför bara deras egna domäner. Att gissa fel kostar åt båda hållen:
för brett filter = missad kund, för smalt = kallmejl till någon de sitter i
Branschrådet för Hjärtstartare med.
"""
