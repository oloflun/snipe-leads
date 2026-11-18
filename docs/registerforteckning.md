# Registerförteckning (GDPR art. 30)

Internt dokument. Ska inte publiceras, men ska kunna lämnas till IMY på
begäran — och det är precis då man inte hinner skriva den.

**Håll den i synk med tre andra ställen:** leverantörslistan i
[`lib/bolag.ts`](../lib/bolag.ts), bilagan till PUB-avtalet (och pilotavtalets
Bilaga 1), och tabell-listan i [`scripts/gdpr_radera.py`](../scripts/gdpr_radera.py).
Läggs en behandling eller en leverantör till någonstans ska den läggas till här
i samma ändring.

Fält markerade **[fylls i]** kräver ett beslut som inte kan härledas ur koden.

Mottagare, regioner och överföringsmekanismer: läget 2026-11-17, ur
leverantörsgranskningen samma dag och Railways regionlista. Kortformerna nedan:

| Leverantör | Plats | Avtal | Överföring |
|---|---|---|---|
| Google Cloud, Vertex AI | Inom EU (anrop i Belgien, Nederländerna, Finland; inte nödvändigtvis i det landet). Flaggade meddelanden upp till 90 dagar | Cloud DPA, automatiskt. Avtalspart **[fylls i]** | DPF och SCC |
| Railway | Amsterdam (EU West), alla tjänster och volymer. Jobbkö och cache sedan 2026-11-17, över det privata nätverket och med en egen databas per miljö. Backupplats **[fylls i: Railways besked]** | DPA signeras via DocuSign, ännu inte signerad 2026-11-17 | DPF, annars SCC, när DPA:n är signerad |
| Redis Cloud (Redis EMEA Ltd, UK), avvecklas | Google Cloud europe-west1 (Belgien). Används inte i driften sedan 2026-11-17; kvarvarande cache och arbetsminne tills databasen raderats | DPA automatiskt via Redis Cloud Agreement §5.3; betald plan **[fylls i]** | SCC med UK-tillägg |
| Resend | Skickar från Irland; innehåll och loggar lagras i USA i 30 dagar | DPA automatiskt med avtalet | DPF (under omprövning) och SCC. TIA ej gjord |
| TypeSafe AI, Inc. (Jev) | USA. Bara leadsdelen; kundmejl går inte hit sedan 2026-11-17 | DPA inkorporerad i MCA; ej belagt vilka villkor kontot accepterade. Telemetrivillkor utan tidsgräns | SCC; ej i DPF |
| ScrapeGraphAI, Inc. | USA | Ingen publicerad DPA | Ingen angiven; ej i DPF |
| GitHub (Actions-synken) | Region anges inte (Azure, vissa AWS) | DPA gäller inte Free-planen, som kontot har | Ingen avtalad |
| Supabase (avvecklas) | Irland (eu-west-1). Historiska uppgifter tills projektet raderats | DPA automatiskt | SCC |

---

## A. Snajp som personuppgiftsansvarig

Det vi behandlar för vår egen räkning.

### A1. Konton och arbetsytor

| | |
|---|---|
| **Ändamål** | Ge inloggning och knyta en användare till rätt arbetsyta |
| **Kategorier av registrerade** | Anställda hos våra kunder |
| **Kategorier av uppgifter** | Namn, e-postadress, lösenordshash, inloggningstidpunkter |
| **Rättslig grund** | Fullgörande av avtal (art. 6.1 b) |
| **Mottagare** | Railway (drift och databas, Amsterdam), GitHub (synken från produktion till testmiljö bär produktionens persondata), Supabase (historiska uppgifter tills det gamla projektet raderats) |
| **Tredjelandsöverföring** | Databasen ligger i EU. Railway och GitHub är amerikanska bolag: Railway enligt DPA (DPF, annars SCC) när den är signerad; GitHub utan avtalad mekanism. Se tabellen överst |
| **Lagringstid** | **[fylls i — förslag: raderas X månader efter att avtalet upphört]** |
| **Var i systemet** | `auth.users`, `profiles`, `workspaces` |

### A2. Utgående försäljning (våra egna kallmejl)

