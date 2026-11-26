// Enskilda bildrutor ur filmen, för granskning före fullrenderingen.
//
//   node verktyg/stills.mjs <mapp> <ruta> [<ruta> …]      skriver <mapp>/f00123.jpeg
//
// Välj en ruta per scen vid start + min(längd − 45, 95) (se `node verktyg/tider.mjs`): där har markören
// landat och bildtexten syns. Faller den med "Timed out … connect to the browser", kör igen.
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [ut, ...rutor] = process.argv.slice(2);
if (!ut || rutor.length === 0) throw new Error("Användning: node verktyg/stills.mjs <mapp> <ruta> [<ruta> …]");
mkdirSync(ut, { recursive: true });
const browserExecutable = process.env.CHROME_PATH || null;
const serveUrl = await bundle({ entryPoint: path.join(ROT, "src", "index.ts"), publicDir: path.join(ROT, "public"), outDir: path.join(ROT, "tmp", "bundle") });
const composition = await selectComposition({ serveUrl, id: "Film", browserExecutable });
for (const f of rutor) {
  await renderStill({ composition, serveUrl, output: path.join(ut, `f${String(f).padStart(5, "0")}.jpeg`), frame: Number(f), imageFormat: "jpeg", jpegQuality: 85, browserExecutable });
  console.log("ruta", f);
}
