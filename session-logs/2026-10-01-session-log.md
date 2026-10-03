# Session Log — 2026-10-01

## Session Summary
Ett mejlutkast till Merinfo (Informationsgruppen) med en förfrågan om företagsdata via API är skrivet i `docs/utkast-merinfo-api-forfragan.md`, men inte skickat. Det är Antons handgrepp i planens del B (beslut 1): Merinfos villkor förbjuder kopiering utan skriftligt samtycke. Volymen i mejlet är uppskattad till 1 000–7 500 bolagsuppslag i månaden för 1–5 aktiva kunder, med ett tak runt 15 000.

## What Changed

### Files Created
- `~/snipe-leads/docs/utkast-merinfo-api-forfragan.md` — mejlutkastet: datafält, användning, volym, fyra frågor (pris, visning/export och sparade orgnr, personuppgifter, samtycke för webbhämtning som reserv)
- `~/snipe-leads/session-logs/2026-10-01-session-log.md` — denna logg

### Files Modified
- `~/snipe-leads/plans/2026-10-01-leads-suite-och-korningar.md` — merinfo-raden pekar på utkastet och volymen

## Decisions Made
- **Volymen räknas på aktiv användning, inte på dagens data:** produktionen har bara 9 batchkörningar fördelade på 3 kunder (15–30 sep) och inga listor. Anton angav målbilden: Iris 3–10 leads om dagen eller listor på 50–100 i veckan.
- **Mejlet ber om fast månadspris eller volymtrappa** och om rätt att spara orgnr för redan visade bolag. Skäl: vid 1 kr per uppslag kostar en aktiv kund ~1 500 kr i månaden, en tredjedel av Leads-paketets 4 490 kr.

## Context & Discussion
- Räknemodell (planens del B/C, inget uppmätt): lista ≈ 4,2 anrop per lead (4 kandidater × bolagssida + listsida per 25); Iris ≈ 5–8 per lead (MAX_RUNDOR 3 × MAX_PER_RUNDA 10 i `korning.py`).
- Typisk aktiv kund: 150–300 leads/mån ≈ 800–1 500 anrop.
- Data lästes med skrivskyddade aggregatfrågor (bara antal) mot main och development.
- Smala nischer (t.ex. bygg i Mölndal, ~1 000 bolag) är genomlästa efter 2–3 veckor vid 100 leads/vecka. Därför behövs en permanent lista per kund över redan sedda orgnr.

## Open Threads
- Anton fyller i efternamn, telefon och mottagaradress (merinfo.se/data-via-api-eller-fil) och skickar mejlet; svaret avgör vilken hämtare del B bygger (`api` eller `webb`).
- Leads-paketet lovar 150 prospekt/mån (`lib/pricing.ts`, GOALS.md) men den aktiva användning Anton beskriver är 280–650 leads/mån. Anton behöver besluta om kvoten ska höjas eller om volymen blir en tilläggstjänst.

## Cross-Project Handoffs
None this session.

## Current State After This Session
Del B väntar på Merinfos svar; utkastet är klart att skicka. Del A och G (körningar, menyn) ligger fortfarande opushade på development enligt HANDOFF-2026-10-01-KORNINGAR.md: migration 080 först, sedan push.

<!-- session-state
date: 2026-10-01
type: research-and-draft
files_created:
  - ~/snipe-leads/docs/utkast-merinfo-api-forfragan.md
  - ~/snipe-leads/session-logs/2026-10-01-session-log.md
files_modified:
  - ~/snipe-leads/plans/2026-10-01-leads-suite-och-korningar.md
decisions_made: 2
open_threads: 2
handoffs_pending: []
priority_changes: false
status_updated: false
goals_updated: "skipped -- kvotfrågan (150 prospekt) är ett öppet beslut för Anton, inte ändrad målbild"
next_session_focus: "Skicka Merinfo-mejlet; besluta Leads-kvoten; migration 080 och push av del A/G"
session-state -->
