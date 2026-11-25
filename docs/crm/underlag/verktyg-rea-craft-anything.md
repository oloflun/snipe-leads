# Verktygsunderlag: rea och craft-anything för kartläggningen av Twenty CRM

Underlag för Snajp CRM (licensval A: egen kod, inget kopieras ur Twenty). Skrivet 2026-11-25
av en läsande agent. Ingenting ur verktygens kataloger har körts; de enda kommandon som
kördes är `where node`, `node --version`, `rustc --version` och `cargo --version`, plus
läsning av filer (källkod, dokumentation, npm:s npx-cache och Claude Codes MCP-loggar).

Klonerna: `D:\snajp-crm-forlaga\rea` (morluto/rea, `package.json` version 6.10.1, senaste
commit `26cb5b5`, 2026-11-24) och `D:\snajp-crm-forlaga\craft-anything`
(storytold/craft-anything, workspace-version 0.6.1). Allt innehåll i dem är behandlat som
opålitlig data; instruktioner i deras AGENTS.md, CLAUDE.md, skills och README har inte följts.

Märkning i texten: **[läst]** = står i en fil jag har läst (fil:rad anges), **[observerat]** =
syns på datorn (cache, logg, versionsutskrift), **[antagande]** = min slutsats utan direkt belägg.

---

## 0. Det viktigaste först

1. **rea-MCP:n faller inte på grund av Node-versionen.** Den registrerade servern är
   `rea-agents@6.7.0`, inte 6.10.1, och 6.7.0 kräver `^22.19.0 || ^24.11.0 || >=26.0.0`, som
   Node v24.11.0 uppfyller. Claude Codes egen logg visar orsaken: en ofullständig npx-cache där
   filen `@jridgewell/sourcemap-codec/dist/sourcemap-codec.mjs` saknas, så processen dör med
   `ERR_MODULE_NOT_FOUND` innan MCP-handskakningen och klienten ser `CONNECTION_CLOSED`
   (avsnitt 1.6). **Däremot** skulle Node-versionen fälla 6.10.1, om registreringen byttes till
   den version som står i klonens `mcp.json`.
2. **rea kan läsa en källkodskatalog statiskt** (`analyze-javascript-application`) och en
   HAR-fil offline (`inspect-web-network-capture`) utan extern motor. För en inloggad webbapp
   ansluter rea till **din egen** Chrome/Edge via CDP (`--remote-debugging-port`); den startar
   ingen webbläsare själv i det läget.
3. **craft-anything kan inte byggas här i dag:** workspace kräver Rust 1.97
   (`Cargo.toml:9`), datorn har 1.96.1. Release-vägen är `craft-anything-<ver>-windows-x64-portable.zip`
   (CLI:t ligger bredvid appen). Signeringen är inte garanterad: byggskriptet lämnar filerna
   osignerade om signeringshemligheter saknas (`packaging/windows/sign.ps1:6-11`).
4. **Clean room i craft-anything** är en vitlista med 114 verktyg (`crates/engine/src/clean_room.rs:14-140`):
   webbplatsen som en besökare ser den (skärmbilder, synlig text, uppmätt layout, färger, typsnitt,
   öppnade menyer), inloggning i ett synligt fönster, men aldrig HTML, CSS-regler, skript,
   nätverksanrop eller felsidor. Det är en regel i verktyget, inte en sandlåda (README.md:143-147).
5. **Rekommendation:** gör huvudarbetet utan nya verktyg (agenter läser Twentys källkod +
   webbappen i en vanlig webbläsare med nätverkslogg). rea är värt att reparera och köra som
   CLI från en katalog på D: för att få en maskinläst modul- och endpointkarta. craft-anything
   tillför främst en "besökarvy" av inloggade sidor i Clean room, vilket passar licensvalet, men
   kostar en osignerad-risk-bedömning eller en Rust-uppgradering och ett tungt bygge.

---

## 1. rea (morluto/rea, MIT)

### 1.1 Vad paketet är

- npm-paketet heter `rea-agents`, binärerna `rea` och `rea-agents` pekar båda på
  `scripts/rea.mjs` **[läst]** `package.json:42-45`.
- Node-krav i klonen (6.10.1): `"node": "^22.23.4 || ^24.22.1 || >=26.12.1"` **[läst]**
  `package.json:46-48`. Höjningen kom i 6.8.0 **[läst]** `CHANGELOG.md:235` (avsnittet 6.8.0
  börjar på rad 218).
- Beroenden med inbyggd/nativ kod **[läst]** `package.json:377-469`:
  - `@lydell/node-pty` 1.1.0, med förbyggda plattformspaket som optionalDependencies,
    bl.a. `@lydell/node-pty-win32-x64` (`package-lock.json:2197-2209`). Inget installationsskript.
  - `frida` 17.23.2 som **optionalDependency** med `hasInstallScript: true` och beroende på
    `prebuild-install` (`package-lock.json:7676-7686`); `package.json:467-469` har
    `"allowScripts": {"frida@17.23.2": true}`. **[antagande]** Installationsskriptet hämtar en
    förbyggd Frida-binär från nätet om npm kör installationsskript.
  - En egen Windows-addon `native/windows/build/rea-windows-x64.node` + `manifest.json` följer med
    det publicerade paketet (`package.json:95-96`); i 6.7.0-cachen är den 881 284 byte
    **[observerat]**.
  - `playwright-core` 1.65.1 (laddar inte ner webbläsare själv; se 1.4).
- `prepare`-skriptet (`scripts/prepare.mjs:26-39`) gör bara något i en källkodsutcheckning
  (patchar release-please, installerar husky-hooks); i ett publicerat paket finns varken `src`
  eller dev-beroenden, så det är en no-op **[läst]**.
- Uppstart: `scripts/rea.mjs:22-29` jämför `engines.node` mot `process.versions.node` med
  `unsupportedRuntimeMessage` **innan** någon kompilerad modul importeras, skriver
  `REA requires Node.js …; this process runs Node.js <v>. Install a supported release, then retry.`
  till stderr och gör `process.exit(1)`. Jämförelsen finns i
  `scripts/lib/runtime-admission.mjs:40-54`: samma major → minor och patch måste vara minst
  golvet. 24.11.0 mot `^24.22.1` ger `11 > 22` = falskt → avvisas **[läst]**.
- Saknas `dist/` skriver den `REA's compiled runtime is missing…` och avslutar med 1
  (`scripts/rea.mjs:60-64`).
- `scripts/lib/cli-process-environment.mjs:4-26` sätter `REA_PACKAGE_VERSION`, tar bort tom
  `USERPROFILE` på Windows och sätter Playwrights cachekatalog bara på Android.

