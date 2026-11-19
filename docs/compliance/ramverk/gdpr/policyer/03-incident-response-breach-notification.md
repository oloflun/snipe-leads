# Incident Response & Breach Notification

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`), och efter varje incident |
| Ramverkets mall | `frk_pt_685e43e23b78127274355980` (avdelning `it`) |
| Täcker kontroll | Personal Data Breach Response Procedure (`frk_ct_69e918e94e68c0fb15ee98d0`) |
| Täcker krav | DS-5 Breach Notification Process |

**Förhållande till `INCIDENT_RESPONSE.md`:** den filen är rutinen som används när det händer, och den går före. Den här policyn säger vad som ska gälla runt rutinen och vad som ska införas. Krockar de, är det policyn som ska ändras.

## Syfte

Upptäcka, stoppa, anmäla och lära av incidenter, så att IMY får en anmälan inom 72 timmar och kunderna får besked i tid för sin egen frist.

## Omfattning

Alla system, leverantörer, miljöer (även testmiljön, som bär produktionens persondata) och personer med åtkomst: Anton, Sebbe och de AI-kodverktyg som arbetar i repot.

## Upptäckt och rapportering

- Den som upptäcker något misstänkt säger till Anton direkt, och senast inom en timme. Gäller också en AI-kodagent som stöter på en exponerad hemlighet eller persondata där den inte ska finnas: den stoppar och rapporterar.
- Tidpunkten då någon **blev medveten** skrivs ned direkt, i ett nytt dokument under `handoffs/` (`INCIDENT_RESPONSE.md` §2). Fristen räknas därifrån.
- **Larm som finns i dag:** interna larm med prefixet `[PRIORITERAT]` till supportbrevlådan (`snajp-support/app/notifications/prioriterat_mejl.py`), och leveransstopp vid studs och klagomål (`snajp-support/app/leads/send_guard.py:68-79`). Det finns ingen felspårning eller säkerhetsövervakning (nulägesinventeringen §2.2: "Sentry … finns inte").
- **Ska införas:** hemlighetsskanning och push-skydd i GitHub (JURIDIK_ATGARDER #2, #21), [FYLL: datum], Anton beslutar och agenten slår på.

## Roller

Mallen kräver fyra roller. Med två personer gäller:

| Mallens roll | Hos Snajp |
|---|---|
| Incidentledare | Anton. Bedömer om det är en personuppgiftsincident (`INCIDENT_RESPONSE.md` §1) |
| Teknisk ledare | Den av Anton och Sebbe som kan systemet bäst för just händelsen |
| Kommunikation | Anton. Kontaktar kunder och IMY (`INCIDENT_RESPONSE.md` §5) |
| Protokollförare | Den som upptäckte händelsen, tills Anton tar över |

**Nåbarhet:** Är Anton inte nåbar inom två timmar dokumenterar den som upptäckte händelsen och behandlar den som anmälningspliktig (`INCIDENT_RESPONSE.md` §1). Det finns ingen jour dygnet runt. Telefonnummer till båda ska stå i en kontaktlista som inte ligger i det publika repot: [FYLL: plats för kontaktlistan], införs [FYLL: datum], ansvarig Anton.

**Körböcker:** mallen nämner skadlig kod, dataläckage, överbelastning och intrång i molnkonto. Snajp har en gemensam rutin (`INCIDENT_RESPONSE.md` §2–6). En kort körbok för läckt nyckel eller lösenord ska skrivas, eftersom det är den vanligaste händelsen i loggen, [FYLL: datum], ansvarig agent.

## Begränsa och åtgärda

- Rotera eller dra in åtkomst först, kontrollera att den gamla vägen är stängd, och utred sedan (`INCIDENT_RESPONSE.md` §3).
- Målet är att stänga åtkomsten inom 30 minuter från att incidenten bekräftats, när någon av oss är vid en dator. Det är ett nytt åtagande, gäller från godkännandet av policyn.
- Varje åtgärd skrivs med klockslag i incidentdokumentet.

## Anmälan och kommunikation

- **Till IMY:** inom 72 timmar, om det inte är osannolikt att incidenten medför risk för de registrerade. Ofullständig anmälan i tid hellre än fullständig för sent (`INCIDENT_RESPONSE.md` §4). Gäller där Snajp är personuppgiftsansvarig (konton, egna kallmejl).
- **Till kunden:** där Snajp är biträde anmäler kunden till IMY. Snajp underrättar kunden utan onödigt dröjsmål, samma dag som bedömningen görs (`INCIDENT_RESPONSE.md` §5). Den avtalade fristen i timmar står i PUB-avtalet när det är granskat: [FYLL: antal timmar; pilotavtalet föreslår 24] (`docs/pub-avtal.md`, fråga 5).
- **Till de registrerade:** när incidenten sannolikt medför hög risk och Snajp är ansvarig, enligt art. 34. Som biträde hjälper Snajp kunden med underlaget.
- Externa uttalanden går genom Anton. Juridisk rådgivare: [FYLL: namn eller byrå].

## Efteråt

- Rad i `STATUS.md` och post i incidentloggen i `INCIDENT_RESPONSE.md` (§6).
- Genomgång av orsaken inom tio arbetsdagar, med åtgärder, ansvarig och datum. Nytt åtagande från godkännandet.
- **Läget i dag:** loggen har sju poster, och ingen är bedömd (`INCIDENT_RESPONSE.md:85-91`). De ska bedömas och stängas av Anton, med de två från 2026-08-24 först (JURIDIK_ATGARDER #15, #20). Policyn kan inte räknas som efterlevd förrän det är gjort.

## Test

Rutinen ska provas en gång per år med en skrivbordsövning på en verklig eller påhittad händelse, till exempel den läckta nyckeln. Första övningen: [FYLL: datum], ansvarig Anton. Den har aldrig provats.

## Mätning

Varje kvartal: tid från upptäckt till stängd åtkomst, tid till bedömning, och om fristerna hölls. Mäts från och med första incidenten efter godkännandet.

## Undantag

Avsteg från ordningen är bara tillåtna för att skydda liv, hälsa eller systemens drift, och skrivs ned efteråt.

## Brister

En incident som inte rapporterats eller hanterats fel tas upp av Anton och leder till en ändring i rutinen eller i koden (`INCIDENT_RESPONSE.md` §6: "En incident som inte gav en ändring … kommer tillbaka").

## Förbättring

Rutinen och körböckerna uppdateras efter varje genomgång.
