# Gemensamt för alla gränssnittsbyggare i Snajp CRM, fas 4 och 5 (läs först, hela)

Arbetskatalog: `C:\Users\Anton L\snipe-leads\.claude\worktrees\snajp-crm-dd0d83` (git-worktree, gren
`claude/snajp-crm-dd0d83`). Next.js 16 med Astryx som komponentbibliotek. Backend är FastAPI under
`snajp-support/` och rörs inte av dig.

## Uppdraget

Antons beställning: hela den befintliga appen (arbetsytan under `/dashboard`, inställningarna, adminytan)
ska finnas i det nya gränssnittet under `/crm`, med ALL funktionalitet kvar, utan att dagens app rörs.
Du bygger ETT steg av det. Måttet är funktionslistan `docs/crm/MIGRERING-FUNKTIONSLISTA.md`: varje rad som
hör till ditt steg ska vara byggd, eller redovisad som inte byggd med skälet.

**Så läser du in dig, i den här ordningen:**

1. `docs/crm/DESIGN-CRM.md`, hela. Formen är låst av Anton. Du bygger ur den, inte bredvid den.
2. Verktygslådan och mönstervyerna, hela filerna: `components/crm/app/kit.tsx`, `Sida.tsx`, `CrmRam.tsx`,
   `BolagVy.tsx`, `BolagPanel.tsx`, `BolagFormular.tsx`, `SparrarVy.tsx` (det senaste exemplet på en
   listvy med dialoger, förlopp och utfall), `UppgifterVy.tsx`, `Tidslinje.tsx`, `crm.css`, `crm-vyer.css`,
   och `lib/crm/api.ts`, `lib/crm/felkoder.ts`.
3. Radernas beskrivning: funktionslistans rader för ditt steg (ID:n står i din beställning), och SAMMA
   ID:n i läsarens underlag under `docs/crm/underlag/app-0N-*.md` (prefixet säger filen: SK app-01,
   OV app-02, LR app-03, LK app-04, LU app-05, SU app-06, KV app-07, IN app-08, AD app-09, AP app-10).
   Underlaget beskriver beteendet rad för rad: gränser, felmeddelanden, tomlägen, roll, förlopp.
4. Dagens komponent för samma sak (din beställning pekar ut den). Den är FACIT FÖR BETEENDET: vilka anrop
   som görs, i vilken ordning, vad som visas när. Den är INTE facit för formen: kopiera aldrig dess
   markup, klasser eller komponenter.

## Gränser

- Du skriver bara i: `app/crm/**`, `components/crm/app/**`, `lib/crm/**`, `app/forhandsvisning/crm/**`
  och `docs/crm/bilder/fas4/` (bilder). Rör ALDRIG dagens app (`components/leads/`, `components/snajp/`,
  `components/settings/`, `components/admin/`, `app/dashboard/`, `app/settings/`, `app/admin/`, `lib/leads/`,
  `lib/data/`), backend (`snajp-support/`), `db/`, `docs/BESLUT.md`, `docs/crm/STATUS-MIGRERING.md`,
  `docs/crm/MIGRERING-FUNKTIONSLISTA.md`, `docs/crm/DESIGN-CRM.md`, `AGENTS.md` eller `CLAUDE.md`.
  Ren logik utan gränssnitt ur `lib/leads/` (tolkning av importfiler, sidindelning, etiketter) får
  IMPORTERAS, inte kopieras.
- **En backend, ett API.** Det nya gränssnittet anropar SAMMA ändpunkter som dagens, genom
  `/api/snajp-support/...` (proxyn bär kundens nyckel, märker kundbesök som test och stoppar läsrollens
  skrivningar). Affärslogik kopieras aldrig till klienten. Saknas en ändpunkt: bygg inte runt det, skriv
  det i rapporten under `saknas_i_backend`.