### 1.2 Vad `npx -y rea-agents@6.10.1 mcp` gör på Windows

Det här är kommandot i klonens `mcp.json:1-12` (och `server.json:12-29` för MCP-registret).

1. **npm-hämtning** (före rea): npx slår upp `rea-agents@6.10.1` i
   `https://registry.npmjs.org` (`server.json:15`), laddar ner paketet och hela beroendeträdet
   till `%LOCALAPPDATA%\npm-cache\_npx\<nyckel>\node_modules`. `-y` godkänner nedladdningen utan
   fråga. **[antagande]** npm kör installationsskript som standard, så frida:s skript körs om
   det optionala paketet installeras. Dokumentationen nämner en `prebuild-install`-varning från
   Frida (`docs/getting-started/installation.md:30-32`).
2. **Node-kontrollen** i `scripts/rea.mjs:22-29`: med Node 24.11.0 avslutas processen
   omedelbart med kod 1. Ingen MCP-server startar. MCP-klienten ser att stdio stängs →
   `CONNECTION_CLOSED`. **Det här är vad som händer om registreringen ändras till 6.10.1.**
3. Med en godkänd Node-version: `classifyCliEntrypoint` ger `mcp-stdio`, och
   `dist/mcp/main.js` → `runEntrypoint()` serverar verktygskatalogen över stdio
   (`scripts/rea.mjs:40,65-67`).
4. **Filer utanför paketkatalogen** vid ren `mcp`-start **[läst + antagande]**: ingen
   agentkonfiguration och inga skills skrivs (det gör bara `setup`). Analysverktyg kan skriva
   privata temporära filer och REA:s cache/tillstånd (`~/.rea`, nämnt i
   `installation.md:484-485`), och sparade providerinställningar i `rea.json`
   (`installation.md:482-483`).
5. **Nätverk**: npm-registret vid hämtning. Själva MCP-servern gör inga nätverksanrop för
   statisk analys **[läst]** README.md:263-266 ("REA analyzes targets locally"). Verktyg som
   uttryckligen fångar webb/körning gör nätverksanrop (SECURITY.md:24-32).
6. **Telemetri:** ingen telemetri hittad. Den enda "ringa hem"-funktionen är en
   uppdateringsnotis från Incur: på en terminal, utan explicit format, startar CLI:t högst en gång
   per dygn en frånkopplad `rea --incur-update-check` som frågar npm-registret om senaste
   version, och cachar svaret i `$XDG_CACHE_HOME/incur/updates/<paket>.json`. Stängs av med
   `NO_UPDATE_NOTIFIER=1`, `npm_config_update_notifier=false` eller `CI`
   **[läst]** `src/cli/updateNotice.ts:29-45,121-128`. `--mcp`/`--update`/update-flaggan
   går förbi den (`src/cliBuiltinArguments.ts:256-261`). **[antagande]** MCP-stdio-läget visar
   ingen notis eftersom stdout inte är en terminal.

### 1.3 Vad `npx rea-agents setup` gör på Windows

Källa: `docs/getting-started/installation.md` **[läst]**.

- Två godkännanden: npm:s nedladdningsfråga och REA:s egen plan (rad 23-25).
- Interaktivt flerval av agentklienter (42 klient-id:n, rad 696-739; Claude Code = `claude_code`).
  Befintliga REA-registreringar förvalda, nyupptäckta klienter **inte** förvalda (rad 40-44).
- Planen visar exakta sökvägar, nätverksursprung och pakethanterarkommandon innan något skrivs
  (rad 53-65). Avbryt = inga ändringar (rad 67-68). `--dry-run` ger en skrivskyddad plan
  (rad 131-136); `--json` likaså utan att tillämpa (rad 145-147).
- **Skrivningar utanför paketkatalogen** för Claude Code (rad 230-232):
  - `mcpServers.rea` i `~/.claude.json` (användarnivå: syns i **alla** projekt).
  - Skillen `reverse-engineer-anything` i `~/.claude/skills/` (rad 249, 170-174).
  - Säkerhetskopior `.rea.backup` och ev. `.rea.backup.<sha256>.recovery` bredvid filen
    (rad 79-86).
  - Utan vald klient: skill i `~/.agents/skills` (rad 173).
- Registreringen pekar på **absolut** `node.exe` + `scripts/rea.mjs` + `mcp` i den installation
  som körde setup (rad 219-221, 2160-2164). Körs setup via npx binds registreringen till
  npx-cachen; rensas cachen slutar servern starta (rad 2184-2190).
- Hopper (macOS/Linux-motor) installeras bara efter eget godkännande; Ghidra/IDA/Kuna används
  bara om de redan finns (rad 46-51). `install.sh` vägrar allt utom macOS/Linux
  (`install.sh:113`), så curl-skriptet är irrelevant på Windows.
- Begränsa till ett projekt: hoppa över setup för Claude Code och registrera lokalt i
  projektkatalogen med `claude mcp add --scope local rea -- "C:\Program Files\nodejs\node.exe" "<väg>\scripts\rea.mjs" mcp`
  (rad 323-353). Dokumentationen säger själv att detta inte är en clean-room-avgränsning: en agent
  under samma Windows-konto kan ändå nå rea via `PATH`/`npx` (rad 235-242).
- Den här datorns faktiska registrering **[observerat]** i `~/.claude.json` (cirka rad 3618-3628):
  `"command": "cmd.exe", "args": ["/d","/c","npx","-y","rea-agents@6.7.0","mcp"]`, alltså en
  äldre npx-registrering på användarnivå. Den startar i varje Claude Code-session, även denna.

### 1.4 CLI-kommandon som är relevanta

Källor: `docs/reference/supported-targets.md:34-37`, `docs/guides/web/*.md`,
`docs/guides/javascript/javascript-application-workflows.md`, `docs/reference/mcp-contracts.md`
**[läst]**. Kommandonamnen nedan finns även i den cachade 6.7.0-installationens `dist/`
(utom `compare-static-and-observed-endpoints`, som jag inte hittade där) **[observerat]**.

**(a) Statisk analys av en JS/TS-källkodskatalog — ingen extern motor**

| Kommando | Vad det ger |
|---|---|
| `rea analyze-javascript-application <abs-sökväg> --json` | Moduler, importer, källkartor, routes, IPC, nativa addons; en "JavaScript Application Graph" + semantisk relationsgraf. Läser katalogen, kör inte koden (mcp-contracts.md:1764-1768). TypeScript `import type`/`export type` hålls isär från körtidsimporter (javascript-application-workflows.md:31-37). |
| `rea trace-application-feature <input.json> --json` | Följer en sträng, route, API, modul m.m. genom grafen (rad 183-230, exempel rad 699-705). |
| `rea compare-application-versions`, `compare-source-to-bundle`, `compare-javascript-export-shapes`, `trace-javascript-semantics`, `inspect-analysis-view` | Jämförelser och vyer över redan skapad Evidence (rad 1-10). |
| `rea recover-javascript-sources` | Återskapar källor ur bundles/källkartor. |
| `rea audit-release-exposure` | Exponeringsrevision av en release (supported-targets.md:34). |

