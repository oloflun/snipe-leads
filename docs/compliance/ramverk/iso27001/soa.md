# Statement of Applicability, utkast

**UTKAST 2026-11-17, uppdaterat 2026-11-18. Ägaren (Anton) ska besluta varje rad.** Inget här är godkänt. Ett ändrat beslut skrivs in med datum, och skälet förs in i `docs/BESLUT.md`.

Underlag: `matris.md` (status och belägg per krav), ISO 27001:2022 bilaga A så som Comp AI-ramverket `frk_681ecc34e85064efdbb76993` (commit `712ee1b3`) återger den: 93 kontroller, A.5.1–A.8.34.

**Kolumner.** *Tillämplig*: ja eller nej. *Motivering*: varför kontrollen gäller Snajp, eller varför inte. *Införd*: ja, delvis, nej eller okänt, enligt statusen i `matris.md` 2026-11-18 (uppfyllt = ja, delvis = delvis, saknas = nej, okänt = okänt).

**Förutsättningar som styr urvalet.** Snajp är en enskild firma med två personer. All drift ligger hos molnleverantörer: Railway i Amsterdam och Google Cloud i EU (`../../bevis/railway-regioner-2026-11-17-efter.txt`). Jobbkön flyttade från Redis Cloud till Railway 2026-11-17. Inga lokaler, inget serverrum, inga egna servrar. Arbetet sker på egna bärbara datorer. Produkterna behandlar kundernas kundmejl och chattar (Snajp är biträde) och B2B-prospekt (Snajp är ansvarig för egna utskick). GDPR art. 32 är huvudskälet till att kontrollerna införs.

Sammanställning 2026-11-18: 85 tillämpliga, 8 inte tillämpliga. Av de tillämpliga: 0 införda, 58 delvis, 15 nej, 12 okänt. (2026-11-17: 0 införda, 55 delvis, 18 nej, 12 okänt.)

**Ändrat 2026-11-18.** Ingen kontroll är införd fullt ut. Tre gick från nej till delvis, enligt `matris.md`: A.5.7 (Dependabot bevakar sårbarheter i beroenden), A.8.8 (Dependabot, kodskanning och hemlighetsskanning påslagna; 10 kritiska och 28 höga larm öppna) och A.8.16 (driftövervakning med provad larmkedja; ser inte intrång). Övriga rader har nya belägg men samma värde; se "ändr. 11-18" i matrisen. Raderna nedan visar dagens värde, och ändrade rader säger vad de var.

## A.5 Organisatoriska kontroller

