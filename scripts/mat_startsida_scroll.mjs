/**
 * Hackar startsidan när man scrollar? Mäter bildrutor och långa uppgifter
 * under en hel scroll uppifrån och ned och tillbaka, med CPU-strypning.
 *
 *   node scripts/mat_startsida_scroll.mjs
 *   BASE=http://localhost:3100 SIDOR=/,/leads STRYP=4,6 KORNINGAR=5 node scripts/mat_startsida_scroll.mjs
 *   VY=390x844 MOBIL=1 node scripts/mat_startsida_scroll.mjs
 *
 * Mät mot produktionsbygget, aldrig mot `next dev`.
 *
 * ## Vad som mäts
 *
 * Sidan scrollas med riktiga hjulhändelser (Lenis lyssnar på hjulet, så ett
 * `scrollTo` hade gått förbi just den kod som misstänks). Under tiden samlar
 * sidan in avståndet mellan `requestAnimationFrame`-anrop och varje `longtask`.
 *
 *  - p50/p95/p99 bildrutetid: 16,7 ms är 60 bilder per sekund.
 *  - tappade: andel bildrutor över 25 ms (minst en utebliven vid 60 Hz).
 *  - hack: bildrutor över 50 ms, det ögat läser som ett ryck.
 *  - långa uppgifter: antal och summerad tid över 50 ms.
 *
 * Medianen över KORNINGAR redovisas. Siffrorna gäller den här maskinen; det
 * som går att jämföra är före mot efter med samma inställningar.
 *
 *   npm i --no-save playwright && npx playwright install chromium
 */
import { chromium } from "playwright";
import { writeFileSync } from "node:fs";

const BASE = process.env.BASE ?? "http://localhost:3100";
const SIDOR = (process.env.SIDOR ?? "/").split(",").map((s) => s.trim()).filter(Boolean);
const STRYP = (process.env.STRYP ?? "4,6").split(",").map(Number);
const KORNINGAR = Number(process.env.KORNINGAR ?? 5);
const [VB, VH] = (process.env.VY ?? "1440x900").split("x").map(Number);
const MOBIL = process.env.MOBIL === "1";
const KANAL = process.env.PW_KANAL ?? "chrome";
const UT = process.env.UT;

function median(v) {
  const s = v.filter(Number.isFinite).sort((a, b) => a - b);
  if (!s.length) return NaN;
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function pct(sorterad, p) {
  if (!sorterad.length) return NaN;
  return sorterad[Math.min(sorterad.length - 1, Math.floor((p / 100) * sorterad.length))];
}

async function enKorning(browser, url, stryp) {
  const context = await browser.newContext({
    viewport: { width: VB, height: VH },
    deviceScaleFactor: MOBIL ? 3 : 1,
    isMobile: MOBIL,
    hasTouch: MOBIL
  });
  const page = await context.newPage();
  const fel = [];
  page.on("pageerror", (e) => fel.push(String(e)));
  const cdp = await context.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: stryp });

  const t0 = Date.now();
  await page.goto(url, { waitUntil: "load" });
  const laddning = Date.now() - t0;
  // Dörren och rörelsepaketet ska hinna gå klart innan scrollen mäts; det är
  // scrollen som mäts här, laddningen har Lighthouse.
  await page.waitForTimeout(3500);

  await page.evaluate(() => {
    const m = (window.__mat = { rutor: [], langa: [], aktiv: true });
    let forra = performance.now();
    const tick = (nu) => {
      if (!m.aktiv) return;
      m.rutor.push(nu - forra);
      forra = nu;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    try {
      new PerformanceObserver((lista) => {
        for (const e of lista.getEntries()) m.langa.push(e.duration);
      }).observe({ entryTypes: ["longtask"] });
    } catch {}
  });

  const hojd = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);
  await page.mouse.move(VB / 2, VH / 2);
  // Ett hjulsteg i taget med en bildrutas paus, som en hand på ett hjul.
  // Mjukscrollen dämpar hjulet (wheelMultiplier), så antalet steg går inte att
  // räkna ut: scrolla tills botten är nådd, med ett tak mot en sida som fastnat.
  const steg = 120;
  const tak = Math.ceil(hojd / steg) * 4 + 40;
  const lage = () => page.evaluate(() => Math.round(scrollY));
  let botten = 0;
  for (let i = 0; i < tak; i++) {
    await page.mouse.wheel(0, steg);
    await page.waitForTimeout(16);
    if (i % 15 === 14 && (botten = await lage()) >= hojd - 4) break;
  }
  await page.waitForTimeout(1200);
  botten = await lage();
  for (let i = 0; i < tak; i++) {
    await page.mouse.wheel(0, -steg);
    await page.waitForTimeout(16);
    if (i % 15 === 14 && (await lage()) <= 4) break;
  }
  await page.waitForTimeout(1200);

  const m = await page.evaluate(() => {
    window.__mat.aktiv = false;
    return { rutor: window.__mat.rutor, langa: window.__mat.langa };
  });
  await context.close();

  const s = [...m.rutor].sort((a, b) => a - b);
  return {
    laddning,
    hojd,
    naddeBotten: botten >= hojd - 40,
    rutor: s.length,
    p50: pct(s, 50),
    p95: pct(s, 95),
    p99: pct(s, 99),
    max: s[s.length - 1],
    tappade: (s.filter((d) => d > 25).length / s.length) * 100,
    hack: s.filter((d) => d > 50).length,
    langaAntal: m.langa.length,
    langaSumma: m.langa.reduce((a, b) => a + b, 0),
    langaMax: m.langa.length ? Math.max(...m.langa) : 0,
    fel
  };
}

