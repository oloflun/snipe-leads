# Handoff 2026-10-18 — Landningssidan: dygnsljus, rörelse, isärtagen översikt

## 1. Läget just nu, verifierat
- Git: gren `development`, senaste commit `19860d9` (merge av origin/development). **Allt arbete nedan är ocommittat och opushat** (Anton: "pusha inget"). Ocommittade filer som INTE är mina: `docs/utkast-merinfo-api-forfragan.md`, `next-env.d.ts`, `package.json`, `strategies.md`, `docs/utkast-allabolag-api-forfragan.md`, `session-logs/2026-09-30-session-log.md`, `.playwright-mcp/`, `gsap.js`, `smooth-scroll.js` (de två senare fanns otrackade före sessionen; `smooth-scroll.js` ändrades av mig, se nedan).
- Inget deployat, inga migrationer, inga env-ändringar.
- Lokalt: dev-servern `web` (preview, port 3005) kör; boardservern `serve_board.py` på 4620 kör. Använd `http://localhost:3005/`, inte 127.0.0.1 (Next dev blockerar andra ursprung, då laddar rörelsen inte).
- Maskinen: commit-minne ~1,2 GB ledigt med dev-servern igång, disk C ~2 GB fritt (jag tog bort Turbopack-cachen 509 MB och npx-cachen 55 MB, båda byggs om av sig själva). `~/.claude/projects` är 5 GB, npm-cachen 587 MB: Antons beslut.
- Fyra Claude-sessioner arkiverades på Antons begäran (allt utom senaste i warehouse-handy); OneDrive och ChatGPT stängdes.

## 2. Vad som byggdes
Antons beställning: utgå från nuvarande startsida, behåll hjälte, bilder, sektioner, Leads/Support-uppdelning och de konstruerade showcase-ytorna; lägg till Dygnets dygnsljus (soluppgång → varmvitt), mjuka övergångar mellan alla sektioner, en isärtagen dashboardbild utan lutning, "Varför Snajp finns"-texten under "Byggt i Göteborg", fetare serif (inte Fraunces).

- `components/marketing/useLandingMotion.ts` (ny): GSAP 3.15 + Lenis via repots `gsap.js`/`smooth-scroll.js`, dynamiskt importerade. Dörr, ljusmotor (mark + fyra ljusrutor), idempotenta avslöjanden (`arm`/`play`, `data-rv="1"`; ScrollTrigger + IntersectionObserver + timer), radmaskade rubriker, ord som fylls i uttalandet, parallax, ritade sektionslinjer, showcase-liv (`data-sc`, `data-drift`), sprängskissen som keyframe-motor med linjer och förklaringar.
- `components/marketing/DashboardIsar.tsx` (ny): översikten (`public/produkt/oversikt*.webp`, demo-exempeldata) i fyra delar ur samma bild, förblurrad tvilling, text till höger med tre förklaringar och SVG-linjer.
- `LandingPhoto.tsx`: `data-mo`-markörer, `key` per produkt+språk på spaltade rubriker, mark- och ljuslager, inline-skript för dörren, Varför Snajp-styckena, Lenis-scrollTo.
- `UspSection`, `PricingSection`, `AgentResultat`, `ProduktBilder`: markörer, ingen egen grund (dygnet äger marken).
- `copy.ts`: `varforSnajp` (sv+en), läses även av `app/vart-team/page.tsx`.
- `lib/fonts.ts` + `globals.css`: Source Serif 4 via `.serif-fet` (bara marknadssidan; appen har Fraunces kvar).
- `gsap.d.ts`, `smooth-scroll.d.ts` (nya): typer för JS-modulerna. `smooth-scroll.js`: återanvänder `window.__lenis` vid hot reload.
- `koncept/_delat/board.json` + `koncept/index.html`: flik "Sidan (live)" som visar localhost:3005. `shoot.py`/`motion_sheet.py`: `--url`.
- `docs/BESLUT.md`: beslutet med två rättningsvarv.

