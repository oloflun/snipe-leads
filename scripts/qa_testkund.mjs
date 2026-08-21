/**
 * Skapar en testkund GENOM YTAN och bevisar grinden, i en riktig webbläsare.
 *
 *   BASE=https://web-development-6c85.up.railway.app node scripts/qa_testkund.mjs
 *
 * Inte programmatiskt med flit: ett konto som skapas med en INSERT bevisar att
 * databasen tar emot raden, inte att en människa kan bli kund. Det som mäts här
 * är hela vägen — Skapa konto, onboardingen, testarbetsytan som hoppar över
 * organisationsnumret, och att den färdiga kunden landar på /dashboard och får
 * 404 på hela /admin.
 *
 * Personnummer-fallet körs som en SEPARAT mätning i samma körning: enskild
 * firma har personnummer som organisationsnummer, och spärren mot det togs bort
 * 2026-08-18. Att testarbetsytan hoppar över fältet säger ingenting om huruvida
 * fältet accepterar ett personnummer — det är två olika vägar in.
 */
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3000";
const BILDER = process.env.BILDER || null;
if (BILDER) fs.mkdirSync(BILDER, { recursive: true });

// Stämpeln gör körningen upprepbar: adressen är ny varje gång, så "kontot finns
// redan" aldrig kan förväxlas med "registreringen fungerar".
const STAMP = process.env.STAMP ?? String(Date.now()).slice(-8);
const EPOST = process.env.QA_TEST_EPOST ?? `testkund+${STAMP}@snajp.se`;
const LOSEN = process.env.QA_TEST_LOSEN ?? "Testkund123!";
const NAMN = `Testkund ${STAMP}`;

/**
 * Personnummer för enskild firma. Luhn-giltigt — kontrollsiffran är UTRÄKNAD,
 * inte påhittad. Ett påhittat nummer faller på Luhn och mäter då att
 * kontrollsiffran fungerar, inte att bolagsformen accepteras. Det misstaget
 * kostade en körning.
 */
const PERSONNUMMER = "19850312-1231";

let fel = 0;
const rad = (ok, text) => {
  if (!ok) fel++;
  console.log(`  ${ok ? " " : "!"} ${text}`);
};

async function bild(page, namn) {
  if (BILDER) await page.screenshot({ path: `${BILDER}/testkund-${namn}.png`, fullPage: true }).catch(() => {});
}

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();

// --- 1. Skapa konto ------------------------------------------------------
console.log(`\n=== Skapa konto (${EPOST}) ===`);
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Skapa konto" }).first().click();
await page.waitForTimeout(800);
await bild(page, "01-skapa-konto");

await page.getByPlaceholder("du@bolag.se").fill(EPOST);
await page.getByPlaceholder("•".repeat(8)).fill(LOSEN);
const namnfält = page.locator('input[name="name"], input[autocomplete="name"]').first();
if (await namnfält.count()) await namnfält.fill(NAMN);
await page.waitForTimeout(1200);
await page.getByRole("button", { name: /Skapa konto/ }).last().click();
await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 45000 }).catch(() => {});
await page.waitForLoadState("networkidle").catch(() => {});
await page.waitForTimeout(1500);

let väg = new URL(page.url()).pathname;
rad(väg === "/onboarding", `registreringen landar på ${väg}   (förväntat /onboarding)`);
await bild(page, "02-onboarding-tom");

// --- 2. Organisationsnumret nekar ett skrivfel, men INTE ett personnummer ---
console.log("\n=== Organisationsnumret ===");
const orgfält = page.getByLabel("Organisationsnummer");
await orgfält.fill("556824-9021");           // Luhn fel med flit
await orgfält.blur();
await page.waitForTimeout(600);
let varning = await page.locator("text=/Kontrollsiffran stämmer inte/").count();
rad(varning > 0, "ett felaktigt nummer varnas i fältet");
await bild(page, "03-orgnr-fel");

await orgfält.fill(PERSONNUMMER);            // enskild firma
await orgfält.blur();
await page.waitForTimeout(600);
const pnrVarning = await page
  .locator("text=/Kontrollsiffran stämmer inte|tio siffror|personnummer/")
  .count();