Linux kräver procps-`ps`; Windows har inget motsvarande krav i dokumentationen
(installation.md:446-457). **[antagande]** Twentys monorepo (React-front, NestJS-server) är stort;
storleksgränser för källanalysen hittade jag inte dokumenterade. Kör hellre per paket
(`packages/twenty-front`, `packages/twenty-server`) eller per modulkatalog än över hela repot.

**(b) Inspelad webbsession och nätverkstrafik**

| Kommando | Kräver | Vad det gör |
|---|---|---|
| `rea inspect-web-network-capture <abs>.har har --json` | Bara filen | Offline: inga URL:er hämtas, ingen webbläsare startas (web-network-captures.md:3-10). HAR 1.2 eller Fiddler SAZ (supported-targets.md:36). |
| `rea environment-build <x>.har <dir> --json` | Bara filen | Härleder en "miljö" (namngivna verktyg per request-rad) ur en HAR (cli.md:1350-1367). |
| `rea list-browser-targets http://127.0.0.1:9222` | Din Chrome/Edge med `--remote-debugging-port` | Listar sidor (browser-observation.md:24). |
| `rea inspect-web-page` | Samma | DOM, tillgänglighetsträd, skript, resurser, nätverks- och konsolmetadata för attach-fönstret (rad 25-34). |
| `rea analyze-web-bundle` | Samma | Chunk-kanter, route- och endpointkandidater, källkartor, utan att köra koden (rad 35-40, mcp-contracts.md:1770-1773). |
| `rea observe-web-session` | Samma | Spelar in navigering/omdirigeringar under en tidsram medan du klickar (rad 41). |
| `rea capture-web-screenshot`, `compare-web-screenshots`, `compare-web-captures` | Samma | Synlig viewport som PNG, pixeljämförelse (rad 130-131, 45). |
| `rea export-web-scripts`, `trace-web-module-imports` | Samma | Exporterar fångade skript till statisk analys. |
| `rea capture-browser-scenario` | Playwright + **en webbläsar-exe du anger** | Kör deklarerade klick i en egenägd tillfällig profil (`mode: "launch"`, `executable_path`; browser-scenario-contract.md:10-15, 85-131, 198-199). Kör målets kod. |

**Inloggad webbapp:** rea "does not launch, own, or terminate this browser" i CDP-läget
(browser-observation.md:200-207). Från Chrome 136 ignoreras `--remote-debugging-port` för
**standardprofilen** (rad 237-240), så du startar en separat profil med
`--user-data-dir=<D:\…>`, loggar in där själv och låter rea ansluta. Porten ska bara lyssna på
loopback (rad 207). Observera: CDP-anslutningen kan återställa en annan klients
`navigator.platform`-emulering och `debugger`-satser kan pausa sidan (rad 176-189).

**Kräver extern motor:** nativ dekompilering (Hopper, Ghidra, IDA, Kuna), Android (JADX + JDK),
pcap (tshark), firmware (Binwalk/Unblob), m.m. (supported-targets.md:9, 38, 45-47). **Inget av
detta behövs för Twenty.**

**Lämpliga MCP-verktygsfamiljer** om MCP används: `browser,pcap,session,javascript-runtime` för
webbutredning, `browser,electron,application,javascript-runtime,session` för JS-appar
(mcp-contracts.md:2419,2424), satt med `REA_MCP_TOOL_FAMILIES` eller `setup --tool-families`
(rad 2399-2401).

### 1.5 rea mot Twenty: källkod respektive inloggad webbapp

- **React/NestJS-monorepo i källkodsform:** `analyze-javascript-application` per paket, sedan
  `trace-application-feature` med strängfrön som `"company"`, `"person"`, `"opportunity"`,
  `"timelineActivity"` eller GraphQL-operationsnamn. Ger en spårbar import- och routekarta.
  Ingen motor behövs.
- **Inloggade app.twenty.com:** antingen (i) spela in en HAR i webbläsarens DevTools och köra
  `inspect-web-network-capture` + `environment-build` offline, eller (ii) starta Edge/Chrome med
  separat profil och debugport, logga in själv och köra `inspect-web-page`,
  `analyze-web-bundle` och `observe-web-session`. Väg (i) är säkrast: ingen öppen debugport,
  och HAR-filen kan granskas och rensas först.
- **Sekretess:** en HAR från en inloggad session innehåller cookies, `Authorization`-huvuden och
  allt data som visades. rea:s dokumentation säger att Evidence och captures kan behålla
  privata data och inte är säkra att publicera (SECURITY.md:89-94). Lägg HAR-filer på D:,
  utanför repot, och checka aldrig in dem.

### 1.6 Varför MCP-servern faller med CONNECTION_CLOSED

**Bekräftat för den registrerade servern: det är INTE Node-versionen.**

- Registreringen kör `rea-agents@6.7.0` **[observerat]** (`~/.claude.json`).
- Cachen `%LOCALAPPDATA%\npm-cache\_npx\a1722018f28f9df2` innehåller `rea-agents` med
  `"version": "6.7.0"` och `"node": "^22.19.0 || ^24.11.0 || >=26.0.0"` **[observerat]**.
  Node v24.11.0 ligger precis på golvet och godkänns. 6.7.0:s `scripts/rea.mjs` har dessutom
  ingen inbyggd Node-kontroll (den kom senare; jämför `scripts/rea.mjs:17-29` i klonen).
- Claude Codes MCP-logg för just den här arbetskatalogen,
  `%LOCALAPPDATA%\claude-cli-nodejs\Cache\C--Users-Anton-L-snipe-leads--claude-worktrees-snajp-crm-dd0d83\mcp-logs-rea\2026-11-25T06-39-45-689Z.jsonl`,
  visar **[observerat]**:
  `Error [ERR_MODULE_NOT_FOUND]: Cannot find module '…\_npx\a1722018f28f9df2\node_modules\@jridgewell\sourcemap-codec\dist\sourcemap-codec.mjs' imported from …\@jridgewell\trace-mapping\dist\trace-mapping.mjs`
  följt av `Connection failed after 66419ms … (CONNECTION_CLOSED)`. Samma fel i loggen från
  hemkatalogen 07:17.
