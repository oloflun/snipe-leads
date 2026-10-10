# Handoff 2026-10-08 — CRM-flödet: översikt, utkast/skickat, massåtgärder, kontaktsökning, Samtal, Processa om, ett bolag på ett ställe

Antons beställning 2026-10-07/08. Plan: `plans/2026-10-08-crm-flode.md` (kopia av
`~/.claude/plans/pasted-content-id-f377-k-r-standup-steady-moonbeam.md`). Logg:
`session-logs/2026-10-08-session-log.md`.

## 1. Läget just nu, verifierat (2026-10-08 ~01:00)

| | Läge |
|---|---|
| git | `development` = `origin/development` = `e816bd8`. Inget opushat utom Antons 4 egna ocommittade filer (docs/utkast-*, next-env.d.ts, package.json, strategies.md) som aldrig rörs. |
| development | Kod `e816bd8` driftsatt (web 200, api `/health` ok). Migration 107 (min) och 108 (webbpoolen, andra sessionen) körda. |
| main | Orörd. Saknar 096–108. Release = PR development → main, Antons merge. |
| Utskick | 26 av Snajps utkast godkändes 2026-10-07 16:41–22:05 (efter sändfönstret) och skickas av `run_godkand_sandare` vardagar 08:00. `python scripts/utkast_status.py --env development` visar läget (bara antal). |
| Parallell session | "Webbplatsbedömning med Scrapegraph" byggde webbpoolen i SAMMA arbetsträd (commit `7d1b22a`). Den sätter Railway-variablerna WEBBPOOL_* i development efter pushen. |
| bd | Fungerar inte på maskinen (Dolt saknas) — spårningen ligger i planfilen. |

## 2. Vad som byggdes

| Del | Varför (Anton) | Commits | Kod |
|---|---|---|---|
| Hämta arbetsgrenen vid start, regel 12–17, hemlig webbbedömning | instruktion | `6f14465`, `b2ef388`, `ce86fb4` | CLAUDE.md, AGENTS.md, `scripts/grenstatus.sh` (SessionStart-hook) |
| Översikt = Aktivitet, Admin-översikt | "döp om" | `45eedbd` | `components/dashboard/StartView.tsx`, `AdminShell.tsx` |
| Utkast/Skickat som stämmer, väntande utkast = senaste icke-kasserade | "Utkast visar 0" | `d85917e` (migr. 107), `6884f45`, `8ec829b` | `app/leads/utkaststatus.py`, storage |
| Massåtgärder (skapa, skapa om, skicka, arkivera, ta bort, flytta till main) | beställt | `1e590e5`, `8ec829b` | `LeadsTabell.tsx`, `app/api/leads_massatgard.py` |
| Skickat → Inkorg › Skickat, svar flyttar, uppföljning som utkast | beställt | `ed26f0f`, `29c03db` | `IrisInkorg.tsx`, `scheduler.run_godkand_sandare` |
| Kontaktsökningen (w-domänbugg, VD-telefon avbröt, Om oss, cfemail, gissade sidor, eget sidtak) + fördelning Iris/ring/ej kval/prövas om | "300+ bortsorterade" | `aa701fb`, `1bd095b`, `29472fe`, `a52be5a` | `discovery.py`, `platshallare.py`, `sources/merinfo.fordela` |
| Leads › Samtal: ringlista + återkoppling med utfall | beställt | `e40d658`, `3331f6e`, `ed31791` | `app/leads/samtal.py`, `Samtalslista.tsx` |
| Ta bort lista, kopiera/flytta lista till kund (admin) | "flytta listor till andra kunder", "ta bort listor" | `29f4672`, `e9afe3e` | `app/api/admin_listor.py` |
| Ett bolag på ett ställe | "aldrig dubbletter" | `b4b29a3` (lagad i `7d1b22a`) | `create_prospect` (dubblettgrind + lås), `upptagna.samma_bolag`, `signal='flyttad'` |
| Processa om på listor | "uttrycklig funktion … se om de kvalificerar", sedan "en knapp" | `b4b29a3`/`7d1b22a` | `POST /leads/listor/{id}/omprova`, `app/leads/omprova.py` |

