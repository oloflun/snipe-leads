# Handoff 2026-10-03/04 — Snajp Suite, design, Jev i inkorgen, merinfo-reglerna och release-PR #30

Till nästa agent. Läs hela före första ändringen. Sessionen gick över två dygn
(2026-10-03 kväll till 2026-10-05 natt) och kontexten komprimerades en gång;
allt nedan är verifierat mot git, Railway och databaserna, inte mot minnet.

Sessionslogg: `session-logs/2026-10-04-session-log.md`.
Planer: `plans/2026-10-03-snajp-suite-struktur.md` (IA:n),
`plans/2026-10-03-appytor-design.md` (designen),
`plans/2026-10-04-leads-merinfo-jev-release.md` (det som återstår, ny).

---

## 1. Läget just nu (verifierat 2026-10-05)

| Vad | Läge |
|---|---|
| `development` lokalt mot origin | I takt. Senaste: `02babb8`. Inget opushat från sessionen. |
| Railway `development` (api) | Kör `02babb8`, status SUCCESS. |
| Railway `main` | Gammal kod (PR #29). Allt nedan finns bara på development tills PR #30 mergas. |
| Migrationer development | 000–091 körda. |
| Migrationer main | 000–089 körda (088 och 089 av agenten med Antons ord). **090 och 091 (Sebbes lösenordsåterställning) saknas** — torrkörning visar dem som väntande. |
| `INKORG_JEV` | `auto` på api/development (driftsatt) och `auto` på api/main (satt med `--skip-deploys`, verkar först efter mergen). |
| `TYPESAFE_API_KEY` (Jev) | development: fanns. main: kopierad från development med `--stdin --skip-deploys` 2026-10-04. |
| `IRIS_JEV` | `pa` på development, saknas på main (Iris-Jev är av i produktion). |
| `LEADS_MERINFO` | `scrapegraph` på development, saknas på main (avtal saknas, ska vara av). |
| ScrapeGraph-krediten | **Slut** ("Insufficient credits", 2026-10-04 20:02). merinfo hämtar inga bolagssidor förrän Anton fyller på (betalning = Antons). |
| Release-PR #30 | Öppen, development → main, öppnad av Sebbe. 64 commits, ~25 000 rader. CI grönt utom Supabase Preview (den kända döda Supabase-grenen). Väntar på Antons review och merge. |
| Nattspegeln main → development | Stannar så länge main och development har olika högsta migrationsversion (`railway_seed_dev.py` avbryter). Startar igen när 090/091 körts på main. Kör 02:00 UTC och skriver då över development. |
| Disken C: | ~1 GB ledigt. Npm-cachen (3,3 GB) och `ms-playwright` (1,6 GB) är de största posterna. `.next` tömdes 2026-10-04. |
| `bd` (beads) | Nere, dolt saknas. Planfilerna är spårningen. |

---

## 2. Vad som byggdes, i ordning

### 2.1 Snajp Suite fas 1–3 (2026-10-03, före kompakteringen)

Antons beställning: en tydlig CRM-översikt i stället för spridda Iris-sidor,
Twenty som förebild, adminens kundsidor ihopbakade, översikterna med
nyckeltalen överst. Godkänd "i sin helhet" med villkoren att Leads heter
Leads och att bara flikar vi har funktion för läggs till.

- **Fas 1 (`a62098e`)**: platt meny: Översikt, Att göra, Leads, Kundtjänst,
  Kvitton, Aktivitet, Inställningar. Leads har vyerna Alla leads, Tabell,
  Pipeline (status-kanban), Listor (`?vy=`). Att göra samlar väntande svar,
  eskalerade ärenden, larm, Iris granskning och inkorg. Aktivitet = körningar +
  journal. Gamla `iris/*`-vägar omdirigeras. Inställningar omgrupperade.
- **Fas 2 (`959b5b5`)**: Översikten med nyckeltalsrad, kön, pipeline, Iris
  senaste körningar och ärenden; `DuoSummary` borttagen.
- **Design (`19d1b10`, `323540e`)**: `/design` över alla appytor (Antons ord:
  "Det ser inte särskilt bra ut"). Understrukna flikar, täta tabeller, chips
  för filter, sidrubrik 1.75rem, `.appyta .kicker`, DESIGN.md § App surfaces.
- **Fas 3 (`3657240`)**: adminen som tre objekt: Översikt, Kunder, Logg;
  kundposten med `KundHuvud` och två flikar.
- **Leads-posten med flikar (`fadbe14`)**: Bedömning, Mejlutkast, Tidslinje.
- **Migrationer**: 088 (nullif-vakt på `dev_flytt_ko`) och 089 (fyra
  Leads Suite-policyer utan nullif) — körda i båda miljöerna, 0 oskyddade
  policyer verifierat via `pg_policies`.
- **Spegeln**: Antons Alunix-konto syns nu i development (spegeln hade aldrig
  kört; triggad manuellt och verifierad).

### 2.2 Provsortera och Jev i inkorgen (`ab4bfa2`, `dd2b165`)

Antons ord: "Kan du lägga till en knapp för att sortera mailen så man kan
testa det i realtid innan vi automatiserar det."

- Knappen **Provsortera** i kundtjänstinkorgen (`components/snajp/Dashboard.tsx`)
  → `POST /api/inbox/sortera` (`snajp-support/app/api/inbox.py`). Visar
  förslag per mejl (support / lead / ej relaterat, källa, Jevs gissning med
  säkerhet) utan att skriva. **Tillämpa** skriver klassen med sin riktiga
  källa; mejl som pipelinen inte släppt (`new`/`processing`) hoppas över
  (kapplöpning sedd i lokalt prov).
- **Dataskyddsfynd**: inkorgens klassning skickade avsändaradress och mejltext
  till Jev (TypeSafe), mot Antons beslut 2026-09-30 i `app/leads/jev.py`.
  Rättat: egen brytare `INKORG_JEV` (off | prov | auto), och även då bara
  avsändarens domän + text utan adresser/telefon. Inkorgens Jev kräver inte
  längre `IRIS_JEV`.
- Anton beslutade därefter: "sätt Jev i drift för alla inkorgar" → `auto`.

### 2.3 Provkörningarna på Alunix och merinfo-rättningarna (`dd2b165`, `72db2cf`, `d65de7f`)

Alunix-arbetsytan i development (slug `kund-ea08b974`, nyckel i
`workspace_tenant_keys`). Skript i scratchpad, inte i repot.

- `valj_branscher` gjorde Alunix målgruppsmening till en påhittad merinfo-bransch
  → noll träffar. Nu blir bara ett eller två ord egen bransch.
- Researchen läste bara bolagets egen sajt; bolag utan sajt fick
  "ingen information kunde hittas" men nivå A. Nu registreras merinfos
  bolagssida som källa (`business_register`) och hämtas via ScrapeGraph i
  `leads_research_v2.py`.
- Saknad webbplats räknas som träff när profilen har `utan_webbplats`
  (`app/leads/profil.py`).

### 2.4 Krocken med Sebbes Skickat-kopia (`72db2cf`)

Sebbes `fb85da9` lade kopian av skickade mejl i tenantens första inkorg oavsett
syfte (migration 084). Nu: samma syfte först, sedan `bada`, sist vilken som
helst. Leads-utskick skickar `syfte="leads"`.

### 2.5 Antons leadsregler (`02babb8`) — gäller tills han säger annat

Står ordagrant i `CLAUDE.md` och `AGENTS.md` (avsnittet "Leads: källor,
filter och kontakter"). Kort:

1. Registret (merinfo) är ett **filter** (bransch, geografi, storlek,
   omsättning), aldrig en kontaktkälla.
2. **Jev är första filtret** mot kundens kriterier.
3. **Bara VD** kontaktas, och bara med en uppgift som kan styrkas tillhöra VD.
4. **Iris**: webbplatsen slås upp ur registerdatan; kontakt, roll och händelser
   hämtas därifrån. Ingen webbplats → nästa bolag.
5. **Listor**: VD:ns mejl eller telefon, bara när den står vid VD:ns namn på
   bolagets egen sajt (`discovery.hamta_vd_kontakt` / `vd_uppgift_i_text`).
6. Merinfos **personsidor används inte** (privatperson: bostad, ålder, familj;
   numren bakom betalvägg — kontrollerat med en maskerad hämtning).

Kod: `snajp-support/app/leads/sources/merinfo.py` (`sok(..., lage="iris"|"lista")`,
`_komplettera`, `vd_namn`, omsättningsfilter i `kontrollera`),
`snajp-support/app/leads/discovery.py` (`hamta_vd_kontakt`, `vd_uppgift_i_text`),
`snajp-support/app/api/leads.py` (listan anropar `lage="lista"`).

**Provet efter reglerna (Alunix, bygg + el, Göteborg/Mölndal):**
Iris 18 kandidater → 15 klarade filtret → Jev fällde 0 → 2–4 hade webbplats →
8 undersökta, 5 fällda för "ingen kontaktperson med roll" på sajten → **1 lead**.
Listan: 15 → 14 → 0 med VD-uppgift vid namnet → **0 rader**. Reglerna fungerar;
volymen är låg eftersom små bygg-/elfirmor sällan har sajt och sällan skriver
VD:ns namn och nummer där.

### 2.6 Övrigt
- `components/leads/IrisGranskning.tsx`: versaler bort (INV-UI-001), från en
  av Sebbes commits (`b185531`).
- Lokala stacken: `scripts/lokal_stack.py --apply` utfärdar inte nycklar om
  `SNAJP_KEY_*` redan står i `.env.local` från en gammal databas → "Ogiltig
  API-nyckel". Lösning: stryk raderna och kör `utfardas_tenantnyckel()` med
  backenden igång.
- Git Bash gör om argument som börjar med `/` till Windows-sökvägar
  (`/api/leads/profil` → `C:/Program Files/Git/api/...`). Sätt
  `MSYS_NO_PATHCONV=1`.

---

## 3. Sebbes arbete (granskat av en Opus-agent, verifierat)

17 commits sedan 2026-10-01, varav 15 ligger i PR #30:

| Område | Vad |
|---|---|
| Textkvalitet (`3912c4c` m.fl.) | Kvalitetslager `app/textkvalitet.py` + `lib/textkvalitet.ts`: deterministisk putsning, flaggor för språkrisk, korrekturpass bara vid flagga. **Flaggad text skickas aldrig automatiskt** — går till granskning. ~80 språkrättningar, skärpta prompter, UI-textskanner i CI, 25 nya tester. Rapport: `HANDOFF-2026-10-03-TEXTKVALITET.md`. |
| Lösenordsåterställning (`a38565d`, `0adfdc6`) | Engångstoken, Resend-väg, migration 090 + 091 (091 ger `snajp_web` en öppen policy på `password_reset_tokens`; skyddet är att token är hashad). |
| Mejlsignatur (`6d6bf7b`) | Iris signatur med logotyp, per tenant i `agent_configs.settings["signatur"]`. **Seedas efter merge** med `scripts/satt_mejlsignatur.py --slug <slug> --env main --jag-menar-produktion --apply`. |
| Inkorg (`fb85da9`, `1944be2`, `c6758ea`) | Skickat-kopia via IMAP APPEND, mellanslag i app-lösenord, synken markerar läst först när sparat, adminfliken Paket + kontoläge (redan i main). |
| `102b564` | Allow-regel för `scripts/railway_tenantnyckel.py` i `.claude/settings.json`. |
| Drift utanför release | Sebbes session bytte `SNAJP_KEY_LIVRUSTNING` på web/main 2026-10-04 (den var död, 401). En produktionsändring som inte gick via Anton. |

Krockar: bara Skickat-kopian (rättad, 2.4). Inga överskrivna rader, inga
trasiga migrationer (dubbla 080-nummer är ofarliga; `railway_migrate.py`
spårar hela filnamnet). Kända risker som inte är krockar: Skickat-kopian är
ren text utan signatur och Message-ID; felmeddelandena i `lib/actions/auth.ts`
(rad ~290, 349, 377) finns bara på svenska och fångas inte av INV-COPY-001.

**Isolera Sebbes delar?** Provat i minnet (`git merge-tree` ovanpå main):
5 av hans 15 commits krockar (`d0657f0`, `304bf49`, `b27c363`, `a38565d`,
`6d6bf7b`) eftersom de bygger på vår kod. Rekommendationen till Anton var
att merga hela PR:en.

---

## 4. Vad som återstår, i prioritetsordning

1. **Före mergen av PR #30**
   - Kör migrationerna 090 och 091 mot main:
     `python scripts/railway_migrate.py --env main` (torr), sedan `--apply`.
     **Kräver Antons ord** — han har inte gett det än.
   - **Ej relaterat-vyn.** Mejl som klassas `ej_relaterat` (av regel eller Jev)
     filtreras bort ur kundens inkorg (`postgres.py` ~rad 2636: `status not in
     ('lead','ej_relaterat')`) och det finns ingen vy för att se dem eller flytta
     tillbaka dem (`POST /api/inbox/{id}/klassa` finns i backenden men används
     inte av UI:t). Med `INKORG_JEV=auto` i main kan ett riktigt kundärende
     försvinna tyst. Förslag till Anton: bygg ett chip "Ej relaterat" i
     inkorgen + knappen "Flytta till support" (anropar `/klassa`), eller sätt
     `INKORG_JEV=prov` i main tills den finns. **Väntar på Antons val.**
2. **Mergen** — Antons handgrepp (code owner-review). Efter mergen:
   - `scripts/satt_mejlsignatur.py` per kund i main.
   - `python scripts/flytt_nycklar.py --check` och flytta ett testmejl.
   - Verifiera att nattspegeln kör igen 02:00 UTC.
3. **ScrapeGraph-krediten** — Anton fyller på (betalning).
4. **Leadsvolymen under de nya reglerna** — Antons beslut:
   - Fler bolag per beställt lead (`PROV_PER_LEAD` i `merinfo.py`, i dag 4) —
     kostar fler ScrapeGraph-hämtningar och webbplatsuppslag (Gemini).
   - Får ett Iris-lead gå till sajtens allmänna adress (info@) med VD:n från
     registret som mottagare när sajten saknar namngiven kontakt? Regelfråga,
     inte byggd.
   - Alunix-profilen saknar branscher; utan dem används inte merinfo i Alunix
     egna körningar. Arbetsytan heter "Alunix workspace" och det står i
     lägesbeskrivningarna — byt namn till "Alunix".
5. **Branschmatchningen**: "VVS" → "Partihandel med VVS-varor", "el" →
   "Lagring av elektricitet" (`valj_branscher`, stammatchning mot sitemapen).
6. **Jev fällde inget** i provet: Alunix kriterier gäller webbplatsen, som Jev
   inte ser i en verksamhetsbeskrivning. Med branschkriterier filtrerar den.
   Möjlig utbyggnad (ej beslutad): Jev klassar svar från leads (intresserad /
   nej / prisfråga) före dyrare steg.
7. **Från IA-planen, ej byggt**: Twenty-vybarens ⋮-meny (Importera, Beställ
   lista); fråga 2 om listrader som leads direkt (kräver migration, Antons beslut).
8. **a11y-skuld** och **/simplify** — inte körd på sessionens ändringar.
9. **Kvarliggande, ej sessionens**: dataskyddsfrågan om språkmodell-leverantören
   (GOALS delmål 9), `IMAP_PASSWORD_LIVRUSTNING`, API-avtal med merinfo/allabolag
   (Antons utkast i `docs/`, ocommittade).

---

## 5. Fällor

- **Rör inte Antons ocommittade filer**: `strategies.md`, `next-env.d.ts`,
  `docs/utkast-merinfo-api-forfragan.md`, `docs/utkast-allabolag-api-forfragan.md`,
  `session-logs/2026-09-30-session-log.md`. `gsap.js` och `smooth-scroll.js`
  lades av en hook och är inte committade.
- Python på Windows: `write_text` gör LF till CRLF; använd `write_bytes`.
  Kontrollera `git diff --stat` mot `git diff --stat -w` före commit.
- UI-filer får bara skrivas med Write/Edit (design-gate-hooken stoppar `sed -i`).
- Development är en spegel med riktig kunddata: inga skärmdumpar med kunddata,
  lokal dev-server pekas aldrig dit (`scripts/lokal_stack.py --apply`).
- Disken: kontrollera ledigt utrymme före tunga körningar; den gick till 0 byte
  mitt i sessionen.

---

## 6. Antons instruktioner i sessionen, ordagrant

> Kör /standup och gå igenom underlaget från förra sessionen. Allt ska ha genomförts, men jag kan inte se den tydliga CRM- "Snajp- Suite" som jag bad om, allt är väldigt rörigt och utspitt över många sidor utan någon bra överblick eller struktur. Alla Iris-sidor är nu fler och mer spridda än någonsin. Gå igenom Twenty igen och undersök hur vi kan strukturera datan bättre och mer proffsigt. Kundsidorna från adminvyn hade kunnat bakas ihop, översikterna för både admin och kunder är röriga och intetsägande med många viktiga mätvärden gömda längre ned eller på andra sidor. Speglingen från main fungerar fortfarande inte, då mitt Alunix-konto inte dykt upp där.

> Jag godkänner strukturen i sin helhet, men har några frågor. Leads ska heta leads, inte bolag. Var även noga med att lägga till flikar som vi enbart har funktion för, så vi inte lägger till funktioner från Twenty som vi inte har, vad står tex kanban för?

> Det ser inte särksilt bra ut, applicera /design på all frontend

> Ja, kör 088 mot main och fortsätt med fas 2. Har lyft alla permissions, tillåt inga fler blockerare, fortsätt tills allt är klart.

> Cahce är rensad, vad återstår?

> Är Jev för leads och inkorgen samt de övriga fixarna för körningarna helt implementerade?

> Förtydliga vad du menar en brevlåda kopplad som leads. Kan du lägga till en knapp för att sortera mailen så man kan testa det i realtid innan vi automatiserar det.

> Kör provkörningen för Leads på Alunix, se till att merinfo också är på och sätt Jev i drift för alla inkorgar, meddela mig även om allt Sebbe gjort och se till att inget krockar

> Okej, merinfo är egentligen och ska behandlas som ett enkelt filter av företag utifrån branch och storlek/omsättning, inte kontaktuppgifter. Det är dessa som Jev ska klassificera utifrån de kriterier som angetts, som ett första filter. Du har rätt i att styrelseledamöter ej ska kontaktas, endast VD, men eftersom de telefonnummer som anges inte går att säkerställa till en viss person kan inte dessa heller användas. De aktuella uppgifterna med kontaktinformation och roller finns med största sannolikhet på företagets hemsida, använd informationen från merinfo för att hitta hemsidan och använd informationen därifrån för nästa steg. Om det inte finns en hemsida, gå vidare. Detta gäller bara för de mer detaljerade Iris-leadsen, där roll, kontaktperson och företagshändelser/nyheter spelar roll för att bygga en bra ingång. För listorna räcker det med mailadress eller telefonnummer till respektive lista, om detta kan styrkas tillhöra VD, vilket är den relevanta personen att kontakta då företag utan hemsida oftast är mindre företag med VD som beslutsfattare. Spara detta som globala instruktioner för projektet så att ytterligare funktioner byggs utifrån det tills annat sägs. Förklara gärna om Jev har någon ytterligare funktion för leads utöver detta för leads. Verkställ detta och utveckla även ytterligare vad Sebbes PR gör för något.

> Är det säkert att merga Sebbes PR, vad bör jag tänka på? Jag har fortfarande lite punkter att jobba vidare med gällande allt som vi gjort, kan vi korrigera PR:en för att isolera till Sebbes ändringar? Eller skicka med UI-delarna (även om vi kommer behöva ändra många av dem igen)

> Okej, jag vill att du kör /conclude och skriver en utförlig handoff till nästa agent om allt som gjorts denna session och vad som återstår. Jag vill även att du updaterar instruktionerna för conclude-skillen med att ALLTID skriva en detaljerad handoff med vad som gjorts och vad som återstår, eftersom att jag alltid skriver så här för att försäkra mig om det.

**Obesvarat av Anton vid sessionens slut:** (a) kör 090/091 mot main? (b) Ej
relaterat-vyn före mergen, eller `INKORG_JEV=prov` i main? (c) volymfrågorna i § 4.4.
