"""Redis-nycklarnas NAMNRYMD — en per driftsättning.

## Varför den finns

Uppmätt 2026-08-29: `main` och `development` pekade på SAMMA Redis-instans
(gratisnivån, EN logisk databas — `SELECT 1` svarar "DB index is out of
range"), och ingen nyckel bar miljö. Båda svarade `jobs: redis` i sin
hälsokontroll samtidigt. Följderna var inte teoretiska:

- **En consumer group, `agenter`, på `crm:jobb:chatt`, med konsumenter från
  NIO containrar.** En grupp delar ut varje post till exakt EN konsument, så
  ett chattjobb från en riktig kund kunde plockas och köras av en
  development-container — mot spegeldatabasen — och tvärtom.
- **Svarscachen delades.** `svarscache_idx` filtrerar på `tenant`, och
  development är en SPEGEL med identiska tenant-id:n. Ett svar från en
  testkörning kunde alltså matchas och serveras till en riktig kund. Posten
  som låg där hade 21 dagars TTL kvar.
- **Arbetsminnet delades** (`minne:{tenant}:{kund}`), av samma skäl.

Planen (plans/2026-08-29-redis-agentarkitektur.md, R5) säger redan att `main`
ska ha en EGEN databas — "aldrig delad, samma tysta-korskopplings-regel som
GEMINI_API_KEY". Regeln stod alltså skriven medan konfigurationen som kördes
bröt mot den. Det här är kodens försvar: även när två driftsättningar delar
instans kan de inte längre läsa varandras nycklar. Egen instans åt main är
fortfarande rätt slutläge, men det är ett konsolmoment och en betald nivå.

## Vad fröet är, och varför det MÄTTES fram

Fröet är HELA `DATABASE_URL` plus miljönamnet. Båda delarna behövs, och det
är inte försiktighet — det är ett mätresultat.

Första utkastet hashade värd + databasnamn, med motiveringen att databasen
identifierar driftsättningen (samma doktrin som
`Settings.har_riktig_kunddata`). Mätt mot Railways API 2026-08-29 hade det
varit VERKNINGSLÖST: inne i Railway kör båda miljöerna mot

    postgresql://snajp_app:***@postgres.railway.internal:5432/railway

— identisk värd, identisk databas, identisk användare. Bara lösenordet
skiljer (`APP_PASSWORD` står i `PER_ENV_SECRETS`). En namnrymd på värd +
databas hade alltså gett `main` och `development` SAMMA värde och sett
korrekt ut medan den inte skyddade någonting.

Därför hela DSN:en. Att lösenordet ingår i fröet är ofarligt: värdet hashas
med sha256 och kapas till åtta hextecken, vilket inte går att vända tillbaka
till en hemlighet — det finns oändligt många urbilder. Miljönamnet ligger med
som andra hälft eftersom det skiljer sig på Railway (mätt: `main` respektive
`development`) och därmed håller även om två miljöer en dag skulle dela
databasuppgifter.

Semantiken är den avsedda: två processer mot SAMMA databas med samma
uppgifter delar cache (det är hela poängen med en cache), två mot olika gör
det aldrig. En lösenordsrotation nollställer cachen, vilket är ofarligt.

Saknas databas helt (lokal körning, testsviten) faller den på miljönamnet och
sist på "lokal". Ingen av dem når riktig kunddata.

## Vad som händer vid införandet

Nycklarna byter namn, alltså börjar varje cache tom och varje ström från noll.
Det är avsiktligt och ofarligt: cacheposter är härledda och har TTL, jobbposter
lever minuter. Den gamla strömmens eventuella oavslutade poster lämnas kvar och
tas inte över av någon — rulla därför inte ut mitt i en känd kö.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

from .config import get_settings


def _namnrymd_av(dsn: str, miljo: str) -> str:
    """Namnrymden som en REN funktion av sina två indata.

    Skild från `namnrymd()` för att vara testbar: invarianten måste kunna
    fråga "får två driftsättningar som skiljer sig bara på lösenordet olika
    namnrymd?" utan att sätta miljövariabler och ladda om moduler mitt i
    testsviten — det gjorde den först, och sviten hängde på att andra tester
    då ärvde en DATABASE_URL som pekade på en värd som inte svarar.
    """
    # HELA DSN:en, inte värd + databas — se modulens docstring för mätningen
    # som visar varför det senare hade gett main och development samma värde.
    fro = f"{dsn}|{miljo.lower()}" if dsn else (miljo.lower() or "lokal")
    return hashlib.sha256(fro.encode("utf-8")).hexdigest()[:8]


@lru_cache(maxsize=1)
def namnrymd() -> str:
    """Kort, stabil identitet för den här driftsättningen.

    Hashad och aldrig klartext: fröet innehåller en DSN, och en DSN hör inte
    hemma i en Redis-nyckel som syns i varje SCAN och i varje felmeddelande —
    se läckagespärren i CLAUDE.md. Åtta hextecken räcker; namnrymden ska
    skilja en handfull driftsättningar åt, inte stå emot en angripare.
    """
    settings = get_settings()
    return _namnrymd_av(
        str(settings.database_url or ""),
        settings.railway_environment_name or settings.environment or "",
    )


def nyckel(ra: str) -> str:
    """`ra` med driftsättningens namnrymd före.

    ALLA Redis-nycklar i tjänsten går genom den här funktionen. Lägger du till
    en ny nyckelfamilj ska den göra det också — annars delar den yta mellan
    produktionen och spegeln, vilket är precis felet modulen finns för att
    stänga. INV-REDIS-001 fäller en nyckelfamilj som byggs utan den.
    """
    return f"ns{namnrymd()}:{ra}"
