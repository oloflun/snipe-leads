/**
 * Appikonerna, genererade ur `snipe_logo.svg`.
 *
 * ## Varför loggan CENTRERAS och inte beskärs
 *
 * `snipe_logo.svg` är 1206×728, alltså ett liggande märke med förhållandet
 * 1,66:1. En kvadratisk beskärning hade kapat märket på bredden — inte tagit
 * bort luft, utan skurit av själva logotypen. Därför skalas den in i en
 * kvadrat med marginal och läggs på varumärkets pappersfärg.
 *
 * Marginalen är 12 % på iOS-ikonen och 8 % på övriga. Skillnaden är avsiktlig:
 * iOS maskar ikonen till en rundad kvadrat och äter ungefär en tiondel av
 * kanten, så en ikon som ser rätt ut i en webbläsarflik blir beskuren på
 * hemskärmen.
 *
 * Bakgrunden är ogenomskinlig (`paper`), inte transparent. iOS stödjer ingen
 * alfakanal på hemskärmsikoner och lägger annars in svart bakom — ett svart
 * fält bakom en svart logotyp ger en tom ruta.
 *
 * Kör om efter varje ändring av loggan:
 *
 *     node scripts/generera_ikoner.mjs
 */

import { mkdir, writeFile } from "node:fs/promises";
import { readFileSync } from "node:fs";
import path from "node:path";
import sharp from "sharp";

const ROT = path.resolve(import.meta.dirname, "..");
const LOGGA = path.join(ROT, "public", "snipe_logo.svg");
const UT = path.join(ROT, "public", "icons");

/** Ur app/globals.css, konverterade från OKLCH. Se DESIGN.md. */
const PAPPER = "#f6f3ed";

const STORLEKAR = [
  { fil: "icon-192.png", px: 192, marginal: 0.08 },
  { fil: "icon-512.png", px: 512, marginal: 0.08 },
  // iOS maskar till en rundad kvadrat — mer marginal, annars kapas kanten.
  { fil: "apple-touch-icon.png", px: 180, marginal: 0.12 },
  // Maskerbar ikon (Android adaptive): systemet beskär till en cirkel i värsta
  // fall, och säkerhetszonen är de inre 80 % — därav den stora marginalen.
  { fil: "icon-maskable-512.png", px: 512, marginal: 0.2 }
];

/**
 * Rasteriseringstäthet, härledd ur SVG:ns egen bredd och den storlek vi vill ha.
 *
 * Låg fast `density: 600` här. Det fungerade så länge märket var 1206 enheter
 * brett, men en logotyp med en större viewBox rasteras då till tiotusentals
 * pixlar och sharp svarar "Input image exceeds pixel limit". Täckningen ska
 * bero på MÅLET, inte på hur källan råkar vara numrerad.
 *
 * Faktor 2 mot målstorleken ger kantutjämning att arbeta med utan att bygga en
 * bitmapp ingen ser.
 */
function tathet(svgText, malPx) {
  const vb = /viewBox="[\d.]+ [\d.]+ ([\d.]+) /.exec(svgText);
  const bredd = vb ? Number(vb[1]) : 1024;
  return Math.max(24, Math.min(2400, Math.round((malPx * 2 * 72) / bredd)));
}

async function main() {
  await mkdir(UT, { recursive: true });
  const svg = readFileSync(LOGGA);
  const svgText = svg.toString("utf8");

  for (const { fil, px, marginal } of STORLEKAR) {
    const inre = Math.round(px * (1 - marginal * 2));

    const märke = await sharp(svg, { density: tathet(svgText, px) })
      .resize(inre, inre, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
      .png()
      .toBuffer();

    await sharp({
      create: { width: px, height: px, channels: 4, background: PAPPER }
    })
      .composite([{ input: märke, gravity: "center" }])
      .png()
      .toFile(path.join(UT, fil));

    console.log(`${fil}  ${px}×${px}  marginal ${Math.round(marginal * 100)} %`);
  }

  // Faviconen som webbläsarfliken använder. SVG före PNG: den skalar skarpt i
  // varje storlek, och PNG-varianterna ovan fångar upp de klienter som inte
  // stödjer SVG-favicon.
  await writeFile(path.join(UT, ".gitkeep"), "");
}

await main();
