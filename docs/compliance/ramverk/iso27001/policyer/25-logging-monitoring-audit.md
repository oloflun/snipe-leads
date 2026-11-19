# Logging, Monitoring & Audit

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); larm och loggar månadsvis |
| Ramverkets mall | `frk_pt_685e43997555c7ab39983c21` (avdelning `it`) |
| Täcker kontroller | Security Monitoring & Detection (`frk_ct_683f46f3f181af3f93773c1d`), Utility Tool monitoring (`frk_ct_6849ba93636ff0155eb89158`) |
| Täcker krav | A.5.28, A.8.15, A.8.16, A.8.17, A.8.18 |

## Syfte

Kunna upptäcka fel och intrång, och visa i efterhand vad som hänt.

## Omfattning

Loggar i appen, i Railway, hos GitHub och hos leverantörerna.

## Loggar som finns

- `X-Request-Id` i varje svar och i loggen, och `platform_events` (`snajp-support/app/sparning.py`).
- `agent_runs` med stegloggar, och `ss_decision_log` för inkorgens beslut (`../../../nulage-inventering.md` §4).
- Railways tjänstloggar. Hur länge de sparas är inte belagt: [FYLL: Railways loggtid för Snajps plan].
- GitHubs historik över commits, PR:er och Actions-körningar.
- **Saknas:** en logg över vad plattformsadmin läser och ändrar. Ska införas eller medvetet avstås, beslut [FYLL: datum], ansvarig Anton (samma punkt som G02).

## Central logg

Mallen kräver en central SIEM. Det finns ingen, och för två personer är det inte rimligt i dag. I stället: Railways loggar plus felspårning (nedan). Undantag som Anton godkänner, omprövas när kunderna blir fler än [FYLL: antal].

## Lagring och skydd

- Säkerhetsrelevanta loggar ska finnas minst 90 dagar. Klarar Railways plan inte det, exporteras de: [FYLL: beslut].
- `agent_runs` sparar fulla promptar med persondata utan slutdatum. Lagringstid beslutas tillsammans med gallringen (G02, JA #8).
- Bara Anton och Sebbe når loggarna.

## Larm

- **Läget i dag:** internlarmet `[PRIORITERAT]` (`snajp-support/app/notifications/prioriterat_mejl.py`) skickar bara om `INTERNLARM_SMTP_ANVANDARE` och `INTERNLARM_SMTP_LOSENORD` är satta (rad 141-158). De saknas i api i båda miljöerna (`../../../bevis/railway-konfiguration-2026-11-17.txt` rad 83-132, 224-266). Larmet är alltså troligen inte aktivt. Det som verkar automatiskt är leveransstoppet vid studs och klagomål (`snajp-support/app/leads/send_guard.py:68-79`).
- **Ska införas,** [FYLL: datum], ansvarig Anton (variablerna) och agent (resten):
  1. Sätt larmvariablerna i `main` och prova med ett larm.
  2. En upptidskontroll av webb, api och support med larm till båda.
  3. Felspårning, till exempel en tjänst i EU. Kräver leverantörsgodkännande (G06).
  4. Larm vid misslyckad deploy och röd CI (GitHub och Railway skickar mejl).
- Larmen går till båda. Det finns ingen jour; larm utanför kontorstid hanteras nästa arbetsdag om inte kunddata är i fara.

## Granskning

Varje månad går Anton igenom larmen och tar stickprov i loggarna. Fynd skrivs i `../../../loggar/loggranskning.md` (finns inte). Mallens kvartalsrapport blir ett stycke i ledningens genomgång (P10).

## Bevis vid incident (krav A.5.28)

Vid misstänkt incident sparas berörda loggar direkt, innan de roteras bort: export ur Railway, `platform_events` och `agent_runs` för perioden, med klockslag och vem som exporterade. Sparas utanför det publika repot tillsammans med incidentdokumentet (G03).

## Tidssynk

Railway och leverantörerna synkar sina klockor. Datorerna använder operativsystemets tidssynk; det ska kontrolleras vid datorkontrollen (P13). Beviset är uppgiften *Utility Monitoring*.

## Mätning

Larmen fungerar (provade), månadsgranskningen gjord.

## Undantag

En tjänst som inte kan logga skrivs i undantagsregistret.

## Brister

Ett larm som inte gåtts igenom på en vecka tas upp med Anton.

## Förbättring

Nya larm läggs till efter varje incident.
