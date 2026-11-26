// Records the leads flow in Snajp's public demo (/demo: example data only, no login, no database)
// as one sharp 1920x1080 frame per step plus the click target, for the Remotion film to animate.
// Same rig as the WMS film (warehouse-handy-next docs/presentation/production/rec/lib.mjs).
//   node rec/record-leads.mjs  ->  public/film/NN.png + src/data/film.json
// Needs Playwright's Chromium once: npx playwright install chromium
//
// The script (Anton 2026-11-25): show what Iris DOES, how EASY it is and what the customer GETS from each
// function. Not where to click, and not what each figure means. Many clicks below are therefore made
// without a frame being taken; only the steps that carry a point of their own are filmed.
// Lengths are in bars of the music bed (110 BPM, 4 beats to the bar), so every cut lands on the beat.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

// Only the public example surfaces of development: /demo and /forhandsvisning. Never a logged-in surface,
// the development database is a mirror of production.
const APP = "https://web-development-6c85.up.railway.app";
const ROT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROT, "public", "film");
const DATA = path.join(ROT, "src", "data", "film.json");
const V = { width: 1280, height: 720, dsf: 1.5 };
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: V.width, height: V.height }, deviceScaleFactor: V.dsf, locale: "sv-SE", timezoneId: "Europe/Stockholm" });
const p = await ctx.newPage();
const problems = [];
p.on("pageerror", (e) => problems.push("pageerror: " + e.message.slice(0, 200)));

const items = [];
let n = 0;
const title = (text, extra = {}) => items.push({ kind: "title", text, bars: 2, ...extra });
/** Wait until two screenshots in a row are identical, so no row animation is caught mid-flight. */
async function still() {
  let prev = null;
  for (let i = 0; i < 24; i++) {
    const b = await p.screenshot();
    if (prev && Buffer.compare(prev, b) === 0) return;
    prev = b;
    await p.waitForTimeout(250);
  }
  console.log("  (never came to rest)");
}
/** Where the cursor tip lands, in image pixels. A click lands right of and below the middle, so the label
 *  stays readable; a pointer without a click lands just under the first line of the text it points at. */
const aim = (b, click) =>
  click
    ? { x: Math.round((b.x + b.width / 2 + Math.min(b.width * 0.22, 36)) * V.dsf), y: Math.round((b.y + b.height * 0.66) * V.dsf) }
    : { x: Math.round((b.x + Math.min(b.width / 2, 200)) * V.dsf), y: Math.round((b.y + Math.min(b.height, 26) + 3) * V.dsf) };
/** Scroll `target` so that its middle sits `y` px down the viewport. */
const lagg = (target, y) =>
  target.evaluate((el, yy) => {
    const r = el.getBoundingClientRect();
    let s = el.parentElement;
    while (s && !(s.scrollHeight > s.clientHeight + 4 && /auto|scroll/.test(getComputedStyle(s).overflowY))) s = s.parentElement;
    (s ?? document.scrollingElement).scrollBy(0, r.top + r.height / 2 - yy);
  }, y);
/** Frame a step. `target` = locator the cursor travels to (clicked afterwards when click=true). `y` = where the target should sit in the viewport. `vila=false` takes the frame at once. */
async function shot(caption, { target, click = false, y = null, vila = true, ...extra } = {}) {
  if (target && y !== null) await lagg(target, y);
  if (vila) await still();
  let cursor = null;
  if (target) {
    const b = await target.boundingBox({ timeout: 5000 }).catch(() => null);
    if (!b) console.log("  (no target box for", caption + ")");
    if (b) cursor = aim(b, click);
    if (b && (b.y < 0 || b.y + b.height > V.height)) console.log("  (target outside the viewport for", caption + ")");
  }
  const file = `${String(++n).padStart(2, "0")}.png`;
  await p.screenshot({ path: `${OUT}/${file}` });
  items.push({ kind: "desktop", file, w: V.width * V.dsf, h: V.height * V.dsf, caption, cursor, click, bars: 2, ...extra });
  console.log("shot", file, caption);
  if (click && target) await target.click();
}
const top = () => p.evaluate(() => window.scrollTo(0, 0));
const go = async (url) => { await p.goto(APP + url, { waitUntil: "networkidle", timeout: 120000 }); await p.waitForTimeout(400); };

// 0. The Instagram reel first, whole (marknad/video, the 4:5 composition, rendered to public/reel.mp4):
// shown at full height in the middle of the frame, so nothing is cropped the way a feed crops it.
items.push({ kind: "clip", file: "reel.mp4", frames: 795, w: 1080, h: 1350 });
title("Så här jobbar Iris åt er", { bars: 1.5 });

// 1. The target group, once.
await go("/demo/installningar");
await shot("Ni beskriver er drömkund en enda gång", { target: p.getByText("Tillverkande bolag som växer", { exact: false }).first() });

