# Risk Management

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); registret kvartalsvis |
| Ramverkets mall | `frk_pt_685e3fc75bd72cd0745dc5d1` (avdelning `admin`) |
| Täcker kontroll | Risk Management (`frk_ct_69e639b90a3bf8c1443cbf5b`) |
| Täcker krav | 6.1.1, 6.1.2, 6.1.3, 8.2, 8.3, A.5.6, A.5.7 (ramverket kopplar kontrollen till alla 119 krav) |

## Syfte

Hitta, rangordna och åtgärda de risker som kan skada kunddata eller stoppa tjänsten, på ett sätt som två personer orkar upprepa.

## Omfattning

Tekniska, leverantörs-, juridiska och verksamhetsrisker för allt inom omfånget i `07-information-security-privacy-governance.md`.

## Riskregister

- Registret är `risks` i `../import.json` (säkerhet) och i `../../gdpr/import.json` (dataskydd). Fälten följer mallen: risk, påverkan 1–5, sannolikhet 1–5, ägare, behandling, status.
- Registret uppdateras när en ny leverantör, tjänst eller miljö tillkommer, när en driftvariabel ändrar dataflöden, och efter varje incident.
- Registret får aldrig vara tomt. Det är det inte: 14 poster här och 15 i GDPR-registret, med överlapp.

## Bedömning och prioritering

- Påverkan och sannolikhet bedöms 1–5. Risknivå = påverkan × sannolikhet.
- **Acceptansnivå (förslag):** risker med nivå 12 eller mer behandlas före första betalande kund. Lägre risker får accepteras av Anton med datum och motivering. [FYLL: Antons beslut]
- Varje kvartal pekas de tre högsta ut. I dag är det plattformsadminens lösenord i publik historik (25), kundmejl till TypeSafe (20), och på delad tredje plats testmiljön som spegel och den saknade övervakningen (16 vardera). Produktionsdatabasen utan säkerhetskopior följer på 15; påverkan är högst möjliga, så den behandlas ändå före första kund.
- Ändrad bedömning motiveras i registrets fält.

## Behandling

- Varje risk får ett av fyra svar: minska, överföra, undvika, acceptera.
- Varje svar utom acceptera blir en uppgift med datum och ansvarig.
- Accepterade risker får datum och Antons initialer.
- Kontrollerna som väljs står i `../soa.md` (krav 6.1.3).

## Hotbevakning

Ska införas från godkännandet, ansvarig Anton:

- Prenumerera på CERT-SE:s nyhetsbrev och sårbarhetsvarningar (krav A.5.6).
- Följa säkerhets- och statussidorna för Railway, GitHub, Google Cloud och Redis Cloud.
- Sårbarheter i beroenden kommer via Dependabot när den slås på (`22-vulnerability-patch-management.md`).
- Relevanta varningar skrivs som en rad i `docs/BESLUT.md` eller som en ny risk. Mallen talar om en intern kanal; med två personer räcker mejl.

## Mätning

Registret finns, tre risker är utpekade, ingen åtgärd är mer än 30 dagar försenad.

## Undantag

En risk med påverkan 5 får bara accepteras med skriftligt beslut av Anton, med restrisken beskriven.

## Brister

Ett register som inte uppdaterats på 90 dagar tas upp vid nästa ledningsgenomgång (P10).

## Förbättring

Stängda risker tas bort vid kvartalsgenomgången. Skalan justeras efter incidenter.
