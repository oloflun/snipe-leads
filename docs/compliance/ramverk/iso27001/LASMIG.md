# Läs mig: ISO 27001-ramverket för Snajp

Mappen innehåller det som Comp AI-plattformen annars skulle hålla för ISO 27001, skrivet som filer eftersom plattformen inte är driftsatt (JURIDIK_ATGARDER #30). Syftet är att täcka säkerhetskraven i GDPR art. 32 med en erkänd struktur inför första betalande kund. Snajp ska inte certifieras nu.

**Ursprung.** Comp AI:s ISO 27001-ramverk, `frk_681ecc34e85064efdbb76993` version 2022, ur seed-datan i `trycompai/comp` på commit `712ee1b3d722ca1b4f09eb4e5b67cd3bde8713ed` (`packages/db/prisma/seed/primitives/*.json` och `relations/*.json`). Krav, kontroller, policymallar och uppgiftsmallar är tagna därifrån med sina id: 119 krav, 27 kontroller, 26 policyer, 24 uppgifter. Inget är tillagt. Relationerna går krav → kontroll → policy och uppgift.

**Filerna.**

| Fil | Innehåll |
|---|---|
| `matris.md` | Alla 119 krav med kontroll, policy, uppgifter, status, bevis, gap och ansvarig. Summering, tio åtgärder, frågor till ägaren |
| `soa.md` | Utkast till Statement of Applicability för de 93 kontrollerna i bilaga A. Ägaren beslutar |
| `policyer/07–26-*.md` | De 20 policyer som inte redan finns i GDPR-mappen, anpassade till Snajp. Utkast, inte godkända |
| `uppgifter.md` | De 24 uppgifterna: vad mallen kräver, befintligt bevis, vad som saknas, vem, om den kan stängas i dag |
| `import.json` | Samma innehåll maskinläsbart: `policies` (26), `tasks` (24), `risks` (14). Statusvärden och riskskalor följer plattformens enum (`PolicyStatus`, `TaskStatus`, `RiskCategory`, `Likelihood`, `Impact`) |

**Delat med GDPR-mappen.** Sex policymallar har samma id i båda ramverken och står bara i `../gdpr/policyer/`: 01 Compliance & Regulatory Monitoring, 02 Data Classification & Handling, 03 Incident Response & Breach Notification, 04 Privacy & Data-Subject Rights, 05 Security & Privacy Awareness Training, 06 Vendor & Third-Party Risk. De är inte ändrade. Där ISO 27001 kräver mer än GDPR-versionen står det i `matris.md` och i fältet `isoGap` i `import.json`. Fem uppgifter delas också (App Availability, Encryption at Rest, Incident Response, Monitoring & Alerting, Public Policies); GDPR-filen gäller, med tilläggen i `uppgifter.md`. Läs in delade poster en gång.

**Underlag.** `../../nulage-inventering.md`, `../../leverantorsgranskning.md`, `../../BESLUTSUNDERLAG-2026-11-17.md`, `../../bevis/` och repots egna dokument. `import.json` är tänkt för `POST/PATCH /v1/policies`, `/v1/tasks` och `/v1/risks`. Exakt fältmappning mot API:t är inte prövad.

**Licens.** Policymallarnas avsnittsindelning och kravtexter kommer ur Comp AI Community Edition, som är licensierad under AGPLv3. Mappen ligger under `docs/compliance/` och är sedan 2026-11-18 committad, eftersom repot är privat. **Flytta ut den om repot görs publikt igen**, innan licensfrågan är bedömd: om policytexterna räknas som bearbetningar av mallarna, och vad AGPLv3 då kräver.

**Sekretess.** Filerna beskriver öppna brister i detalj. De ska inte heller av det skälet ligga i ett publikt repo. Inga hemligheter, värdnamn eller lösenord står i filerna; de hänvisar till bevisfilerna.
