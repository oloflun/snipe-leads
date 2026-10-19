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