Verifierat (riktig Chromium 1920, hjulskroll): 0 dolda element hela vägen ned, bildrutor p95 17 ms (var 50 ms, 31 % tappade; orsak multiply-blend på helskärmslagret), inga överflöden 320–1440, produkt-/språkväxel och tangentbord utan fel, `tsc` grön, impeccable-detektor 0 fynd.

## 3. Vad som återstår, i prioritetsordning
1. **Antons visuella dom** på `http://localhost:3005/` (Ctrl+F5). Han var missnöjd två gånger; inget svar efter tredje varvet än.
2. **Ny copy att godkänna (Anton):** sprängskissen "Hela dagen på *en skärm*." + ingress + förklaringarna "Nyckeltalen", "Pågår just nu", "Iris, leadsagenten" (`DashboardIsar.tsx`).
3. **Serif-valet (Anton):** Source Serif 4 är agentens val; vikten 600 kan behöva bli 700.
4. **Commit (bara med Antons ja)** av de egna filerna, inte hans ocommittade filer.
5. Demo-ytans inre skrollytor kan behöva `data-lenis-prevent` (ej observerat).
6. Koncept-runda 3 (06–10) ligger halvfärdig och är avstannad på Antons "Stopp".

## 4. Fällor
- `127.0.0.1:3005` laddar inte rörelsen i dev (cross-origin-blockering); använd `localhost`.
- `mix-blend-mode: multiply` på ett fast helskärmslager halverar bildfrekvensen. Ljuset ligger under innehållet med vanlig alfa nu.
- SplitText kollapsar NBSP; tankstreck binds via `wordDelimiter` (ORDSKILJE).
- En klass på `<html>` från inline-skript ger hydreringsvarning; dörren använder `<style id="door-armed">`.
- Disken fylls av Turbopack-cachen (`.next/dev/cache`, ~500 MB) och skärmbilder; skriv JPEG.
- Mätloopar med Lenis: räkna på `__lenis.targetScroll`, inte `scrollY`.

## 5. Antons instruktioner ordagrant
- "Jag vill att du utgår helt ifrån den nuvarande Snajp- sidan behåll den nuvarnde heron och bilderna, lägg endast till nya som passar in i temat och så vill jag att du lägger till den dynamiska dygns-bakgrunden från nr 1, som ska börja med soluppgång och matcha heron, för att sedan bli varmvit längst ned. Skapa vackra övergångar och effekter mellan alla sektioner, behåll alla nuvarande  och uppdelningen mellan support och leads, behåll även de konstruerade "dashboard"- showcasen och visa även någon enstaka dynamisk bild av dashboarden med uppdelning av elementen likt Isärtagning, men utan lutning, gör allt detta mjukt. Lägg även till texten från sektionen Varför Snajp i /vart-team (inte rubriken ), under Byggt i Göteborg.  Anpassa typsnittet på sidan till en till en fetare Serif , men som inte är Fraunces"
- "Jag ser ingen skillnad i boarden"
- "Ja, gör vad som krävs utan att ta bort något. Avsluta alla Claude-sessioner, utom den senaste i warehouse-handy"
- "Skapa animationer för showcase- rutorna och fixa att dashboarden vibrerar och hackar och hoppar åt sidan, lägg även till någon text där, nu ligger den tomt." / "Nu är bakgrunden helt borta, det såg bättre ut innan"
- "Det ser fortfarande för jävligt ut, och de konstruerade showcase-rutorna är helt osynliga och rör sig inte ett dugg, de ska inte tonas, de ska röra på sig mjukt med den beskrivande texten som dyker upp till den, och dashboarden hackar fortfarande på samma sätt och det finns ingen tydlighet, det känns inte intentionellt. Jag vill att du fixar detta till en mycket högre visuell produktions- nivå, det här håller inte, gör vad som krävs för att kunna verifiera detta visuellt, du får inte sluta förrän det nått den högsta nivå av det du hittills producerat med ALLT polerat in i minsta detalj."
- "Kör /conclude, pusha inget"
