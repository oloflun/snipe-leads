# Språkmodellens kostnad: underlag, spärrar och uppföljning

Skapad 2026-11-20 på Antons beställning: "spara det här kostnadsunderlaget att
följa upp, se även hur du kan begränsa och hålla koll på kostnaden så den inte
sticker iväg av misstag." Mätningarna bakom finns i
[`compliance/modellbyte-underlag.md`](compliance/modellbyte-underlag.md)
§ 3.7, § 4 och § 6.6. Besluten finns i [`BESLUT.md`](BESLUT.md) 2026-11-20.

## 1. Vad som körs (development 2026-11-20, main sedan 2026-11-22)

| Steg | Modell | Pris i `eu`, USD per M tokens (in / ut) |
|---|---|---|
| Support, triage, Iris-utkast, humanizer, profil (`MODEL`) | gemini-3.5-flash-lite | 0,33 / 2,75 |
| Webbplatsbedömningen (`VISION_MODEL`) | gemini-3.8-flash | 0,825 / 4,125 till 2026-12-31, därefter 1,65 / 8,25 |
| Kvitton (`KVITTO_MODEL`) | gemini-3.8-flash, men pausade och utan verkan | |

Tänkandet räknas som utdata. `eu`-priset är AI Studios globala pris plus 10 %.
Dollarn räknas som 10,5 kr.

## 2. Kostnad per enhet

| Enhet | Kostnad | Källa |
|---|---|---|
| En webbplatsbedömning med 3.8 | 0,047 kr (0,094 kr från 2027) | 2,59 kr för 55 bildbedömda sajter, 2026-11-18 |
| Samma med Lite | 0,011 kr | 0,59 kr för samma sajter |
| **Merkostnad för 3.8 per 100 leads** | **3,60 kr (8,40 kr från 2027)** | Antons godkännande 2026-11-20: "fullt acceptabelt" |
| Skärmbild per sajt (ScrapeGraph) | 2 krediter, 7 med stealth | Samma oavsett modell |
| Hela evalsviten med Lite (50 support, 7 golden, 50 triage, 10 utkast) | 17 kr | 2026-11-20 |
| 1 000 supportchattar med Lite | ~160 kr | Underlaget § 4 |
| 1 000 triagerade mejl med Lite | ~49 kr | Underlaget § 4 |
| Leads per månad med Lite överallt, vid oktobers volym | ~1 340 kr | Underlaget § 4 (354 M tokens i månaden) |

Utkasten är huvuddelen av leadsens kostnad: ett utkast läste omkring 150 000
tokens med 2.5-flash. **Siffran per lead för Lite är inte uppmätt i drift.**
Den ska tas fram ur de första skarpa körningarna (avsnitt 5).

## 3. Spärrarna som finns i dag

| Spärr | Var | Värde nu | Vad den skyddar | Svaghet |
|---|---|---|---|---|
| Leadsbudget per kund och dygn | `app/leads/budget.py`, `LEADS_DAILY_TOKEN_BUDGET` | 40 M i development (sedan 2026-11-21) och main (sedan 2026-11-22) | Nya körningar avvisas när taket nås. Förvarning vid 80 % till `platform_events`. 40 M är omkring 180 kr per kund och dygn med Lite. Ett jobb som redan står i kön stoppas inte. |
| Supportbudget per kund och dygn | `app/budget.py`, `SUPPORT_BUDGET_<SLUG>` och `SUPPORT_DAILY_TOKEN_BUDGET` | Livrustning: 1 M tokens. Globalt: 2 M i development (2026-11-21) och main (2026-11-22) | Chatten svarar 429 när taket nås. Förvarning vid 80 %. | – |
| Webbpoolens dygnstak | `app/leads/webbpool.py`, `WEBBPOOL_DAGSTAK` | 300 domäner (kodens standard) | Högst omkring 14 kr bildmodell per dygn, plus 600–2 100 ScrapeGraph-krediter | Räknas per process. En omstart nollställer räknaren. |
| ScrapeGraph-tak per körning | `app/leads/sidhamtning.py` | Per körning | Stoppar betalda hämtningar i en körning | Krediten är förbetald, så den sätter ett naturligt tak. |
| Google Cloud, kreditkontot | `0159BE-C0FCCA-881885`, projekt `rock-sentinel-515323-r8` | Budget 3 000 kr/mån (brutto, larm 50/80/100 % utfall och 100 % prognos). Tak 8 000 kr/mån på Vertex. Båda sedan 2026-11-21 | Larm vid varje oväntad ökning. Taket pausar Vertex i projektet | Taket slår inom minuter, inte direkt. Kontot är ett betalkonto, så kortet dras när krediten är slut |
| Google Cloud, Snajp-kontot | `01D8D9-D35BE6-BE0D5D`, projekt `snajp-506221` | **Ingen budget, inget larm, inget tak** | – | Bär inget sedan 2026-11-22 (main flyttad). Läggs ned eller får en budget |

