# Licensförteckning över beroendena

Genererad av `python scripts/licenser.py --skriv`. Redigera inte för hand:
kör skriptet igen. Grinden `python scripts/licenser.py --kontrollera` körs i
CI (jobbet `licenser` i `.github/workflows/verify.yml`) och fäller på
copyleft och okända licenser som inte står i
[`licenser-vitlista.json`](licenser-vitlista.json). ISO 27001 A.5.32.

- Genererad: 2026-11-18
- Python-miljö: 3.14.0 (win32)
- npm: läst ur lockfilerna `package-lock.json` (web) och
  `support-webb/package-lock.json` (agentsajten). `marknad/video/` byggs
  inte och är inte med.
- pip: `snajp-support/requirements.txt` och `scripts/requirements-scripts.txt`
  med alla transitiva beroenden, lästa ur de installerade paketens metadata.
  Versionerna är de som var installerade där filen genererades; en lokal
  miljö kan skilja sig från CI:s rena installation, och det är CI-körningen
  som avgör grinden. `dev` för pip betyder testberoenden (raderna efter
  `# test`) och driftskripten.

Antal paket: npm (support-webb): 136, npm (web): 211, pip (scripts): 1, pip (snajp-support): 63.

## Väntar på beslut eller är undantagna

Status `obeslutad` betyder att paketet står i vitlistan utan namn i
`godkant_av`: grinden släpper igenom det, men licensen är inte beslutad.
Bedömningen är ett underlag, inte ett beslut.

| Ekosystem | Projekt | Paket | Version | Licens | Status | Motivering | Bedömning (underlag) |
|---|---|---|---|---|---|---|---|
| npm | support-webb | @img/sharp-libvips-darwin-arm64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-darwin-x64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-linux-arm | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-linux-arm64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-linux-ppc64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-linux-riscv64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-linux-s390x | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-linux-x64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-linuxmusl-arm64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-libvips-linuxmusl-x64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | support-webb | @img/sharp-wasm32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later AND MIT | obeslutad | obeslutad, kräver Antons godkännande | Samma libvips som ovan, inbyggt i ett valfritt plattformspaket (Windows respektive WebAssembly) som inte installeras i driften. Föreslås godkänd. |
| npm | support-webb | @img/sharp-win32-arm64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | Samma libvips som ovan, inbyggt i ett valfritt plattformspaket (Windows respektive WebAssembly) som inte installeras i driften. Föreslås godkänd. |
| npm | support-webb | @img/sharp-win32-ia32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | Samma libvips som ovan, inbyggt i ett valfritt plattformspaket (Windows respektive WebAssembly) som inte installeras i driften. Föreslås godkänd. |
| npm | support-webb | @img/sharp-win32-x64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | Samma libvips som ovan, inbyggt i ett valfritt plattformspaket (Windows respektive WebAssembly) som inte installeras i driften. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-darwin-arm64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-darwin-x64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-linux-arm | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-linux-arm64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-linux-ppc64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-linux-riscv64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-linux-s390x | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-linux-x64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-linuxmusl-arm64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-libvips-linuxmusl-x64 | 1.3.4 | LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | libvips (LGPL-3.0-or-later) levereras som förbyggt delat bibliotek som sharp länkar dynamiskt; Next.js använder sharp för bildoptimering. LGPL kräver då att biblioteket går att byta ut och att licenstexten följer med, inte att vår kod öppnas. Plattformspaketen är valfria: bara det som passar driftens plattform (Linux) installeras. Föreslås godkänd. |
| npm | web | @img/sharp-wasm32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later AND MIT | obeslutad | obeslutad, kräver Antons godkännande | Samma libvips som ovan, inbyggt i ett valfritt plattformspaket (Windows respektive WebAssembly) som inte installeras i driften. Föreslås godkänd. |
| npm | web | @img/sharp-win32-arm64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | Samma libvips som ovan, inbyggt i ett valfritt plattformspaket (Windows respektive WebAssembly) som inte installeras i driften. Föreslås godkänd. |
| npm | web | @img/sharp-win32-ia32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | Samma libvips som ovan, inbyggt i ett valfritt plattformspaket (Windows respektive WebAssembly) som inte installeras i driften. Föreslås godkänd. |
| npm | web | @img/sharp-win32-x64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | obeslutad | obeslutad, kräver Antons godkännande | Samma libvips som ovan, inbyggt i ett valfritt plattformspaket (Windows respektive WebAssembly) som inte installeras i driften. Föreslås godkänd. |
| npm | web | gsap | 3.15.1 | Standard 'no charge' license: https://gsap.com/standard-license. | obeslutad | obeslutad, kräver Antons godkännande | Ingen öppen källkodslicens utan GreenSocks egna avgiftsfria standardlicens (proprietär). Villkoren behöver läsas mot hur Snajp använder biblioteket (animationer på webbplatsen) innan beslut. |
| pip | scripts | psycopg2-binary | 2.9.12 | LGPL | obeslutad | obeslutad, kräver Antons godkännande | LGPL-3.0 med undantag (OpenSSL), importeras som oförändrat bibliotek. Används bara av driftskripten i scripts/ och CI:s databasjobb, aldrig i den deployade containern. Föreslås godkänd. |
| pip | snajp-support | certifi | 2026.6.17 | MPL-2.0 | obeslutad | obeslutad, kräver Antons godkännande | MPL-2.0 är filbaserad copyleft: bara ändringar i certifis egna filer måste delas. Vi använder paketet oförändrat (CA-certifikaten via httpx/requests). Föreslås godkänd. |
| pip | snajp-support | tqdm | 4.67.3 | MPL-2.0 AND MIT | obeslutad | obeslutad, kräver Antons godkännande | Transitivt beroende (förloppsindikator), används oförändrat. MPL-2.0 är filbaserad copyleft och påverkar inte vår kod. Föreslås godkänd. |

