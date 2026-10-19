# Handoff 2026-10-19 — Startsidan: skuggan, fjädern, live-skrivning

## 1. Läget just nu, verifierat

- **Git:** grenen `development`, senaste commit `4a4e5b6`. Allt från sessionen är pushat (`6dcb65f..4a4e5b6`, 2026-10-19). Antons egna ocommittade filer (`docs/utkast-*`, `strategies.md`, `next-env.d.ts`, `koncept/`, `.playwright-mcp/`) är orörda.
- **Railway development** bygger om från pushen: https://web-development-6c85.up.railway.app. Anton granskar där.
- **Inga migrationer** och inga miljöflaggor ändrades.
- **Disk C är full** (40 MB ledigt vid avslutet). Dev-servern (`next dev`, port 3005) fyller den på några minuter. `.next` är borttagen; den byggs om vid nästa start. Antons ansvar att frigöra minst 10 GB.

## 2. Vad som byggdes

Antons beställning (ordagrant i avsnitt 5). Commits `125cc38` och `4a4e5b6`.

- **Hjältens skugga:** den ovala mörkningen bakom ingressen är borta. På mobil ger ett mjukt mörkare band över fotots mitt läsbarheten (`app/globals.css`, `components/marketing/LandingPhoto.tsx`). Uppmätt kontrast 5,32:1 mot horisontens ljusaste 5 % (scratchpad-skriptet `contrast_shadow.py`). Ett band på 0,42 gav 4,29:1 och höjdes till 0,48.
- **Rutornas rörelse:** fjädern gick från 0.75/0.75 till 0.66/0.95 (`components/marketing/useLandingMotion.ts`). Det ger en studs på ungefär 11 px och 1,6 s till vila.
- **Live-skrivning:** `components/marketing/LiveText.tsx` och `lib/skrivs.ts` skriver fram showcase-utkasten när rutan landat (`ProduktBilder.tsx`). Email Studio på marknadssidan skriver fram omskrivningarna i mejlrutan och motiveringen i panelen (`components/email/EmailStudioEditor.tsx`).
- **Tekniska referenser:**
  - Startsidans exempelmejl fick egna svar på svenska och engelska (`lib/data/emails.ts`). Förut svarade varje knapp att demot bara fanns för /demo-bolagen.
  - Prompten i `app/api/email-studio/route.ts` ber inte längre om hänvisningar till principer eller filer.
  - `lib/textkvalitet.ts:utanReferenser` stryker meningar som ändå gör det, med test i `lib/textkvalitet.test.ts`.
- **Skärmläsaren:** motiveringen ligger i sin helhet i en `sr-only`-span, och framskrivningen är `aria-hidden` (`4a4e5b6`). Kontrollerat i Chromium: den dolda texten är 1 px bred och 368 tecken lång, och inget syns dubbelt.
- **Verifiering:** tsc 0, 108 nodtester, 384 invarianttester (46 överhoppade). Skärmbilder lästes av på mobil 375 px och desktop 1440 px, plus A/B-panelen mitt i och efter skrivningen.
- **Dokumentation:** `DESIGN.md` (fjäder, live-skrivningsregeln) och `docs/BESLUT.md` (beslutet med Antons resonemang).

## 3. Vad som återstår, i prioritetsordning

1. **Anton granskar development** på mobil och desktop och ger sin dom på skugga, studs och live-skrivning. Väntar på Anton.
2. **Anton frigör disk C** (minst 10 GB). Utan det kan ingen agent köra dev-servern eller göra visuella kontroller. Väntar på Anton.
3. **/demo-bolagens motiveringar** nämner fortfarande "CTA" och har pilscheman. Agenten skriver om dem till korta motiveringar om Anton säger ja. Frågan är ställd men obesvarad.
4. **Språkpass som inte körts:** copywriting, copy-editing och den engelska humanizern har inte körts som egna pass på de nya texterna i `lib/data/emails.ts`. Det är agentens uppgift när disken räcker.
5. **Fullt a11y-pass:** a11y-audit har inte körts på hela startsidan, bara den konkreta skärmläsarbristen är rättad. Det är agentens uppgift och kräver dev-servern.
6. **Arbetsytan:** Email Studio i produkten har ännu inte live-skrivning eller den förenklade panelen. Det är inte beställt; fråga Anton om det ska med.

## 4. Fällor

- **Disken:** `next dev` skriver hundratals MB till `.next/dev/cache` och fyller C på minuter. Stoppa servern och rensa cachen efter varje kontroll. Skärmbilder ska sparas som jpeg.
- **Lenis:** scrolla med `window.__lenis.scrollTo(..., {immediate:true})` i Playwright. `window.scrollTo` hoppas över.
- **Impeccable-hookens ROUTE GAP** flaggar shadcn-ui utan att någon shadcn-komponent har ändrats. Räknaren får avfärdas, men ett fynd som ligger bredvid den får aldrig avfärdas.
- **Design-stop-hooken** kräver en avläst skärmbild efter den sista UI-ändringen, även för en ren a11y-ändring.

