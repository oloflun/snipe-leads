# Läs mig: underlag att signera, fylla i och skicka

**8 dokument att signera, 5 att fylla i, 7 brev att skicka (i 6 filer), cirka 8 timmar av din tid totalt.** Sebbe behöver dessutom cirka 3 timmar (genomgången, enheterna, åtkomstgenomgången, övningen).

Skrivet 2026-11-17 av en agent. Inget är signerat, skickat eller gjort i drift. Ett krav räknas som flyttat först när du signerat, fyllt i eller skickat, och flera blir uppfyllda först när åtgärden bakom är utförd (till exempel att säkerhetskopiorna slagits på).

Sorterat efter hur många krav dokumentet flyttar per minut av din tid. Beteckningar: GDPR = `ramverk/gdpr/matris.md`, 27001 = `ramverk/iso27001/matris.md`, 42001 = `ramverk/iso42001/matris.md`.

| # | Dokument | Krav det stänger eller flyttar | Din åtgärd | Tid |
|---|---|---|---|---|
| 1 | `beslut/f-godkannande-ny-leverantor-modell.md` | Flyttar GDPR AG-2, DS-1; 27001 A.5.19, A.5.20, A.8.9; 42001 A.10.3, 6.3, 8.1 | Läs, signera | 15 min |
| 2 | `beslut/b-dataskyddsombud.md` | Stänger GDPR AG-4 och uppgiften *Appoint or Review DPO* (`not_relevant`) | Fyll i antal kunder, signera | 5 min |
| 3 | `beslut/g-sakerhetskopiering-aterstallning.md` | Flyttar 27001 A.8.13, A.5.30, A.5.29, A.8.14; GDPR DS-2. Stängs först när Pro-planen gäller och första provet är gjort | Besluta målen, fyll i datum och intervall, signera | 10 min (+ Pro-planen) |
| 4 | `beslut/a-ansvarig-dataskydd-informationssakerhet.md` | Stänger GDPR AG-1 (delvis: dataskyddsadressen saknas); 27001 5.3, A.5.2; 42001 5.3, A.3.2 | Fyll i Sebbes ställning, ersättare och systemägarskap; du och Sebbe signerar | 15 min |
| 5 | `beslut/c-eu-representant.md` | Stänger GDPR AG-3 (dokumenterar ej tillämpligt) | Signera | 3 min |
| 6 | `beslut/d-gallringsperiod.md` | Flyttar GDPR DS-2, LBT-1, LBT-3; 27001 A.8.10. Blir sant först när gallringsjobbet körs | Läs, signera | 15 min |
| 7 | `rutiner/a-begaran-fran-registrerad.md` | Flyttar GDPR PR-1 till PR-6; PR-4 går från saknas till delvis | Fyll i adress, frister, ersättare; öppna brevlådan | 30 min |
| 8 | `beslut/e-omfattning-ledningssystem.md` | Stänger 27001 4.3, 42001 4.3; flyttar 4.4 i båda | Läs, signera | 10 min |
| 9 | `brev/a-typesafe.md` | Flyttar GDPR AG-2; 27001 A.5.26 (incidentposten 2026-11-17) | Fyll i konto och datum, skicka | 10 min |
| 10 | `rutiner/b-begaranslogg.md` | Flyttar uppgiften *Data Subject Rights Request Handling*; GDPR PR-1 | Kopiera till `loggar/begaranden.md` | 5 min |
| 11 | `brev/b-scrapegraphai.md` | Flyttar GDPR AG-2; 27001 A.5.20 | Hitta adressen, skicka | 10 min |
| 12 | `rutiner/e-enheter.md` | Flyttar 27001 A.8.1, A.8.7, A.7.7–A.7.10, A.5.9, A.6.7 (okänt → bedömt) och uppgifterna *Device List*, *Secure Devices* | Fyll i, ta skärmbilder (du och Sebbe) | 30 min var |
| 13 | `brev/f-forsta-kunden-foljebrev.md` | Flyttar GDPR AG-2 (kundsidan), PR-7; 42001 A.8.2, A.10.2 | Skicka efter juristgranskning av PUB-avtalet | 20 min |
| 14 | `brev/c-railway.md` | Flyttar GDPR AG-2; 27001 A.5.20, A.5.23; ger underlag till PUB 10.3 | Signera DPA:n i DocuSign först, sedan skicka | 20 min |
| 15 | `utbildning/genomgang.md` + `utbildning/kvittens.md` | Flyttar GDPR DS-3; 27001 7.2, 7.3, A.6.3; 42001 7.2, 7.3, A.4.6; AI-förordningen art. 4 | Läs och diskutera med Sebbe, båda signerar kvittensen | 65 min |
| 16 | `brev/d-supabase-och-render.md` | Flyttar 27001 A.5.23, A.8.10; incidentposterna 2026-08-24 | Radera i konsolerna, rotera Render-nyckeln, skicka två brev | 30 min |
| 17 | `brev/e-redis.md` | Flyttar 27001 A.5.23; stänger rad 3 i PUB Bilaga 3 | Besluta och radera databasen, ta bort reservvariabeln, skicka | 15 min |
| 18 | `rutiner/d-atkomstgenomgang.md` | Flyttar 27001 A.5.15–A.5.18, A.8.2, A.8.5 och uppgifterna *2FA*, *Access Review Log*, *Employee Access* | Fyll i med Sebbe, ta skärmbilder | 90 min |
| 19 | `rutiner/c-incidentovning.md` | Flyttar GDPR DS-5; 27001 A.5.24, A.5.27, 10.1 | Håll övningen med Sebbe, signera protokollet | 45 min |