- **Pusha aldrig.** Inga grenar, inga worktrees, ingen rebase, ingen reset, ingen stash.
- **Commit:** bara dina egna filer, med sökvägarna utskrivna: `git add <filer>` och
  `git commit -F <meddelandefil> -- <filer>`. Aldrig `git add -A`, aldrig `git commit -a`. Skriv
  meddelandet i en fil med Write (heredoc fungerar inte här). Avsluta med raden
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `AGENTS.md` är redan ändrad av någon annan:
  rör den inte och committa den inte.
- Installera ingenting. Kör aldrig `next build`. `.next` är en länk till D: och får inte tas bort.

## Formen (DESIGN-CRM.md gäller, det här är det som oftast går fel)

- **Bara Astryx-komponenter och verktygslådan.** Ingen egen knapp, ingen egen dialog, ingen egen tabell.
  Behöver du ett mönster som inte finns (din beställning säger vilka som är NYA MÖNSTER), bygg det EN gång
  i `components/crm/app/` i samma form (radier, chips, piller, tokens) och skriv en kort kommentar om
  vad det är till för, så att nästa byggare återanvänder det.
- **Inga färger utanför tokens.** Inga hex, ingen `rgb()`, ingen ny `oklch()` med egna tal. Använd de
  befintliga klasserna (`text-ink`, `text-ink2`, `text-ink-muted`, `text-danger`, `crm-ton-*`, `crm-chip`,
  `crm-kallkort`, `crm-raknefot`, `crm-tabell` med flera) och variablerna i `crm.css`.
- **INV-UI-001:** ingen kicker, inga versaler som etikett, ingen spärrad text, ingen kursiv rubrik, inget
  tankstreck (—) i text. Rubriken i Fraunces står bara i sidhuvudet (`Sida`).
- **En ny funktion byggs in i den befintliga ytan, aldrig ovanpå den** (CLAUDE.md). Ingen ny ruta, rad tal
  eller panel bara för att funktionen är ny. Två tal som säger nästan samma sak på samma sida är fel.
- **Listvyn** är `Sida` med sidhuvud (objektikon, rubrik, antal, primär handling), vyrad (`Vyval`, sök),
  tabell på bred skärm och rader på telefon (`useSmal`), räknefot, tomlägen med väg vidare.
- **Posten** öppnas i en panel från höger (`BolagPanel` är förebilden) med `?<nyckel>=<id>` i adressen.
- **Formulär** är dialoger med fältfel vid rätt fält (`BolagFormular` är förebilden).
- Fokus: när en rad lämnar en lista, använd `grannfokus` ur kit. Dialoger stängs inte medan de sparar.
  Utfall och fel sägs upp i en region som finns hela tiden (`role="status"` som bara byter text).

## Reglerna (CLAUDE.md gäller i sin helhet, det här är det som oftast går fel)

- **Tvåspråkigt, utan undantag.** Varje synlig text, `aria-label`, tomläge, felmeddelande och besked genom
  `lib/i18n.tsx`: `const { text } = useLocale()` och `text({ sv: "…", en: "…" })` i EXAKT den
  bokstavsformen (INV-COPY-001 fäller svenska bokstäver utan sitt par, och fäller ternärer eller
  funktionsanrop inuti `sv:`). Ental och flertal på båda språken ("1 rad", "2 rader").
- **Förlopp och utfall där handlingen startades**, och utfallet ska finnas kvar efter en omladdning. Det
  mesta bär backenden redan (körningar, jobb): läs hur dagens vy pollar och visa samma förlopp.
- **Webbplatsbedömningen är hemlig** (webbrevision, webbnivå, betyg, brister, platshållarskäl, webbpoolens
  listor, `lan`). Det nya gränssnittet räknar ALDRIG ut den och visar en kolumn, ett filter, en
  sortering, en flik eller en tooltip om den BARA när svaret från backenden bär fälten. Saknas fältet
  finns inget val att visa. Läs funktionslistans avsnitt "Sekretess" innan du bygger en vy som rör leads
  eller listor.