| | |
|---|---|
| **Ändamål** | Ta en första affärskontakt med potentiella kunder |
| **Kategorier av registrerade** | Kontaktpersoner hos svenska företag |
| **Kategorier av uppgifter** | Namn, tjänstemejladress, roll, bolagsuppgifter |
| **Rättslig grund** | Berättigat intresse (art. 6.1 f). Intresseavvägningen ska dokumenteras **[fylls i]** |
| **Informationsplikt** | Art. 14 — uppgifterna kommer inte från personen själv. Lämnas i varje utskick, se `snajp-support/app/leads/utskicksfot.py` |
| **Källor** | Bolagens egna webbplatser; bolagsregister som filter: merinfo.se (hämtas via ScrapeGraphAI) och allabolag.se (direkthämtning, inget avtal); hitta.se (telefon och e-post på org.nr, kan vara en persons nummer); JobTech/Arbetsförmedlingen (platsannonser som köpsignal); nyheter, RSS och Mynewsdesk (bolagshändelser, kan innehålla namn). Registrets personsidor används inte |
| **Mottagare** | Google Cloud Vertex AI (research, textgenerering, grundad sökning med bolagskriterier), TypeSafe (klassning av bolag; e-post och telefon bortfiltrerade), ScrapeGraphAI (hämtning av publika sidor), Resend (utskick), Railway (drift och databas), GitHub (synken), Supabase (historiska uppgifter) |
| **Tredjelandsöverföring** | Ja: TypeSafe och ScrapeGraphAI i USA, Resends lagring i USA, GitHubs körmaskiner i ospecificerad region. Mekanismer enligt tabellen överst |
| **Lagringstid** | **[fylls i]**. Undantag: raden i `suppressions` behålls tills vidare — den finns för att personen inte ska kontaktas igen |
| **Var i systemet** | `contacts`, `prospects`, `companies`, `outreach_threads`, `outreach_messages`, `suppressions`, `workspace_invites`. Adressen kan dessutom stå i löptext i `generated_emails` och `agent_runs` |

### A2b. Webbpoolen (bedömning av bolagssajter) — preliminär 2026-10-08

| | |
|---|---|
| **Ändamål** | Bedöma bolags publika webbplatser och fördela bolag med trasig eller föråldrad sajt till webbyråkunderna efter län |
| **Kategorier av registrerade** | Inga: bara juridiska personer. Enskilda firmor (orgnr = personnummer) utesluts i kod, `webbpool.ar_enskild_firma` |
| **Kategorier av uppgifter** | Bolagsnamn, organisationsnummer, webbplats, ort, postnummer, län, SNI, sidbedömning |
| **Rättslig grund** | Ej personuppgifter (juridiska personer) |
| **Mottagare** | Webbyråkunderna (Alunix, Umeå Webbdesign), Google Cloud Vertex AI (bildbedömning, inom EU), ScrapeGraphAI (skärmbild, USA) |
| **Lagringstid** | **[fylls i — förslag: 12 månader efter senaste observation]** |
| **Var i systemet** | `webbpool`, `webbpool_fordelad` (migration 108), `app/leads/webbpool.py`, INV-SEC-008 |

### A3. Support till våra egna kunder

| | |
|---|---|
| **Ändamål** | Besvara frågor från våra kunder |
| **Kategorier av registrerade** | Kontaktpersoner hos kunder |
| **Kategorier av uppgifter** | Namn, e-postadress, ärendeinnehåll |
| **Rättslig grund** | Fullgörande av avtal / berättigat intresse |
| **Lagringstid** | **[fylls i]** |

---

## B. Snajp som personuppgiftsbiträde

Det vi behandlar **för kundens räkning**. Här är kunden ansvarig och vi
biträde. Förteckningen ska ändå finnas — art. 30.2 gäller biträden också.

### B1. Supportagenten