| Kontroll | Tillämplig | Motivering | Införd |
|---|---|---|---|
| A.5.1 Informationssäkerhetspolicyer | ja | Krävs för allt annat; GDPR art. 24.2 | nej |
| A.5.2 Roller och ansvar | ja | Två personer med full åtkomst behöver tydlig ansvarsfördelning | delvis |
| A.5.3 Åtskillnad av uppgifter | ja | Begränsad med två personer; kompenseras med granskning av `main`, loggar och granskning i efterhand (P11) | delvis |
| A.5.4 Ledningens ansvar | ja | Anton ska kräva att reglerna följs | nej |
| A.5.5 Kontakt med myndigheter | ja | IMY vid personuppgiftsincident, CERT-SE och polis vid intrång | delvis |
| A.5.6 Kontakt med intressegrupper | ja | Billig bevakning (CERT-SE) räcker | nej |
| A.5.7 Hotunderrättelser | ja | Leverantörernas säkerhetsmeddelanden och sårbarheter i beroenden | delvis (var nej, ändr. 11-18) |
| A.5.8 Säkerhet i projekt | ja | Ny funktionalitet rör kunddata nästan alltid | delvis |
| A.5.9 Förteckning över tillgångar | ja | Data, tjänster, konton och datorer måste vara kända | delvis |
| A.5.10 Tillåten användning | ja | Egna datorer används för både jobb och privat | delvis |
| A.5.11 Återlämning av tillgångar | ja | Gäller nycklar, konton och kunddata på egna datorer när någon slutar | nej |
| A.5.12 Klassning | ja | Kundmejl, nycklar och den hemliga webbplatsbedömningen kräver olika skydd | delvis |
| A.5.13 Märkning | ja | I förenklad form: klassning efter plats, inte per fil (G02) | delvis |
| A.5.14 Informationsöverföring | ja | Kunddata går till flera leverantörer och mellan miljöer | delvis |
| A.5.15 Åtkomststyrning | ja | Kärnan i art. 32 | delvis |
| A.5.16 Identitetshantering | ja | Delade konton finns i dag | delvis |
| A.5.17 Autentiseringsinformation | ja | Lösenord har läckt via publik git-historik | delvis |
| A.5.18 Åtkomsträttigheter | ja | Åtkomst till leverantörskonton måste kunna granskas | delvis |
| A.5.19 Säkerhet i leverantörsrelationer | ja | All drift ligger hos leverantörer | delvis |
| A.5.20 Säkerhet i leverantörsavtal | ja | Art. 28-avtal med underbiträden | delvis |
| A.5.21 IKT-leveranskedjan | ja | Öppen källkod (pip, npm, basimage) och underbiträdenas underbiträden | delvis |
| A.5.22 Uppföljning av leverantörer | ja | Villkor och regioner ändras (Resend, TypeSafe) | delvis |
| A.5.23 Molntjänster | ja | Hela driften är molntjänster | delvis |
| A.5.24 Planering av incidenthantering | ja | Art. 33 och 34; biträdesplikten mot kunden | delvis |
| A.5.25 Bedömning av händelser | ja | Sju obedömda poster i loggen | nej |
| A.5.26 Hantering av incidenter | ja | Som A.5.24 | delvis |
| A.5.27 Lärdomar | ja | Samma fel (läckta hemligheter) har återkommit | delvis |
| A.5.28 Insamling av bevis | ja | Krävs för att kunna anmäla och visa vad som nåtts | nej |
| A.5.29 Säkerhet vid avbrott | ja | Ett avbrott hos Railway eller GitHub stoppar allt | nej |
| A.5.30 IKT-beredskap för kontinuitet | ja | Art. 32.1 c, förmåga att återställa | nej |
| A.5.31 Rättsliga och avtalsenliga krav | ja | GDPR, marknadsföringslagen, e-handelslagen, AI-förordningen, kundavtal | delvis |
| A.5.32 Immateriella rättigheter | ja | Öppen källkod med licenser; vendorade skills; registerdata | delvis |
| A.5.33 Skydd av register | ja | Incidentlogg, beslut, avtal och kvittenser ska bevaras | delvis |
| A.5.34 Integritet och skydd av personuppgifter | ja | Kärnverksamheten | delvis |
| A.5.35 Oberoende granskning | ja | Kräver en extern person; kan göras i liten skala (P10) | nej |
| A.5.36 Efterlevnad av policyer | ja | Följer av A.5.1 | nej |
| A.5.37 Dokumenterade driftrutiner | ja | Driften sköts med skript och rutiner i `DEPLOY.md` | delvis |

## A.6 Personalrelaterade kontroller

| Kontroll | Tillämplig | Motivering | Införd |
|---|---|---|---|
| A.6.1 Bakgrundskontroll | ja | Gäller nästa person som får åtkomst. Föreslaget undantag för Anton och Sebbe, som känner varandra sedan tidigare (P15) | nej |
| A.6.2 Anställningsvillkor | ja | Sebbe har full åtkomst; avtalsformen är okänd | okänt |
| A.6.3 Medvetenhet och utbildning | ja | Art. 32.4 och 39; båda hanterar kunddata | nej |
| A.6.4 Disciplinär process | ja | I form av avtalsvillkor, inte en personalprocess | okänt |
| A.6.5 Ansvar efter avslut | ja | Den som slutar känner nycklar och kunddata | okänt |
| A.6.6 Sekretessavtal | ja | Art. 28.3 b kräver att den som behandlar har tystnadsplikt | okänt |
| A.6.7 Distansarbete | ja | Allt arbete sker på distans | delvis |
| A.6.8 Rapportering av händelser | ja | Båda ska kunna rapportera direkt | delvis |

## A.7 Fysiska kontroller

| Kontroll | Tillämplig | Motivering | Införd |
|---|---|---|---|
| A.7.1 Fysiska skalskydd | nej | Inga egna lokaler eller serverrum. Driften ligger i leverantörernas datacenter, vars skalskydd följs upp under A.5.19–A.5.23 (Railway SOC 2 Type II, Redis SOC 2 och ISO 27001, Google ISO 27001; `../../leverantorsgranskning.md` §1, 3, 4) | – |
| A.7.2 Fysiskt tillträde | nej | Som A.7.1 | – |
| A.7.3 Kontor, rum och anläggningar | nej | Inget kontor. Hemarbetet täcks av A.6.7, A.7.7 och A.7.9 | – |
| A.7.4 Fysisk övervakning | nej | Som A.7.1 | – |
| A.7.5 Fysiska hot och miljöhot | nej | Inga egna anläggningar. Stöld och brand hemma täcks av A.7.9 och säkerhetskopiorna (A.8.13) | – |
| A.7.6 Arbete i säkra områden | nej | Inga säkra områden finns | – |
| A.7.7 Tom skrivbordsyta och låst skärm | ja | Bärbara datorer används hemma och på andra platser | okänt |
| A.7.8 Placering av utrustning | ja | Datorerna och var de förvaras | okänt |
| A.7.9 Tillgångar utanför lokalerna | ja | Alla datorer är utanför lokaler; stöld ger åtkomst till nycklar | okänt |
| A.7.10 Lagringsmedia | ja | Datorernas diskar, eventuella USB-minnen och databasdumpar | okänt |
| A.7.11 Försörjning | nej | Ström och kyla för driften sköts av leverantörerna; datorerna har batteri | – |
| A.7.12 Kablage | nej | Ingen egen kabeldragning | – |
| A.7.13 Underhåll av utrustning | ja | Datorer som lämnas på service | okänt |
| A.7.14 Kassering och återanvändning | ja | Datorer och telefoner som byts eller säljs | nej |

