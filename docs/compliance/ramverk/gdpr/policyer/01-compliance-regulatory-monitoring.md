# Compliance & Regulatory Monitoring

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton (ägare av Snajp, enskild firma) |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`), och när Snajp börjar behandla data i ett nytt land eller med en ny leverantör |
| Ramverkets mall | `frk_pt_685e4010bde64520b9abaf1d` (avdelning `gov`) |
| Täcker kontroll | GDPR Accountability Roles and Representatives (`frk_ct_69e918ea7bd6df3b3cdd2ddc`) |
| Täcker krav | AG-1 GDPR Accountability Owner, AG-3 EU Representative, AG-4 Data Protection Officer |

## Syfte

Snajp ska veta vilka lagar, avtal och åtaganden som gäller för verksamheten och kunna visa belägg för att de följs. Det gäller särskilt kundernas kunders mejl och chattar (Snajp är biträde) och prospektdata i leadsagenten (Snajp är ansvarig för egna utskick).

## Omfattning

Alla produkter (supportagenten, leadsagenten, kvittohanteraren), all behandling av personuppgifter och alla avtal med kunder och leverantörer. Gäller Anton och Sebbe och de AI-kodverktyg som arbetar i repot. Driften ligger hos Railway i Amsterdam (`../../../bevis/railway-regioner-2026-11-17.txt`).

## Ansvar och roller (kontrollens krav)

- **GDPR-ansvarig (AG-1):** Anton. Han beslutar i dataskyddsfrågor, bedömer incidenter (`INCIDENT_RESPONSE.md` §1) och svarar för kontakten med IMY och kunder.
- **Kontaktadress för dataskydd:** ska vara `integritet@snajp.se`. Brevlådan finns inte i dag (`lib/bolag.ts:48`); tills dess gäller `kontakt@snajp.se`. Ska införas [FYLL: datum], ansvarig Anton (JURIDIK_ATGARDER #5).
- **EU-representant (AG-3):** behövs inte. Art. 27 gäller bara den som saknar etablering i EU. Snajp är en svensk firma. Beslutet ska skrivas in i `docs/BESLUT.md`, ansvarig Anton, [FYLL: datum].
- **Dataskyddsombud (AG-4):** behövs inte i dag enligt bedömningen i `../matris.md` (AG-4). Anton ska fatta och dokumentera beslutet i `docs/BESLUT.md`, [FYLL: datum], och pröva det igen när någon av utlösarna i matrisen inträffar.
- **Sebbe:** medutvecklare. Hans formella ställning (uppdragstagare eller delägare) och vad han har åtkomst till är inte dokumenterat: [FYLL: roll och åtkomst].

## Förteckning över skyldigheter

Förteckningen är `../matris.md` (GDPR, krav för krav) plus tabellen nedan över övriga regler. Den ska ses över varje halvår och när verksamheten växer till nya marknader.

| Regel | Gäller? | Varför |
|---|---|---|
| GDPR och dataskyddslagen | Ja | Personuppgifter i mejl, chattar, leads och konton |
| Marknadsföringslagen 19 § och lagen om elektronisk kommunikation | Ja | Kallmejl; enskilda firmor fälls i kod (`leads/forfilter.py`) |
| E-handelslagen 8 § | Ja | Avsändarens org.nr i utskick; saknas i dag (JURIDIK_ATGARDER #5, #17) |
| AI-förordningen art. 50 | Ja | Upplysning om AI i chatt och automatiska svar saknas (JURIDIK_ATGARDER #12) |
| Bokföringslagen | Ja, för kunden | Kvittohanteraren lagrar inte originalunderlag (`app/villkor/VillkorSida.tsx`) |
| Kundavtal (PUB, pilotavtal) | Ja | `docs/pub-avtal.md` och `docs/pilotavtal.md`, båda ogranskade utkast |
| Leverantörsavtal | Ja | `../../../leverantorsgranskning.md` |

## Efterlevnadsregister

Registret är `../matris.md` och `../uppgifter.md`. Varje krav har en hänvisning till bevis (fil och rad). Bevis som saknas eller är äldre än tolv månader räknas som en lucka. Plattformen (Comp AI) är inte driftsatt; tills den är det är filerna registret.

## Kontakt med tillsynsmyndighet och kunder

- Frågor från IMY, kunder eller deras jurister går till dataskyddsadressen och besvaras av Anton.
- Mottagandet ska bekräftas inom två arbetsdagar (mallens 48 timmar).
- Varje fråga loggas med datum, fråga och svar. Loggen finns inte; den ska föras i `../../../loggar/forfragningar.md`, införs [FYLL: datum], ansvarig Anton.

## Genomgång av bevis

En gång per år går Anton igenom matrisen och uppgifterna, uppdaterar hänvisningarna och skriver datum för genomgången överst i `../matris.md`. Första genomgången: [FYLL: datum].

## Mätning

Inget bevis äldre än tolv månader. Ingen lucka öppen mer än 30 dagar utan beslut om tidsplan.

## Undantag

En lucka som skjuts upp kräver en skriven motivering, en måldag och Antons beslut i `docs/BESLUT.md`.

## Brister

En obesvarad fråga eller en försenad lucka tas upp i nästa genomgång och läggs som ärende i `bd`.

## Förbättring

Efter varje kundfrågeformulär eller revision justeras matrisen så att nästa svar går fortare.