// 2. One click starts it.
await go("/demo/leads");
// The demo list plays back a run on load; wait until it has landed (no "Research pågår").
await p.locator("#leads-iris").scrollIntoViewIfNeeded().catch(() => {});
await p.waitForFunction(() => !document.body.innerText.includes("Research pågår"), null, { timeout: 60000 }).catch(() => console.log("  (research never finished)"));
await p.waitForTimeout(1500);
await top();
await p.getByRole("button", { name: "Kör Iris" }).first().click();
const inner = p.getByRole("button", { name: "Kör Iris" }).nth(1);
await inner.waitFor();
await shot("Ett klick, sedan gör Iris jobbet", { target: inner, click: true, y: 420 });
const laser = p.getByText("Läser sajterna och hittar kontakten");
await laser.waitFor();
await p.waitForFunction(() => [...document.querySelectorAll("li")].some((li) => li.textContent.includes("Läser sajterna") && li.className.includes("font-medium")));
// The steps move on every 900 ms, so this frame is taken at once, without waiting for rest.
await shot("Iris hittar bolagen, läser på och skriver mejlen", { target: laser, vila: false });

// 3. What comes back: ranked companies, each with its reasons.
const visa = p.getByRole("button", { name: "Visa i listan" });
await visa.waitFor();
await visa.click();
await p.waitForTimeout(1500);
const hammar = p.locator('[id^="iris-rad-"]', { hasText: "Hammarnäs" }).first();
await shot("Ni får bolagen rankade efter hur väl de passar", { target: hammar.getByText("Hammarnäs Bygg Sverige AB"), y: 430, click: true });
const lada = p.locator('[role="dialog"]').first();
await lada.waitFor();
await p.waitForTimeout(700);
await shot("Varje bolag kommer med skäl, citat och källa", { target: lada.getByText("källa", { exact: true }).first(), anchor: "right" });
await lada.getByRole("tab", { name: "Mejlutkast" }).or(lada.getByRole("button", { name: "Mejlutkast" })).first().click();
await p.waitForTimeout(600);
await shot("Mejlet utgår från något som hänt hos just dem", { target: lada.locator("textarea").first(), anchor: "right" });
await p.keyboard.press("Escape");
await p.waitForTimeout(600);

// 4. Changing and approving: one click each.
await top();
const utkast = p.getByRole("button", { name: /Hjärtstartare på listan/ }).first();
await lagg(utkast, 300);
await utkast.click();
const kortare = p.getByRole("button", { name: "Kortare" }).first();
await kortare.waitFor();
await p.waitForTimeout(600);
await shot("Vill ni ändra texten räcker ett klick", { target: kortare, click: true, y: 560 });
await p.getByText("Kortare:", { exact: false }).first().waitFor({ timeout: 20000 });
const godkann = p.getByRole("button", { name: "Godkänn och skicka", exact: true }).first();
await shot("Inget går ut förrän ni har sagt ja", { target: godkann, click: true, y: 500 });
await p.getByText("godkänt", { exact: false }).first().waitFor({ timeout: 20000 });

// 5. Follow-up and the way to a meeting. The demo has no such tab, so this is the preview
// /forhandsvisning/konversationer: made-up companies, no database. The page has no rail, so the camera
// frames the middle of it. The mail shown must read as a follow-up (Anton 2026-11-25): "Läs" opens the
// waiting follow-up itself, "Om mitt förra mejl", follow-up 1 of 3.
const mitt = { center: true, zoom: 1.12 };
await go("/forhandsvisning/konversationer");
await p.getByRole("tab", { name: "Uppföljningar" }).click();
await p.getByText("Iris skriver förfallna uppföljningar", { exact: false }).waitFor({ timeout: 20000 });
await p.getByRole("button", { name: /^Läs/ }).first().click();
const uppf = p.getByText("Jag skrev förra veckan", { exact: false }).first();
await uppf.waitFor({ timeout: 20000 });
await shot("Uteblir svaret följer Iris upp av sig själv", { target: uppf, y: 360, vila: false, ...mitt });
await p.getByRole("tab", { name: "Konversationer" }).click();
const boka = p.getByRole("button", { name: "Markera Möte bokat" }).first();
await boka.waitFor({ timeout: 20000 });
await top();
// Fixed framing (image pixels): from just left of the company name, from the top of the page, so the
// picture ends under the meeting question and before the thread's first mail. No click: the preview
// serves one thread, so the button changes nothing here.
await shot("Hela vägen till svar eller bokat möte", { target: boka, zoom: 1.65, focus: { x: 1314, y: 0 } });

// 6. Data security, what you get, the offer.
title("Datasäkerhet", {
  lines: [
    "All drift, lagring av kunddata och behandling i språkmodeller sker inom EU",
    "Varje kunds data är avskild på databasnivå",
    "Alla underleverantörer står med namn i integritetspolicyn",
  ],
  bars: 3,
});
title("Vad ni får", {
  lines: [
    "Bolag som passar er målgrupp, med skäl och källor",
    "Ett första mejl till varje bolag, skrivet på svenska",
    "Uppföljning fram till svar eller bokat möte",
    "Ni godkänner varje mejl innan det skickas",
  ],
  bars: 3.5,
});
title("Kostnadsfri pilot i två månader", { sub: "snajp.se", bars: 3, invert: true });

fs.mkdirSync(path.dirname(DATA), { recursive: true });
fs.writeFileSync(DATA, JSON.stringify(items, null, 2));
await browser.close();
console.log(problems.length ? "PROBLEMS:\n" + problems.join("\n") : "no page errors");
console.log("items", items.length);
