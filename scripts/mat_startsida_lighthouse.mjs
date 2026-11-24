/**
 * Lighthouse mot publika sidor, flera körningar, medianen redovisas.
 *
 *   node scripts/mat_startsida_lighthouse.mjs                    # startsidan, 5 + 5
 *   BASE=http://localhost:3100 SIDOR=/,/leads,/faq KORNINGAR=5 node scripts/mat_startsida_lighthouse.mjs
 *   UT=matning.json node scripts/mat_startsida_lighthouse.mjs    # spara råvärdena
 *
 * Mät ALLTID mot produktionsbygget (`npm run build && npx next start -p 3100`).
 * Dev-läget är långsammare och ger siffror som inte säger något om snajp.se.
 *
 * En enda körning duger inte: TBT och LCP varierar tiotals procent mellan två
 * körningar på samma maskin. Därför medianen över KORNINGAR, aldrig bästa värdet.
 *
 * Kräver lighthouse (inte ett beroende i package.json, det är ett mätverktyg):
 *   npm i --no-save lighthouse
 */
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE = process.env.BASE ?? "http://localhost:3100";
const SIDOR = (process.env.SIDOR ?? "/").split(",").map((s) => s.trim()).filter(Boolean);
const KORNINGAR = Number(process.env.KORNINGAR ?? 5);
const ENHETER = (process.env.ENHETER ?? "mobil,desktop").split(",");
const UT = process.env.UT;
const LH = process.env.LIGHTHOUSE_BIN ?? "lighthouse";

const tmp = mkdtempSync(join(tmpdir(), "lh-"));

function median(varden) {
  const s = varden.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (!s.length) return NaN;
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function kor(url, enhet, n) {
  const fil = join(tmp, `${enhet}-${n}-${Date.now()}.json`);
  const flaggor = [
    url,
    "--quiet",
    "--only-categories=performance",
    "--output=json",
    `--output-path=${fil}`,
    "--chrome-flags=--headless=new --no-first-run"
  ];
  if (enhet === "desktop") flaggor.push("--preset=desktop");
  const r = spawnSync(LH, flaggor, { shell: true, encoding: "utf8" });
  if (r.status !== 0) {
    console.error(`  körning ${n} föll: ${(r.stderr || "").split("\n").slice(-3).join(" ")}`);
    return null;
  }
  const lhr = JSON.parse(readFileSync(fil, "utf8"));
  const a = lhr.audits;
  return {
    poang: Math.round((lhr.categories.performance.score ?? 0) * 100),
    fcp: a["first-contentful-paint"].numericValue,
    lcp: a["largest-contentful-paint"].numericValue,
    tbt: a["total-blocking-time"].numericValue,
    cls: a["cumulative-layout-shift"].numericValue,
    si: a["speed-index"].numericValue,
    // Byte över nätet och JS-vikt: det som faktiskt skiljer före från efter.
    vikt: a["total-byte-weight"].numericValue,
    lcpElement: a["largest-contentful-paint-element"]?.details?.items?.[0]?.items?.[0]?.node?.snippet ?? ""
  };
}

const allt = [];
for (const sida of SIDOR) {
  for (const enhet of ENHETER) {
    const url = BASE + sida;
    console.log(`\n${url}  [${enhet}]  ${KORNINGAR} körningar`);
    const rader = [];
    for (let n = 1; n <= KORNINGAR; n++) {
      const r = kor(url, enhet, n);
      if (!r) continue;
      rader.push(r);
      console.log(
        `  ${n}: poäng ${r.poang}  FCP ${Math.round(r.fcp)}  LCP ${Math.round(r.lcp)}  TBT ${Math.round(r.tbt)}  CLS ${r.cls.toFixed(3)}  SI ${Math.round(r.si)}`
      );
    }
    const med = {
      sida,
      enhet,
      korningar: rader.length,
      poang: median(rader.map((r) => r.poang)),
      fcp: Math.round(median(rader.map((r) => r.fcp))),
      lcp: Math.round(median(rader.map((r) => r.lcp))),
      tbt: Math.round(median(rader.map((r) => r.tbt))),
      cls: Number(median(rader.map((r) => r.cls)).toFixed(3)),
      si: Math.round(median(rader.map((r) => r.si))),
      viktKb: Math.round(median(rader.map((r) => r.vikt)) / 1024),
      lcpElement: rader[0]?.lcpElement ?? ""
    };
    console.log(
      `  MEDIAN: poäng ${med.poang}  FCP ${med.fcp} ms  LCP ${med.lcp} ms  TBT ${med.tbt} ms  CLS ${med.cls}  SI ${med.si} ms  vikt ${med.viktKb} kB`
    );
    allt.push({ ...med, ravarden: rader });
  }
}

if (UT) {
  writeFileSync(UT, JSON.stringify(allt, null, 2));
  console.log(`\nSparat: ${UT}`);
}
