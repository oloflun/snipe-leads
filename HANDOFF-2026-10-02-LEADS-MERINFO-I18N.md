# Handoff 2026-10-02 — Körningar, merinfo-kedjan, adminfelet, listorna och översättningen

Skriven vid /conclude på Antons uttryckliga order: "gör inget i denna session,
kör bara /conclude". Ingenting av det Anton bad om i sitt sista meddelande är
påbörjat. Allt nedan är nästa sessions arbete, i Antons ordning.

Antons fyra meddelanden från sessionen står ORDAGRANT längst ned (§ 9). Läs dem
innan du börjar. De är beställningen, och den här texten är bara en karta.

---

## 1. Läget i git och i miljöerna (2026-10-02, verifierat)

| Vad | Läge |
|---|---|
| Gren | `development`, lokalt **5 commits före** `origin/development`, **inte pushat** |
| Lokala commits | `5f05678` körningar (A), `13e9ea9` menyn i railen (G), `469e729` a11y-fix Körningar, `c2e9378` conclude 10-01 (en annan session), `0db86ac` merinfo-kedjan |
| Rebase | Gjord 2026-10-02 ovanpå Sebbes `1944be2`, `fb85da9`, `c6758ea` (PR #29). Ren, inga konflikter. |
| Tester efter rebase | **INTE körda.** Anton avbröt sviten. Kör `pytest snajp-support/tests` och `npx tsc --noEmit` före push. |
| `origin/main` | `2b4dbbd` = PR #29. Main och development har samma kod (0 commits isär på origin). |

**Migrationer, torrkörda 2026-10-02:**

| Migration | development | main |
|---|---|---|
| 079_iris_bedomning | körd | **saknas** |
| 080_paket_admin (Sebbe) | körd | **saknas** |
| 080_korningar (den här sessionen) | väntar | väntar |
| 081_kontakt_telefon (den här sessionen) | väntar | väntar |

Ej committat i arbetsträdet och INTE från den här sessionen (rör dem inte utan
att fråga): `docs/utkast-merinfo-api-forfragan.md`, `docs/utkast-allabolag-api-forfragan.md`,
`snipe-leads.md`, `strategies.md`, `session-logs/2026-09-30-session-log.md`.

---

## 2. Gör först: adminytan är trasig (Antons prioritet 1)

**Symptom (Antons skärmdumpar 2026-10-02):** `www.snajp.se/admin`, `/admin/kunder`
och `/admin/paket` visar alla "Något gick fel på vår sida. Felet är loggat."
Anton antar att samma fel finns på development.

**Trolig rotorsak, inte verifierad i loggarna:** Sebbes `c6758ea` (PR #29,
mergad till main) ändrade `list_tenants_with_stats` att läsa `ss_tenants.status`
från migration 080_paket_admin. Commit-meddelandet säger själv: "Mot main:
torrkör och kör den INNAN mergen". Torrkörningen 2026-10-02 visar att 080_paket_admin
**inte är körd mot main**. Det gör inte heller 079_iris_bedomning, trots att
Iris-koden som läser `prospects.motivering/niva/jev` ligger i main sedan PR #28.

**Gör så här:**
1. Läs api-loggen i main för felet bakom /admin (Railway, tjänst `api`, miljö `main`).
   Bekräfta att det är en saknad kolumn och inte något annat.
2. Kolla development likadant (`web-development-6c85.up.railway.app/admin`).
   Där är 080_paket körd, så felet där, om det finns, har en annan orsak.
   Sök då i `components/admin/PaketHantering.tsx`, `app/admin/paket/page.tsx`
   och `snajp-support/app/api/admin.py`.
3. Main är produktion: att köra migrationer mot main kräver Antons uttryckliga
   ord (CLAUDE.md §8.1a). Han har bett om att felet löses. Visa torrkörningen,
   säg att 079 + 080_paket_admin är vad som saknas, och fråga om du får köra
   `python scripts/railway_migrate.py --env main --apply`. 080_korningar och
   081 kan följa med i samma körning först när den koden har nått main.
4. Verifiera med skärmbild att /admin, /admin/kunder, /admin/paket renderar.

---

## 3. Sedan: Antons avbrutna order (prioritet 2)

Anton skrev: "Kör migrationerna åt mig, pusha och aktivera scrapegraph- kedjan
samt Jev i development." Den avbröts efter rebasen. Ordning:

```bash
python -m pytest snajp-support/tests -q
npx tsc --noEmit
python scripts/railway_migrate.py --env development --apply
git push origin development
railway variables --set LEADS_MERINFO=scrapegraph --service api --environment development
python scripts/keys.py --push-jev development
```

- `--push-jev` läser `TYPESAFE_API_KEY` ur `snajp-support/.env`, provar den
  skarpt mot TypeSafe och avbryter om den saknas. Saknas den: be Anton köra
  `python scripts/keys.py --key TYPESAFE_API_KEY`. Agenten hanterar aldrig värdet.
- `--push-jev` sätter `IRIS_JEV=skugga` som standard (mäter men fäller inget).
  Anton sa "aktivera Jev". Fråga om han menar skugga eller `pa` (`--jev-lage pa`).
  Valvets och handoffens linje är skugga först, `pa` när falska bortval ≤5 %.
- `SCRAPEGRAPHAI_API_KEY` måste finnas på `api` i development. Kontrollera innan
  merinfo slås på (namnet, inte värdet).
- Verifiera: starta en lista och en Iris-körning på development, följ dem i
  Iris › Körningar, kontrollera att raderna har namn, roll och telefon.

---

## 4. Listorna: Antons nya krav (prioritet 3, inte påbörjat)

Ordagrant i § 9. Kort, med vad det betyder i koden:

1. **Spara även prospekt med bara mejl, inte bara de med telefon.**
   I dag sållar `app/leads/sources/merinfo.py::sok` bort listrader utan telefon
   redan på listsidan (`if r["telefon"]`), och `kontrollera()` kräver telefon.
   Ändra till: telefon ELLER mejl räcker för att bli en rad, men namn + roll
   krävs fortfarande. Mejl finns sällan på merinfo ("Lägg till e-post"), så
   rader utan telefon behöver bolagssidan hämtad och sedan
   `discovery.hamta_kontaktvag(website)` för att hitta en adress på bolagets
   sajt. Det kostar fler ScrapeGraph-anrop; mät.
2. **Underflik per lista, inte en separat blandad mejllista.** I samma lista:
   flikar eller filter "Telefon", "Mejl", "Båda", och sortering på telefon/mejl.
   `LeadslistorView.tsx`. Kontaktvägen per rad finns redan (`contact_phone`,
   `contact_email`).
3. **Kombinera flera listor till en skräddarsydd.** Välj flera listor och bygg
   en ny: flera branscher i samma region, samma bransch i flera regioner, och
   filtrera på bara mejl, bara telefon eller båda. Dedup på `orgnr` (därför
   finns `lead_list_items.orgnr` sedan 081). Ny lista med `kalla='kombinerad'`
   och referenser till källistorna, eller en ny rad i `lead_lists` med raderna
   kopierade. Välj det enklaste som går att granska i efterhand.
4. **Flytta listrader till Iris för utkast, eller "skriv utkast för samtliga"
   i Iris.** Bron finns delvis: "Lägg alla i registret" och "Skriv utkast till
   alla med mejladress" (`LeadslistorView.tsx`, `skrivUtkastForRad`). Kravet:
   varje utkast ska fortfarande vara anpassat till varje bolag. Det betyder att
   varje rad ska gå genom Iris research (lägesbeskrivning, signaler, kontakt)
   innan utkastet skrivs, inte en mall. Se minnesregeln "Aldrig mall som utkast"
   (2026-09-19). Rimlig väg: "Flytta till Iris" skapar prospekt och köar en
   körning med egna bolagsnamn (`company_names`), så Körningar visar förloppet.

---

## 5. Engelska versionen och tvåspråkighetsregeln (prioritet 4, inte påbörjat)

**Antons ord:** den engelska versionen är inte översatt på ett stort antal
ställen. Gå igenom VARJE sida och åtgärda det.

**Vad skärmdumparna 2026-10-02 visar.** Antons webbläsare markerar oöversatt text
med orange bakgrund, och det är den markeringen som syns här:
- `/kvitton` på engelska: nästan allt är svenska ("Kvitton ur mejlen", "Inkorgen",
  "Sammanfattning", "Fråga kvitto-assistenten", "Utplockade kvitton",
  kolumnrubrikerna, demotexterna).
- `/support` och `/leads` på engelska: sektionsrubrikerna är engelska men
  demoytorna, chatten, inkorgsraderna, utkasten och "Nya leads i natt" är svenska.
- `/demo` på engelska: "Workspace", "Shared overview" är engelska, men
  nyckeltalen ("ARBETSYTA", "AGENTEN", "KUNSKAPSBAS", "SENASTE KÖRNING",
  "2 utkast väntar på dig") är svenska och dessutom versala och spärrade, alltså
  ett brott mot INV-UI-001 (inga kicker-etiketter) på en appyta.
- `/demo/iris/installningar` och `/demo/iris/granskning` visar en ny post
  **"CRM-lista"** i Iris-menyn som inte kommer från den här sessionen. Spåra den
  (troligen Sebbe) innan du rör Iris-menyn.

**Mekanismen:** `lib/i18n.tsx` (`useLocale`, `t()`, nycklar `{ sv, en }`).
Många komponenter skriver svenska strängar direkt i JSX.

**Den här sessionens egna komponenter är enspråkiga och ska rättas först:**
`components/leads/IrisKorningar.tsx` (hela vyn), statusraden och "Följ körningen"
i `components/leads/LeadsRunForm.tsx`, railfoten och mobilraden i
`components/AppShell.tsx` ("Logga ut", "Logga in", "Till startsidan"),
telefonvisningen i `LeadslistorView.tsx` och CSV-rubrikerna ("Org.nr",
"Telefon"), raden "Beslutsfattare" i `IrisBolag.tsx`.

**Regeln Anton beställde, ska in i projektets agentinstruktioner:** VARJE ny
komponent som innehåller text MÅSTE göras tvåspråkig (sv + en via
`lib/i18n.tsx`), utan undantag. Skriv in den i `CLAUDE.md` och `AGENTS.md`
(håll dem i synk, se `sync-agent-configs`), gärna i `DESIGN.md` under Copy.
Gör den mekanisk: ett invariantstest (förslagsvis INV-I18N-001 i
`tests/invariants/`) som fäller svenska bokstäver (å, ä, ö) i JSX-text i
`components/**` och `app/**` utanför `lib/i18n.tsx`, med en tillåtelselista
för demodata. Det är samma mönster som INV-UI-001. En regel som bara står i
text missas; det är precis vad som hände nu.

---

## 6. Vad den här sessionen byggde (2026-10-01 – 10-02)

### Del A — Körningar (commit `5f05678` + `469e729`)
- Migration `20261001100000_080_korningar.sql`: `leads_job_ledger` får `korning jsonb`,
  `error text`, `is_test`, `updated_at`.
- Motorn skriver tillståndet till liggaren efter varje steg (`_spara_korning` i
  `snajp-support/app/api/leads.py`), batchraden står i `processing` tills motorn
  säger klar, varje fel sparar felorsaken i klartext.
- `GET /api/leads/korningar` och `/korningar/{id}`. Ny vy Iris › Körningar
  (`components/leads/IrisKorningar.tsx`). Körformuläret pollar liggaren och
  återupptar en pågående körning efter omladdning.
- INV-JOB-003 i `ARCHITECTURE_INVARIANTS.md`, test `test_inv_job_003.py`, API-test `test_korningar.py`.

### Del G — Menyn i railen (commit `13e9ea9`)
- Kundytans kontroller (Byt kund, Admin/Demo, Meny, e-post, Logga ut, språk)
  ligger i railens fot från `lg`, som adminytan. Toppraden finns bara på mobil.

### Merinfo-kedjan (commit `0db86ac`)
- `snajp-support/app/leads/sources/merinfo.py`, bakom `LEADS_MERINFO=scrapegraph`.
  Antons arbetsflöde: bransch ur sitemapen, län eller kommun, listsidor,
  bolagssidor. Två kommuner ger separata sökningar, tre eller fler i samma län
  ger länet, landsdelar ger sina län, okänd ort ger ingen sökning.
- Träd incheckat: `merinfo_taxonomi.json`, 275 branscher, 21 län, 290 kommuner.
  Generera om: `python -m app.leads.sources.merinfo taxonomi` (i `snajp-support/`).
- Kontaktkrav i kod (namn + roll + telefon; **ändras enligt § 4.1**), rangordning
  i kod plus Jevs `fit` när Jev är på.
- Migration `20261001200000_081_kontakt_telefon.sql`: `contact_phone` på prospekt
  och listrader, `orgnr` på listrader. Telefonen syns i listvyn, CSV:n och Iris.
- 22 tester i `snajp-support/tests/leads/test_merinfo.py`, syntetiska sidor (inga riktiga personuppgifter i repot).
- Skarpt prov lokalt: bygg i Mölndal, 3 leads på 30 s, alla med namn, roll, telefon.
- ScrapeGraph har en egen hastighetsgräns; hämtaren väntar och försöker igen.

### Planen
`plans/2026-10-01-leads-suite-och-korningar.md`: hela beställningen i delar A–G
(körningar, merinfo, Iris med lägesbeskrivning, Jev-sorterad inkorg och
leads-inkorg, nattlig spegling main → dev med admin-väg tillbaka, Leads Suite
efter Twenty, menyn). A, G och den tillfälliga merinfo-delen är bockade.

---

## 7. Öppet från tidigare i sessionen, fortfarande gäller

- **Pixelgranskning ej gjord** av Körningar-vyn och railen (A7, G4). Maskinen
  hade 1,4 GB ledigt commit-minne. Se `HANDOFF-2026-10-01-KORNINGAR.md`.
- **Iris "leverbar" kräver fortfarande mejl.** Merinfo-leads med bara telefon räknas
  inte mot N i Iris-körningar. Ändras i planens del C.
- **merinfos villkor** förbjuder kopiering utan skriftligt samtycke. Källan är av
  som standard; slå inte på den i main. Anton skickar API-förfrågan till merinfo
  och allabolag (utkasten i `docs/`).
- **Nattlig spegling main → development** kan inte köras förrän main och
  development har samma schemaversion (§ 1-tabellen).
- **bd (beads) är nere**, dolt saknas i PATH. Planen är spårningen tills dess.

---

## 8. Fällor

- Pythons `write_text` på Windows skriver CRLF; använd `write_bytes`.
- Bash-heredocs med `'''` inuti föll i den här miljön; skriv redigeringsskript
  som fil i scratchpad och kör dem.
- Catch-all-proxyn `app/api/snajp-support/[...path]/route.ts` täcker nya GET-routes;
  ingen ny Next-fil behövs för backendens läsvägar.
- Testsviten är hermetisk: `LEADS_MERINFO`, `LEADS_KALLOR`, `IRIS_JEV`,
  `TYPESAFE_API_KEY` m.fl. töms i `snajp-support/tests/conftest.py`.

---

## 9. Antons instruktioner, ordagrant

### 9.1 Första meddelandet (2026-10-01)

> Kör /standup . Nuvarande problem: Det finns inget sätt att bevaka eller återvända till en körning när den är startad, vilket är en stor brist, eftersom att jag startade en körning som inte hann slutföras och jobbet verkade sluta eftersom att inga leads genererades, det är fortfarande endast de gamla kvar. Fundera ut och bygg in bra interface för det.  Leadslistorna är katastrof och stämmer inte mot kraven. Gör såhär: använd https://www.merinfo.se/sitemap/bransch , välj sedan branch enligt kundens målgrupp, tex https://www.merinfo.se/sitemap/bransch/alla-lan/alla-kommuner/byggbranschen och välj sedan län utifrån kundens preferenser: https://www.merinfo.se/sitemap/bransch/vastra-gotalands-lan/alla-kommuner/byggbranschen , där går det sedan att vara specifik, https://www.merinfo.se/byggbranschen/molndal/foretag/1  , eller bred: https://www.merinfo.se/byggbranschen/vastra-gotalands-lan/foretag/1 . Om flera sammanhängande städer/län/regioner nämns, täck alla med ett bredare filter, och om två specifika kommuner/städer nämns, kör separata sökningar för dessa. Fundera ut och bygg en filtrering av dessa med Jev som hittar de bästa/mest kvalificerade utifrån de övriga kraven och sammanställer en lista på de bästa matchningarna motsvarande det beställda antalet. Minsta krav för ett kvalificerat lead till listan: en verifierad kontaktperson med roll och telefonnummer. Detsamma grundprocessen gäller Iris-körningarna: Jev ska även, om möjligt, cross-referencea mot de bästa kanditaterna i merinfo och välja ut de prospekt som har nyheter, bolagshändelser, Linkedin-poster som matchar de signaler företaget letar efter.- LLM:en får sedan processa och söka upp mer information kring för att kunna leverera den OBLIGATORISKA lägesbeskrivningen om företaget med poäng och signaler, som idag knappt fungerar överhuvudtaget, det inklusive kontaktperson MÅSTE finnas för ALLA leads som presenteras av Iris, de de ska vara kvalificerade med tydliga signaler som överensstämmer med kundens önskemål, vilket också lägger grunden till mailet som MÅSTE vara anpassat utifrån varje enskilt prospekt och deras läge. Nästa steg som jag även vill att du ritar ut är att rita ut arkitekturen för att låta Jev sortera och kvalificera inkorgen för kundtjänst för vad som är supportrelaterat, dela upp de i olika klassificeringar samt vad som inte är relaterat och vad som bör gå till leads- skapa in inkommande inkorg för leads till kunder som endast har leads-paketet, dit de också kan koppla sin inkorg. Samma miljo och system som kundtjänst-inkorgen, men tillgängligt som flik under i Leads/Iris. En sak till: Just nu är konton och data som är skapat i main inte tillgängligt i development, det behöver åtgärdas eftersom att alla kundkonton kommer att skapas via main, men för att testa fixar till problem som kunder upplevt, behöver vi en isolerad miljö där vi kan göra det mot samma sak de hade problem med via byt konto-funktionen, men då behöver alla konton OCH data speglas till development, som blir en envägsspegel som inte skriver, eftersom att vi inte vill att våra tester dyker upp i den riktiga kundmiljön. Jag vill dock att du lägger till en funktion- ENDAST tillgänglig för Admin, att VIA byt kund-funktionen, kunna välja, markera  och flytta supportmail eller leadskörningar till main om det är så att man vill spara något till den riktiga miljön, men det får vara den ENDA vägen. Jag vill även att du går igenom och tar inspiration från ledande CRM som salesforce och upsales- använd https://github.com/twentyhq/twenty som inspiration för den tekniska implementationen och skapa en Leads Suite, där kunden kan få en verklig CRM- överblick över sina leads, både från listorna och Iris-leads, med intuitiva alternativ för att hålla koll och fylla i svar/status på varje lead från leadslistan, genererade ska sköta sig själva. Gör det även möjligt att integrera med sitt befintliga CRM-system för att få möjlighet att ladda upp befintliga kundbaser för att få tillgång till Snajpa verktyg för detta, det ska till exempel gå att skapa ett utkast för varje enskilt prospekt från någon av listorna, det ska om möjligt även gå att synka mot leads-inkorgen som jag nämnde och skapa möjlighet att följa upp och svara samt alternativ för att automatisera detta med mer filter och val för olika typer av leads i inställningarna. Slutligen, gör även så att menyfliken hoppar ned och läggs i sidobaren som i Admin-workspace istället för att ta plats högst upp på sidan. Gå igenom allt detta noggrannt, se till att få med allt och skapa en noga uttänkt plan för att lyckas med allt detta.

(Bifogat: nio skärmdumpar av `/admin/support`, `/admin/iris`, `www.snajp.se/dashboard/iris`.)

### 9.2 Andra meddelandet (merinfo-arbetsflödet)

> Vi kommer skicka ett mail med en förfrågan om att teckna avtal för API till både merinfo och allabolag för att jämföra. Under tiden: Skapa en workaround där du använder scrapegraph för att hämta alla leads manuellt enligt samma arbetsflöde som jag beskrev: Använd https://www.merinfo.se/sitemap/bransch , välj sedan branch enligt kundens målgrupp, tex https://www.merinfo.se/sitemap/bransch/alla-lan/alla-kommuner/byggbranschen och välj sedan län utifrån kundens preferenser: https://www.merinfo.se/sitemap/bransch/vastra-gotalands-lan/alla-kommuner/byggbranschen , där går det sedan att vara specifik, https://www.merinfo.se/byggbranschen/molndal/foretag/1  , eller bred sökning: https://www.merinfo.se/byggbranschen/vastra-gotalands-lan/foretag/1 .

### 9.3 Tredje meddelandet (avbrutet efter rebasen)

> Kör migrationerna åt mig, pusha och aktivera scrapegraph- kedjan samt Jev i development.

### 9.4 Fjärde meddelandet (2026-10-02, den här handoffens beställning)

> Viktigt tillägg: Sebbe gjorde tidigare en PR som gick igenom mot main och bröt UI:n, vi får anta att det även ligger på development, lös det först. En annan sak om listorna: skippa inte alla prospekt utan telefonnummer, utan spara även dem som enbart har en mailadress, som en separat underflik för den listan, ej en separat, blandad maillista, så man kan sortera listan på telefon eller mail. Men gör det också möjligt att kombinera flera listor genom att välja flera och bygga en skräddarsydd utifrån flera brancher i samma region eller samma branch i olika regioner och utifrån enbart mail eller telefon eller både och. Skapa även en funktion som gör att dessa går att förflytta till Iris för att skapa utkast, eller lägg till en Iris-funktion som gör att det går att skapa utkast för samtliga på en gång- se bara till att dem fortfarande är anpassade efter varje företag. Sedan så är den engelska versionen inte heller översatt på ett stort antal ställen vilket är ren katastrof, gå igenom VARENDA sida och åtgärda det, samt skriv in i agentinstruktionerna för projektet att  VARJE ny komponent som innehåller text ALLTID måste göras tvåspråkig, det får inte missas nu när vi bygger ut appen, kontrollera även de ändringar vi gjort i det här arbetet. Vet du vad, gör inget i denna session, kör bara /conclude , sammanfatta allting i en utförlig och detaljerad handoff med mina exakta instruktioner bifogade i sin helhet härifrån och se till att inget viktigt från den här sessionen missas då det är många rörliga delar.

(Bifogat: femton skärmdumpar. `/admin`, `/admin/kunder` och `/admin/paket` på www.snajp.se med felsidan; `/demo`, `/kvitton`, `/support`, `/leads`, `/demo/iris/installningar` och `/demo/iris/granskning` på engelska med oöversatt text markerad i orange.)