## A.8 Tekniska kontroller

| Kontroll | Tillämplig | Motivering | Införd |
|---|---|---|---|
| A.8.1 Användarenheter | ja | Datorerna når driften och har nycklarna | okänt |
| A.8.2 Privilegierad åtkomst | ja | Plattformsadmin och leverantörskonton når alla kunders data | delvis |
| A.8.3 Begränsning av åtkomst | ja | Isolering mellan kunder (RLS) | delvis |
| A.8.4 Åtkomst till källkod | ja | Skrivåtkomst ger direkt deploy | delvis |
| A.8.5 Säker autentisering | ja | Kunder och admin loggar in i appen; konton hos leverantörer | delvis |
| A.8.6 Kapacitetshantering | ja | Kvoter hos modelleverantörer och en replik per tjänst | delvis |
| A.8.7 Skydd mot skadlig kod | ja | På datorerna; driften är containrar hos Railway | okänt |
| A.8.8 Tekniska sårbarheter | ja | Python- och Node-beroenden | delvis (var nej, ändr. 11-18) |
| A.8.9 Konfigurationshantering | ja | Driftvariabler styr dataflöden (t.ex. `INKORG_JEV`) | delvis |
| A.8.10 Radering av information | ja | Art. 5.1 e och 17 | delvis |
| A.8.11 Maskering | ja | Personnummer och hälsouppgifter i kundmejl | delvis |
| A.8.12 Skydd mot dataläckage | ja | Publikt repo och flera miljöer | delvis |
| A.8.13 Säkerhetskopiering | ja | Art. 32.1 c | nej |
| A.8.14 Redundans | ja | Kunderna förväntar sig att supportagenten svarar | nej |
| A.8.15 Loggning | ja | Krävs för incidentutredning och art. 33 | delvis |
| A.8.16 Övervakning | ja | Fel och intrång måste upptäckas | delvis (var nej, ändr. 11-18) |
| A.8.17 Tidssynkronisering | ja | Loggar ska gå att jämföra; fristen räknas i timmar | okänt |
| A.8.18 Privilegierade verktyg | ja | Railway CLI, psql och skript med full åtkomst | delvis |
| A.8.19 Programvara i drift | ja | Bygget ur repot; datorerna som deployar | delvis |
| A.8.20 Nätverkssäkerhet | ja | Databas och Redis nås över nät | delvis |
| A.8.21 Nätverkstjänster | ja | HTTPS, Redis, leverantörernas API:er | delvis |
| A.8.22 Nätverkssegmentering | ja | Två miljöer som ska hållas isär | delvis |
| A.8.23 Webbfiltrering | ja | I begränsad form: appens utgående trafik och webbläsarskydd på datorerna. Ingen proxy krävs | delvis |
| A.8.24 Kryptografi | ja | Art. 32.1 a | delvis |
| A.8.25 Säker utvecklingslivscykel | ja | Snajp utvecklar själv hela produkten | delvis |
| A.8.26 Säkerhetskrav på applikationer | ja | Publika agentytor och kundinloggning | delvis |
| A.8.27 Säker arkitektur | ja | AI-agenter med åtkomst till kunddata | delvis |
| A.8.28 Säker kodning | ja | Som A.8.25 | delvis |
| A.8.29 Säkerhetstestning | ja | Som A.8.25 | delvis |
| A.8.30 Utlagd utveckling | ja | AI-kodverktyg skriver kod; Sebbes avtalsform okänd | delvis |
| A.8.31 Separerade miljöer | ja | Testmiljön speglar produktionen | delvis |
| A.8.32 Ändringshantering | ja | Flera deployer om dagen | delvis |
| A.8.33 Testinformation | ja | Testdata är produktionens persondata | delvis |
| A.8.34 Skydd vid revision och test | ja | Granskningar mot driften görs av agenter | delvis |

## Beslut

Anton beslutar: [FYLL: datum], [FYLL: ändringar mot utkastet]. Nästa översyn: senast tolv månader efter beslutet, eller när Snajp skaffar lokaler, egna servrar eller fler medarbetare.
