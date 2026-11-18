# Information Security & Privacy Governance

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`), och när någon får eller förlorar åtkomst |
| Ramverkets mall | `frk_pt_685e3f7b4ebcb27b60c51434` (avdelning `admin`) |
| Täcker kontroll | Policy Compliance (`frk_ct_683f3ecd42e62fde624c59c1`) |
| Täcker krav | 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 7.1, 7.4, 9.1.1, 10.2, A.5.1, A.5.2, A.5.4 |

Den här policyn är Snajps informationssäkerhetspolicy (krav 5.2). De andra 25 policyerna bygger på den.

## Syfte

Bestämma vem som äger säkerheten och dataskyddet hos Snajp, vad som omfattas, och hur besluten dokumenteras. Målet är att kunderna ska kunna lita på att deras kunders mejl och chattar skyddas enligt GDPR art. 32.

## Omfattning (ISMS-omfång, krav 4.3)

Förslag till beslut:

- **Verksamhet:** supportagenten, leadsagenten och kvittohanteraren, med webb, api och agentsajt.
- **Miljöer:** Railway-miljöerna `main` och `development` (Amsterdam), Redis Cloud, Google Cloud (Vertex AI), Resend, GitHub (kod, CI, synk), Loopia (DNS), och övriga leverantörer i `../../../leverantorer.json`.
- **Personer:** Anton och Sebbe, och de AI-kodverktyg som arbetar i repot.
- **Utrustning:** de egna datorer och telefoner som når kod, driften eller kunddata.
- **Utanför omfånget:** kundernas egna system och konton (inkorgar, CRM), som kunden ansvarar för.

**Sammanhang (krav 4.1, 4.2).** Snajp är en svensk enskild firma utan betalande kund. Kunderna kräver ett biträdesavtal med säkerhetsåtgärder (art. 28.3 c). De registrerade är kundernas kunder och B2B-prospekt. IMY är tillsynsmyndighet. Nuläget står i `../../../nulage-inventering.md` och `../matris.md`.

## Roller

- **Säkerhets- och dataskyddsansvarig:** Anton. Beslutar policyer, risker och undantag, bedömer incidenter (`INCIDENT_RESPONSE.md` §1).
- **Ersättare:** [FYLL: Sebbe eller ingen]. I dag finns ingen. Är Anton borta mer än två arbetsdagar fattas inga säkerhetsbeslut, utom att stoppa en pågående incident.
- **Sebbe:** medutvecklare med åtkomst till kod och driften. Roll, befogenheter och avtal är inte dokumenterade: [FYLL: roll], ansvarig Anton, [FYLL: datum].
- **AI-kodverktyg:** följer `CLAUDE.md`. De fattar inga säkerhetsbeslut.
- Rollerna bekräftas varje år och när någon börjar eller slutar. Mallen säger att namnen förs in i Comp AI; plattformen är inte driftsatt, så de står här.

## Ledningens ansvar

- Anton skriver under ett årligt åtagande om att han bär ansvaret för säkerhet och dataskydd. Första gången: [FYLL: datum].
- **Ledningens genomgång** hålls två gånger per år, enligt P10. Mallen kräver kvartalsvis först över en viss storlek; Snajp ligger under den.
- Varje arbetsvecka med kodändringar ska ha minst en säkerhetsåtgärd ur `../matris.md` i arbete. Nytt åtagande från godkännandet. Tid: [FYLL: timmar per månad] (krav 7.1).

## Policyhantering

Styrs av `08-policy-management-exception-handling.md`.

## Medvetenhet

Den som får åtkomst läser policyerna och kvitterar innan åtkomsten ges (`../../gdpr/policyer/05-security-privacy-awareness-training.md`). Anton och Sebbe har åtkomst utan kvittens i dag.

## Kommunikation (krav 7.4)

| Vad | Till vem | Vem | Hur |
|---|---|---|---|
| Godkända policyer och ändringar | Sebbe | Anton | Mejl eller möte inom fem arbetsdagar |
| Incident som rör en kunds data | Kunden | Anton | Enligt `INCIDENT_RESPONSE.md` §5 |
| Säkerhetsfrågor från kunder | Kunden | Anton | Svar inom fem arbetsdagar, med `../matris.md` som underlag |

## Mätning

Varje år: policyerna godkända och granskade inom tolv månader, roller bekräftade, åtagandet underskrivet, kvittenser aktuella. I dag är inget av det uppfyllt.

## Undantag

Avsteg skrivs i undantagsregistret (P08) med skäl, restrisk och slutdatum.

## Brister

Saknade loggar eller försenade åtgärder rättas inom två veckor eller tas upp vid nästa ledningsgenomgång.

## Förbättring

Lärdomar från revisioner och incidenter förs in vid nästa årliga översyn.
