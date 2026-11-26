# Snajps demofilm (click-through)

Fristående Remotion-projekt, ingen del av appen (`.dockerignore` utesluter `marknad`, rotens
`tsconfig.json` utesluter mappen). Filmen visar en Instagramreel hel och sedan produkten steg för steg,
med musik och klipp på takten.

Hur filmen kom till och alla Antons domar: [`docs/marknad/DEMOFILM-LEADS-2026-11-25.md`](../../docs/marknad/DEMOFILM-LEADS-2026-11-25.md).
Nästa steg (supportdelen): [`docs/marknad/UPPDRAG-DEMOFILM-SUPPORT.md`](../../docs/marknad/UPPDRAG-DEMOFILM-SUPPORT.md).

## Kom igång

Kräver Node 22 eller senare, `ffmpeg` och `ffprobe` i PATH, och bash (Git Bash på Windows).

```bash
cd marknad/demofilm
npm install
npx playwright install chromium
```

Iris-reelen renderas ur `marknad/video` och checkas inte in:

```bash
cd ../video
npm install
npm run ljud
npx remotion render src/index.ts Flode-4x5 ../demofilm/public/reel.mp4 --crf=14 --jpeg-quality=100
cd ../demofilm
```

`npm run ljud` kräver Python med numpy.

## Kommandon

| Kommando | Vad |
|---|---|
| `node verktyg/tider.mjs` | Tidslinjen: varje del, start i rutor och sekunder, musikavsnitten |
| `node verktyg/stills.mjs <mapp> <ruta> …` | Enskilda bildrutor att granska |
| `bash bygg.sh` | Hela filmen till `out/snajp-demo.mp4`, `out/snajp-demo-mobil.mp4` (under 30 MB) och `out/kontaktark.png` |
| `node rec/record-leads.mjs` | Spelar in leadsdelen på nytt. **Skriver över** `public/film/` och `src/data/film.json` |
| `node rec/utforska-support.mjs` | Skärmbilder och sidtext från demons kundtjänstdel till `explore/support/` |
| `npx remotion studio src/index.ts` | Förhandsvisning i webbläsaren |
| `npx tsc --noEmit -p tsconfig.json` | Typkontroll |

Miljövariabler: `DEMOFILM_TEMP=<mapp>` flyttar temporära filer (Remotion lämnar hundratals MB per körning
i TEMP), `CHROME_PATH=<fil>` pekar ut en egen headless Chrome.

## Hur den är byggd

- `src/data/film.json` är manuset: `clip` (en färdig film, spelas hel i full höjd), `title` (rubrikkort,
  ev. rader eller undertext) och `desktop` (en skärmbild med markör, bildtext och kamera). Längden anges
  i takter (`bars`) av musiken, 110 BPM.
- `src/Film.tsx` är motorn: kameran, markören, den flytande bildtexten, övergångarna, och `layout()` som
  lägger varje övertoning på ett taktslag. Ett klipp startar om takträkningen.
- `verktyg/tider.mjs` räknar samma tidslinje utan Remotion; `bygg.sh` stoppar om de två skiljer sig.
- `verktyg/ljud.mjs` lägger varje klipps eget ljud och musikbädden (`public/musik/badd-110bpm.mp3`) i
  varje avsnitt mellan klippen.
- `public/film/` är leadsdelens skärmbilder (godkända 2026-11-25), `public/fonts/` Fraunces och Geist (SIL
  OFL), `public/musik/` bädden som Anton valde.

## Regler

- Filma bara de publika exempelytorna `/demo` och `/forhandsvisning` på development. Development-databasen
  är en spegel av produktionen.
- Webbplatsbedömningen visas aldrig. Inga påståenden om svarsfrekvens. "Supportagent", aldrig "supportbot".
- Remotions licens: fri upp till tre anställda; större bolag behöver företagslicens före kommersiell
  användning.
