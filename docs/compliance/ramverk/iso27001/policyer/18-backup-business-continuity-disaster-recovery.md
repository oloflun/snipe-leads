# Backup, Business Continuity & Disaster Recovery

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`); återställningsprov kvartalsvis |
| Ramverkets mall | `frk_pt_685e44939f827e6a9f736fd4` (avdelning `it`) |
| Täcker kontroller | Business Continuity & ICT Readiness (`frk_ct_69e639b9d5ced482c12ae932`), Disaster Recovery Planning (`frk_ct_683f4dd564057a97ae323c9f`), Resource Capacity Management (`frk_ct_683f4b7614d209f8b6ffd477`) |
| Täcker krav | A.5.29, A.5.30, A.8.6, A.8.13, A.8.14 |

## Syfte

Kunna återställa kunddata och tjänsten inom bestämd tid efter ett fel, och fortsätta arbeta säkert under ett avbrott. GDPR art. 32.1 c kräver förmågan.

## Läget i dag

**Produktionsdatabasen har inga säkerhetskopior.** Railways API visar inga scheman och inga kopior på någon volym, varken i `main` eller `development` (`../../../bevis/railway-backuper-2026-11-17.txt`). Testmiljön synkas från produktionen, men ligger hos samma leverantör i samma region och tar emot samma fel (`../../../BESLUTSUNDERLAG-2026-11-17.md` A4). Ett förstört schema i produktionen går inte att återställa.

## Omfattning

Postgres i `main` (all kunddata), Redis (jobbkö, kort livslängd), koden i GitHub, driftvariablerna i Railway, DNS hos Loopia.

## Säkerhetskopior

Ska införas, ansvarig Anton, [FYLL: datum], helst före första betalande kund:

- Railways schemalagda kopior på produktionsvolymen: dagligen, veckovis och månadsvis. Railway sparar dem 6, 27 och 89 dagar (`../../../leverantorsgranskning.md` §3). Mallen kräver 30 dagar online; veckokopiorna täcker det.
- **En kopia utanför Railway** (mallens krav på separat leverantör eller region), till exempel en krypterad dump en gång i veckan till en lagring i EU: [FYLL: plats]. Hos vem och hur den krypteras beslutar Anton.
- Var Railways kopior lagras är inte belagt. Anton begär besked när DPA:n signeras (JA #6).
- Driftvariablerna exporteras utan värden varje månad (som `../../../bevis/railway-konfiguration-2026-11-17.txt`). Värdena finns i `.env.deploy`.
- Koden finns i GitHub och lokalt hos båda. Redis säkerhetskopieras inte: innehållet lever högst en timme och liggaren i Postgres är sanningen (INV-JOB-002, INV-JOB-003).

## Återställningsprov och mål

- **Mål (förslag, Anton beslutar):** RPO 24 timmar (högst ett dygns data förloras), RTO 8 arbetstimmar. [FYLL: beslut]
- Första provet: återställ senaste kopian till en tom volym, kontrollera tabellerna, skriv tiden. Ska göras direkt efter att kopiorna slagits på, ansvarig agent på Antons ja. Beviset är uppgifterna *Planning* och *Backup Restoration Test*.
- Därefter varje kvartal, som mallen kräver.

## Kontinuitetsplan

| Händelse | Vad vi gör |
|---|---|
| Railway nere | Vänta och informera kunderna. Ingen reservdrift finns. Supportagenten slutar svara; kunderna hanterar sin inkorg själva |
| Vertex AI nere | Agenterna kan inte svara. Hur koden beter sig är inte provat; reservvägen till AI Studio får inte bära kunddata (JA #13) |
| GitHub nere | Ingen deploy. Driften fortsätter. Synken stannar |
| Databasen förstörd | Återställ senaste kopian (finns inte i dag) |
| Anton otillgänglig | Sebbe stoppar pågående skada men fattar inga incidentbeslut (`INCIDENT_RESPONSE.md` §1). [FYLL: vem har nycklar och lösenord om Anton är borta längre] |
| Läckt nyckel | Rotera först (`INCIDENT_RESPONSE.md` §3) |

Under ett avbrott gäller samma säkerhetsregler. Inga tillfälliga genvägar som att stänga av RLS eller öppna databasen publikt (krav A.5.29).

## Roller

Anton beslutar om återställning och kontaktar kunderna. Kontaktlista till Railway, Redis, Google och Resend: [FYLL: plats utanför det publika repot].

## Kapacitet och redundans

- En replik per tjänst i en region (`../../../bevis/railway-regioner-2026-11-17.txt`). Ingen redundans.
- Tillgänglighetskrav: [FYLL: Antons beslut, t.ex. kontorstid, inget avtalat]. Redundans införs när ett avtal kräver det.
- Kvoter: hastighetsbegränsning (`snajp-support/app/api/rate_limit.py`), tokenbudget för leads, och kreditslut hanteras som fel (INV-QUOTA-001).

## Mätning

Minst 95 procent lyckade kopior. Senaste återställningsprovet inom tre månader och inom målen.

## Undantag

Ett system utan kopia kräver Antons beslut och ett sätt att bygga upp det igen.

## Brister

En misslyckad kopia eller ett misslyckat prov åtgärdas direkt och tas upp vid nästa ledningsgenomgång.

## Förbättring

Planen uppdateras efter varje prov och avbrott.