Sedan 2026-11-22 fakturerar både development och main kreditprojektet
(samma servicekonto; ett eget för main återstår, se avsnitt 4, punkt 5).

## 4. Spärrarna Anton godkände 2026-11-21

Anton: "Det låter bra, men vi ska använda oss av det nya kreditprojektet även
för main". Läget per punkt står sist i varje punkt.

1. **Budget med larm i Google Cloud** (bara larm, stoppar inget). Förslag:
   3 000 kr i månaden för projektet, med mejl vid 50, 80 och 100 % av faktiskt
   utfall och vid 100 % av prognosen. Fångar varje oväntad ökning, vad den än
   beror på. **Gjort** på kreditkontot (3 000 kr, brutto före kredit).
2. **Utgiftstak på Vertex** ("Spend cap enforcement", GA november 2026, gäller
   `aiplatform.googleapis.com`). Taket pausar Vertex i hela projektet tills det
   lyfts, alltså även kundernas chatt. Det ska därför ligga långt över det
   normala, som sista skydd mot en skenande loop. Förslag: 8 000 kr i månaden. **Gjort** på
   kreditprojektet.
   Taket kräver exakt trösklarna 50/80/100 %. Det räknas på uppskattad
   bruttokostnad och slår inom minuter, men inte direkt, och det som hinner
   användas faktureras ändå.
3. **Sänk leadsbudgeten** från 150 M till omkring 40 M tokens per kund och dygn.
   Det rymmer en körning på 200 leads (~30 M) med marginal och motsvarar
   omkring 180 kr per kund och dygn med Lite, mot 670 kr i dag. **Gjort i
   development.** Main fick det 2026-11-22.
4. **Sätt ett globalt supporttak**, till exempel `SUPPORT_DAILY_TOKEN_BUDGET`
   = 2 M tokens per kund och dygn (omkring 12 kr med Lite), så att nya kunder inte
   startar utan tak. Livrustnings eget värde gäller före det globala. **Gjort i development och main.**
5. **Development och main till kreditprojektet.** Driften blir gratis så länge
   krediten räcker (omkring 2 600 kr kvar efter 2026-11-20). **Development gjort**
   2026-11-21. **Main flyttad 2026-11-22** med Lite och 3.8 (mains kod stöder `eu`). Ge main ett eget servicekonto i
   projektet vid bytet (JURIDIK_ATGARDER #14). Skillen `vertex-gratiskrediter`
   beskriver uppsättningen.

## 5. Uppföljning

| När | Vad | Hur |
|---|---|---|
| Efter de första 2–3 skarpa körningarna med Lite | Faktisk kostnad per lead och per körning, mot uppskattningen i avsnitt 2 | Tokens ur `agent_runs` (`LEADS_BUDGET_AGENT_TYPES`) × priset ovan, och Vertex-raden i Cloud Billing → Reports filtrerad på tjänsten |
| Varje månadsskifte | Vertex-kostnad per modell (SKU) mot prognosen i avsnitt 2 | Cloud Billing → Reports, gruppera på SKU. Kreditprojektet: Credits-sidans "Remaining value", inte Reports (som visar nettot efter kredit) |
| Före 2026-12-31 | 3.8:s pris dubblas. Bildbedömningen går från 0,047 till 0,094 kr per sajt. | Ingen åtgärd krävs, eftersom Anton har godkänt det. Stäm av prognosen. |
| Före 2027-01-28 | Inget att göra för oss: 3.6 och 3.7 stängs, men vi kör ingen av dem | – |
| När main får ett eget servicekonto | Skapa kontot i kreditprojektet och byt mains `GOOGLE_SERVICE_ACCOUNT_JSON` (main delar i dag developments) | Kontrollera Vertex-anrop i mains logg efter deployen |
| När krediten närmar sig noll | Kortet börjar dras. Budgeten mejlar på bruttokostnaden, inte på krediten | Credits-sidans "Remaining value" vid månadsskiftet |
| När en kund läggs till | Att kunden har ett supporttak | `SUPPORT_BUDGET_<SLUG>` eller det globala taket (punkt 4) |

Båda budgetarna skriver sina förvarningar (80 %) och stopp (100 %) till
`platform_events`.