rad(pnrVarning === 0, `personnummer (${PERSONNUMMER}) accepteras — enskild firma`);
await bild(page, "04-personnummer-godtas");

// --- 3. Testarbetsytan hoppar över numret helt ---------------------------
console.log("\n=== Testarbetsyta ===");
await orgfält.fill("");
const ruta = page.locator('input[type="checkbox"]').first();
await ruta.check();
await page.waitForTimeout(400);
rad(await ruta.isChecked(), "testarbetsytan går att kryssa i");
await bild(page, "05-testarbetsyta-ikryssad");

// getByLabel och inte getByPlaceholder: platshållarna är exempeltexter som
// byts när copyn skrivs om, och ett fält som tyst inte fylls i ser ut som ett
// fel i formuläret. Uppmätt — webbplatsen hade platshållaren
// "https://exempel.se", inte den skriptet gissade, och submit föll på
// "Fyll i webbplatsen".
for (const [etikett, värde] of [
  ["Webbplats", "https://testkund.example.se"],
  ["Vad ni säljer", "Vi säljer besiktning av lyftanordningar till industri och bygg."],
  ["Något extra att fokusera på (valfritt)", "Helst bolag i Skåne med egen produktion."]
]) {
  await page.getByLabel(etikett).fill(värde);
}
await page.waitForTimeout(400);
await bild(page, "06-onboarding-ifylld");

await page.getByRole("button", { name: /Spara och läs in/ }).click();
await page.waitForURL((u) => !u.pathname.startsWith("/onboarding"), { timeout: 45000 }).catch(() => {});
await page.waitForLoadState("networkidle").catch(() => {});
await page.waitForTimeout(2000);

väg = new URL(page.url()).pathname;
rad(väg === "/dashboard", `onboardingen landar på ${väg}   (förväntat /dashboard)`);
await bild(page, "07-dashboard");

// --- 4. Grinden: kunden ser inte adminytan -------------------------------
console.log("\n=== Grinden ===");
for (const v of ["/admin", "/admin/kunder", "/admin/korningar", "/admin/testkorningar",
                 "/admin/handelser", "/admin/arbetsyta"]) {
  const r = await page.goto(BASE + v, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(400);
  const saknas = await page.evaluate(() => /Sidan finns inte/.test(document.body.innerText));
  rad(r?.status() === 404 && saknas, `${v.padEnd(22)} → ${r?.status()} "Sidan finns inte"`);
}
await bild(page, "08-kund-nekas-admin");

// --- 5. Kunden når sin egen arbetsyta ------------------------------------
console.log("\n=== Kundens egen arbetsyta ===");
// Väg → var man SKA hamna. Två av dem är inte sig själva, och båda är
// avsiktliga 308:or i next.config.ts: "Målgrupp och autonomi" är en
// inställning och flyttade in i inställningarna. Listan sa tidigare att varje
// väg skulle landa på sig själv, så den flaggade en dokumenterad omdirigering
// som en avvikelse — ett QA-skript som ropar varg slutar man läsa.
const KUNDVAGAR = [
  ["/dashboard", "/dashboard"],
  ["/dashboard/leads", "/dashboard/leads"],
  ["/dashboard/leads/kontroll", "/settings/leads"],
  ["/dashboard/emails", "/dashboard/emails"],
  ["/dashboard/support", "/dashboard/support"],
  ["/settings", "/settings"]
];
for (const [v, forvantat] of KUNDVAGAR) {
  const r = await page.goto(BASE + v, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(400);
  const info = await page.evaluate(() => ({
    hamnade: location.pathname,
    saknas: /Sidan finns inte/.test(document.body.innerText)
  }));
  rad(r?.status() === 200 && !info.saknas && info.hamnade === forvantat,
      `${v.padEnd(26)} → ${r?.status()} ${info.hamnade}` +
      (forvantat === v ? "" : `   (förväntat ${forvantat})`));
  await bild(page, `09-kund${v.replace(/\//g, "-")}`);
}

await browser.close();
console.log(
  `\nKonto: ${EPOST} / ${LOSEN}` +
  `\n${fel === 0 ? "GRÖNT — inga avvikelser." : `${fel} avvikelser, se raderna märkta !`}`
);
process.exit(fel === 0 ? 0 : 1);
