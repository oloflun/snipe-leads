# Security & Privacy Awareness Training

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e458a49e1eff0af54e3d2` (avdelning `it`) |
| Täcker kontroll | Information Security Policy and Awareness Training (`frk_ct_69e918e8c57e2f6756c995ca`) |
| Täcker krav | DS-3 Internal Security Policy and Awareness |

Kontrollen kräver både en intern säkerhetspolicy och utbildning. Snajp är två personer, så båda ryms här.

## Syfte

Anton och Sebbe ska känna igen risker för kunddata och veta vad de gör när något händer.

## Omfattning

Alla med åtkomst till kod, driftmiljöer eller kunddata: Anton och Sebbe. Inga anställda finns enligt underlaget. Den som senare får åtkomst (anställd, konsult, praktikant) omfattas från första dagen. AI-kodverktyg som arbetar i repot styrs av `CLAUDE.md`, som räknas som deras instruktion.

## Interna säkerhetsregler

Reglerna gäller från godkännandet. Det som redan står i `CLAUDE.md` gäller redan för agenterna och tas här in för människorna.

1. **Hemligheter** skrivs aldrig ut, committas aldrig och klistras inte in i chattar eller handoffs. De läses ur `.env.deploy`, som är gitignorerad (`CLAUDE.md`, "Läckagespärr"). Repot är publikt.
2. **Testmiljön** har samma sekretess som produktionen: inga skärmdumpar med kunddata, inga länkar till utomstående, ingen lokal server mot den (`CLAUDE.md`).
3. **Tvåfaktorinloggning** ska vara påslagen på GitHub, Railway, Google Cloud, Redis Cloud, Resend och Loopia för båda. Läget är inte kontrollerat: [FYLL: bekräftat datum per konto], ansvarig Anton.
4. **Delade konton och nycklar** ska bytas mot personliga där leverantören tillåter det. Ett servicekonto per miljö hos Google (JURIDIK_ATGARDER #14).
5. **Datorer** som når driftmiljöerna ska ha diskkryptering och skärmlås. Läget är inte kontrollerat: [FYLL: bekräftat datum], ansvarig Anton och Sebbe.
6. **Kunddata** lämnar inte driftmiljöerna, utom för att besvara en begäran enligt `04-privacy-data-subject-rights.md`.
7. **Misstänkt incident** rapporteras till Anton inom en timme (`03-incident-response-breach-notification.md`).

## Innehåll i utbildningen

En genomgång på ungefär en timme som tar upp:

- reglerna ovan,
- klassningen i `02-data-classification-handling.md`,
- nätfiske och falska inloggningssidor, särskilt mot GitHub och Railway,
- vad en personuppgiftsincident är och fristerna (72 timmar till IMY, utan dröjsmål till kunden),
- de registrerades rättigheter och hur en begäran tas emot,
- Snajp-specifikt: kundmejl kan innehålla personnummer och hälsouppgifter, testmiljön är en spegel, och webbplatsbedömningen är hemlig.

Material: de här policyerna, `INCIDENT_RESPONSE.md` och, om plattformen driftsätts, plattformens fem utbildningsvideor ("Security Awareness Training del 1–5").

## Vid start

Den som får åtkomst går igenom materialet under första veckan och kvitterar med namn och datum i `docs/compliance/loggar/utbildning.md`. Ingen åtkomst till produktionen eller testmiljön innan kvittensen finns.

Anton och Sebbe har åtkomst redan. Deras första genomgång ska ske senast [FYLL: datum], ansvarig Anton. Ingen utbildning är genomförd eller dokumenterad i dag.

## Årlig repetition och rollanpassning

En gång per år, samma format. Den som skriver kod går dessutom igenom de säkerhetsinvarianter som rör kunddata (`ARCHITECTURE_INVARIANTS.md`, INV-SEC-001 till INV-SEC-012).

## Nätfiskeövningar

Mallen kräver simulerade nätfiskeförsök varje kvartal. Det görs inte: med två personer som känner varandras mejlvanor ger en simulering inget mått. I stället tas verkliga nätfiskeförsök som någon av oss fått upp vid den årliga genomgången. Avsteget är ett undantag och ska godkännas av Anton.

## Dokumentation och mått

- Kvittenserna sparas i tre år i `docs/compliance/loggar/utbildning.md`.
- Mål: alla med åtkomst har en kvittens som är högst tolv månader gammal.

## Undantag

Vid frånvaro görs genomgången inom två veckor efter återkomsten.

## Brister

Den som saknar giltig kvittens får inte ny åtkomst till produktionsdata förrän den är gjord.

## Förbättring

Innehållet uppdateras efter varje incident och när nya leverantörer eller lagkrav tillkommer.