## Innan du klistrar in besluten i `docs/BESLUT.md`

`docs/BESLUT.md` ligger i det publika repot. Beslut b, c och e är ofarliga att publicera. Beslut f och g beskriver kända brister (kundmejl till TypeSafe, inga säkerhetskopior). Vänta med dem tills du beslutat om repots synlighet (BU A1), eller förvara dem i `docs/compliance/loggar/` så länge.

## Det som inte gick att skriva färdigt

- Sebbes formella ställning, ersättare och systemägare (beslut a), antal kunder som utlöser omprövning (b), datum för Pro-planen och kopian utanför Railway (g): dina uppgifter.
- Mottagaradress till Railway, Render, Redis och ScrapeGraphAI: inte belagd i leverantörsgranskningen. Bara TypeSafe (`privacy@typesafe.ai`) och Supabase (`privacy@supabase.io`) är belagda.
- Åtkomstförteckningen och enhetslistan: nästan allt är [FYLL]. Det enda belagda är att Gmail-kontot har tvåstegsverifiering, att plattformsadmin är det delade Gmail-kontot och att Vertex har ett gemensamt servicekonto.
- Rätten till begränsning går bara att hantera manuellt. En spärrflagga kräver kod.
- Kontoradering: inget skript raderar ett konto i `auth.users`.

## Motsägelser i underlaget

1. P07:s omfång och 27001-matrisens avsnitt A.7 räknar Redis Cloud som drift. Jobbkön flyttade till Railways Redis 2026-11-17. Beslut e rättar det.
2. Integritetspolicyn säger att 24 månader är "beslutat" (kodkommentar) och att gallringen är automatiserad och loggas. BU B2 och registerförteckningen säger att perioden inte är beslutad, och inget jobb körs.
3. Spärrlistan: `gdpr_radera.py` och G02 behåller den tills vidare; PUB-avtalet Bilaga 1 sparar den "så länge avtalet gäller" och 10.6 raderar den med övrig data vid avtalets slut.
4. `gdpr_radera.py` hänvisar kontoradering till `scripts/admin_cleanup.py`, men det skriptet raderar inga konton; det sätter Gmail-kontot som enda plattformsadmin.
5. `gdpr_radera.py` listar "Redis" som en kopia med kort livslängd men nämner inte den gamla Redis Cloud-databasen, som har kvar cache tills den raderas.
6. `INCIDENT_RESPONSE.md` §2 och G03 säger att incidentanteckningen skrivs under `handoffs/`. Den mappen är inte undantagen i `.gitignore`, och repot är publikt.
7. GDPR-uppgift 11 säger att *Monitoring & Alerting* kan stängas med en skärmbild av ett larm. ISO-uppgifterna rättar det: larmvariablerna saknas, så inget larm skickas.
8. Integritetspolicyn säger att sajten sätter "en enda cookie". Cookiesidan och GDPR-uppgift 3 nämner två (tema och session).
9. P11, P13 och P18 anger redan intervallen (kvartalsvis åtkomstgenomgång, datorkontroll och återställningsprov). Rutinerna lämnar intervallet som [FYLL] enligt beställningen, med policyns värde som förslag.
