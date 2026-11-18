# Incidentrutin — personuppgifter

Den här filen finns för att 72-timmarsfristen i GDPR art. 33 börjar löpa när
någon i verksamheten **blir medveten** om händelsen, inte när utredningen är
klar. En rutin som skrivs medan klockan tickar är inte en rutin.

Håll den kort. En checklista som ingen orkar läsa vid 23:30 en fredag är
samma sak som ingen checklista.

---

## 1. Vem bedömer

**Anton** är den som avgör om en händelse är en personuppgiftsincident. Ingen
annan gör den bedömningen ensam, och ingen skjuter upp den för att "det
antagligen inte var något".

Är Anton inte nåbar inom två timmar: den som upptäckte händelsen dokumenterar
enligt punkt 2 och behandlar den som anmälningspliktig tills någon sagt annat.
Att överskatta är obehagligt. Att underskatta är sanktionsgrundande.

## 2. Vad som skrivs ned, direkt

Innan något åtgärdas — skriv ned i ett nytt dokument under `handoffs/`:

- **När** händelsen upptäcktes (klockslag, inte bara datum). Det här är den
  tidpunkt fristen räknas från.
- **Vad** som hände, i en mening, utan bedömning.
- **Vilka uppgifter** som kan ha berörts, och **vems** (våra egna, en kunds,
  en kunds kunders).
- **Hur många** personer det kan gälla — en storleksordning räcker.
- **Vad som redan gjorts** (nyckel roterad, tjänst stoppad, åtkomst dragen).

## 3. Stoppa blödningen

Innan utredningen. En läckt nyckel roteras **först** och analyseras sedan —
en nyckel som fortfarande är giltig medan man funderar är en nyckel som
fortfarande används.

Ordning: rotera eller dra åtkomsten → verifiera att den gamla vägen är död →
sedan börja utreda vad den nådde.

## 4. Är den anmälningspliktig?

Anmäl till **IMY inom 72 timmar** om det inte är osannolikt att incidenten
medför en risk för de registrerades rättigheter och friheter. Notera dubbla
negationen: *osannolikt* är beviskravet, och det ligger på oss.

Anmäl alltid när något av detta gäller:

- Uppgifter har varit åtkomliga för någon utanför vår krets.
- Vi kan **inte visa** att de inte varit det. Avsaknad av loggar är inte ett
  frikort — det är en försvårande omständighet.
- Det rör en kunds kundtjänstinkorg, alltså tredje parts personuppgifter.