- I cachen innehåller `@jridgewell/sourcemap-codec/dist/` bara `sourcemap-codec.umd.js`
  **[observerat]**; `.mjs`-filen som `trace-mapping` importerar saknas. Installationen är alltså
  ofullständig. Det är samma felklass som rea-dokumentationen beskriver för Windows och just
  6.7.0 i issue #5259 (`installation.md:521-566`): "Repeating the same npx command can reuse that
  incomplete installation". Orsaken till att filen försvann är okänd; dokumentationen ber om att
  kontrollera säkerhetsprogrammets skyddshistorik (rad 563-566) **[läst]**.
- En annan körning 10:22 i hemkatalogen gav i stället `CONNECT_TIMEOUT` efter 120 s
  **[observerat]**: troligen npx-uppslag/nedladdning eller start som tog för lång tid. Det är en
  andra, separat felbild.

**Node-versionen blir orsaken om** registreringen byts till `rea-agents@6.10.1` (eller
`@latest`): då avslutar `scripts/rea.mjs:26-29` med kod 1 och meddelandet
`REA requires Node.js 22.x (>=22.23.4), 24.x (>=24.22.1), 26.12.1+; this process runs Node.js 24.11.0.`
innan servern startar, vilket MCP-klienten också visar som `CONNECTION_CLOSED`.

**Andra möjliga orsaker till CONNECTION_CLOSED** (för fullständighet):

