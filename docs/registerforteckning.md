# Registerförteckning (GDPR art. 30)

Internt dokument. Ska inte publiceras, men ska kunna lämnas till IMY på
begäran — och det är precis då man inte hinner skriva den.

**Håll den i synk med tre andra ställen:** leverantörslistan i
[`lib/bolag.ts`](../lib/bolag.ts), bilagan till PUB-avtalet, och tabell-listan
i [`scripts/gdpr_radera.py`](../scripts/gdpr_radera.py). Läggs en behandling
eller en leverantör till någonstans ska den läggas till här i samma ändring.

Fält markerade **[fylls i]** kräver ett beslut som inte kan härledas ur koden.

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
| **Mottagare** | Supabase (databas), Railway (drift) |
| **Tredjelandsöverföring** | **[fylls i — beror på Railways datacenterregion]** |
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
| **Mottagare** | OpenAI (textgenerering), Railway, Supabase |
| **Lagringstid** | **[fylls i]**. Undantag: raden i `suppressions` behålls tills vidare — den finns för att personen inte ska kontaktas igen |
| **Var i systemet** | `contacts`, `companies`, `outreach_threads`, `outreach_messages`, `suppressions` |

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
| **Mottagare (underbiträden)** | OpenAI, Supabase, Railway |
| **Tredjelandsöverföring** | **[fylls i — kräver besked om OpenAI:s dataregion]** |
| **Lagringstid** | Enligt `ss_gallringspolicy`. **Perioden är ännu inte beslutad** — se `scripts/gallra.py` |
| **Var i systemet** | `ss_emails`, `ss_email_attachments`, `ss_classifications`, `ss_drafts`, `ss_human_reviews`, `ss_tickets` |
| **Säkerhetsåtgärder** | Radnivåsäkerhet per tenant i databasen; ingen delning mellan kunder; utgående mejl kräver mänskligt godkännande |

### B2. Leadsagenten

Samma som A2, men uppgifterna är kundens och ändamålet kundens försäljning.
Kunden är ansvarig, vi är biträde. **Avsändaridentiteten i varje utskick är
kundens** — se de sex spärrarna i `snajp-support/app/leads/send_guard.py`.

### B3. Bokföringsagenten

| | |
|---|---|
| **Ändamål** | Läsa av kvitton och föreslå kontering |
| **Kategorier av uppgifter** | Det som står på underlaget: motpart, belopp, datum. Kan innehålla personnamn |
| **Särskilt** | **Originalfilen lagras inte.** Bara en sha256-summa sparas — se `supabase/migrations/045_bookkeeping.sql`. En fil vi inte har kan inte läcka och behöver ingen gallring |
| **Var i systemet** | `bk_underlag` |

---

## C. Vad som saknas

Skrivs av så snart det är gjort, inte innan:

- [ ] Intresseavvägning för A2 dokumenterad
- [ ] Lagringstider beslutade och ifyllda ovan
- [ ] OpenAI:s dataregion och avtalsform bekräftad
- [ ] Railways datacenterregion bekräftad
- [ ] DPIA för supportagentens automatiska klassificering och eskalering