Anmälan görs på [imy.se](https://imy.se). Är utredningen inte klar inom 72
timmar: anmäl ändå, med det man vet, och komplettera efteråt. Det är
uttryckligen tillåtet och är alltid bättre än en sen fullständig anmälan.

## 5. Vem kontaktar kunderna

**Anton**, samma dag som bedömningen görs.

När vi är **personuppgiftsbiträde** — allt som rör en kunds inkorg — är det
kunden som anmäler till IMY, inte vi. Vår skyldighet är att underrätta kunden
**utan onödigt dröjsmål**, så att de hinner med sin egen frist. Vi ska alltså
höra av oss snabbare än 72 timmar, inte inom 72 timmar.

Underrättelsen ska innehålla det som står under punkt 2. En underrättelse som
säger "vi har haft en incident, återkommer" hjälper inte kunden att göra sin
egen bedömning och gör dem försenade i stället för informerade.

## 6. Efteråt

Skriv en rad i `STATUS.md` om vad som ändrades i systemet, och lägg
händelsen i incidentloggen nedan. En incident som inte gav en ändring i koden
eller i rutinen kommer tillbaka.

---

## Incidentlogg

| Datum | Händelse | Bedömning | Anmäld | Åtgärd |
|---|---|---|---|---|
| 2026-08-24 | Render-API-nyckel exponerad | **Öppen.** Bedömningen är delvis gjord: nyckeln gav åtkomst till två levande Render-tjänsters miljövariabler, som bär `DATABASE_URL` och LLM-nycklar. Alltså inte direkt åtkomst till persondata, men till de uppgifter som når dem | Nej, ej bedömd | Rotera. Se `docs/JURIDIK_ATGARDER.md`, P0.2. Fortfarande öppen 2026-11-17 |
| 2026-08-24 | **Bortglömd Render-stack körde DeepSeek mot riktig databas** | **Öppen.** Två tjänster (`snajp-support`, `snajp-support-dev`) var aldrig avstängda, deployade automatiskt vid varje push till `main`/`development`, och startade med `provider=deepseek` och `storage: postgres`. Ingen trafik syns i loggarna de senaste tre dygnen, men tjänsterna levde | Nej, ej bedömd | Se P0.2b. Fortfarande öppen 2026-11-17 |
| 2026-08-29 | **Redis-trafik utan TLS.** Jobbposterna, som bär agentens svar till kundernas kunder, går okrypterat mellan Railway och Redis Cloud (`europe-west1`). 2026-11-17 pekar `REDIS_URL` fortfarande på `redis://`, och main och development delar samma Redis-databas. Källa: `HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md:112-115`; `docs/JURIDIK_ATGARDER.md:359-361`; Railways driftkonfiguration 2026-11-17 (internt underlag, inte i repot). Ingen post i `docs/BESLUT.md` | ej bedömd, Anton | Nej, ej bedömd | Kör `scripts/redis_tls_pa.py --apply` (Antons hand; agentens försök stoppades 2026-08-29). **Öppen**, fortfarande öppen 2026-11-17. Se DPIA R8. Tillägg 2026-11-17: TLS går inte att slå på i den nuvarande planen; Redis Cloud-databasen ligger på gratisplanen, som saknar TLS-stöd. Inget är ändrat. Skriptet byter bara adressen i development fast main delar databasen, och får inte köras som det är. Valet mellan betald plan och Railways egen Redis på det privata nätverket är Antons. Tillägg 2026-11-17, kväll: Anton valde flytten (`docs/BESLUT.md`, 2026-11-17). Jobbkön ligger nu på Railways egen Redis, en databas per miljö, och api-tjänsten når den över Railways privata nätverk; trafiken går inte längre över publikt nät. Verifierat i uppstartsloggen i båda miljöerna, och hälsokontrollen svarar ok. `scripts/redis_tls_pa.py` är inaktuellt och får inte köras. Kvar: radera den gamla Redis Cloud-databasen, som har kvar cache och arbetsminne, och ta bort reservvariabeln med den gamla adressen (Antons beslut). Bedömningen av tiden 2026-08-29 till 2026-11-17, då trafiken gick okrypterat, är fortfarande **öppen** och Antons |
| 2026-10-24 | **~600 kallmejl i skräpposten.** Volymdubblingen från 2026-10-21 (20 → 40 → 80 → 160 per dag; 223 skickade 2026-10-21) släppte ut ~600 kallmejl på några dagar från `snajp.se`. 9 svar, varav 2 mänskliga, tydde på att de flesta fastnade i mottagarnas skräpfilter. Inget i systemet räknade studs eller klagomål. Källa: `docs/BESLUT.md` rad 1399-1406 och 1531-1535; `docs/UTSKICK-SVARSFREKVENS-DIAGNOS-2026-10-24.md`; `snajp-support/app/leads/send_guard.py:51-57` | ej bedömd, Anton | Nej, ej bedömd | Flack upptrappning, leveransstopp vid studs och klagomål, ren text i första mejlet (BESLUT 2026-10-24, rad 1408-1424). Om Resends webhookhemlighet är registrerad i båda miljöerna är inte belagt (BESLUT rad 1426-1428); `RESEND_WEBHOOK_SECRET` är satt på api i main och development 2026-11-17. Kodåtgärden är gjord; bedömningen är **öppen** |
| 2026-11-09 | **Plattformsadminlösenordet låg i skript och handoffs.** Lösenordet togs ur filerna samma dag men ligger kvar i git-historiken och är inte bytt. Källa: `docs/BESLUT.md` rad 488-489; `docs/stabilitet-2026-11/SLUTRAPPORT.md:173` | ej bedömd, Anton | Nej, ej bedömd | Byt lösenordet (Antons hand). Rensning av historiken är ett eget beslut. **Öppen**, inget belägg för byte 2026-11-17 |
| 2026-11-10 | **Agentpromptar lämnades ut i jobbsvaret.** `GET /api/jobs/{id}`, som den anonyma chattwidgeten pollar, bar hela stegloggen: verksamhetskontext, kundminne, kunskapsbasens artiklar och modellens resonemang. Samma texter gick ut via `/api/leads/runs` och två direkta agentsvar, och researchpromptarna kan bära webbplatsbedömningen. Sedan när felet funnits och vilka uppgifter som nåtts är inte utrett. Källa: `docs/BESLUT.md` rad 344-347 och 351-354; `docs/stabilitet-2026-11/SLUTRAPPORT.md:138-143` | ej bedömd, Anton | Nej, ej bedömd | Rättat i `snajp-support/app/api/stegtexter.py` (commit `62ea7d56`), i `main` via PR #43 (merge `c1ee244e`, 2026-11-10). Exponeringstid och berörda kunder **ej utredda** |
| 2026-11-17 | **Kundmejltext till TypeSafe utan avtal.** `INKORG_JEV=auto` i main och development skickar ämnesrad och upp till 1 500 tecken av varje nytt kundmejl som kodreglerna inte sorterar, med e-postadresser och telefonnummer borttagna, till `api.typesafe.ai`. TypeSafe står inte i någon underbiträdesförteckning, har inget avtal och okänd region. `leads/jev.py:24-28` anger Antons beslut 2026-09-30 att Jev aldrig ser kundmejl; `email_pipeline/klassning.py:23-30` (2026-10-04) inför ändå brytaren. Sedan när `auto` är satt är inte känt. Källa: `snajp-support/app/email_pipeline/klassning.py:157-167`; `processor.py:369`; `railway-konfiguration-2026-11-17.txt` rad 95 och 235; nulägesinventeringen 2026-11-17 (internt underlag, inte i repot). Ingen post i `docs/BESLUT.md` | ej bedömd, Anton | Nej, ej bedömd | Anton avgör om beslutet 2026-09-30 gäller; i så fall `INKORG_JEV=off` i båda miljöerna. Annars DPA och förteckningar. **Öppen**. Se DPIA R7. Tillägg 2026-11-17: flödet stoppades samma dag genom Antons beslut (`docs/BESLUT.md`, 2026-11-17). `INKORG_JEV` är av i main och development, nya deployer kom upp och hälsokontrollerna svarar ok; inkorgen sorteras bara av kodreglerna. Kvar: bedömning av anmälningsplikt och underrättelse till berörda kunder (Antons). Radering hos TypeSafe av det som redan skickats är inte begärd. Bedömningen är **öppen** |

**Den öppna posten är det första skarpa testet av den här rutinen.** Kör den
genom punkterna 2–6 ovan, i ordning. Går rutinen inte att följa på ett
verkligt fall är det rutinen som ska ändras, inte fallet som ska hoppas över.