1. npm-arbetsytans konflikter: npx inspekterar anroparens `package.json` och kan dö med
   `EOVERRIDE` innan rea startar (installation.md:2261-2277, issue #3690). Claude Code startar
   servern med projektets katalog som cwd, och snipe-leads har en `package.json` **[antagande]**.
2. Ogiltig rea-miljövariabel (t.ex. `REA_LOG_LEVEL`, `REA_GHIDRA_STARTUP_TIMEOUT_MS`) som MCP-starten
   avvisar (installation.md:432-437).
3. Antivirus som karantänsätter filer i npx-cachen (rad 563-566) eller nativa `.node`-filer.
4. Långsam första start (nedladdning + frida-skript) som ger timeout i stället (syns som
   `CONNECT_TIMEOUT`, inte `CONNECTION_CLOSED`).

**Felsökning utan att köra setup:**

1. Läs Claude Codes logg: `%LOCALAPPDATA%\claude-cli-nodejs\Cache\<projekt-slug>\mcp-logs-rea\*.jsonl`
   (raden `Server stderr:` bär rea:s eller npm:s eget felmeddelande).
2. Läs versionen och `engines.node` i
   `%LOCALAPPDATA%\npm-cache\_npx\<nyckel>\node_modules\rea-agents\package.json` och jämför med
   `node --version`.
3. Kontrollera att filen som felet nämner finns.
4. Reparera bara den trasiga posten (rea:s egen anvisning, installation.md:535-561), i PowerShell:
   `npm.cmd cache npx ls`, `npm.cmd cache npx info a1722018f28f9df2`,
   `npm.cmd cache npx rm a1722018f28f9df2`, sedan från en tom, betrodd katalog
   `npx.cmd --yes rea-agents@6.7.0 doctor --json`. `doctor --json` är skrivskyddad
   (installation.md:473) och visar om starten fungerar. **Kräver godkännande:** ny nedladdning.
5. Vill man inte ha servern i varje session alls: ta bort användarregistreringen
   (`claude mcp remove --scope user rea`) och använd rea som CLI vid behov. **Kräver godkännande:**
   ändring av global agentkonfiguration.

---

## 2. craft-anything (storytold/craft-anything, MIT/Apache-2.0)

### 2.1 Vad det är

Ett Rust-program (desktopapp i egui, CLI, MCP-server) som studerar en webbplats, app eller ett
spel, låter en kodagent bygga en egen version och jämför resultatet med originalet
(README.md:96-105). 320 verktyg, varje verktyg både CLI-underkommando och MCP-verktyg
(README.md:89, 189-196). Status: "early alpha" (README.md:30, 237-257).

### 2.2 Installation på Windows

**Bygga med cargo** **[läst]**:

- `rust-version = "1.97"` (`Cargo.toml:9`, README.md:200 "Requires Rust 1.97 or newer").
  Datorn har `rustc 1.96.1` och `cargo 1.96.1` **[observerat]** → bygget vägras tills
  `rustup update` körs. **Kräver godkännande** (uppgraderar verktygskedjan för hela kontot).
- Workspace: `members = ["crates/*", "apps/*", "xtask"]` (`Cargo.toml:3`) = 13 crates under
  `crates/` + 3 appar + `xtask` = 17 egna paket. `Cargo.lock` listar 904 paket totalt
  **[observerat]**. Över 20 beroenden hämtas via git från `github.com/storytold/craft-libs` på en
  fast commit (`Cargo.toml:13-55`), plus lokala patchar av `wgpu-hal` och `winit` under `vendor/`
  (`Cargo.toml:131-135`).
- Release-profilen kör `lto = "thin"`, `codegen-units = 1` (`Cargo.toml:115-117`).
  **[antagande]** Ett releasebygge av bara CLI:t (`cargo build --release -p craft-anything-cli`)
  kompilerar ändå motorn, AI-lagret och MCP (CLI-beroenden i `apps/craft-anything-cli/Cargo.toml:12-24`)
  och troligen några hundra crates: räkna med tiotals minuter, flera GB i `target/` och flera GB
  RAM i länksteget. Med 16 GB RAM och tidigare commit-krasch är det en verklig risk; sätt i så
  fall `CARGO_TARGET_DIR` på D: och `-j 2`.
- **[antagande]** Kräver MSVC-verktygskedjan (link.exe, Windows SDK för `winresource`,
  `apps/craft-anything-cli/Cargo.toml:32-34`). Om de finns gick inte att kontrollera med de
  tillåtna kommandona.
- README-kommandot `cargo install --path apps/craft-anything-cli` (rad 212) installerar
  `craft-anything-cli.exe` i `%USERPROFILE%\.cargo\bin` på C:.

**Release i stället för bygge** **[läst]**:

- Windows x64: `craft-anything-<ver>-windows-x64.msi` eller
  `craft-anything-<ver>-windows-x64-portable.zip` (README.md:278-283). Det finns ingen separat
  CLI-zip för Windows: `craft-anything-cli.exe` ligger bredvid `craft-anything.exe` i både MSI och
  zip (`packaging/windows/package.ps1:8-10,59-61`; `docs/releasing.md:88`). Binärerna länkar
  C-runtime statiskt, så ingen VC++-redist behövs (`package.ps1:12`).
- Med workspace-version 0.6.1 heter filen sannolikt
  `craft-anything-0.6.1-windows-x64-portable.zip` **[antagande]**: kontrollera på
  Releases-sidan.
- Signering: README säger "Installers and executables are code-signed" (rad 283), men
  `packaging/windows/sign.ps1:6-11` lämnar filerna **osignerade med exit 0** om varken
  certifikat eller Azure Trusted Signing är konfigurerat. Verifiera därför själv:
  `Get-AuthenticodeSignature .\craft-anything-cli.exe` (Status `Valid`, rätt utfärdare) och
  SHA-256 mot `SHA256SUMS.txt` (README.md:274). Kontrollsummorna ligger i samma release och
  skyddar bara mot korrupt nedladdning, inte mot ett komprometterat konto.
- Portabelt läge: `portable.txt` bredvid exe-filen gör att inställningar hamnar i
  `CraftAnythingData\` bredvid programmet (`crates/engine/src/settings.rs:340-344`;
  `docs/releasing.md:103-104`). Packa upp på D: så hamnar inställningarna där.

### 2.3 Vad kommandona gör

Globala flaggor (`apps/craft-anything-cli/src/main.rs:27-50`): `--format` (standard JSON),
`--project <mapp.cany>`, `--allow-run` ("Allow tools that run code or change a device without
asking"), `--deep`, `--clean-room`.

- **`craft-anything-cli mcp`** (`main.rs:55-76, 264-301`): MCP-server på stdin/stdout. Visar
  "Essentials plus enabled toolsets", `--all-tools` visar alla. `--restricted` stänger av
  maskinstyrande verktyg och som standard webb- och fångstverktyg; `--allow-web`/`--allow-capture`
  slår på dem igen. `--inbox <mapp>` låter desktopappen besvara frågor och godkännanden.
  Utan `--allow-run` och utan inbox **misslyckas** verktyg som kör främmande kod, t.ex.
  `web_site_open`, med `ConsentRequired` (`crates/mcp/src/lib.rs:570, 590-595`). Med `--allow-run`
  skrivs en varning till stderr (`lib.rs:151-157`). Miljövariabler:
  `CRAFT_ANYTHING_MCP_ALL_TOOLS`, `_RESTRICTED`, `_ALLOW_WEB`, `_ALLOW_CAPTURE`,
  `_MAX_RESPONSE_BYTES` (`lib.rs:103-107`).
- **`craft-anything-cli commands`** (`main.rs:319-345`): listar alla verktyg per toolset, i JSON
  med `command`, `tool`, `toolset`, `title`, `summary`, `needs_target`. Skapar motorn och läser
  inställningar, men rör inget mål.
- **`craft-anything-cli doctor`** (`apps/craft-anything-cli/src/setup_cmd.rs:142-165`,
  `crates/setup/src/doctor.rs:1-2`): skrivskyddade kontroller av installationen,
  agentregistreringar, skills, motorer och MCP-servern. Kontrollerar dessutom att konfigurerade
  AI-backends svarar (`ai_cmd.rs:511-527`), vilket betyder nätverksanrop **om** en backend är
  inlagd. Exit 1 vid problem.
- **`craft-anything-cli setup`** (`setup_cmd.rs:12-25, 78`): skriver craft-anythings
  MCP-registrering och skill i agentappar. För Claude Code: `mcpServers` i `~/.claude.json`
  och skill i `~/.claude/skills` (`crates/setup/src/clients.rs:303-305`). `--dry-run` finns.
- **`craft-anything-cli rebuild <mål> "<begäran>"`** (`rebuild_cmd.rs:19-60`): skapar ett projekt
  (standard `Documents/Craft Anything`, README.md:226-229), studerar målet, **startar en kodagent
  som bygger**, jämför och förfinar i `--rounds` (standard 2) varv. Det är byggflödet, inte en
  inventering; för Snajp CRM ska det **inte** användas.

### 2.4 Startar craft-anything en kodagent, och med vilka behörigheter?

Ja, i `rebuild`, chatt och frågor (inte i `mcp`, `commands`, `doctor` eller enskilda verktyg)
**[läst]** `docs/claude-code.md:8-45`:

- Hittar `claude` på PATH eller `~/.local/bin` och kör `claude -p <uppgift> --output-format stream-json --verbose`
  (+ `--resume`), med projektmappen som arbetskatalog, egen MCP-server via
  `--strict-mcp-config --mcp-config` och `--permission-prompt-tool mcp__craft-anything__core_action_approve`
  (`crates/ai/src/cli_agents/adapters.rs:503-523`).
- Byggaren får verktygen `Bash,PowerShell,Read,Write,Edit,MultiEdit,Glob,Grep,TodoWrite,NotebookEdit`
  (+ `Agent` i Deep) (`adapters.rs:505-508`). Godkännandeverktyget tillåter ändringar i projektets
  `app/` och en fast lista byggkommandon, och avgör resten per slag (webb, kommandon, filer utanför
  projektet, push/publicering, borttagning, systemändringar). Auto-läget är på som standard
  (`settings.rs:228`) och dess standard för kommandon är "allow" (claude-code.md:30-40). Med
  "commands: allow" kan byggaren köra vad som helst med ditt kontos rättigheter
  (claude-code.md:37-40).
- Claude Code körs med användarens egen inloggning; craft-anything läser inga credentials
  (claude-code.md:95-104).
- En annan adapter (Antigravity) skickar `--dangerously-skip-permissions` i byggläge
  (`crates/ai/src/cli_agents/adapters/antigravity.rs:4,18`). Gäller inte Claude Code.

### 2.5 Verktyg för webbplatser

Toolset "Websites (`browser`, 24)" (`docs/tools.md:225-256`). Det som efterfrågas:

| Behov | Verktyg | Clean room? | Inloggad sida? |
|---|---|---|---|
| Öppna sidan | `web_site_open` | Ja | Ja, om `web_site_sign_in` sparat inloggning för exakt host+port, eller via `cdp_endpoint` till din egen webbläsare (`website_tools.rs:32-45`) |
| Skärmbilder vid flera bredder, synlig text, uppmätt layout, färger, typsnitt, avstånd | `web_site_capture` | Ja (besökarvy) | Ja, på den öppnade sidan |
| Öppnade menyer, dialoger, flikar | `web_page_states_capture` | Ja | Ja |
| En skärmbild | `web_page_screenshot_take` | Ja | Ja |
| Pixeljämförelse | `web_pixels_compare` | Ja | – |
| Logga in själv i synligt fönster / glöm inloggningen | `web_site_sign_in` / `web_site_sign_out` | Ja | – |
| DOM, sidans JS, modulgraf, lyssnare, skript, HAR/nätverksinspelning, stand-in-backend ur HAR | `web_page_show`, `web_page_js_analyze`, `web_modules_trace`, `web_listeners_list`, `web_scripts_save`, `web_recording_show`, `web_standin_build` | **Nej, bara Deep** | Ja |

Detaljer **[läst]**:

- `web_site_capture` skriver i en ny mapp fullsides-PNG per bredd, renderad HTML, designtokens
  (typsnitt, storlekar, vikter, text- och bakgrundsfärger som hex, radier, skuggor, avstånd,
  innehållsbredder, CSS-variabler), brytpunkter, layout per bredd, en layoutöversikt, tillgångslistor,
  länkar och formulärkonturer (aldrig värden), plus `capture.json` och `README.md`
  (`website_tools.rs:47-56`). Standardbredder för ett enskilt verktygsanrop: `[1440, 390]`
  (`website_tools.rs:801`); jämförelsen i rebuild använder `[1440, 768, 390]`
  (`crates/engine/src/settings.rs:174`), vilket är de "tre bredderna" i README.
- **I Clean room** stängs HTML av (`p.include_html &= !visitor`, `website_tools.rs:1002-1004`) och
  `visitor_view` tar bort meta, brytpunkter, oläsbara stilmallar, hälsa, klassnamn, element-id:n,
  query-strängar på adresser och formuläraction (`website_tools.rs:1222-1260`). Evidence får
  begränsningen `visitor_view`: "only what a visitor sees was kept … not the page's HTML, CSS
  rules, scripts, requests or errors" (`website_tools.rs:1090-1091`).
- **Startar en egen webbläsare:** ja. `web_site_open` startar en "private browser owned by this
  session (fresh profile, no history or logins)" om ingen `cdp_endpoint` ges
  (`website_tools.rs:1-7, 34`). Den letar upp en installerad Chromium-webbläsare: Chrome i
  `ProgramFiles`/`LOCALAPPDATA` eller Edge (`crates/engines/src/table.rs:237-241, 459-472`). Den
  laddar inte ner någon webbläsare **[antagande, inget nedladdningsflöde för chromium hittat]**.
  `web_site_sign_in` öppnar ett **synligt** fönster och väntar tills du stänger det (standard
  600 s, högst 1800 s) (`site_sign_in.rs:46-49`).
- **Från CLI:t fungerar inte öppna→fånga som separata kommandon:** "each command is a session of
  its own, a later `web-site-capture` finds no site". Kör dem i samma MCP-session
  (`docs/tool-status.md:64-66`).

### 2.6 Vad craft-anything skriver till disk och var

| Vad | Var | Källa |
|---|---|---|
| Inställningar, plugin-cache | `%APPDATA%\craft-anything\` (via `dirs::config_dir`), eller `CRAFT_ANYTHING_CONFIG_DIR`, eller `CraftAnythingData\` bredvid exe i portabelt läge | `settings.rs:336-346` |
| Sparade inloggningar (hela webbläsarprofilen utom lösenords- och kortlager) | `<config>\sign-ins\site-<host>_<port>\profile` + `sign-in.json` | `site_sign_in.rs:1-10, 31-39, 136-138` |
| Projekt (`craft.json`, `capture/`, `app/`, `checks/`, `investigation.cany/`, `inbox/`) | `Documents\Craft Anything` | README.md:226-229 |
| Fångster från `web_site_capture` / `web_page_states_capture` | Den `output_directory` du anger | `website_tools.rs:47-61` |

Två observationer: Dokumenten på den här datorn ligger i OneDrive (valvet ligger under
`OneDrive\Dokument`), så projektmappen skulle **[antagande]** synkas till molnet, med
skärmbilder av en inloggad CRM. Och den sparade inloggningsprofilen innehåller sessionscookies:
"anyone who can open your files here could use it" (`site_sign_in.rs:46`).

Uppdateringskontroll finns i desktopappen (`crates/ui-egui/src/updates.rs:1-9`), inte i CLI:t.
Ingen telemetri hittad.

### 2.7 Clean room mot Deep, exakt

**[läst]** `crates/engine/src/clean_room.rs:1-8, 14-140, 147-157`, README.md:132-150,
`docs/claude-code.md:46-64`.

- Standardläget är Clean room: `deep_mode: false` (`settings.rs:221`). Byts med Settings,
  `settings_set deep_mode true`, eller för en körning med `--deep`/`--clean-room`.
- **Clean room läser:** bara verktygen i `TOOLS`. Grupper: sessionen, evidence och
  frågor/minne (`core_*`); genererade bilder och nycklar (`assets_*`, `ai_model_options_*`);
  projekt och rebuild (`project_*`, `rebuild_*`); byggarens eget projekt (`build_*`); inställningar,
  motorer, plugins, setup (`settings_*`, `engines_*`, `plugins_*`, `setup_*`); webbplatsen som
  besökare (`web_site_open`, `web_site_capture`, `web_page_states_capture`,
  `web_page_screenshot_take`, `web_pixels_compare`, `web_site_close`); inloggning
  (`web_site_sign_in`, `web_site_sign_out`, uttryckligen "a policy call", rad 117-120);
  `web_walkthrough_check`; program sett utifrån (`native_window_capture`, `runtime_ui_read`,
  `runtime_ui_walkthrough_record`, `runtime_walkthrough_record`, `runtime_captures_compare`);
  telefon via adb (`adb_*`, tio verktyg).
- **Clean room vägrar:** allt annat, också plugins och nya verktyg ("a new tool is Deep-only until
  it's added here", rad 7-8). Vägran ger felkod `FeatureMissing` med `details.reason = "clean_room"`,
  orsak "This looks inside the original (its code, files or page source), which Clean room never
  does." och anvisningen att slå på Deep (rad 147-158). Testet nämner uttryckligen
  `core_target_open`, `core_target_triage`, `native_function_pseudocode`, `native_strings_browse`,
  `js_app_map`, `web_page_show`, `game_archives_list` (rad 186-199). För en webbplats betyder det:
  ingen DOM-dump, ingen JS-analys, ingen HAR/nätverksinspelning, inga skript, inga felsidor,
  inga request-listor.
- **Kodagenten i Clean room:** i bygget går även läsningar genom godkännandeverktyget, som vägrar
  allt i originalets mapp eller på dess webbplats (projektmappen undantagen); `Agent` (subagenter)
  tas bort. I chatt startas Claude Code med `--disallowedTools` för `Read`, `Glob`, `Grep`, `LS`,
  `NotebookRead` och ändrande/webbverktyg (claude-code.md:20-25, 52-55; `adapters.rs:517-522`).
  Detta är "not yet checked live" (claude-code.md:63-64). Andra agenter än Claude Code hålls inte
  till regeln i chatt (rad 60-61).
- **Begränsning:** "Clean room is a rule about what Craft Anything offers and refuses. It is not an
  operating-system sandbox" (README.md:143-147). En byggare med kommandon tillåtna kan hämta
  Twentys källkod från GitHub på egen hand.

**Vad det betyder för licensval A:** Clean room ger en dokumenterad besökarvy av app.twenty.com
(bilder, synlig text, mått) där Twentys AGPL-kod uttryckligen inte lästs. Det passar en
funktionsinventering, men två saker gäller ändå:

1. Den synliga texten och skärmbilderna är också Twentys material. De duger som underlag för
   *vad* funktionen gör; UI-texter och ikoner ska inte kopieras ordagrant till Snajp CRM
   **[antagande, juridisk bedömning ej gjord]**.
2. Om andra agenter samtidigt läser Twentys källkod är arbetet som helhet inte clean room.
   Vill Anton ha den åtskillnaden: en agent läser källkoden och skriver en funktionsbeskrivning
   utan kod, och de agenter som bygger Snajp CRM ser bara beskrivningen och besökarvyn.

---

## 3. Bedömning

### 3.1 Vad tillför verktygen utöver direkt källkodsläsning och en vanlig webbläsare med nätverkslogg?

**rea**

- Tillför: en reproducerbar, maskinläsbar karta (moduler, importer, routes, endpointkandidater)
  med Evidence-id:n som kan citeras i inventeringen, och `trace-application-feature` som följer en
  funktion genom hela grafen. Offline-läsning och normalisering av en HAR
  (`inspect-web-network-capture`) och `environment-build` som grupperar API-anropen till namngivna
  operationer: snabbare än att läsa en HAR för hand.
- Tillför inte mycket: Twentys källkod är öppen och läsbar; GraphQL-schemat och
  metadatamodellen (standardobjekten company, person, opportunity, note, task, timelineActivity)
  hittas lika bra med grep och genom att läsa koden. rea är byggt för reverse engineering utan
  källkod, och den styrkan behövs inte här.
- Netto: **måttligt värde**, främst för HAR-analysen och för en citerbar modulkarta. Värt det
  bara om reparationen är billig (avsnitt 1.6, steg 4).

**craft-anything**

- Tillför: besökarvyn av en inloggad SPA i Clean room, med skärmbilder vid flera bredder,
  designtokens och automatiskt öppnade menyer/dialoger (`web_page_states_capture`). Det är just
  "en funktionsinventering utan att läsa AGPL-koden" i dokumenterad form.
- Tillför inte: något om datamodell, API eller behörigheter (allt sådant är Deep). Rebuild-flödet
  bygger en kopia av utseendet, vilket inte är målet och är juridiskt tveksamt för en kommersiell
  produkt. En vanlig webbläsare plus skärmbilder ger 80 % av besökarvyn utan ny binär.
- Netto: **lågt till måttligt värde**, i förhållande till kostnaden (osignerad-risk eller
  Rust-uppgradering + tungt bygge, en ny agentintegration och lagrad inloggningsprofil).

### 3.2 Säkerhetsrisker på Antons dator (16 GB RAM, ont om disk på C:, gott om plats på D:)

| Risk | rea | craft-anything |
|---|---|---|
| Kör tredjepartskod med Antons rättigheter | Ja: npm-paket med ~40 direkta beroenden, frida-installationsskript; ingen sandlåda (SECURITY.md:9-12, 84-88) | Ja: egen binär; byggaren kör kommandon med Antons rättigheter (claude-code.md:37-40) |
| Leveranskedja | npm-registret, `-y` hoppar över frågan; `@latest` byter version tyst | Releasebinär som kan vara osignerad (sign.ps1:6-11); källbygge hämtar git-beroenden från craft-libs |
| Global påverkan | `setup` skriver `~/.claude.json` och `~/.claude/skills` på användarnivå, synligt i alla projekt; redan i dag startar en npx-server i varje session | `setup` skriver samma filer; `rebuild` startar `claude -p` |
| Inloggningsdata | HAR-filer innehåller cookies och tokens; öppen CDP-port ger full kontroll över webbläsaren (rea:s egen varning, browser-observation.md:207) | Sparad webbläsarprofil med sessionscookies i `%APPDATA%\craft-anything\sign-ins` (site_sign_in.rs:46) |
| Kunddata/sekretess | Inget om man bara analyserar Twenty; peka aldrig verktygen mot Snajps egna miljöer (development är en spegel av produktionen) | Projektmappen hamnar i OneDrive-synkade Dokument |
| Minne | Analysarbetare med egen heap; storleksgräns för stora källträd odokumenterad | Releasebygge med LTO kan ta flera GB RAM; samtidigt med andra tunga processer → commit-brist |
| Disk på C: | npx-cache under `%LOCALAPPDATA%\npm-cache` (C:) | `~/.cargo`, `target/` (flera GB), `%APPDATA%` |
| MCP över HTTP | `mcp --http` är okrypterat och utan autentisering (SECURITY.md:34-38); använd inte | – |

### 3.3 Rekommenderad minsta säkra körordning

Grundprincip: allt nytt på D:, inget på användarnivå i agentkonfigurationen, inga
`setup`-kommandon, ingen `rebuild`.

**Steg 0 – utan nya verktyg (gör först, inget godkännande utöver vanlig git-kloning)**

1. Agenter läser Twentys källkod direkt (en grund klon på D:, t.ex. `D:\snajp-crm-forlaga\twenty`).
2. Webbappen kartläggs i en vanlig webbläsare. Spara HAR via DevTools → Network → "Save all as HAR"
   till `D:\snajp-crm-forlaga\har\`, med ett testkonto/testdata i Twenty.

**Steg 1 – rea som CLI, version 6.7.0 (fungerar med nuvarande Node 24.11.0)**

Kräver Antons godkännande: nedladdning av `rea-agents@6.7.0` med beroenden från npm.

```powershell
# a) Ta bort den trasiga npx-posten (rör inga andra cacheposter)
npm.cmd cache npx rm a1722018f28f9df2

# b) Lokal installation på D:, utan installationsskript (frida blir då otillgängligt, behövs inte)
New-Item -ItemType Directory -Force D:\verktyg\rea-6.7.0
Set-Location D:\verktyg\rea-6.7.0
npm.cmd install --no-save --ignore-scripts rea-agents@6.7.0

# c) Kör från D:\verktyg\rea-6.7.0, aldrig inifrån snipe-leads eller rea-klonen
$env:NO_UPDATE_NOTIFIER = "1"
node .\node_modules\rea-agents\scripts\rea.mjs doctor --json
node .\node_modules\rea-agents\scripts\rea.mjs analyze-javascript-application "D:\snajp-crm-forlaga\twenty\packages\twenty-front" --json > D:\snajp-crm-forlaga\rea-ut\front.json
node .\node_modules\rea-agents\scripts\rea.mjs inspect-web-network-capture "D:\snajp-crm-forlaga\har\twenty-session.har" har --json > D:\snajp-crm-forlaga\rea-ut\har.json
```

Kommentarer: `--ignore-scripts` för `npm install` och att `rea.mjs` kan köras direkt med `node`
är **[antagande]** utifrån `package.json:42-45` och installation.md:338-345, där rea själv visar
formen `node <väg>\scripts\rea.mjs`. Varför inte `npx` i snipe-leads: npx inspekterar
anroparens `package.json` (installation.md:2263-2267), och rea:s dokumentation säger "run this
from a trusted directory outside the project you plan to analyze" (README.md:75-76).

Kör en analys i taget och kontrollera ledigt virtuellt minne före (maskinens regel om
`FreeVirtualMemory`).

**Steg 1b – bara om MCP verkligen behövs (godkännande: ändring av agentkonfiguration)**

Byt den globala npx-registreringen mot en lokal, projektbunden med absoluta sökvägar
(installation.md:338-353), från den katalog där den ska gälla:

```powershell
claude mcp remove --scope user rea
claude mcp add --scope local rea -- "C:\Program Files\nodejs\node.exe" "D:\verktyg\rea-6.7.0\node_modules\rea-agents\scripts\rea.mjs" mcp
```

Begränsa gärna med `REA_MCP_TOOL_FAMILIES=browser,session,javascript-runtime,application`
(mcp-contracts.md:2399-2424).

**Steg 1c – bara om 6.8+ behövs (godkännande: uppgradering av Node för hela datorn)**

Node måste upp till minst 24.22.1 (`package.json:46-48`). Det påverkar alla Node-projekt på
datorn, även snipe-leads; rekommenderas inte för det här ändamålet.

**Steg 2 – craft-anything, besökarvy i Clean room (valfritt)**

Kräver Antons godkännande: nedladdning av en körbar fil från GitHub Releases, och att han själv
loggar in i Twenty i det fönster som öppnas.

1. Hämta `craft-anything-<ver>-windows-x64-portable.zip` + `SHA256SUMS.txt` från
   `https://github.com/storytold/craft-anything/releases/latest` till `D:\verktyg\craft-anything\`.
2. Kontrollera innan körning:
   `Get-FileHash .\craft-anything-<ver>-windows-x64-portable.zip -Algorithm SHA256` mot
   `SHA256SUMS.txt`, och efter uppackning `Get-AuthenticodeSignature .\craft-anything-cli.exe`.
   Är status inte `Valid`: kör inte.
3. Packa upp på D:. `portable.txt` håller inställningar och inloggningsprofiler i
   `D:\verktyg\craft-anything\CraftAnythingData\` i stället för `%APPDATA%`
   (`settings.rs:340-344`).
4. Från `D:\verktyg\craft-anything\`:
   ```powershell
   .\craft-anything-cli.exe --clean-room doctor
   .\craft-anything-cli.exe commands
   ```
   Kör **inte** `setup` och **inte** `rebuild`.
5. Fångsten måste ske i en MCP-session (tool-status.md:64-66). Registrera tillfälligt, lokalt för
   en arbetskatalog på D: (inte snipe-leads):
   ```powershell
   claude mcp add --scope local craft-anything -- "D:\verktyg\craft-anything\craft-anything-cli.exe" --clean-room mcp --allow-web --allow-capture
   ```
   `--allow-run` krävs för att `web_site_open` och `web_site_sign_in` inte ska avvisas med
   `ConsentRequired` när ingen inbox finns (`crates/mcp/src/lib.rs:570, 590-595`). Lägg till den bara
   för den sessionen, och låt Claude Codes egen behörighetsfråga vara grinden per anrop.
   Ordningen för agenten: `web_site_sign_in {url: "https://app.twenty.com"}` (Anton loggar in och
   stänger fönstret) → för varje vy: `web_site_open` → `web_site_capture {output_directory: "D:\snajp-crm-forlaga\besokarvy\<vy>"}`
   → `web_page_states_capture` → `web_site_close`. Avsluta med `web_site_sign_out` och
   `claude mcp remove --scope local craft-anything`.
6. Kontrollera efteråt att inget skrivits till `Documents\Craft Anything` (OneDrive).

**Byggvägen** (`cargo install --path apps/craft-anything-cli`) rekommenderas inte nu: den kräver
`rustup update` till 1.97 (godkännande), MSVC-verktyg som inte är verifierade, och ett tungt
LTO-bygge på en maskin med känd minnesbrist. Görs den ändå: `CARGO_TARGET_DIR=D:\cargo-target`,
`cargo build --release -p craft-anything-cli -j 2`, inga andra tunga processer samtidigt.

### 3.4 Det Anton måste godkänna

| Åtgärd | Varför |
|---|---|
| `npm.cmd cache npx rm a1722018f28f9df2` | Tar bort den trasiga rea-posten i npm-cachen |
| Nedladdning av `rea-agents@6.7.0` (+ beroenden) från registry.npmjs.org till D: | Körbar tredjepartskod |
| Ev. ändring av `~/.claude.json` (ta bort user-registreringen, lägga till en lokal) | Global agentkonfiguration |
| Ev. Node-uppgradering till ≥24.22.1 | Bara om rea 6.8+ behövs; påverkar alla projekt |
| Nedladdning av craft-anything-zip från GitHub Releases | Körbar fil, signering ej garanterad |
| Inloggning i Twenty i craft-anythings fönster, och att profilen sparas tills `web_site_sign_out` | Sessionscookies lagras på disk |
| Ev. `rustup update` till 1.97 och ett lokalt bygge | Ändrar verktygskedjan; tungt bygge |

---

## 4. Öppna frågor

- Exakt filnamn och signeringsstatus för senaste craft-anything-release (kräver att någon tittar
  på Releases-sidan; inte gjort här).
- Om rea:s `analyze-javascript-application` klarar hela `twenty-front` utan att spräcka minnet
  (odokumenterat; prova på en modulkatalog först).
- Vad som tog bort `sourcemap-codec.mjs` ur npx-cachen (antivirus? avbruten installation?).
  Kolla Windows Säkerhet → Skyddshistorik före ominstallation.
- Om Anton vill ha strikt åtskillnad (läsare av källkoden ≠ byggare av Snajp CRM). Det avgör om
  craft-anythings Clean room tillför något utöver en vanlig webbläsare.