- **Läsrollen** (`arLasare` i `useDashboard()`): skrivande knappar stängs av med en förklaring, anropet
  ska inte få falla på 403. **Kundbesök** (`impersonation`): gå aldrig förbi proxyn.
- **Leadsreglerna** i CLAUDE.md ("Leads: källor, filter och kontakter") beskriver vad backenden gör.
  Gränssnittet visar det backenden svarar och lägger inte till egna regler.
- Text säger **supportagent**, aldrig supportbot. Namn på agenterna: Iris (leads), Jev.
- Inga riktiga bolag, personer eller adresser i exempeldata: domänen `.test`, telefonserien
  070-174 06 xx, namn som "Exempelbolaget AB", "Kim Exempel".

## Förhandsvisningen (krav: varje ny yta ska gå att se utan inloggning och utan databas)

`app/forhandsvisning/crm/Forhandsvisning.tsx` fångar `fetch` i webbläsaren och svarar med påhittad data.
I dag fångar den `/api/snajp-support/crm` och `/api/snajp-support/hjalp`.

- Lägg dina svar i EGNA filer under `app/forhandsvisning/crm/svar/<omrade>.ts`, en funktion
  `(url: URL, init?: RequestInit) => Promise<Response> | null` som svarar på de vägar din vy anropar och
  `null` för allt annat. Koppla in den med EN rad i `fangaAnrop`. Bygg inte in svaren i den stora filen.
- Svaren ska ha EXAKT backendens form: läs ändpunkten i `snajp-support/app/api/` och svara likadant.
  Skrivningar ska ändra den påhittade datan, så att flödet går att följa (skapa, ändra, ta bort, ångra).
- Vyn ska gå att öppna på `/forhandsvisning/crm/<vyns väg>` (läs `[[...vy]]/page.tsx`: den tar i dag
  bara första segmentet, utöka den så att `iris/leads` och liknande fungerar).

## Kontroller som ska vara gröna innan du committar

1. Avgränsad typkontroll (maskinen har lite minne: kör ALDRIG full `tsc`). Skriv filen
   `tsconfig.crm.json` i repo-roten med innehållet
   `{ "extends": "./tsconfig.json", "compilerOptions": { "noEmit": true, "incremental": false }, "include": ["next-env.d.ts", "app/crm/**/*.tsx", "app/forhandsvisning/crm/**/*.tsx", "app/forhandsvisning/crm/**/*.ts", "app/api/snajp-support/crm/**/*.ts", "components/crm/app/**/*.tsx", "components/crm/app/**/*.ts", "lib/crm/**/*.ts"] }`,
   kör `NODE_OPTIONS=--max-old-space-size=2560 node node_modules/typescript/bin/tsc -p tsconfig.crm.json`
   (Bash) och TA BORT filen efteråt. Noll fel.
2. Från repo-roten: `python -m pytest tests/invariants -q -p no:cacheprovider`. Noll fel.

## Bilderna (du tar dem, orkestratören bedömer dem)

Orkestratören gör den slutliga visuella bedömningen, men du ska ha sett din egen yta och rättat det
uppenbara (text som kapas, överlapp, vågrät rullning på telefon, tomma ytor, fel i mörkt läge).

1. Kontrollera ledigt minne i PowerShell: `(Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory/1024`
   ska vara över 4000 (MB). Under det: ta inga bilder, skriv det i rapporten.
2. Kontrollera att port 3111 är ledig (`Get-NetTCPConnection -LocalPort 3111 -State Listen`). Starta EN
   server i bakgrunden: `NODE_OPTIONS=--max-old-space-size=3072 npx next dev -p 3111` (Bash,
   `run_in_background`). Vänta med
   `curl -s -o /dev/null -w "%{http_code}" --retry 40 --retry-delay 3 --retry-connrefused --max-time 240 http://localhost:3111/forhandsvisning/crm/<vy>`.
