// Filmens tidslinje ur manuset, utan Remotion: när varje del börjar, var klippen ligger och var musiken
// ska spela. SAMMA räkning som layout() i src/Film.tsx. Ändras den ena ska den andra ändras; bygg.sh
// stoppar om de skiljer sig.
//
//   node verktyg/tider.mjs            tabell över delarna
//   node verktyg/tider.mjs --totalt   antal bildrutor
//   node verktyg/tider.mjs --klipp    klippens filnamn, ett per rad
//   node verktyg/tider.mjs --json     allt som JSON (ljud.mjs läser det)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const FPS = 30;
export const FADE = 20;
const BAR = (60 / 110) * 4 * FPS;
const BEAT0 = 17;

export function lasManus() {
  return JSON.parse(fs.readFileSync(path.join(ROT, "src", "data", "film.json"), "utf8"));
}

/** starts, durs och total som layout() i Film.tsx, plus klippen och musikavsnitten. */
export function tider(items) {
  const starts = [];
  let origin = 0;
  let bars = 0;
  let t = 0;
  const avsnitt = [];
  items.forEach((it) => {
    if (it.kind === "clip") {
      starts.push(t);
      t += it.frames - FADE;
      origin = t;
      bars = 0;
      avsnitt.push({ origin });
      return;
    }
    if (avsnitt.length === 0) avsnitt.push({ origin: 0 });
    starts.push(bars === 0 ? origin : origin + Math.round(BEAT0 - FADE / 2 + bars * BAR));
    bars += it.bars;
    t = origin + Math.round(BEAT0 - FADE / 2 + bars * BAR);
  });
  const durs = items.map((it, i) => (i < items.length - 1 ? starts[i + 1] - starts[i] + FADE : it.kind === "clip" ? it.frames : t - starts[i] + FADE));
  const total = starts[items.length - 1] + durs[items.length - 1];
  const klipp = items.flatMap((it, i) => (it.kind === "clip" ? [{ file: it.file, start: starts[i], frames: it.frames }] : []));
  // Ett musikavsnitt går från sin början till nästa klipps början (plus övertoningen) eller filmens slut.
  // Ett avsnitt som börjar där filmen slutar (ett klipp sist) har ingen musik och tas bort.
  const musik = avsnitt
    .map((a) => {
      const nasta = klipp.find((k) => k.start >= a.origin);
      return { start: a.origin, slut: nasta ? nasta.start + FADE : total, sist: !nasta };
    })
    .filter((a) => a.slut - a.start > FADE);
  return { starts, durs, total, klipp, musik };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const items = lasManus();
  const r = tider(items);
  const flagga = process.argv[2];
  if (flagga === "--totalt") console.log(r.total);
  else if (flagga === "--klipp") r.klipp.forEach((k) => console.log(k.file));
  else if (flagga === "--json") console.log(JSON.stringify(r));
  else {
    items.forEach((it, i) => {
      const text = it.kind === "clip" ? `klipp ${it.file}` : it.kind === "title" ? `rubrik: ${it.text}` : `${it.file}: ${it.caption}`;
      console.log(`${String(r.starts[i]).padStart(5)}  ${(r.starts[i] / FPS).toFixed(2).padStart(6)} s  ${String(r.durs[i]).padStart(4)} rutor  ${text}`);
    });
    console.log(`totalt ${r.total} rutor, ${(r.total / FPS).toFixed(2)} s`);
    r.musik.forEach((m) => console.log(`musik ${(m.start / FPS).toFixed(2)}–${(m.slut / FPS).toFixed(2)} s${m.sist ? " (sist)" : ""}`));
  }
}