Verifiering: backend 3067 passed, rotinvarianter 477, `tsc` rent, `npm test` 172. Visuellt granskat själv
(375/1440) på `/forhandsvisning/samtal`, `/forhandsvisning/leads-skickat`, `/demo`; fynd rättade
(Samtal som kort på mobil, Iris-tabellen rullade i sidled → kolumnen Typ borttagen, dubbel Avmarkera).

## 3. Vad som återstår, i prioritetsordning

1. **Anton:** torrkörningen av `scripts/omklassa_listspar.py` blev klar för kund `kund-ea08b974`
   (236 rader → 35 Iris, 6 ring, 29 prövas om, 166 ej kvalificerade) men inte för Snajp (393 rader;
   avbröts när en låsande anslutning löstes). Enklare väg nu: **Processa om** i listvyn på varje gammal
   lista (berikar raderna, flyttar inget), sedan Flytta till Iris / Skriv utkast till alla med mejladress.
2. **Agent:** 166 "ej kvalificerade" hos kund-ea08b974 är bolag utan sajt, mejl och telefon i registrets
   cache — kontrollera ett stickprov att registerdatan verkligen saknar telefon (inte bara att cachen är tom).
3. **Anton:** release till main (migration 096–108 torrkörda först, sedan merge av PR development → main).
4. **Agent:** skarp Iris-körning N=5 i development och läs fördelningen i körningsraden.
5. **Andra sessionen/agent:** webbbedömningen är hemlig — grindad i API:t av den andra sessionen
   (`webbpool.far_se`); kontrollera även Iris-tabellens webbkolumn och lådan för kunder som inte är
   admin/Umeå Webdesign/Alunix.
6. Öppen fråga till Anton: säljlistan (Sebbes) och ringlistan är två samtalslistor — slå ihop?

## 4. Fällor

- **Två sessioner i samma arbetsträd:** committa aldrig delade filer med `git apply --unidiff-zero` av
  utplockade hunkar — de landar på fel rad när den andra sessionen ändrat filen (b4b29a3 blev
  oparsbar). Kör `ast.parse` på `git show HEAD:<fil>` före push, eller låt en session committa hela filen.
- **Migration före push** när koden skriver nya kolumner.
- **psycopg2 utan autocommit** håller lås under långa skript ("idle in transaction") — släpp
  transaktionen före långa nätverkssteg.
- Designspärren tillåter bara Write/Edit på UI-filer (inga python-/heredoc-skrivningar).
- Minnet: ~20 andra claude-processer; kör aldrig `next dev` och `tsc` samtidigt, kontrollera FreeVirtualMemory.

## 5. Antons instruktioner ordagrant

- "Kör /standup och läs den senaste versionen av development från github. Lägg in i projektinstruktionerna att ALLTID hämta den senaste versionen av arbetsbranchen från github vid start." (Resten av beställningen 2026-10-07 står ordagrant i planfilen och sessionsloggen.)
- "Obs, ta inte bort några befintliga listor, och lägg till en funktion för att kunna flytta/lägga till listor till andra kunder i systemet." / "Men gör det även möjligt för användaren att ta bort listor."
- "Säkerställ att omprocessningar av gamla listor eller Iris-leads aldrig genererar dubletter, varje bolag ska bara finnas på ett ställe i systemet."
- "Jag vill att du också skapar en uttrycklig funktion som processar om prospekten i en lista och försöker hämta alla uppgifter på nytt för att se om de kvalificerar till Iris."
- "Har den här 'research' någon funktion idag? Jag tänker faktiskt att det är lättare om det bara finns en knapp för Gör om research eller Processa om istället, sedan kan användaren flytta leadsen i listan till Iris eller skicka alla på en gång, till de som har fått mejladress."
- "En viktig sak: Webbplatsbedömningen är ett hemligt värde som bara är synligt för Admin, Umeå Webdesign och Alunix i det här läget."
- "Innan du pushar, koordinera med den andra sessionen så ingenting krockar och allt går ihop fint."
- "När du är klar, kör conclude och se till att hemliga värdet om webbplatsbedömningen antecknas som regel så det inte exponeras av misstag."