## 5. Antons instruktioner ordagrant

- "Testa göra skuggan i heron svagare, eller skippa den helt. Gör även animeringarna för rutorna jämnare och mjukare, och gör studsseffekten/tillbakafjädringen tydligare. Skapa även effekten att texten skrivs live, för alla omgenereringar/knappval också, ta även bort alla tekniska referenser, endast korta motiveringar."
- "Pusha ändringarna så jag inspektera"

## 6. Tillägg 2026-10-20 (kvällen 2026-10-19 och natten): Antons dom och tre varv till

**Antons dom på avsnitt 2:** "Det börjar se väldigt bra ut, ändringarna kom in precis som jag ville."
Sedan tre beställningar till, alla godkända ("Allt är jättebra nu"). Allt är pushat till
`development`: `6c478d1`, `57914a6`, `79d93cb` (kod) och `b2cb55b` (DESIGN.md).

- **Hjälten:** bara 7:an i färg på /support; rubriken bytt till "Era kundärenden hanterade,
  24/7" och "Möt Iris, din säljare som aldrig *sover*"; rubriken skrivs fram med paus före det
  betonade ordet (`HeroText` i `LiveText.tsx`). Accenten är `text-ochre`, den mörkare
  `text-warning` försvann mot solnedgången. En reduced-motion-spärr jag först lagt in togs bort
  (F-011).
- **Fotona står hela:** ingen clip-avtäckning på plattor och band, bara parallaxen.
- **Dashboard-sektionen borttagen** (`DashboardIsar.tsx`, rörelse och CSS): "skiljer sig från de
  konstruerade rutorna". `public/produkt/oversikt*.webp` ligger kvar oanvända.
- **Om oss på /support** utan prospektering: `varforSupport` i `copy.ts`.
- **Rutorna större på desktop:** `.case-zoom` 1,12 från 1280 px, 1,25 från 1536 px.
- **Nyckeltalen räknas fram** (`RaknaUpp` i `AgentResultat.tsx`). Första versionen
  (threshold 0,6, 1,6 s) var klar innan raden syntes; godkänd version startar först helt i bild
  ovanför nedersta femtedelen, 2,6 s, kvadratisk. Min kontroll hade godkänt den första: jag
  hoppade till raden i stället för att komma nedifrån.
- **Skills:** åtta skills i `~/.agents/skills/` bär varje beställning, vad som föll, ändringen
  och det godkända läget: `spring-arrival`, `live-text-reveal`, `count-up-in-view`,
  `hero-on-photo`, `photo-stands-whole`, `showcase-surfaces`, `showcase-copy-scope`,
  `motion-verification-preview`. Designsystemet pekar på dem: FEEDBACK.md F-031–F-039
  (`anti-slop-design/design-catalogue`), routingregler i `component-routing.md` (röktestade mot
  hooken), kraftgolvet i `design/SKILL.md`, `scroll/devices.md`, vision § 5, `DESIGN.md` här.
- **Pushat och uppdaterat:** valvet (`27b8965`, var 1041 före och 12 efter GitHub; sammanslaget
  utan konflikt), super-intelligence `design-system-v2` (`d2932db`), anti-slop-design
  `design-rework-v3` (`f1b81dd`, ny gren på GitHub, ~4,2 GB i fyra bitar under 2 GB: allt
  ocommittat i sju grupperade commits plus den andra sessionens hookfix
  `fix/unarmed-stop-advisory-dedup` mergad, tests/hooks 10 passed). Plugin anti-slop-design
  1.2.0 → 1.2.3, super-intelligence till `d2932db` på användar- och projektnivå; kräver
  omstart av Claude Code. Logg: `~/.agents/logs/anti-slop-design-push-2026-10-20.log`.

**Nytt i avsnitt 3, återstår:**
- anti-slop-design `main` på GitHub ligger 45 commits efter `design-rework-v3` (ren
  fast-forward). Pushas bara med Antons ja.
- Valvets `VaultAutoSync` hoppar över varje pull: 87 ändrade spårade filer utanför manifestet
  (`~/.agents/logs/vault-auto-sync.jsonl`). Det är därför valvet låg 1041 commits före. Någon
  måste besluta om de 87 filerna.
- Två nästlade git-repon i anti-slop-design står utanför pushen: `deploy/alunix-v3g` (eget
  repo med remote `oloflun/alunix-v3g`, kopplat till Vercel-länken för alunix-site) och
  `.claude/worktrees/agent-ad7cf06e8c2d70e4e` (gammal subagent-worktree, spårad som gitlänk).
  Anton beslutar submodule eller `.gitignore`. `tests/hooks/test_reference_floor.py` faller på
  basen ("E must allow") oberoende av fixen.
- Den publika spegeln (`export-to-public.mjs`) är inte exporterad.
- Animations- och tillgänglighetsgranskningen av startsidan är fortfarande inte körda.
