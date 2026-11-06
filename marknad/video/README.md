# Snajps marknadsvideo: Iris från körning till svar

Fristående Remotion-projekt för Instagram-reelen som visar Iris-flödet:
Kör Iris → filter (stad, bransch) → 50 leads → utkasten är skrivna → ett
klick → 30 svar i inkorgen. Ingen del av appen; ingenting här byggs eller
deployas av Railway (`.dockerignore` och rotens `tsconfig.json` utesluter
mappen).

Research och principerna bakom tempot: [`docs/marknad/video-research.md`](../../docs/marknad/video-research.md).

## Köra

```bash
cd marknad/video
npm install
npm run ljud        # syntetiserar public/ljud.wav (numpy)
npm run studio      # Remotion Studio, förhandsvisning i webbläsaren
npm run rendera     # out/snajp-iris-reel-9x16.mp4 och out/snajp-iris-flode-4x5.mp4
```

Renderade filer ligger i `out/` och är gitignorerade, liksom ljudfilen
(den byggs om av skriptet, deterministiskt).

## Hur den är byggd

- `src/Film.tsx`: scenerna i följd, ljudet, scenytans position per format.
- `src/scener/`: en fil per scen (Krok, Korning, Pang, Utkast, Svar, Slut),
  varje med sin tidslinje i bildrutor överst.
- `src/delar/`: pekaren, bildtexten, paneler, leadrader, bakgrund och
  scenytan (`Yta`: 1080×1330 som ligger innanför Reels knappfält, 250 px
  ner i 9:16 och nästan i kant i 4:5).
- `src/tema.ts`: Snajps OKLCH-färger ur `app/globals.css`, Fraunces och
  Geist via `@remotion/google-fonts`, appens easing och kameran.
- `src/data.ts`: allt innehåll är påhittat (bolag med .example-domäner,
  bara förnamn, svar skrivna för filmen).
- `ljud/gor_ljud.py`: ljudet syntetiseras från grunden, låst till
  bildrutorna: slag, klick, tick, plingar. Ingen annans musik.

Tempot sitter på ett 15-rutors slag (120 bpm vid 30 fps): klick, smällen
och slutslaget faller på slagen.

## Regler som gäller filmen

- Allt är illustration. Raden "Illustration med påhittade exempel" ligger i
  bild under kroken och svarssekvensen, och ingen text påstår en
  svarsfrekvens (marknadsföringslagen).
- Webbplatsbedömningen (webbrevision, webbnivå, betyg) visas aldrig.
- Inget är inspelat från development eller main.
- Remotions licens: fri för bolag med upp till tre anställda; större bolag
  behöver en företagslicens innan filmen används kommersiellt.