| | |
|---|---|
| **Personuppgiftsansvarig** | Kunden |
| **Ändamål** | Klassificera inkommande kundmejl och föreslå svar |
| **Kategorier av registrerade** | Kundens kunder — alltså konsumenter, inte bara företagskontakter |
| **Kategorier av uppgifter** | Avsändarens namn och e-postadress, meddelandeinnehåll, bilagor. Innehållet är **okontrollerat**: en kund kan skriva vad som helst i ett supportmejl, inklusive personnummer och hälsouppgifter |
| **Mottagare (underbiträden)** | Google Cloud Vertex AI (språkmodell, inom EU), Railway (drift, databas och jobbkö/cache med TTL, Amsterdam), Redis Cloud (tidigare jobbkö/cache, europe-west1; används inte sedan 2026-11-17 men har kvar tillfälliga uppgifter tills databasen raderats), Resend (utgående mejlsvar; lagring i USA i 30 dagar), GitHub (synken bär produktionens persondata), Supabase (historiska uppgifter tills det gamla projektet raderats) |
| **Tredjelandsöverföring** | Ja: Resends lagring (DPF och SCC), GitHub (ingen avtalad mekanism), Railway och Google som amerikanska bolag (DPF och SCC; Railways först när DPA:n är signerad). Se tabellen överst. TypeSafe fick mejltext utan adresser fram till 2026-11-17, då ägaren stoppade flödet och inkorgsklassningen stängdes av i båda miljöerna. Det som redan skickats ligger kvar hos TypeSafe; radering är inte begärd |
| **Lagringstid** | Enligt `ss_gallringspolicy`. **Perioden är ännu inte beslutad** — se `scripts/gallra.py` |
| **Var i systemet** | `ss_emails`, `ss_email_attachments`, `ss_classifications`, `ss_drafts`, `ss_human_reviews`, `ss_tickets` |
| **Säkerhetsåtgärder** | Radnivåsäkerhet per tenant i databasen; ingen delning mellan kunder; utgående mejl kräver mänskligt godkännande; personnummer maskeras innan texten går till modelleverantören |

### B2. Leadsagenten

Samma som A2 (källor, mottagare och överföringar), men uppgifterna är
kundens och ändamålet kundens försäljning.
Kunden är ansvarig, vi är biträde. **Avsändaridentiteten i varje utskick är
kundens** — se de sex spärrarna i `snajp-support/app/leads/send_guard.py`.

### B3. Bokföringsagenten

| | |
|---|---|
| **Ändamål** | Läsa av kvitton och föreslå kontering |
| **Kategorier av uppgifter** | Det som står på underlaget: motpart, belopp, datum. Kan innehålla personnamn |
| **Särskilt** | **Originalfilen lagras inte.** Bara en sha256-summa sparas — se `db/migrations/045_bookkeeping.sql`. En fil vi inte har kan inte läcka och behöver ingen gallring |
| **Var i systemet** | `bk_underlag` |

---

## C. Vad som saknas

Skrivs av så snart det är gjort, inte innan:

- [ ] Intresseavvägning för A2 dokumenterad
- [ ] Lagringstider beslutade och ifyllda ovan
- [x] Modellnivå: chatten går via Vertex AI på betalt Google Cloud-projekt sedan 2026-09-12. Reservvägen till Google AI Studio finns kvar i koden och ska spärras där data är riktig
- [x] Googles dataregion och överföringsmekanism bekräftade (2026-11-17): inom EU, DPF och SCC. Avtalsparten **[fylls i]**
- [ ] OpenAI:s dataregion och avtalsform bekräftad (om den tas i drift; inte i drift 2026-11-17)
- [x] Railways region bekräftad: Amsterdam för alla tjänster och volymer (2026-11-17)
- [ ] Railways DPA signerad och besked om backupplats
- [x] Redis Clouds region (europe-west1) och avtalsläge (DPA automatisk) bekräftade 2026-11-17
- [x] Jobbkön skyddad i transit: flyttad 2026-11-17 till Railways egen Redis över det privata nätverket, en databas per miljö, verifierad i uppstartsloggen i båda miljöerna
- [ ] Redis Cloud-databasen raderad och kontot uppsagt (ägarens beslut)
- [x] Resends region, DPA och DPF/SCC-status bekräftade 2026-11-17 (lagring i USA)
- [ ] Resends USA-lagring godkänd av ägaren, med TIA
- [x] Beslut om TypeSafe för kundmejl: stoppat 2026-11-17 genom ägarens beslut, inkorgsklassningen avstängd i båda miljöerna. Kvar: begära radering av det som redan skickats, och beslut om leadsdelen
- [ ] ScrapeGraphAI: betald plan bekräftad och DPA begärd
- [ ] Synken flyttad från GitHub Actions, eller plan som omfattas av GitHubs DPA
- [ ] Supabase-projektet raderat och raderingen bekräftad
- [ ] DPIA för supportagentens automatiska klassificering och eskalering
