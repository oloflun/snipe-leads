# Policy Management & Exception Handling

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e405054f7c35d89ccccf2` (avdelning `admin`) |
| Täcker kontroll | Policy Compliance (`frk_ct_683f3ecd42e62fde624c59c1`) |
| Täcker krav | 4.4, 7.5.1, 7.5.2, 7.5.3, A.5.1, A.5.33, A.5.36 |

## Syfte

Hålla Snajps policyer aktuella och spårbara, och se till att varje avsteg är godkänt, tidsbegränsat och skrivet.

## Omfattning

Alla policyer i `../../gdpr/policyer/` och `./`, rutinerna i repot (`INCIDENT_RESPONSE.md`, `DEPLOY.md`, `AUTH.md`), och alla som har åtkomst: Anton och Sebbe.

## Förteckning och ägare

- Förteckningen är `policies` i `../import.json` (26 policyer, mall-id, sökväg, status). Ägare för alla är Anton.
- Den läggs in i Comp AI om plattformen driftsätts. Tills dess är filen förteckningen.

## Versioner och spridning

- **Läget i dag:** `docs/compliance/` är undantagen från git eftersom repot är publikt. Policyerna har alltså ingen versionshistorik.
- **Ska införas:** en privat lagringsplats med historik, till exempel ett privat repo, [FYLL: plats], [FYLL: datum], ansvarig Anton. Krav 7.5.3 är inte uppfyllt förrän policyerna ligger utom räckhåll för utomstående och med historik.
- Varje policy har status, datum och granskningsintervall överst. När en policy godkänns ändras statusraden till "GODKÄND [datum], version [n]".
- Sebbe får besked om en större ändring inom fem arbetsdagar.
- Rutiner som beskriver öppna brister flyttas inte till det publika repot. `INCIDENT_RESPONSE.md` med incidentloggen ligger där i dag; Anton beslutar om loggen ska flyttas, [FYLL: datum].

## Granskning

Varje policy granskas minst var tolfte månad. Ägaren skriver "Granskad, ingen ändring" eller ändringen, med datum. Granskningen görs före en planerad revision eller ett kundfrågeformulär.

## Begäran om undantag

- Den som behöver ett avsteg skriver: vad, varför, risken, kompenserande skydd och slutdatum.
- Anton beslutar inom tio arbetsdagar. Mallen kräver att policyägaren och ledningen beslutar gemensamt; hos Snajp är det samma person. Det är ett undantag från mallen som Anton godkänner med den här policyn.
- Anton kan inte godkänna ett undantag som han själv begär utan att Sebbe har läst det. Det är den kompenserande kontrollen för att samma person beslutar och ansöker.

## Undantagsregister och slutdatum

- Registret förs i `../../../loggar/undantag.md`. Det finns inte; införs [FYLL: datum], ansvarig Anton.
- Undantag som redan står i policyerna (till exempel att nätfiskeövningar inte görs, G05) förs in där vid godkännandet.
- Registret gås igenom varje månad. Mallen kräver det; med få poster räcker det att genomgången sker vid månadens första arbetsdag och noteras med datum.

## Mätning

Förteckningen finns. Minst 90 procent av policyerna granskade inom tolv månader. Inga undantag efter slutdatum.

## Undantag

Hanteras enligt avsnitten ovan.

## Brister

Utebliven granskning eller ett utgånget undantag rättas inom 30 dagar.

## Förbättring

Synpunkter från revisioner och från Sebbe tas in vid nästa översyn.
