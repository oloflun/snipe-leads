# Läs mig: ISO 42001-ramverket för Snajp

Mappen innehåller det som Comp AI-plattformen annars skulle hålla för ISO 42001 (ledningssystem för AI), skrivet som filer eftersom plattformen inte är driftsatt (JURIDIK_ATGARDER #30). Syftet är en sann bild av hur Snajp styr sin AI-användning inför första betalande kund. Snajp ska inte certifieras nu. Comp AI har inget ramverk för EU:s AI-förordning; den kartläggs separat i `ai-forordningen.md`.

**Ursprung.** Comp AI:s ISO 42001-ramverk, `frk_68cc0e2a21184ed168ab2eea` version 1.0.0, ur seed-datan i `trycompai/comp` på commit `712ee1b3d722ca1b4f09eb4e5b67cd3bde8713ed` (`packages/db/prisma/seed/primitives/*.json` och `relations/*.json`). Krav, kontroller, policymallar och uppgiftsmallar är tagna därifrån med sina id: 70 krav, 76 kontroller, 21 policyer, 61 uppgifter. Inget är tillagt. Relationerna går krav → kontroll → policy och uppgift.

**Filerna.**

| Fil | Innehåll |
|---|---|
| `matris.md` | Alla 70 krav med kontroll, policy, uppgifter, status, bevis, gap och ansvarig. Summering, tio åtgärder, frågor till ägaren |
| `ai-forordningen.md` | Riskklass, roll och skyldigheter per AI-system enligt förordning (EU) 2024/1689. Bedömning som jurist ska granska |
| `policyer/27-ai-policy-control-framework.md` | AI-policyn, ur ramverkets mall och anpassad till Snajp. Utkast |
| `policyer/28-sanctions-disciplinary.md` | Disciplinpolicyn. Utkast |
| `uppgifter.md` | De 61 uppgifterna: vad mallen kräver, befintligt bevis, vad som saknas, vem, om den kan stängas i dag |
| `import.json` | Samma innehåll maskinläsbart: `policies` (21), `tasks` (61), `risks` (8). Statusvärden och riskskalor följer plattformens enum |

**Delat med de andra mapparna.** 19 av de 21 policymallarna har samma id som i GDPR- eller ISO 27001-ramverket och står bara där: G01–G06 i `../gdpr/policyer/` och P07, P09, P11–P15, P18–P21, P24 och P25 i `../iso27001/policyer/`. De är inte ändrade; vad ISO 42001 kräver utöver dem står i `matris.md` och i fältet `iso42001Gap` i `import.json`. Två policyer är nya här: AI Policy Control Framework och Sanctions & Disciplinary (den senare ingick inte i ISO 27001-ramverkets policyer trots att krav A.6.4 där handlar om disciplin). 15 av de 61 uppgifterna delas med ISO 27001 och fem av dem även med GDPR; `../iso27001/uppgifter.md` gäller för dem, med tilläggen i `uppgifter.md`. Läs in delade poster en gång.

**Underlag.** `../../nulage-inventering.md`, `../../leverantorsgranskning.md`, `../../BESLUTSUNDERLAG-2026-11-17.md`, `../../bevis/`, `ARCHITECTURE_INVARIANTS.md`, `docs/BESLUT.md`, DPIA, intresseavvägningen, evalsviterna och agentkoden. `import.json` är tänkt för `POST/PATCH /v1/policies`, `/v1/tasks` och `/v1/risks`. Exakt fältmappning mot API:t är inte prövad.

**Licens.** Policymallarnas avsnittsindelning och kravtexter kommer ur Comp AI Community Edition, som är licensierad under AGPLv3. Mappen ligger under `docs/compliance/` och är sedan 2026-11-18 committad, eftersom repot är privat. **Flytta ut den om repot görs publikt igen**, innan licensfrågan är bedömd: om policytexterna räknas som bearbetningar av mallarna, och vad AGPLv3 då kräver.

**Sekretess.** Filerna beskriver öppna brister i AI-kedjan i detalj. De ska inte heller av det skälet ligga i ett publikt repo. Inga hemligheter, värdnamn eller lösenord står i filerna.