const browser = await chromium.launch({ channel: KANAL, headless: true });
const allt = [];
for (const sida of SIDOR) {
  for (const stryp of STRYP) {
    const url = BASE + sida;
    console.log(`\n${url}  ${VB}x${VH}${MOBIL ? " mobil" : ""}  CPU ${stryp}x  ${KORNINGAR} körningar`);
    const rader = [];
    for (let n = 1; n <= KORNINGAR; n++) {
      const r = await enKorning(browser, url, stryp);
      rader.push(r);
      console.log(
        `  ${n}: p50 ${r.p50.toFixed(1)}  p95 ${r.p95.toFixed(1)}  p99 ${r.p99.toFixed(1)}  max ${r.max.toFixed(0)}  tappade ${r.tappade.toFixed(1)} %  hack ${r.hack}  långa ${r.langaAntal} st/${r.langaSumma.toFixed(0)} ms (max ${r.langaMax.toFixed(0)})${r.naddeBotten ? "" : "  [nådde inte botten]"}${r.fel.length ? "  JS-FEL: " + r.fel[0] : ""}`
      );
    }
    const med = {
      sida,
      vy: `${VB}x${VH}${MOBIL ? " mobil" : ""}`,
      stryp,
      p50: Number(median(rader.map((r) => r.p50)).toFixed(1)),
      p95: Number(median(rader.map((r) => r.p95)).toFixed(1)),
      p99: Number(median(rader.map((r) => r.p99)).toFixed(1)),
      max: Math.round(median(rader.map((r) => r.max))),
      tappade: Number(median(rader.map((r) => r.tappade)).toFixed(1)),
      hack: median(rader.map((r) => r.hack)),
      langaAntal: median(rader.map((r) => r.langaAntal)),
      langaSumma: Math.round(median(rader.map((r) => r.langaSumma))),
      langaMax: Math.round(median(rader.map((r) => r.langaMax)))
    };
    console.log(
      `  MEDIAN: p50 ${med.p50} ms  p95 ${med.p95} ms  p99 ${med.p99} ms  max ${med.max} ms  tappade ${med.tappade} %  hack ${med.hack}  långa uppgifter ${med.langaAntal} st / ${med.langaSumma} ms`
    );
    allt.push({ ...med, ravarden: rader });
  }
}
await browser.close();

if (UT) {
  writeFileSync(UT, JSON.stringify(allt, null, 2));
  console.log(`\nSparat: ${UT}`);
}
