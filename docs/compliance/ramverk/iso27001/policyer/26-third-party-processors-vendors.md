# Third-Party Processors (Vendors)

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); leverantörslistan kvartalsvis |
| Ramverkets mall | `frk_pt_68bb155d6b8eaafd14904188` (avdelning `admin`) |
| Täcker kontroll | Supplier & Third-Party Security (`frk_ct_69e639b9bf66b5a6ffb17d27`) |
| Täcker krav | A.5.19, A.5.20, A.5.21, A.5.22, A.5.23 |

**Förhållande till Vendor & Third-Party Risk.** Mallens text är, utom de villkorade HIPAA-avsnitten, ordagrant densamma som mallen *Vendor & Third-Party Risk* (`frk_pt_685e462046667f75a50a2c3e`), som redan är anpassad till Snajp i `../../gdpr/policyer/06-vendor-third-party-risk.md`. Den filen gäller för leverantörslista, nivåer, granskning, avtal, uppföljning och avslut. Den här policyn skriver inte om den. Den lägger bara till det ISO 27001 kräver utöver GDPR-versionen.

## Syfte

Hantera risken från leverantörer som når Snajps data eller som driften står på.

## Omfattning

Alla leverantörer i `../../../leverantorer.json`, och dessutom den öppna källkod och de verktyg som driften byggs av.

## Leverantörslista och nivåer

Enligt G06. Nivån "Kritisk" (verksamheten stannar utan den) gäller Railway, Google Cloud (Vertex), Redis Cloud, Resend och GitHub.

## Granskning av säkerhet

Enligt G06. Tillägg: för kritiska leverantörer sparas intyget (SOC 2-rapport eller ISO 27001-certifikat) eller en anteckning om varför det inte gått att få. Läget: Railway SOC 2 Type II (rapport på trust.railway.com, inte hämtad), Redis SOC 2 och ISO 27001 (inte lästa), Resend SOC 2 Type II, Google ISO 27001 enligt DPA:n (`../../../leverantorsgranskning.md` §1, 3, 4, 5). Inget intyg är sparat. [FYLL: datum], ansvarig Anton.

## Avtal

Enligt G06. Tillägg för krav A.5.20: utöver DPA:n kontrolleras att avtalet säger hur snabbt leverantören meddelar en incident, att Snajp får ut sin data vid avslut, och att leverantören raderar den. Railways DPA gäller först när den är signerad (JA #6).

## IKT-leveranskedjan (krav A.5.21, utöver G06)

- **Öppen källkod:** Python- och Node-beroenden och basimagen granskas genom Dependabot (P22). Nya beroenden läggs till i PR och granskas som annan kod.
- **Vendorade skills** ändras bara med deklarerad uppdatering (INV-SKILL-005, 006).
- **AI-kodverktyg** (Claude Code, Codex) skriver kod och läser repot. De räknas som leverantörer: vilka data de ser och på vilka villkor ska stå i leverantörslistan, [FYLL: datum], ansvarig Anton. I dag läser de testmiljöns kunddata (JA #28).
- Underbiträdenas egna underbiträden står i leverantörsgranskningen.

## Löpande uppföljning (krav A.5.22, utöver G06)

- Varje kvartal: leverantörslistan mot driften. Exempel på vad det fångar: TypeSafe fick kundmejl utan att stå i någon lista (`../../../BESLUTSUNDERLAG-2026-11-17.md` A2).
- Ändrade villkor, regioner eller underbiträden hos en kritisk leverantör läses inom en månad från att de meddelats.

## Molntjänster (krav A.5.23, utöver G06)

- Hela driften är molntjänster. För varje kritisk leverantör ska det stå hur Snajp tar sig ut: Postgres-dump (P18), DNS hos Loopia, koden i git. Exitplan: [FYLL: datum], ansvarig Anton.
- Tjänster som inte längre används stängs och raderas. **Avsteg:** Render-tjänsten pingas fortfarande av `.github/workflows/keep-backend-awake.yml`, och Supabase-projektet finns kvar (JA #15).

## Avslut

Enligt G06.

## Mätning

Alla kritiska leverantörer har sparat intyg och signerat avtal. Listan stämd mot driften varje kvartal.

## Undantag

Snabb anslutning utan full granskning kräver Antons skriftliga ja och en plan, och aldrig för kunddata.

## Brister

En leverantör som får kunddata utan avtal stoppas och behandlas som incident.

## Förbättring

Frågorna till leverantörerna förenklas varje år.
