# Handoff 2026-10-10: parallella körningar, katalogkontakt, listverktyg, kö, autopilot

## 1. Läget just nu, verifierat

- **Git:** gren `development`, senaste commit `effeb0c`. **Allt arbete i den här sessionen är ocommittat**
  (se `git status`: 28 ändrade, 10 nya filer). Inget pushat.
- **Development (Railway):** kör `effeb0c`. Migration 110 (`supabase/migrations/20261010090000_110_listrader_i_listan.sql`)
  är torrkörd mot development men **inte körd**.
- **Main:** orörd. Släppet med migration 096–108 väntar fortfarande på Anton.
- **Miljöflagga:** `LEADS_AUTOPILOT` är inte satt någonstans, så autopiloten är avstängd. Utskicksloopen är
  avstängd i alla miljöer (uppmätt i Railway): inget mejl skickas av sig självt.
- **Disk:** C: hade 0 byte ledigt mitt i sessionen; `.next` raderades (0,8 GB). Nu ca 0,65 GB ledigt.
  Startar man `next dev` fylls disken igen. Det som växte i natt: `~/.cache/qmd` (1,4 GB, omindexering)
  och `AppData/Local/Microsoft` (1,1 GB). Anton behöver frigöra plats.
- **Trasiga verktyg:** `bd` (Dolt saknas), Playwright-MCP och cognee-vault svarade inte.

## 2. Vad som byggdes

| Del | Vad och varför | Filer | Verifierat |
|---|---|---|---|
| Parallella körningar | Två körningar hos samma kund fick samma cachade registerbolag; den senare brände sökrundor på dubbletter. Nu hoppar en körning över bolag som en annan pågående körning har, och en helt upptagen runda räknas inte (högst tre i rad). | `automation.py`, `storage/*`, `tests/test_korning_samtidighet.py`, `test_upptagna_bolag.py` | Test med två samtidiga körningar |
| Katalogkontakt | Hitta.se slås upp på org.nr per bolag (gratis, en förfrågan). Norrtech, Örnbergs och Devoted Intelligence får alla kontakt. "Under uppbyggnad" = platshållare; parkerad domän avslutar inte sökningen. | `leads/katalog.py` (ny), `platshallare.py`, `sources/merinfo.py`, `test_katalog.py` | Enhetstester + manuell körning mot de tre bolagen |
| Eniro | Fungerar inte: 403 för bot-UA, numret bakom klick. Ingen förklädnad som webbläsare. | – | Öppen punkt |
| Gemini-utredning | Grounded sökning duger inte för kontakter (2.5-flash bytte bolag, 2.5-pro tomt, Gemini 3 bara på Vertex global = utanför EU). Duger för bolagshändelser om varje länk hämtas och styrks. | – | Manuella anrop |
| Listorna | "Flytta till Iris" bort; rader stannar, markeras en/alla, klick öppnar samma detaljvy som Iris. Skapa utkast = samma research som Iris, hoppar över rader med utkast (granskningsbugg rättad). Processa om prövar bara oprövade källor. Förlopp i listan som överlever omladdning. | `LeadslistorView.tsx`, `api/leads.py`, `schemas.py`, `omprova.py`, migration 110, `test_leadslistor.py`, `test_listutkast.py` | Tester; skärmbild av verktygsrad och tabell |
| Kön | Markerade mejl: skicka nu eller ny tid, standardtiden orörd. Sändfönstret vardagar 08–16 gäller även Skicka nu (eget val, skyddar domänen). | `SkickatLista.tsx`, `api/leads.py`, `test_schemalagg_utskick.py` | Tester |
| Autopiloten | En körning per vardag från 06:00, standard 10 leads/vardag, tak 50, inställbart under Automation, av tills `LEADS_AUTOPILOT=1`. | `leads/autopilot.py` (ny), `IrisAutomation.tsx`, `jobs/stadare.py`, `test_autopilot.py` | Tester |
| Regler | Regeln "varje funktion går att följa" och BESLUT-regeln i CLAUDE.md/AGENTS.md; resonemangen i `docs/BESLUT.md` (ny). | `CLAUDE.md`, `AGENTS.md`, `docs/BESLUT.md` | – |

Samlat: 3161 backendtester gröna, typkontroll ren, språkgrinden (INV-COPY-001) grön.

## 3. Vad som återstår, i prioritetsordning

1. **Anton frigör diskutrymme på C:.** Utan det går ingen dev-server att starta.
2. **Anton svarar: committa, köra migration 110 mot development och pusha?** Agenten gör det efter ja
   (`python scripts/railway_migrate.py --env development --apply`, sedan `git push origin development`).
   Obs: `gsap.js`, `smooth-scroll.js`, `.playwright-mcp/`, `next-env.d.ts`, `package.json` och
   `session-logs/2026-09-30-session-log.md` hör inte till detta arbete; stage bara sessionens filer.
3. **Anton svarar: räcker hitta.se-numret för ringlistan utan namngiven VD?** (Örnbergs; tolkning av regel 15.)
4. **Anton svarar: ska Skicka nu respektera sändfönstret 08–16?**
5. **Anton svarar: autopilot och automatiska utskick i main, och hur många leads per dag?** I development
   bara körningarna, aldrig utskicken (spegeldatabas).
6. **Agenten, när disken tillåter:** rendera förloppspanelen, detaljvyn och kön och granska dem själv,
   plus a11y-audit på dem.
7. **Agenten:** `/simplify` på diffen; lägg upp bd-ärenden när Dolt finns (Eniro, Gemini-händelser).
8. **Anton:** besluta om Gemini 3 på Vertex global får användas för offentliga bolagsuppgifter
   (delmålet "Avgör dataskyddsfrågan om språkmodell-leverantören").
9. Kvar sedan tidigare: Processa om på de gamla listorna, skarp Iris-körning N=5, Antons release till main.

## 4. Fällor

- Disken: `next dev` + qmd-omindexering fyller C:. Kontrollera ledigt utrymme innan dev-servern startas.
- Hitta.se-svaret kan ge en mejldomän som pekar på den riktiga sajten bakom en parkerad domän; lita inte
  på registrets domän.
- Development-databasen speglar riktiga kunder: slå aldrig på utskick där.
- Arbetsträdet innehåller Antons/andras ocommittade filer; rör dem inte.

## 5. Antons instruktioner

Sessionens tidiga del komprimerades, så instruktionerna finns inte ordagrant kvar här. Hans beslut och
resonemang från dagen är nedskrivna i `docs/BESLUT.md`, och de två nya reglerna står ordagrant i
`CLAUDE.md` ("Varje funktion har ett sätt att följa flödet", "Varje nytt beslut skrivs i docs/BESLUT.md").
