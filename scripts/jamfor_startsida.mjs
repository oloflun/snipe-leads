/**
 * Ser startsidan likadan ut före och efter en ändring, och står något kvar dolt?
 *
 *   FORE=http://localhost:3101 EFTER=http://localhost:3100 node scripts/jamfor_startsida.mjs
 *   SIDOR=/,/leads,/support VYER=1440x900,390x844 node scripts/jamfor_startsida.mjs
 *
 * Två kontroller per sida och skärmstorlek:
 *
 * 1. **Inget fastnar dolt.** Sidan scrollas igenom i lugn takt, och när rörelsen
 *    lagt sig letas element som ännu är osynliga: opacitet under 1, en textrad
 *    som inte rest sig, en ruta som inte landat. Det är felet som drabbat sidan
 *    förut (2026-10-18: rubriker som stod kvar på opacitet 0).
 * 2. **Samma bild.** Skärmbilder tas på samma höjder i båda versionerna och
 *    jämförs bildpunkt för bildpunkt. Hjältens ytor svävar några pixlar och
 *    dygnsljuset skrivs i steg, så en liten andel avvikande punkter är väntad;
 *    skriptet redovisar andelen per höjd och sparar bilderna för ögat.
 *
 * Bilderna hamnar i .shots/jamfor-startsida/ (ignoreras av git).
 *
 *   npm i --no-save playwright
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const FORE = process.env.FORE ?? "http://localhost:3101";
const EFTER = process.env.EFTER ?? "http://localhost:3100";
const SIDOR = (process.env.SIDOR ?? "/").split(",");
const VYER = (process.env.VYER ?? "1440x900,390x844").split(",");
const UT = process.env.UT ?? ".shots/jamfor-startsida";
mkdirSync(UT, { recursive: true });

const browser = await chromium.launch({ channel: process.env.PW_KANAL ?? "chrome", headless: true });

/** Scrolla igenom sidan, vänta ut rörelsen, och ta bilder på fasta höjder. */
async function gaIgenom(bas, sida, vy) {
  const [w, h] = vy.split("x").map(Number);
  const mobil = w < 768;
  const context = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, isMobile: mobil, hasTouch: mobil });
  const page = await context.newPage();
  const fel = [];
  page.on("pageerror", (e) => fel.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") fel.push(m.text().slice(0, 200)); });
  await page.goto(bas + sida, { waitUntil: "load" });
  await page.waitForTimeout(6500); // dörren, rubriken som skrivs, ytorna som landar

  const hojd = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);
  // Lugn takt: varje sektion får stå i bild så att dess avslöjande hinner spela.
  for (let y = 0; y <= hojd; y += Math.round(h * 0.5)) {
    await page.evaluate((y) => (window.__lenis ? window.__lenis.scrollTo(y, { immediate: true }) : window.scrollTo(0, y)), y);
    await page.waitForTimeout(900);
  }
  await page.evaluate((y) => (window.__lenis ? window.__lenis.scrollTo(y, { immediate: true }) : window.scrollTo(0, y)), hojd);
  await page.waitForTimeout(5000);

  // 1. Vad står kvar dolt?
  const dolda = await page.evaluate(() => {
    const ut = [];
    const namn = (el) => `${el.tagName.toLowerCase()}${el.dataset.mo ? `[data-mo=${el.dataset.mo}]` : ""}.${String(el.className).split(" ").slice(0, 2).join(".")} "${(el.textContent ?? "").trim().slice(0, 40)}"`;
    for (const el of document.querySelectorAll(".landing [data-mo], .landing [data-case], .landing [data-case-text], .landing [data-kapitel-namn], .landing [data-kapitel-rad]")) {
      if (["light", "ground", "hero-scrim"].includes(el.dataset.mo ?? "")) continue;
      const s = getComputedStyle(el);
      if (Number(s.opacity) < 0.99 || s.visibility === "hidden") ut.push(`opacitet ${s.opacity}: ${namn(el)}`);
    }
    for (const el of document.querySelectorAll(".landing .ln, .landing .kb")) {
      const m = new DOMMatrixReadOnly(getComputedStyle(el).transform);
      if (Math.abs(m.m42) > 1) ut.push(`rad ${Math.round(m.m42)} px ur läge: ${namn(el)}`);
    }
    for (const el of document.querySelectorAll(".landing [data-case-box], .landing [data-case]")) {
      const m = new DOMMatrixReadOnly(getComputedStyle(el).transform);
      if (Math.abs(m.m41) > 1 || Math.abs(m.m42) > 1) ut.push(`ruta ${Math.round(m.m41)},${Math.round(m.m42)} px ur läge: ${namn(el)}`);
    }
    const kvar = [...document.querySelectorAll(".landing *")].filter((el) => el.style.willChange).length;
    return { ut, kvar };
  });

  // 2. Bilder på fasta höjder, uppifrån.
  const bilder = [];
  const steg = Math.round(h * 0.9);
  for (let y = 0, n = 0; y <= hojd; y += steg, n += 1) {
    await page.evaluate((y) => (window.__lenis ? window.__lenis.scrollTo(y, { immediate: true }) : window.scrollTo(0, y)), y);
    await page.waitForTimeout(450);
    bilder.push({ n, y, png: await page.screenshot({ type: "png" }) });
  }
  await context.close();
  return { hojd, dolda, bilder, fel };
}