## Alla paket

| Ekosystem | Projekt | Paket | Version | Licens | Källa | Prod/dev |
|---|---|---|---|---|---|---|
| npm | support-webb | @alloc/quick-lru | 5.3.0 | MIT | lockfil | dev |
| npm | support-webb | @emnapi/runtime | 1.11.3 | MIT | lockfil | prod |
| npm | support-webb | @img/colour | 1.1.0 | MIT | lockfil | prod |
| npm | support-webb | @img/sharp-darwin-arm64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-darwin-x64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-freebsd-wasm32 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-darwin-arm64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-darwin-x64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-linux-arm | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-linux-arm64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-linux-ppc64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-linux-riscv64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-linux-s390x | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-linux-x64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-linuxmusl-arm64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-libvips-linuxmusl-x64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-linux-arm | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-linux-arm64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-linux-ppc64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-linux-riscv64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-linux-s390x | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-linux-x64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-linuxmusl-arm64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-linuxmusl-x64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-wasm32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later AND MIT | lockfil | prod |
| npm | support-webb | @img/sharp-webcontainers-wasm32 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @img/sharp-win32-arm64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-win32-ia32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @img/sharp-win32-x64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | lockfil | prod |
| npm | support-webb | @jridgewell/gen-mapping | 0.3.13 | MIT | lockfil | dev |
| npm | support-webb | @jridgewell/resolve-uri | 3.1.2 | MIT | lockfil | dev |
| npm | support-webb | @jridgewell/sourcemap-codec | 1.6.0 | MIT | lockfil | dev |
| npm | support-webb | @jridgewell/trace-mapping | 0.3.31 | MIT | lockfil | dev |
| npm | support-webb | @next/env | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @next/swc-darwin-arm64 | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @next/swc-darwin-x64 | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @next/swc-linux-arm64-gnu | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @next/swc-linux-arm64-musl | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @next/swc-linux-x64-gnu | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @next/swc-linux-x64-musl | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @next/swc-win32-arm64-msvc | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @next/swc-win32-x64-msvc | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | @nodelib/fs.scandir | 2.1.5 | MIT | lockfil | dev |
| npm | support-webb | @nodelib/fs.stat | 2.0.5 | MIT | lockfil | dev |
| npm | support-webb | @nodelib/fs.walk | 1.2.8 | MIT | lockfil | dev |
| npm | support-webb | @swc/helpers | 0.5.23 | Apache-2.0 | lockfil | prod |
| npm | support-webb | @types/node | 26.6.6 | MIT | lockfil | dev |
| npm | support-webb | @types/react | 19.3.0 | MIT | lockfil | dev |
| npm | support-webb | @types/react-dom | 19.3.0 | MIT | lockfil | dev |
| npm | support-webb | any-promise | 1.3.0 | MIT | lockfil | dev |
| npm | support-webb | anymatch | 3.1.3 | ISC | lockfil | dev |
| npm | support-webb | arg | 5.0.2 | MIT | lockfil | dev |
| npm | support-webb | autoprefixer | 10.6.2 | MIT | lockfil | dev |
| npm | support-webb | baseline-browser-mapping | 2.11.23 | Apache-2.0 | lockfil | prod |
| npm | support-webb | binary-extensions | 2.3.0 | MIT | lockfil | dev |
| npm | support-webb | braces | 3.0.3 | MIT | lockfil | dev |
| npm | support-webb | browserslist | 4.28.9 | MIT | lockfil | dev |
| npm | support-webb | camelcase-css | 2.0.1 | MIT | lockfil | dev |
| npm | support-webb | caniuse-lite | 1.0.30001810 | CC-BY-4.0 | lockfil | prod |
| npm | support-webb | chokidar | 3.6.0 | MIT | lockfil | dev |
| npm | support-webb | client-only | 0.0.1 | MIT | lockfil | prod |
| npm | support-webb | commander | 4.1.1 | MIT | lockfil | dev |
| npm | support-webb | csstype | 3.2.3 | MIT | lockfil | dev |
| npm | support-webb | detect-libc | 2.1.2 | Apache-2.0 | lockfil | prod |
| npm | support-webb | didyoumean | 1.2.2 | Apache-2.0 | lockfil | dev |
| npm | support-webb | dlv | 1.1.3 | MIT | lockfil | dev |
| npm | support-webb | electron-to-chromium | 1.5.427 | ISC | lockfil | dev |
| npm | support-webb | es-errors | 1.3.0 | MIT | lockfil | dev |
| npm | support-webb | escalade | 3.2.0 | MIT | lockfil | dev |
| npm | support-webb | fast-glob | 3.3.3 | MIT | lockfil | dev |
| npm | support-webb | fastq | 1.20.3 | ISC | lockfil | dev |
| npm | support-webb | fdir | 6.5.0 | MIT | lockfil | dev |
| npm | support-webb | fill-range | 7.1.1 | MIT | lockfil | dev |
| npm | support-webb | fraction.js | 5.3.4 | MIT | lockfil | dev |
| npm | support-webb | fsevents | 2.3.3 | MIT | lockfil | dev |
| npm | support-webb | function-bind | 1.1.2 | MIT | lockfil | dev |
| npm | support-webb | glob-parent | 5.1.2 | ISC | lockfil | dev |
| npm | support-webb | glob-parent | 6.0.2 | ISC | lockfil | dev |
| npm | support-webb | hasown | 2.0.4 | MIT | lockfil | dev |
| npm | support-webb | is-binary-path | 2.1.0 | MIT | lockfil | dev |
| npm | support-webb | is-core-module | 2.16.2 | MIT | lockfil | dev |
| npm | support-webb | is-extglob | 2.1.1 | MIT | lockfil | dev |
| npm | support-webb | is-glob | 4.0.3 | MIT | lockfil | dev |
| npm | support-webb | is-number | 7.0.0 | MIT | lockfil | dev |
| npm | support-webb | jiti | 1.21.7 | MIT | lockfil | dev |
| npm | support-webb | lilconfig | 3.1.3 | MIT | lockfil | dev |
| npm | support-webb | lines-and-columns | 1.2.4 | MIT | lockfil | dev |
| npm | support-webb | lucide-react | 0.468.0 | ISC | lockfil | prod |
| npm | support-webb | merge2 | 1.4.1 | MIT | lockfil | dev |
| npm | support-webb | micromatch | 4.0.8 | MIT | lockfil | dev |
| npm | support-webb | mz | 2.7.0 | MIT | lockfil | dev |
| npm | support-webb | nanoid | 3.3.20 | MIT | lockfil | prod |
| npm | support-webb | next | 16.4.6 | MIT | lockfil | prod |
| npm | support-webb | node-releases | 2.0.55 | MIT | lockfil | dev |
| npm | support-webb | normalize-path | 3.0.0 | MIT | lockfil | dev |
| npm | support-webb | object-assign | 4.1.1 | MIT | lockfil | dev |
| npm | support-webb | object-hash | 3.0.0 | MIT | lockfil | dev |
| npm | support-webb | path-parse | 1.0.7 | MIT | lockfil | dev |
| npm | support-webb | picocolors | 1.1.1 | ISC | lockfil | prod |
| npm | support-webb | picomatch | 2.3.2 | MIT | lockfil | dev |
| npm | support-webb | picomatch | 4.0.7 | MIT | lockfil | dev |
| npm | support-webb | pirates | 4.0.7 | MIT | lockfil | dev |
| npm | support-webb | postcss | 8.5.23 | MIT | lockfil | prod |
| npm | support-webb | postcss | 8.5.33 | MIT | lockfil | dev |
| npm | support-webb | postcss-import | 15.1.0 | MIT | lockfil | dev |
| npm | support-webb | postcss-js | 4.1.0 | MIT | lockfil | dev |
| npm | support-webb | postcss-load-config | 6.0.1 | MIT | lockfil | dev |
| npm | support-webb | postcss-nested | 6.2.0 | MIT | lockfil | dev |
| npm | support-webb | postcss-selector-parser | 6.1.6 | MIT | lockfil | dev |
| npm | support-webb | postcss-value-parser | 4.2.0 | MIT | lockfil | dev |
| npm | support-webb | queue-microtask | 1.2.3 | MIT | lockfil | dev |
| npm | support-webb | react | 19.3.1 | MIT | lockfil | prod |
| npm | support-webb | react-dom | 19.3.1 | MIT | lockfil | prod |
| npm | support-webb | read-cache | 1.0.2 | MIT | lockfil | dev |
| npm | support-webb | readdirp | 3.6.0 | MIT | lockfil | dev |
| npm | support-webb | resolve | 1.22.12 | MIT | lockfil | dev |
| npm | support-webb | reusify | 1.1.0 | MIT | lockfil | dev |
| npm | support-webb | run-parallel | 1.2.0 | MIT | lockfil | dev |
| npm | support-webb | scheduler | 0.28.0 | MIT | lockfil | prod |
| npm | support-webb | semver | 7.8.6 | ISC | lockfil | prod |
| npm | support-webb | sharp | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | support-webb | source-map-js | 1.2.2 | BSD-3-Clause | lockfil | prod |
| npm | support-webb | styled-jsx | 5.1.6 | MIT | lockfil | prod |
| npm | support-webb | sucrase | 3.35.1 | MIT | lockfil | dev |
| npm | support-webb | supports-preserve-symlinks-flag | 1.0.0 | MIT | lockfil | dev |
| npm | support-webb | tailwindcss | 3.4.19 | MIT | lockfil | dev |
| npm | support-webb | thenify | 3.3.1 | MIT | lockfil | dev |
| npm | support-webb | thenify-all | 1.6.0 | MIT | lockfil | dev |
| npm | support-webb | tinyglobby | 0.2.17 | MIT | lockfil | dev |
| npm | support-webb | to-regex-range | 5.0.1 | MIT | lockfil | dev |
| npm | support-webb | ts-interface-checker | 0.1.13 | Apache-2.0 | lockfil | dev |
| npm | support-webb | tslib | 2.9.1 | 0BSD | lockfil | prod |
| npm | support-webb | typescript | 5.9.3 | Apache-2.0 | lockfil | dev |
| npm | support-webb | undici-types | 8.9.0 | MIT | lockfil | dev |
| npm | support-webb | update-browserslist-db | 1.3.3 | MIT | lockfil | dev |
| npm | support-webb | util-deprecate | 1.0.2 | MIT | lockfil | dev |
| npm | web | @ai-sdk/gateway | 4.0.149 | Apache-2.0 | lockfil | prod |
| npm | web | @ai-sdk/openai | 4.0.121 | Apache-2.0 | lockfil | prod |
| npm | web | @ai-sdk/provider | 4.0.39 | Apache-2.0 | lockfil | prod |
| npm | web | @ai-sdk/provider-utils | 5.0.82 | Apache-2.0 | lockfil | prod |
| npm | web | @alloc/quick-lru | 5.2.0 | MIT | lockfil | dev |
| npm | web | @auth/core | 0.41.3 | ISC | lockfil | prod |
| npm | web | @babel/runtime | 7.29.2 | MIT | lockfil | prod |
| npm | web | @emnapi/runtime | 1.11.3 | MIT | lockfil | prod |
| npm | web | @img/colour | 1.1.0 | MIT | lockfil | prod |
| npm | web | @img/sharp-darwin-arm64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-darwin-x64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-freebsd-wasm32 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-libvips-darwin-arm64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-darwin-x64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-linux-arm | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-linux-arm64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-linux-ppc64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-linux-riscv64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-linux-s390x | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-linux-x64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-linuxmusl-arm64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-libvips-linuxmusl-x64 | 1.3.4 | LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-linux-arm | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-linux-arm64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-linux-ppc64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-linux-riscv64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-linux-s390x | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-linux-x64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-linuxmusl-arm64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-linuxmusl-x64 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-wasm32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later AND MIT | lockfil | prod |
| npm | web | @img/sharp-webcontainers-wasm32 | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | @img/sharp-win32-arm64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-win32-ia32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | lockfil | prod |
| npm | web | @img/sharp-win32-x64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | lockfil | prod |
| npm | web | @jridgewell/gen-mapping | 0.3.13 | MIT | lockfil | dev |
| npm | web | @jridgewell/resolve-uri | 3.1.2 | MIT | lockfil | dev |
| npm | web | @jridgewell/sourcemap-codec | 1.5.5 | MIT | lockfil | dev |
| npm | web | @jridgewell/trace-mapping | 0.3.31 | MIT | lockfil | dev |
| npm | web | @next/env | 16.4.6 | MIT | lockfil | prod |
| npm | web | @next/swc-darwin-arm64 | 16.4.6 | MIT | lockfil | prod |
| npm | web | @next/swc-darwin-x64 | 16.4.6 | MIT | lockfil | prod |
| npm | web | @next/swc-linux-arm64-gnu | 16.4.6 | MIT | lockfil | prod |
| npm | web | @next/swc-linux-arm64-musl | 16.4.6 | MIT | lockfil | prod |
| npm | web | @next/swc-linux-x64-gnu | 16.4.6 | MIT | lockfil | prod |
| npm | web | @next/swc-linux-x64-musl | 16.4.6 | MIT | lockfil | prod |
| npm | web | @next/swc-win32-arm64-msvc | 16.4.6 | MIT | lockfil | prod |
| npm | web | @next/swc-win32-x64-msvc | 16.4.6 | MIT | lockfil | prod |
| npm | web | @nodelib/fs.scandir | 2.1.5 | MIT | lockfil | dev |
| npm | web | @nodelib/fs.stat | 2.0.5 | MIT | lockfil | dev |
| npm | web | @nodelib/fs.walk | 1.2.8 | MIT | lockfil | dev |
| npm | web | @panva/hkdf | 1.2.1 | MIT | lockfil | prod |
| npm | web | @standard-schema/spec | 1.1.0 | MIT | lockfil | prod |
| npm | web | @swc/helpers | 0.5.23 | Apache-2.0 | lockfil | prod |
| npm | web | @types/d3-array | 3.2.2 | MIT | lockfil | prod |
| npm | web | @types/d3-color | 3.1.3 | MIT | lockfil | prod |
| npm | web | @types/d3-ease | 3.0.2 | MIT | lockfil | prod |
| npm | web | @types/d3-interpolate | 3.0.4 | MIT | lockfil | prod |
| npm | web | @types/d3-path | 3.1.1 | MIT | lockfil | prod |
| npm | web | @types/d3-scale | 4.0.9 | MIT | lockfil | prod |
| npm | web | @types/d3-shape | 3.1.8 | MIT | lockfil | prod |
| npm | web | @types/d3-time | 3.0.4 | MIT | lockfil | prod |
| npm | web | @types/d3-timer | 3.0.2 | MIT | lockfil | prod |
| npm | web | @types/node | 26.6.6 | MIT | lockfil | dev |
| npm | web | @types/pg | 8.23.1 | MIT | lockfil | dev |
| npm | web | @types/react | 19.3.0 | MIT | lockfil | dev |
| npm | web | @types/react-dom | 19.3.0 | MIT | lockfil | dev |
| npm | web | @vercel/oidc | 3.2.0 | Apache-2.0 | lockfil | prod |
| npm | web | @workflow/serde | 4.1.0 | Apache-2.0 | lockfil | prod |
| npm | web | ai | 7.0.176 | Apache-2.0 | lockfil | prod |
| npm | web | any-promise | 1.3.0 | MIT | lockfil | dev |
| npm | web | anymatch | 3.1.3 | ISC | lockfil | dev |
| npm | web | arg | 5.0.2 | MIT | lockfil | dev |
| npm | web | autoprefixer | 10.6.2 | MIT | lockfil | dev |
| npm | web | baseline-browser-mapping | 2.11.38 | Apache-2.0 | lockfil | prod |
| npm | web | binary-extensions | 2.3.0 | MIT | lockfil | dev |
| npm | web | braces | 3.0.3 | MIT | lockfil | dev |
| npm | web | browserslist | 4.29.6 | MIT | lockfil | dev |
| npm | web | camelcase-css | 2.0.1 | MIT | lockfil | dev |
| npm | web | caniuse-lite | 1.0.30001826 | CC-BY-4.0 | lockfil | prod |
| npm | web | chokidar | 3.6.0 | MIT | lockfil | dev |
| npm | web | client-only | 0.0.1 | MIT | lockfil | prod |
| npm | web | clsx | 2.1.1 | MIT | lockfil | prod |
| npm | web | commander | 4.1.1 | MIT | lockfil | dev |
| npm | web | csstype | 3.2.3 | MIT | lockfil | prod |
| npm | web | d3-array | 3.2.4 | ISC | lockfil | prod |
| npm | web | d3-color | 3.1.0 | ISC | lockfil | prod |
| npm | web | d3-ease | 3.0.1 | BSD-3-Clause | lockfil | prod |
| npm | web | d3-format | 3.1.2 | ISC | lockfil | prod |
| npm | web | d3-interpolate | 3.0.1 | ISC | lockfil | prod |
| npm | web | d3-path | 3.1.0 | ISC | lockfil | prod |
| npm | web | d3-scale | 4.0.2 | ISC | lockfil | prod |
| npm | web | d3-shape | 3.2.0 | ISC | lockfil | prod |
| npm | web | d3-time | 3.1.0 | ISC | lockfil | prod |
| npm | web | d3-time-format | 4.1.0 | ISC | lockfil | prod |
| npm | web | d3-timer | 3.0.1 | ISC | lockfil | prod |
| npm | web | decimal.js-light | 2.5.1 | MIT | lockfil | prod |
| npm | web | detect-libc | 2.1.2 | Apache-2.0 | lockfil | prod |
| npm | web | didyoumean | 1.2.2 | Apache-2.0 | lockfil | dev |
| npm | web | dlv | 1.1.3 | MIT | lockfil | dev |
| npm | web | dom-helpers | 5.2.1 | MIT | lockfil | prod |
| npm | web | electron-to-chromium | 1.5.489 | ISC | lockfil | dev |
| npm | web | es-errors | 1.3.0 | MIT | lockfil | dev |
| npm | web | escalade | 3.2.0 | MIT | lockfil | dev |
| npm | web | eventemitter3 | 4.0.7 | MIT | lockfil | prod |
| npm | web | eventsource-parser | 3.1.1 | MIT | lockfil | prod |
| npm | web | fast-equals | 5.4.0 | MIT | lockfil | prod |
| npm | web | fast-glob | 3.3.3 | MIT | lockfil | dev |
| npm | web | fastq | 1.20.1 | ISC | lockfil | dev |
| npm | web | fdir | 6.5.0 | MIT | lockfil | dev |
| npm | web | fill-range | 7.1.1 | MIT | lockfil | dev |
| npm | web | fraction.js | 5.3.4 | MIT | lockfil | dev |
| npm | web | fsevents | 2.3.3 | MIT | lockfil | dev |
| npm | web | function-bind | 1.1.2 | MIT | lockfil | dev |
| npm | web | glob-parent | 5.1.2 | ISC | lockfil | dev |
| npm | web | glob-parent | 6.0.2 | ISC | lockfil | dev |
| npm | web | gsap | 3.15.1 | Standard 'no charge' license: https://gsap.com/standard-license. | lockfil | prod |
| npm | web | hasown | 2.0.3 | MIT | lockfil | dev |
| npm | web | internmap | 2.0.3 | ISC | lockfil | prod |
| npm | web | is-binary-path | 2.1.0 | MIT | lockfil | dev |
| npm | web | is-core-module | 2.16.2 | MIT | lockfil | dev |
| npm | web | is-extglob | 2.1.1 | MIT | lockfil | dev |
| npm | web | is-glob | 4.0.3 | MIT | lockfil | dev |
| npm | web | is-number | 7.0.0 | MIT | lockfil | dev |
| npm | web | jiti | 1.21.7 | MIT | lockfil | dev |
| npm | web | jose | 6.2.9 | MIT | lockfil | prod |
| npm | web | js-tokens | 4.0.0 | MIT | lockfil | prod |
| npm | web | json-schema | 0.4.0 | (AFL-2.1 OR BSD-3-Clause) | lockfil | prod |
| npm | web | lenis | 1.3.27 | MIT | lockfil | prod |
| npm | web | lilconfig | 3.1.3 | MIT | lockfil | dev |
| npm | web | lines-and-columns | 1.2.4 | MIT | lockfil | dev |
| npm | web | lodash | 4.18.1 | MIT | lockfil | prod |
| npm | web | loose-envify | 1.4.0 | MIT | lockfil | prod |
| npm | web | lucide-react | 0.468.0 | ISC | lockfil | prod |
| npm | web | merge2 | 1.4.1 | MIT | lockfil | dev |
| npm | web | micromatch | 4.0.8 | MIT | lockfil | dev |
| npm | web | mz | 2.7.0 | MIT | lockfil | dev |
| npm | web | nanoid | 3.3.20 | MIT | lockfil | prod |
| npm | web | next | 16.4.6 | MIT | lockfil | prod |
| npm | web | next-auth | 5.0.0-beta.32 | ISC | lockfil | prod |
| npm | web | node-releases | 2.0.65 | MIT | lockfil | dev |
| npm | web | normalize-path | 3.0.0 | MIT | lockfil | dev |
| npm | web | oauth4webapi | 3.8.7 | MIT | lockfil | prod |
| npm | web | object-assign | 4.1.1 | MIT | lockfil | prod |
| npm | web | object-hash | 3.0.0 | MIT | lockfil | dev |
| npm | web | path-parse | 1.0.7 | MIT | lockfil | dev |
| npm | web | pg | 8.23.1 | MIT | lockfil | prod |
| npm | web | pg-cloudflare | 1.4.1 | MIT | lockfil | prod |
| npm | web | pg-connection-string | 2.14.1 | MIT | lockfil | prod |
| npm | web | pg-int8 | 1.0.1 | ISC | lockfil | prod |
| npm | web | pg-pool | 3.14.0 | MIT | lockfil | prod |
| npm | web | pg-protocol | 1.16.1 | MIT | lockfil | prod |
| npm | web | pg-types | 2.2.0 | MIT | lockfil | prod |
| npm | web | pgpass | 1.0.5 | MIT | lockfil | prod |
| npm | web | picocolors | 1.1.1 | ISC | lockfil | prod |
| npm | web | picomatch | 2.3.2 | MIT | lockfil | dev |
| npm | web | picomatch | 4.0.4 | MIT | lockfil | dev |
| npm | web | pify | 2.3.0 | MIT | lockfil | dev |
| npm | web | pirates | 4.0.7 | MIT | lockfil | dev |
| npm | web | postcss | 8.5.23 | MIT | lockfil | prod |
| npm | web | postcss | 8.5.33 | MIT | lockfil | dev |
| npm | web | postcss-import | 15.1.0 | MIT | lockfil | dev |
| npm | web | postcss-js | 4.1.0 | MIT | lockfil | dev |
| npm | web | postcss-load-config | 6.0.1 | MIT | lockfil | dev |
| npm | web | postcss-nested | 6.2.0 | MIT | lockfil | dev |
| npm | web | postcss-selector-parser | 6.1.6 | MIT | lockfil | dev |
| npm | web | postcss-value-parser | 4.2.0 | MIT | lockfil | dev |
| npm | web | postgres-array | 2.0.0 | MIT | lockfil | prod |
| npm | web | postgres-bytea | 1.0.1 | MIT | lockfil | prod |
| npm | web | postgres-date | 1.0.7 | MIT | lockfil | prod |
| npm | web | postgres-interval | 1.2.0 | MIT | lockfil | prod |
| npm | web | preact | 10.24.3 | MIT | lockfil | prod |
| npm | web | preact-render-to-string | 6.5.11 | MIT | lockfil | prod |
| npm | web | prop-types | 15.8.1 | MIT | lockfil | prod |
| npm | web | queue-microtask | 1.2.3 | MIT | lockfil | dev |
| npm | web | react | 19.3.1 | MIT | lockfil | prod |
| npm | web | react-dom | 19.3.1 | MIT | lockfil | prod |
| npm | web | react-is | 16.13.1 | MIT | lockfil | prod |
| npm | web | react-is | 18.3.1 | MIT | lockfil | prod |
| npm | web | react-smooth | 4.0.4 | MIT | lockfil | prod |
| npm | web | react-transition-group | 4.4.5 | BSD-3-Clause | lockfil | prod |
| npm | web | read-cache | 1.0.0 | MIT | lockfil | dev |
| npm | web | readdirp | 3.6.0 | MIT | lockfil | dev |
| npm | web | recharts | 2.15.4 | MIT | lockfil | prod |
| npm | web | recharts-scale | 0.4.5 | MIT | lockfil | prod |
| npm | web | resolve | 1.22.12 | MIT | lockfil | dev |
| npm | web | reusify | 1.1.0 | MIT | lockfil | dev |
| npm | web | run-parallel | 1.2.0 | MIT | lockfil | dev |
| npm | web | scheduler | 0.28.0 | MIT | lockfil | prod |
| npm | web | semver | 7.8.6 | ISC | lockfil | prod |
| npm | web | sharp | 0.35.5 | Apache-2.0 | lockfil | prod |
| npm | web | source-map-js | 1.2.2 | BSD-3-Clause | lockfil | prod |
| npm | web | split2 | 4.2.0 | ISC | lockfil | prod |
| npm | web | styled-jsx | 5.1.6 | MIT | lockfil | prod |
| npm | web | sucrase | 3.35.1 | MIT | lockfil | dev |
| npm | web | supports-preserve-symlinks-flag | 1.0.0 | MIT | lockfil | dev |
| npm | web | tailwindcss | 3.4.19 | MIT | lockfil | dev |
| npm | web | thenify | 3.3.1 | MIT | lockfil | dev |
| npm | web | thenify-all | 1.6.0 | MIT | lockfil | dev |
| npm | web | tiny-invariant | 1.3.3 | MIT | lockfil | prod |
| npm | web | tinyglobby | 0.2.16 | MIT | lockfil | dev |
| npm | web | to-regex-range | 5.0.1 | MIT | lockfil | dev |
| npm | web | ts-interface-checker | 0.1.13 | Apache-2.0 | lockfil | dev |
| npm | web | tslib | 2.8.1 | 0BSD | lockfil | prod |
| npm | web | typescript | 5.9.3 | Apache-2.0 | lockfil | dev |
| npm | web | undici-types | 8.9.0 | MIT | lockfil | dev |
| npm | web | update-browserslist-db | 1.4.0 | MIT | lockfil | dev |
| npm | web | util-deprecate | 1.0.2 | MIT | lockfil | dev |
| npm | web | victory-vendor | 36.9.2 | MIT AND ISC | lockfil | prod |
| npm | web | xtend | 4.0.2 | MIT | lockfil | prod |
| npm | web | zod | 4.6.7 | MIT | lockfil | prod |
| pip | scripts | psycopg2-binary | 2.9.12 | LGPL | klassificerare | dev |
| pip | snajp-support | annotated-doc | 0.0.4 | MIT | License-Expression | prod |
| pip | snajp-support | annotated-types | 0.7.0 | MIT | klassificerare | prod |
| pip | snajp-support | anyio | 4.14.1 | MIT | License-Expression | prod |
| pip | snajp-support | asyncpg | 0.31.0 | Apache-2.0 | License-Expression | prod |
| pip | snajp-support | attrs | 26.1.0 | MIT | License-Expression | prod |
| pip | snajp-support | certifi | 2026.6.17 | MPL-2.0 | klassificerare | prod |
| pip | snajp-support | cffi | 2.1.0 | MIT-0 | License-Expression | prod |
| pip | snajp-support | charset-normalizer | 3.4.7 | MIT | License-fält | prod |
| pip | snajp-support | click | 8.4.2 | BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | colorama | 0.4.6 | BSD | klassificerare | prod |
| pip | snajp-support | cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | distro | 1.9.0 | Apache-2.0 | klassificerare | prod |
| pip | snajp-support | fakeredis | 2.37.1 | BSD-3-Clause | License-Expression | dev |
| pip | snajp-support | fastapi | 0.139.0 | MIT | License-Expression | prod |
| pip | snajp-support | google-auth | 2.53.0 | Apache-2.0 | klassificerare | prod |
| pip | snajp-support | griffelib | 2.0.2 | ISC | License-Expression | prod |
| pip | snajp-support | h11 | 0.16.0 | MIT | klassificerare | prod |
| pip | snajp-support | httpcore | 1.0.9 | BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | httptools | 0.8.0 | MIT | License-Expression | prod |
| pip | snajp-support | httpx | 0.28.1 | BSD | klassificerare | prod |
| pip | snajp-support | httpx-sse | 0.4.3 | MIT | License-fält | prod |
| pip | snajp-support | idna | 3.18 | BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | iniconfig | 2.3.0 | MIT | License-Expression | dev |
| pip | snajp-support | jiter | 0.15.0 | MIT | License-Expression | prod |
| pip | snajp-support | jmespath | 1.1.0 | MIT | klassificerare | prod |
| pip | snajp-support | jsonschema | 4.26.0 | MIT | License-Expression | prod |
| pip | snajp-support | jsonschema-specifications | 2025.9.1 | MIT | License-Expression | prod |
| pip | snajp-support | mcp | 1.28.1 | MIT | klassificerare | prod |
| pip | snajp-support | openai | 2.53.0 | Apache-2.0 | klassificerare | prod |
| pip | snajp-support | openai-agents | 0.19.4 | MIT | License-Expression | prod |
| pip | snajp-support | packaging | 25.0 | Apache-2.0 OR BSD | klassificerare | dev |
| pip | snajp-support | pluggy | 1.6.0 | MIT | klassificerare | dev |
| pip | snajp-support | pyasn1 | 0.6.3 | BSD-2-Clause | License-fält | prod |
| pip | snajp-support | pyasn1_modules | 0.4.2 | BSD | klassificerare | prod |
| pip | snajp-support | pycparser | 3.0 | BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | pydantic | 2.13.4 | MIT | License-Expression | prod |
| pip | snajp-support | pydantic-settings | 2.14.2 | MIT | License-Expression | prod |
| pip | snajp-support | pydantic_core | 2.46.4 | MIT | License-Expression | prod |
| pip | snajp-support | Pygments | 2.20.0 | BSD-2-Clause | License-Expression | dev |
| pip | snajp-support | PyJWT | 2.13.0 | MIT | License-Expression | prod |
| pip | snajp-support | pypdf | 6.16.2 | BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | pytest | 9.1.1 | MIT | License-Expression | dev |
| pip | snajp-support | python-dotenv | 1.2.2 | BSD-3-Clause | License-fält | prod |
| pip | snajp-support | python-multipart | 0.0.32 | Apache-2.0 | License-Expression | prod |
| pip | snajp-support | pywin32 | 312 | PSF-2.0 | klassificerare | prod |
| pip | snajp-support | PyYAML | 6.0.3 | MIT | klassificerare | prod |
| pip | snajp-support | redis | 6.4.0 | MIT | License-Expression | prod |
| pip | snajp-support | referencing | 0.37.0 | MIT | License-Expression | prod |
| pip | snajp-support | requests | 2.34.2 | Apache-2.0 | klassificerare | prod |
| pip | snajp-support | rpds-py | 2026.6.3 | MIT | License-Expression | prod |
| pip | snajp-support | scrapegraph-py | 2.1.0 | MIT | License-Expression | prod |
| pip | snajp-support | sniffio | 1.3.1 | Apache-2.0 OR MIT | klassificerare | prod |
| pip | snajp-support | sortedcontainers | 2.4.0 | Apache-2.0 | klassificerare | dev |
| pip | snajp-support | sse-starlette | 3.4.5 | BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | starlette | 1.3.1 | BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | tqdm | 4.67.3 | MPL-2.0 AND MIT | License-fält | prod |
| pip | snajp-support | typing-inspection | 0.4.2 | MIT | License-Expression | prod |
| pip | snajp-support | typing_extensions | 4.16.0 | PSF-2.0 | License-Expression | prod |
| pip | snajp-support | tzdata | 2026.2 | Apache-2.0 | License-fält | prod |
| pip | snajp-support | urllib3 | 2.7.0 | MIT | License-Expression | prod |
| pip | snajp-support | uvicorn | 0.51.0 | BSD-3-Clause | License-Expression | prod |
| pip | snajp-support | watchfiles | 1.2.0 | MIT | klassificerare | prod |
| pip | snajp-support | websockets | 16.0 | BSD-3-Clause | License-Expression | prod |
