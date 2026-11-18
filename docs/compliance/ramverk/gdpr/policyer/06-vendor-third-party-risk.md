# Vendor & Third-Party Risk

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); leverantörslistan kvartalsvis |
| Ramverkets mall | `frk_pt_685e462046667f75a50a2c3e` (avdelning `it`) |
| Täcker kontroller | Data Processing Agreements with Third Parties (`frk_ct_69e918eaa930d07ea41dd0d0`), Data Protection Impact Assessment Process (`frk_ct_69e918e9be6da6eba7d0ea4e`) |
| Täcker krav | AG-2 Data Processor Agreements, DS-4 Data Protection Impact Assessment |

Ramverket kopplar DPIA-kontrollen till den här policyn. Därför har den ett eget avsnitt om konsekvensbedömningar sist.

## Syfte

Hantera risken med leverantörer som får Snajps eller kundernas data, och se till att ingen leverantör får kunddata innan den är godkänd.

## Omfattning

Alla molntjänster, SaaS-tjänster, modelleverantörer och datakällor. GDPR-delen gäller alla som behandlar personuppgifter för Snajps räkning (underbiträden), och det som kunden själv kopplar in (kanaler och CRM) i den mån Snajp skickar data dit.

## Leverantörslista och nivåer

Listan är `../../../leverantorer.json` med underlaget i `../../../leverantorsgranskning.md` (15 leverantörer granskade 2026-11-17). Varje post har namn, roll, vilka personuppgifter, plats för behandlingen, överföringsmekanism, DPA och hur den ingås, och bedömning. Det mallen dessutom kräver och som saknas i dag:

- ägare hos Snajp per leverantör (Anton för alla tills annat beslutas),
- rättslig grund per leverantör (finns per behandling i registerförteckningen),
- datum då DPA:n ingicks, senaste granskning och nästa granskning: [FYLL per leverantör], ansvarig agent.

Nivåer enligt mallen:

| Nivå | Betyder | Hos Snajp |
|---|---|---|
| Kritisk | Verksamheten stannar utan den | Railway, Google Cloud Vertex AI, Resend, Redis Cloud |
| Hög | Får kunddata eller Begränsad data | TypeSafe (så länge inkorgsklassningen är på), GitHub (synken), Supabase och Render (historiska data) |
| Medel | Interna verktyg, publik eller bolagsnivådata | ScrapeGraphAI, Loopia, Cal.com |
| Låg | Ingen persondata | Google PageSpeed, IndexNow, Cloudflare DNS |

Underbiträdena står på fyra ställen som ska stämma: `lib/bolag.ts`, `docs/pub-avtal.md` Bilaga 3, `docs/pilotavtal.md` Bilaga 1 och `docs/registerforteckning.md` (`docs/JURIDIK_ATGARDER.md`, "Löpande").

## Godkännande av ny leverantör innan data skickas

**Det här gäller från godkännandet av policyn.** TypeSafe fick kundmejltext utan att stå i någon förteckning, utan avtal och mot ett tidigare beslut (`INCIDENT_RESPONSE.md`, post 2026-11-17). Ordningen nedan finns för att det inte ska hända igen.

En leverantör får inte ta emot personuppgifter eller kunddata, i någon miljö där data är riktig, förrän alla sju stegen är gjorda:

1. **Vad som skickas.** Skriv vilka fält och vilken data, och från vilken miljö.
2. **Avtal.** DPA finns och gäller kontot. Skriv hur den ingicks (automatiskt, signerad, klick) och spara en kopia eller länk med datum.
3. **Plats och överföring.** Var behandlas och lagras data? Vid tredjeland: DPF-status (slå upp i deltagarlistan), annars SCC, och en överföringsbedömning (TIA) om skyddet beror på SCC.
4. **Villkor.** Ingen träning på kunddata, ingen tidsobegränsad rätt att använda härledd data (som TypeSafes telemetrivillkor), känd lagringstid och radering vid avtalets slut.
5. **Förteckningar.** Leverantören läggs in på alla fyra ställen ovan i samma commit som koden.
6. **Kunderna.** Är leverantören ett nytt underbiträde för kunddata meddelas kunderna i förväg enligt PUB-avtalet, så att de kan invända (art. 28.2).
7. **Beslut.** Anton godkänner skriftligt i `docs/BESLUT.md`.

