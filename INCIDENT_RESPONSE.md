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
| 2026-08-24 | Render-API-nyckel exponerad | **Öppen.** Bedömningen är delvis gjord: nyckeln gav åtkomst till två levande Render-tjänsters miljövariabler, som bär `DATABASE_URL` och LLM-nycklar. Alltså inte direkt åtkomst till persondata, men till de uppgifter som når dem | Nej, ej bedömd | Rotera. Se `docs/JURIDIK_ATGARDER.md`, P0.2 |
| 2026-08-24 | **Bortglömd Render-stack körde DeepSeek mot riktig databas** | **Öppen.** Två tjänster (`snajp-support`, `snajp-support-dev`) var aldrig avstängda, deployade automatiskt vid varje push till `main`/`development`, och startade med `provider=deepseek` och `storage: postgres`. Ingen trafik syns i loggarna de senaste tre dygnen, men tjänsterna levde | Nej, ej bedömd | Se P0.2b |

**Den öppna posten är det första skarpa testet av den här rutinen.** Kör den
genom punkterna 2–6 ovan, i ordning. Går rutinen inte att följa på ett
verkligt fall är det rutinen som ska ändras, inte fallet som ska hoppas över.
