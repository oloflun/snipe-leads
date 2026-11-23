/**
 * En Lighthouse-körning i detalj: var LCP-tiden går, vad som väger, vilka
 * typsnitt och bilder som hämtas och vilka skript som kostar.
 *
 *   node scripts/mat_startsida_detalj.mjs /
 *   BASE=http://localhost:3100 ENHET=desktop node scripts/mat_startsida_detalj.mjs /faq
 *
 * `mat_startsida_lighthouse.mjs` ger medianen över flera körningar. Det här är
 * förstoringsglaset för EN körning, när en siffra behöver en förklaring.
 */
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE = process.env.BASE ?? "http://localhost:3100";
const SIDA = process.argv[2] ?? "/";
const ENHET = process.env.ENHET ?? "mobil";
const LH = process.env.LIGHTHOUSE_BIN ?? "npx lighthouse";

const fil = join(mkdtempSync(join(tmpdir(), "lhd-")), "lh.json");
const flaggor = [BASE + SIDA, "--quiet", "--only-categories=performance", "--output=json", `--output-path=${fil}`, "--chrome-flags=--headless=new"];
if (ENHET === "desktop") flaggor.push("--preset=desktop");
const r = spawnSync(LH, flaggor, { shell: true, encoding: "utf8" });
if (r.status !== 0) {
  console.error((r.stderr || "").split("\n").slice(-4).join("\n"));
  process.exit(1);
}
const l = JSON.parse(readFileSync(fil, "utf8"));
const a = l.audits;
const kB = (b) => Math.round((b || 0) / 1024);
const namn = (url) => url.split("/").pop().split("?")[0].slice(0, 30);

console.log(
  `${BASE}${SIDA} [${ENHET}]  poäng ${Math.round(l.categories.performance.score * 100)}  FCP ${Math.round(a["first-contentful-paint"].numericValue)}  LCP ${Math.round(a["largest-contentful-paint"].numericValue)}  TBT ${Math.round(a["total-blocking-time"].numericValue)}  CLS ${a["cumulative-layout-shift"].numericValue.toFixed(3)}  SI ${Math.round(a["speed-index"].numericValue)}`
);
const el = a["largest-contentful-paint-element"];
const faser = el?.details?.items?.[1]?.items?.map((i) => `${i.phase} ${Math.round(i.timing)}`).join(", ");
console.log(`LCP-element: ${(el?.details?.items?.[0]?.items?.[0]?.node?.snippet ?? "").slice(0, 110)}`);
console.log(`LCP-faser: ${faser ?? "saknas"}`);

const nat = a["network-requests"].details.items;
const perTyp = {};
for (const x of nat) perTyp[x.resourceType] = (perTyp[x.resourceType] ?? 0) + (x.transferSize || 0);
console.log(`vikt: ${kB(nat.reduce((s, x) => s + (x.transferSize || 0), 0))} kB i ${nat.length} förfrågningar · ${Object.entries(perTyp).map(([k, v]) => `${k} ${kB(v)}`).join(", ")}`);
console.log("typsnitt: " + nat.filter((x) => x.resourceType === "Font").map((x) => `${kB(x.transferSize)} kB ${namn(x.url)}`).join(" | "));
console.log("bilder:   " + nat.filter((x) => x.resourceType === "Image").map((x) => `${kB(x.transferSize)} kB ${namn(x.url)}`).join(" | "));
console.log("skript:   " + nat.filter((x) => x.resourceType === "Script").sort((x, y) => y.transferSize - x.transferSize).slice(0, 6).map((x) => `${kB(x.transferSize)} kB ${namn(x.url)}`).join(" | "));
console.log("skripttid: " + (a["bootup-time"].details.items ?? []).slice(0, 5).map((x) => `${Math.round(x.total)} ms ${namn(x.url) || "sidan"}`).join(" | "));
console.log("huvudtråd: " + (a["mainthread-work-breakdown"].details.items ?? []).map((i) => `${i.groupLabel} ${Math.round(i.duration)}`).join(", "));
const oanvant = a["unused-javascript"]?.details;
if (oanvant?.items?.length) console.log(`oanvänd JS: ${kB(oanvant.overallSavingsBytes)} kB · ` + oanvant.items.slice(0, 4).map((i) => `${namn(i.url)} ${kB(i.wastedBytes)}/${kB(i.totalBytes)}`).join(", "));
