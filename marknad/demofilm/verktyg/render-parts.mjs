// Renderar filmens bild i delar, en del per process, så att en webbläsare som kraschar eller inte hinner
// starta bara kostar en del. Sätter sedan ihop delarna till out/stum.mp4.
//
//   ONLY_PART=3 PART_SIZE=500 node verktyg/render-parts.mjs   bara del 3 (hoppar över delar som finns)
//   PART_SIZE=500 node verktyg/render-parts.mjs               alla saknade delar, sedan ihopsättningen
//   BARA_LANGD=1 node verktyg/render-parts.mjs                skriver bara kompositionens längd i rutor
//
// CHROME_PATH pekar ut en egen headless Chrome; annars hämtar Remotion sin egen.
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROT, "out");
const PARTS = path.join(OUT, "parts");
const browserExecutable = process.env.CHROME_PATH || null;
mkdirSync(PARTS, { recursive: true });

const serveUrl = await bundle({ entryPoint: path.join(ROT, "src", "index.ts"), publicDir: path.join(ROT, "public"), outDir: path.join(ROT, "tmp", "bundle") });
const composition = await selectComposition({ serveUrl, id: "Film", browserExecutable });
if (process.env.BARA_LANGD) {
  console.log(composition.durationInFrames);
  process.exit(0);
}
const size = Number(process.env.PART_SIZE) || 500;
const parts = Math.ceil(composition.durationInFrames / size);
const files = [];
for (let i = 0; i < parts; i++) {
  const a = i * size;
  const b = Math.min(composition.durationInFrames - 1, a + size - 1);
  const file = path.join(PARTS, `part-${i + 1}.mp4`);
  files.push(file);
  if (existsSync(file)) continue;
  if (process.env.ONLY_PART && Number(process.env.ONLY_PART) !== i + 1) continue;
  let last = -1;
  await renderMedia({
    composition, serveUrl, codec: "h264", crf: 20, concurrency: 1, browserExecutable, frameRange: [a, b],
    offthreadVideoCacheSizeInBytes: 256 * 1024 * 1024, mediaCacheSizeInBytes: 256 * 1024 * 1024,
    outputLocation: file + ".tmp.mp4",
    onProgress: ({ progress }) => { const p = Math.floor(progress * 10); if (p !== last) { last = p; console.log(`del ${i + 1}/${parts} ${p * 10} %`); } },
  });
  renameSync(file + ".tmp.mp4", file);
  console.log("del klar", i + 1);
}
if (process.env.ONLY_PART) process.exit(0);
writeFileSync(path.join(PARTS, "list.txt"), files.map((f) => `file '${f.replaceAll("\\", "/").replaceAll("'", "'\\''")}'`).join("\n"));
execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", path.join(PARTS, "list.txt"), "-c", "copy", path.join(OUT, "stum.mp4")]);
console.log("klar", path.join(OUT, "stum.mp4"));