**Teknisk spärr:** en ny utgående väg för kunddata ska ha en brytare som står på av som standard och en kodspärr där data är riktig, efter samma mönster som DeepSeek-spärren (`snajp-support/app/config.py:609-700`). Ska införas för AI Studio-vägen, [FYLL: datum], ansvarig agent (JURIDIK_ATGARDER #13).

## Granskning av säkerhet

- **Kritisk och Hög:** SOC 2- eller ISO 27001-intyg, eller leverantörens publicerade säkerhetsbeskrivning, läses före avtal. I dag är intygen noterade men inte lästa för Railway, Redis, Resend och TypeSafe (`../../../leverantorsgranskning.md`).
- **Medel:** leverantörens publika villkor och integritetspolicy läses.
- Fynd och beslut skrivs i leverantörsgranskningen.

## Avtalskrav

Varje DPA ska kräva att leverantören:

- bara behandlar enligt Snajps dokumenterade instruktioner,
- har lämpliga tekniska och organisatoriska åtgärder,
- har sekretess för sin personal,
- bara anlitar nya underbiträden efter förhandsbesked och för vidare samma krav,
- hjälper till med de registrerades rättigheter, säkerhet, incidenter och konsekvensbedömningar,
- raderar eller lämnar tillbaka data när avtalet slutar,
- ger den information som behövs för att visa efterlevnad och tillåter granskning,
- meddelar personuppgiftsincidenter utan onödigt dröjsmål.

Läget mot kraven (2026-11-17, ur leverantörsgranskningen):

| Leverantör | DPA | Det som fattas |
|---|---|---|
| Google Cloud Vertex AI | Automatisk | Avtalsparten inte utläst |
| Railway | **Inte signerad** | Anton signerar via DocuSign; besked om backupplats (JURIDIK_ATGARDER #6) |
| Redis Cloud | Automatisk | Betald plan obekräftad; TLS av (#4, #10) |
| Resend | Automatisk | Signerad kopia inte nedladdad; lagring i USA ej godkänd; ingen TIA (#10) |
| TypeSafe | Oklart vilka villkor kontot godkände | Telemetrivillkor utan tidsgräns; ej DPF; ingen radering vid avtalsslut. Beslut om stopp (#3) |
| ScrapeGraphAI | Ingen | Betald plan och DPA (#10) |
| GitHub | Gäller inte Free-planen | Flytta synken eller byt plan (#11) |
| Supabase, Render | Automatisk | Radera och få raderingen bekräftad (#15) |

## Löpande uppföljning

- DPA:erna för alla underbiträden granskas en gång per år. Granskningen loggas med leverantör, datum för DPA, senaste och nästa granskning.
- Aviseringar om nya underbiträden läses och listorna uppdateras. Varseltider: Google 30 dagar, Resend 14, TypeSafe 15, Redis 5 (`docs/JURIDIK_ATGARDER.md`, "Löpande").
- Nyheter om incidenter hos Kritiska och Höga leverantörer bedöms när de kommer.

## Avslut

När en leverantör slutar användas: radera eller hämta hem data, begär skriftlig bekräftelse på radering, dra in nycklar och integrationer inom 48 timmar och stryk leverantören på alla fyra ställen. Gäller nu Supabase och Render, som inte är stängda (`INCIDENT_RESPONSE.md`, poster 2026-08-24).

## Konsekvensbedömning (DS-4)

**När en DPIA ska göras.** Före en ny behandling eller en väsentlig ändring, om något av följande gäller:

- ny teknik eller en ny modelleverantör som får kunddata,
- storskalig behandling av kundernas kunders uppgifter,
- känsliga uppgifter som kan förekomma i löptext,
- systematisk uppföljning av personer (till exempel spårning av klick per namngiven mottagare),
- automatiserade svar eller beslut som kan påverka personer i betydande grad,
- data till ett nytt tredjeland.

**Hur.** Mallen är `docs/dpia_supportagenten.md`: behandlingen, nödvändighet, risker med sannolikhet och konsekvens, åtgärder och restrisk. Där Snajp är biträde är DPIA:n ett underlag till kunden, som beslutar. Där Snajp är ansvarig beslutar Anton.

**Förhandssamråd.** Är restrisken hög efter åtgärder samråder den ansvarige med IMY innan behandlingen börjar (art. 36).

**Läget i dag.** En DPIA finns för supportagenten, uppdaterad 2026-11-17, ogranskad. Leadsagenten har en intresseavvägning men ingen DPIA eller skriftlig prövning av om en behövs. Prövningen ska göras, [FYLL: datum], ansvarig agent med Antons beslut. DPIA-posterna sparas i `docs/`.

## Mätning

Alla underbiträden har en DPA på fil, granskad inom tolv månader. Alla överföringar till tredjeland har en dokumenterad mekanism. Listan stäms av mot koden varje kvartal.

## Undantag

En leverantör får tas i bruk utan full granskning bara med Antons skriftliga beslut, en tidsgräns och utan kunddata under tiden.

## Brister

Saknat avtal eller utgånget avtal flaggas till Anton och leder till att dataflödet stängs av tills det är löst.

## Förbättring

Godkännandestegen och nivåerna ses över en gång per år.