/** Andel bildpunkter som skiljer mer än en liten tolerans. Räknas i sidan, på en canvas. */
async function skillnad(page, a, b) {
  return page.evaluate(async ([a, b]) => {
    const las = async (b64) => {
      const bild = await createImageBitmap(await (await fetch("data:image/png;base64," + b64)).blob());
      const c = new OffscreenCanvas(bild.width, bild.height);
      const x = c.getContext("2d");
      x.drawImage(bild, 0, 0);
      return x.getImageData(0, 0, bild.width, bild.height);
    };
    const [A, B] = [await las(a), await las(b)];
    if (A.width !== B.width || A.height !== B.height) return { andel: 1, storlek: true };
    let olika = 0;
    for (let i = 0; i < A.data.length; i += 4) {
      const d = Math.abs(A.data[i] - B.data[i]) + Math.abs(A.data[i + 1] - B.data[i + 1]) + Math.abs(A.data[i + 2] - B.data[i + 2]);
      if (d > 24) olika += 1;
    }
    return { andel: olika / (A.data.length / 4) };
  }, [a.toString("base64"), b.toString("base64")]);
}

let anmarkningar = 0;
const rakna = await (await browser.newContext()).newPage();
for (const sida of SIDOR) {
  for (const vy of VYER) {
    console.log(`\n${sida}  ${vy}`);
    const fore = await gaIgenom(FORE, sida, vy);
    const efter = await gaIgenom(EFTER, sida, vy);
    console.log(`  sidhöjd före ${fore.hojd}, efter ${efter.hojd}${fore.hojd === efter.hojd ? "" : "  <-- SKILJER"}`);
    if (fore.hojd !== efter.hojd) anmarkningar += 1;
    for (const [namn, k] of [["före", fore], ["efter", efter]]) {
      console.log(`  ${namn}: ${k.dolda.ut.length} element kvar dolda eller ur läge, ${k.dolda.kvar} med will-change kvar${k.fel.length ? `, JS-FEL: ${k.fel[0]}` : ""}`);
      for (const rad of k.dolda.ut.slice(0, 8)) console.log(`    ${rad}`);
    }
    if (efter.dolda.ut.length > fore.dolda.ut.length || efter.fel.length) anmarkningar += 1;
    const tagg = `${sida.replace(/\W+/g, "_") || "start"}-${vy}`;
    const rader = [];
    for (let i = 0; i < Math.min(fore.bilder.length, efter.bilder.length); i++) {
      const d = await skillnad(rakna, fore.bilder[i].png, efter.bilder[i].png);
      writeFileSync(join(UT, `${tagg}-${String(i).padStart(2, "0")}-fore.png`), fore.bilder[i].png);
      writeFileSync(join(UT, `${tagg}-${String(i).padStart(2, "0")}-efter.png`), efter.bilder[i].png);
      rader.push(`${i}:${(d.andel * 100).toFixed(1)}`);
      if (d.andel > 0.03) anmarkningar += 1;
    }
    console.log(`  avvikande bildpunkter per höjd (%): ${rader.join("  ")}`);
  }
}
await browser.close();
console.log(anmarkningar ? `\n${anmarkningar} anmärkningar. Öppna bilderna i ${UT} och jämför.` : `\nInga anmärkningar. Bilderna ligger i ${UT}.`);
process.exit(anmarkningar ? 1 : 0);
