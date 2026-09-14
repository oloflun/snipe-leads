# Redis Iris — utvärderingsprotokoll och adoptionsgates (Fas R6)

**Skapad:** 2026-08-29 · **Status:** protokoll klart, sandbox-körningen väntar på kontosteg
**Bakgrund och produktdomar:** [plans/2026-08-29-redis-agentarkitektur.md](../plans/2026-08-29-redis-agentarkitektur.md) §2

Strategival A (Antons godkännande 2026-08-29): förmågorna byggs självt på egen
EU-Redis nu; de managed Iris-tjänsterna (Agent Memory, LangCache) utvärderas i
sandbox med **enbart syntetisk data** och adopteras i drift först när varje
gate nedan är grön. Det här dokumentet är facit för det beslutet — inte en
åsikt som ska omprövas från minnet varje gång frågan dyker upp.

## 1. Gates för managed Iris i DRIFT (alla måste vara gröna)

| # | Gate | Läge 2026-08-29 |
|---|---|---|
| G1 | Tjänsten är GA, inte preview | 🔴 Båda är public preview |
| G2 | Redis DPA tecknad och arkiverad | 🔴 Inte tecknad (se JURIDIK_ATGARDER P1.2) |
| G3 | Tjänstens region bekräftad EU | ⚪ Okänd — preview-tjänsternas region framgår inte av dokumentationen |
| G4 | BYOK med leverantör ur den godkända listan (docs/JURIDIK_ATGARDER.md) — ALDRIG "Redis in-built keys" (okänd modellleverantör/region) | ⚪ Leverantörslistan i konsolen oavläst |
| G5 | Sensitive-data-exclusions allmänt tillgängliga (i dag "selected accounts", och uttryckligen advisory) | 🔴 |
| G6 | Extraktionskontrakt förenligt med INV-MEM-001 (bara kundens egna utsagor — custom memory type med egen extraktionsprompt, verifierad mot injektions- och kontamineringstester) | ⚪ Kräver sandbox-körningen |
| G7 | Underbiträdeslistan (lib/bolag.ts, registerforteckning.md, integritetspolicyn) uppdaterad FÖRE första riktiga kunddatabiten | 🔴 |
| G8 | Publicerat pris (LangCache saknar det — "talk to sales") | 🔴 |

**Regeln:** development speglar produktionen med riktig kunddata — managed
Iris får därför aldrig kopplas mot development "för att testa". Sandboxen är
lokal körning mot MemoryStorage och syntetiska fixturer, ingenting annat.

## 2. Sandbox-protokollet (körs när Anton gjort kontostegen)

Kontosteg (Antons hand, Redis Cloud-konsolen):
1. Skapa en Agent Memory-tjänst med **Quick create** (använder gratis-30MB-databasen).
   Anteckna endpoint + Store ID; spara service-nyckeln i `.env.deploy` som
   `AGENT_MEMORY_ENDPOINT` / `AGENT_MEMORY_STORE_ID` / `AGENT_MEMORY_API_KEY`.
2. Läs av och anteckna i §3 nedan: vilka **BYOK-leverantörer** konsolen
   erbjuder (G4), och vilken region tjänsten uppger (G3).
3. Skapa en LangCache-tjänst mot samma databas; spara motsvarande tre värden.

Körningen (agentens jobb, lokal maskin, `DATABASE_URL` tom = MemoryStorage):
1. 20 syntetiska samtal ur `snajp-support/tests/`-fixturerna och
   exempelbolagen (aldrig riktiga kunder) körs genom Agent Memory:
   sessionshändelser in, vänta ut extraktionscadensen, läs extraherade
   minnen. Bedöm: svensk extraktionskvalitet, brus (extraherar den agentens
   formuleringar? — G6-testet), summeringskvalitet efter 20+ meddelanden,
   latens per anrop.
2. Samma 20 frågor mot LangCache: store + search med `attributes`
   (tenant-scoping), mät träffkvot på parafraser, felträffar under 0.9-tröskel,
   latens. Jämför mot husets egen svarscache (Fas R2) på samma frågor.
3. Skriv utfallet i §3 och uppdatera gate-tabellen.

## 3. Utfall (fylls i av körningen — tomt är ärligare än gissat)

- BYOK-leverantörer i konsolen: _(oavläst)_
- Uppgiven region: _(oavläst)_
- Extraktionskvalitet svenska: _(inte körd)_
- Kontamineringstest (G6): _(inte körd)_
- LangCache träffkvot/latens mot egen cache: _(inte körd)_

## 4. Context Retriever — bevakningspost

Ingen sandbox: produkten löser governed verktygsåtkomst till strukturerad
affärsdata via MCP, och Snajp har i dag ingen sådan yta (typade
lagringsmetoder + RLS är vår motsvarighet). Omprövas den dag agenten ska läsa
KUNDENS operativa system (orderstatus, lagersaldo) — då ställs den mot
handkodade integrationer, och gates G1–G3/G7 gäller likadant.
