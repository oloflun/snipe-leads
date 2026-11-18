# Internal Audit Procedure

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_691e4bd04aac53e783cb7c14` (avdelning `qms`) |
| Täcker kontroll | Internal Audit & Management Review (`frk_ct_69e639b96ad6c5e729676acb`) |
| Täcker krav | 9.1.1, 9.1.2, 9.2, 9.3, 10.1, A.5.35, A.8.34 |

Mallen är skriven för ett kvalitetsledningssystem (ISO 9001, "QMS"). Här gäller den informationssäkerhetsarbetet. Kontrollen omfattar också ledningens genomgång, som mallen saknar; den står sist.

## Syfte

Ta reda på om Snajp följer sina egna policyer och om de fungerar.

## Omfattning

Allt inom omfånget i `07-information-security-privacy-governance.md`, även det som sköts av leverantörer.

## Revisionsprogram

- **Intervall:** en internrevision per år. Den första före första betalande kund om det hinns, annars senast [FYLL: datum].
- **Oberoende:** mallen kräver att ingen granskar sitt eget arbete. Med två personer går det inte fullt ut. Ordningen blir:
  1. Anton granskar det Sebbe bygger och driver, och Sebbe det Anton ansvarar för.
  2. Minst vartannat år granskar en extern person en del av arbetet, till exempel konton och säkerhetskopior: [FYLL: namn eller byrå]. Det täcker också krav A.5.35.
  3. En AI-agent kan göra underlaget (som `../matris.md`), men slutsatsen dras av en människa.
  Avsteget är ett undantag som Anton godkänner.
- **Plan:** inför varje revision skrivs omfång, kriterier (`../matris.md`, `../soa.md`) och datum i `../../../loggar/revisioner.md`. Loggen finns inte; införs [FYLL: datum].

## Genomförande

- Belägg samlas genom att läsa filer, konfiguration och loggar, och genom att fråga den andra.
- Granskning mot driften görs med läsrättighet och torrkörning (krav A.8.34). Ingen skrivande åtgärd under en revision utan Antons ja.
- Fynd delas in i större avvikelse, mindre avvikelse och förbättringsförslag.
- Varje avvikelse får en åtgärd med ansvarig och datum (krav 10.1).

## Samordning

Revisionen görs tillsammans med årsgenomgången av GDPR-matrisen (`../../gdpr/matris.md`), så att samma belägg används en gång.

## Ledningens genomgång (krav 9.3)

Två gånger per år, en timme, Anton och Sebbe. Underlag: ändringar i omfång och leverantörer, incidenter, revisionsfynd, riskregistret, mätvärden ur policyerna och åtgärdernas status. Beslut skrivs i `docs/BESLUT.md` med datum. Första: [FYLL: datum]. Ingen har hållits.

## Mätning

Alla planerade revisioner genomförda. Varje avvikelse har en åtgärdsplan inom 30 dagar.

## Undantag

En revision får flyttas högst 30 dagar med Antons ja, om årscykeln hålls.

## Förbättring

Checklistan (`../matris.md`) uppdateras varje år efter ändringar i tjänster, leverantörer och lagar.