3. Ta bilderna med Playwright-verktyget (`mcp__plugin_playwright_playwright__browser_run_code_unsafe`,
   ladda det med ToolSearch om det inte är laddat): `page.setViewportSize`, `page.goto`,
   `page.addStyleTag({ content: "nextjs-portal{display:none!important}" })`, `page.screenshot({ path })`.
   Mörkt läge: cookien `snajp.tema=morkt` på `http://localhost:3111`. Storlekar: 1440x900 ljust, 1440x900
   mörkt, 390x844 ljust. Varje vy, varje panel, varje dialog, tomläge och fel där det finns.
   Spara som `docs/crm/bilder/fas4/<steg>-<vad>-<1440|1440-morkt|390>.png`. En Astryx-dialog är
   `dialog[open]`, inte `[role=dialog]`.
4. Läs dina bilder med Read och rätta det du ser. Ta om bilderna efter rättningen.
5. STÄNG servern: stoppa bakgrundsjobbet, och döda det som lyssnar på port 3111 i PowerShell
   (`Get-NetTCPConnection -LocalPort 3111 -State Listen | % { Stop-Process -Id $_.OwningProcess -Force }`).
   Kör `git checkout -- next-env.d.ts`. En kvarlämnad server fäller nästa byggare.

Går Playwright-verktyget inte att nå: skriv det i rapporten, committa ändå om kontrollerna är gröna, och
säg vilka adresser orkestratören ska titta på.

## Rapporten

Svara med: commitens hash, filerna, vilka rad-ID:n som är BYGGDA (och var: fil och komponent), vilka som
INTE är byggda med skälet rad för rad, vilka ändpunkter vyn anropar, vad som saknas i backenden, vilka
kontroller du körde med utfall i siffror, bildernas filnamn, och allt du inte kunde verifiera. En lucka
du redovisar är bättre än en du döljer: säg aldrig "klart" om en rad som saknas.

## Lärdomar ur stegen 4.1 till 4.4 (orkestratorns bildgranskning: gör rätt från början)

- **Besluten för en post står i panelens fot, aldrig under vecket.** Godkänn, Spara, Avvisa och liknande
  ska synas utan att man rullar. `Utkastredigerare` har propen `fot` (ett element i panelens
  `LayoutFooter`), se `UtkastPanel.tsx`. Verktyg för innehållet får stå vid innehållet.
- **Tabellen ryms i bladet i 1440, och ingenting kapas där det finns plats.** Mät efter bygget:
  tabellens `scrollWidth` ska vara lika med förälderns `clientWidth` (1165 px i 1440), och ingen cell
  får visa "…" medan en annan kolumn har tomrum. Kolumnen med namn eller fri text är proportionell,
  kolumner med känt innehåll (datum, status, tal) har fast bredd som rymmer det längsta värdet på båda
  språken. En etikett bredvid ett värde (Test, Påfyllt) får `shrink-0`.
- **Två fält i bredd står på samma höjd.** Har bara det ena en förklaring står förklaringen under raden,
  inte mellan etiketten och fältet.
- **Vyraden ryms på en rad i 1440.** Sällan använda vyer läggs under Fler (se `LeadsVy.tsx`).
- **Ta bild på läsroll (`?roll=lasare`) och kundbesök (`?besok=1`) för varje ny vy.** De har hittills
  bara byggts, inte setts.
- **Återanvänd det som finns under `components/crm/app/iris/`:** `Utkastredigerare`, `UtkastPanel`,
  `Mejlvisning`, `Mejlsvans`, `StrukturVal`, `Bekraftelse`, `LeadPanel`, och logiken i `lib/crm/iris/`
  (`anrop`, `lead`, `utkast`, `korning`, `mejl`, `webb`).
- **Disken C: är nästan full (omkring 0,6 GB).** Skriv ingenting utöver koden och bilderna du behöver:
  inga loggdumpar, inga kopior av filer, inga hjälpfiler i repot. Högst omkring 25 bilder per steg.
  Faller ett kommando på "No space left on device": stanna, stäng servern och skriv det i rapporten.
- Invarianterna är i dag 769 gröna och 89 överhoppade.
