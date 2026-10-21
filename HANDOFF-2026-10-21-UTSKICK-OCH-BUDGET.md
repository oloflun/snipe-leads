# Handoff 2026-10-21 — utskicksrättningar, alla leads i listan, leadsbudgeten

## 1. Läget just nu, verifierat
- **Git:** gren `development`, senaste commit `99abd8c`, allt pushat. Ocommittade filer som inte hör till sessionen (rör dem inte): `docs/utkast-merinfo-api-forfragan.md`, `next-env.d.ts`, `strategies.md`, `docs/utkast-allabolag-api-forfragan.md`, `koncept/`, `.playwright-mcp/`, `session-logs/2026-09-30-session-log.md`.
- **PR #35** (development → main): öppen, går att merga, väntar på Antons granskning (code owner). CI körde fortfarande vid avslutet. Kontrollen "agent-core laddas i den byggda imagen" föll efter 7 s. Tidigare i kväll föll den två gånger på att GitHub inte fick hämta Python-bilden från registret. Loggen för det här felet är inte läst. Kör om jobbet (`gh run rerun <id> --failed`) när körningen är klar.
- **Migrationer:** inga behövs. `railway_migrate.py --env main` visar allt t.o.m. 112 kört. PR:en bär ingen SQL.
- **Railway, api:** `LEADS_DAILY_TOKEN_BUDGET=150000000` i både development och main (var 1 500 000 000), kontrollerat efter ändringen. Utkasten kör på flash i båda miljöerna (beslut 2026-10-21 i `docs/BESLUT.md`).
- **Development** kör koden i PR #35.

## 2. Vad som byggdes
- **Trådsvar kraschade** (`14b5891`, `snajp-support/app/leads/send_decision.py`): `last_inbound_at` kom som ISO-sträng och tidsgrinden föll på `datetime - str`, så svar i trådar där prospektet svarat gick aldrig ut. Samma commit: `list_due_send_queue` saknade `ORDER BY` och skickar nu äldst först.
- **Skickas snart** (`c413250`): visar alla godkända mejl, inte bara de bland de 1 000 nyaste leadsen (`get_prospects` med id).
- **Alla leads i listan** (`79a309e`): `GET /api/leads/prospects` bläddrar (`offset`, `fler`, `nasta`), klienterna hämtar alla sidor (`lib/leads/suite.ts:allaProspekt`). Förut syntes 500 av 1 331 i main. Synken (`scripts/railway_synk.py`) öppnar main skrivskyddat utanför första synken, och `flytta_korningar_till_main.py` tar bara körningar.
- **Budgeten** (`1126468`, `99abd8c`): 150 M tokens per dygn ≈ 1 000 leads på flash (~150 k tokens per levererat lead, uppmätt i main 2026-10-20) ≈ 60 USD/dygn om hela taket används.
- **Verifiering:** 2 119 Python-tester gröna. Sid-SQL:en mot development gav 2 066 av 2 066 leads på 3 sidor utan dubbletter. Typkontrollen grön i CI.

## 3. Vad som återstår, i prioritetsordning
1. **Anton** granskar och mergar PR #35. Då kommer rättningarna för trådsvaren, köordningen och listorna till main.
2. **Agenten** kör om den fallna CI-kontrollen när körningen är klar och läser loggen. Är det registerfelet igen räcker en omkörning. Är det något annat ska det rättas före mergen.
3. Efter mergen: kontrollera i main att listan visar alla leads och att ett trådsvar går ut.

## 4. Fällor
- `gh run rerun` vägras medan andra jobb i samma körning fortfarande pågår.
- Budgetvariabeln slår igenom direkt via Railway, den väntar inte på någon merge.
- Railway-anrop görs via `scripts/railway.py q '<graphql>' '<json>'`. Miljö-id: main `47bc7047-…`, api-tjänsten `5828c279-…`.

## 5. Antons instruktioner ordagrant
- "Sänk den just nu … sikta på runt 1000." (om leadsbudgeten i development)
- "Gör samma beslut där, updatera PR:en för merge. Behövs några migrationer sedan?"
- Instruktionerna från sessionens första del (utskicksbuggarna, listan) finns inte kvar ordagrant efter att samtalet återupptogs. Skälen står i commit-meddelandena och i `docs/BESLUT.md`.
