# Läs mig: GDPR-ramverket för Snajp

Mappen innehåller det som Comp AI-plattformen annars skulle hålla för GDPR, skrivet som filer eftersom plattformen inte är driftsatt (vägvalet är Antons, JURIDIK_ATGARDER #30).

**Ursprung.** Strukturen är Comp AI:s GDPR-ramverk, `frk_681ef1952907deb7cb85896d` version 1.0.0, ur seed-datan i `trycompai/comp` på commit `712ee1b3d722ca1b4f09eb4e5b67cd3bde8713ed` (`packages/db/prisma/seed/primitives/*.json` och `relations/*.json`). Krav, kontroller, policymallar och uppgiftsmallar är tagna därifrån med sina id. Inget är tillagt: 19 krav, 12 kontroller, 6 policyer, 15 uppgifter. Relationerna går krav → kontroll → policy och uppgift.

**Filerna.**

| Fil | Innehåll |
|---|---|
| `matris.md` | Alla 19 krav med kontroll, policy, uppgifter, status, bevis, gap och ansvarig. Bedömningar av EU-representant, dataskyddsombud och art. 22. Summering |
| `policyer/01–06-*.md` | De sex policyerna, anpassade till Snajp. Utkast, inte godkända |
| `uppgifter.md` | De 15 uppgifterna: vad mallen kräver, befintligt bevis, vad som saknas, vem |
| `import.json` | Samma innehåll maskinläsbart: `policies`, `tasks`, `vendors` (ur `../../leverantorer.json`), `risks`. Statusvärden och riskskalor följer plattformens enum (`PolicyStatus`, `TaskStatus`, `Likelihood`, `Impact`, `VendorCategory`) |

Underlaget är `../../nulage-inventering.md`, `../../leverantorsgranskning.md`, `../../BESLUTSUNDERLAG-2026-11-17.md`, `../../bevis/` och repots egna dokument. Policyfilerna kan klistras in i plattformens policyredigerare; `import.json` är tänkt för `POST/PATCH /v1/policies`, `/v1/tasks`, `/v1/vendors` och `/v1/risks`. Exakt fältmappning mot API:t är inte prövad.

**Licens.** Policymallarnas avsnittsindelning och kravtexter kommer ur Comp AI Community Edition, som är licensierad under AGPLv3. Mappen ligger under `docs/compliance/` och är sedan 2026-11-18 committad, eftersom repot är privat. **Flytta ut den om repot görs publikt igen**, innan licensfrågan är bedömd: om policytexterna räknas som bearbetningar av mallarna, och vad AGPLv3 då kräver.

**Sekretess.** Filerna beskriver öppna brister i detalj. De ska inte heller av det skälet ligga i ett publikt repo. Inga hemligheter, värdnamn eller lösenord står i filerna; de hänvisar till bevisfilerna.
