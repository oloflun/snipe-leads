// Filmens ljudspår: varje klipps eget ljud där klippet ligger, och musikbädden (version 2, 110 BPM) i
// varje avsnitt mellan klippen, från avsnittets första takt. Skriver out/ljud.wav.
//
// Bädden är 61 s. Är ett avsnitt längre läggs flera kopior efter varandra med 4,273 s övertoning, så att
// varje skarv hamnar på en taktgräns (26 takter = 56,727 s mellan kopiornas början).
//
//   node verktyg/ljud.mjs
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { FPS, lasManus, ROT, tider } from "./tider.mjs";

const BADD = path.join(ROT, "public", "musik", "badd-110bpm.mp3");
const BADD_LANGD = 61.0;
const SKARV = 4.273;
const STEG = 56.727;
const UT = path.join(ROT, "out", "ljud.wav");

const { klipp, musik, total } = tider(lasManus());
const ms = (rutor) => Math.round((rutor / FPS) * 1000);
const harLjud = (fil) =>
  execFileSync("ffprobe", ["-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", fil]).toString().trim() !== "";

const inputs = [];
const delar = [];
const lager = [];

klipp.forEach((k, i) => {
  const fil = path.join(ROT, "public", k.file);
  if (!fs.existsSync(fil)) throw new Error(`Klippet saknas: ${fil}`);
  if (!harLjud(fil)) return console.log(`(klipp ${k.file} har inget ljud)`);
  inputs.push("-i", fil);
  const n = inputs.length / 2 - 1;
  delar.push(`[${n}:a]aresample=48000,adelay=${ms(k.start)}:all=1[k${i}]`);
  lager.push(`[k${i}]`);
});

musik.forEach((m, j) => {
  const langd = (m.slut - m.start) / FPS;
  const kopior = langd <= BADD_LANGD ? 1 : 1 + Math.ceil((langd - BADD_LANGD) / STEG);
  const forsta = inputs.length / 2;
  for (let c = 0; c < kopior; c++) inputs.push("-i", BADD);
  let kedja = `[${forsta}:a]aresample=48000`;
  for (let c = 1; c < kopior; c++) {
    delar.push(`${kedja}[m${j}x${c}]`);
    delar.push(`[m${j}x${c}][${forsta + c}:a]acrossfade=d=${SKARV}:c1=tri:c2=tri[m${j}y${c}]`);
    kedja = `[m${j}y${c}]`;
  }
  // Sist i filmen tonar musiken ut under slutkortet; före ett klipp på en sekund, så att klippets eget ljud tar över.
  const ut = m.sist ? 3.3 : 1.0;
  delar.push(
    `${kedja}atrim=0:${langd.toFixed(3)},afade=t=in:d=0.35,afade=t=out:st=${(langd - ut).toFixed(3)}:d=${ut},volume=0.82,adelay=${ms(m.start)}:all=1[m${j}]`
  );
  lager.push(`[m${j}]`);
  console.log(`musik ${(m.start / FPS).toFixed(2)}–${(m.slut / FPS).toFixed(2)} s, ${kopior} kopia/kopior`);
});

delar.push(`${lager.join("")}amix=inputs=${lager.length}:normalize=0:duration=longest,atrim=0:${(total / FPS).toFixed(3)},alimiter=limit=0.89[ut]`);
fs.mkdirSync(path.dirname(UT), { recursive: true });
execFileSync("ffmpeg", ["-v", "error", "-y", ...inputs, "-filter_complex", delar.join(";"), "-map", "[ut]", "-ar", "48000", "-c:a", "pcm_s16le", UT], { stdio: "inherit" });
console.log(`ljud: ${UT}, ${(total / FPS).toFixed(2)} s`);
