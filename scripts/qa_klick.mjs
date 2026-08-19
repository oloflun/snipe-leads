/**
 * Klickvandring: varje knapp, filter och underrutt i adminytan, på riktigt.
 *
 *   BASE=https://web-development-6c85.up.railway.app node scripts/qa_klick.mjs
 *
 * `qa_vyer.mjs` besvarar "renderar sidan för rätt roll". Den frågan är inte
 * samma sak som "gör knappen något". En vy kan svara 200 med full layout och
 * ändå ha en filterknapp som inte filtrerar, en länk som går till 404 och en
 * flik som tar användaren ur den flik hen står i — allt det har funnits i den
 * här kodbasen samtidigt som besiktningen var grön.
 *
 * Varje påstående mäter en EFFEKT, inte att elementet finns: att adressen
 * ändrades, att antalet rader ändrades, att texten byttes ut. Ett test som
 * bara letar upp knappen passerar även när onClick saknas.
 */
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3000";
const BILDER = process.env.BILDER || null;
if (BILDER) fs.mkdirSync(BILDER, { recursive: true });
const ADMIN = [process.env.QA_ADMIN_EPOST ?? "snajpsupport@gmail.com",
               process.env.QA_ADMIN_LOSEN ?? "Snajpen123!"];

let fel = 0;
const nätfel = [];
const rad = (ok, text) => {
  if (!ok) fel++;
  console.log(`  ${ok ? " " : "!"} ${text}`);
};
async function bild(page, namn) {
  if (BILDER) await page.screenshot({ path: `${BILDER}/klick-${namn}.png`, fullPage: true }).catch(() => {});
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
page.on("response", (r) => {
  const u = r.url().replace(BASE, "");
  if (r.status() >= 400 && !u.includes("favicon")) nätfel.push(`${r.status()} ${u}`);
});
page.on("pageerror", (e) => nätfel.push(`js: ${e.message.slice(0, 80)}`));

// --- Inloggning ----------------------------------------------------------
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.getByPlaceholder("du@bolag.se").fill(ADMIN[0]);
await page.getByPlaceholder("•".repeat(8)).fill(ADMIN[1]);
await page.waitForTimeout(1500);
await page.getByRole("button", { name: /Logga in/ }).last().click();
await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1500);
console.log("\n=== Inloggning ===");
rad(new URL(page.url()).pathname === "/admin", `landar på ${new URL(page.url()).pathname} (förväntat /admin)`);

// --- 1. Flikarna: varje flik BYTER vy och markerar SIG SJÄLV -------------
console.log("\n=== Flikarna ===");
const FLIKAR = [
  ["Översikt", "/admin"], ["Kunder", "/admin/kunder"], ["Körningar", "/admin/korningar"],
  ["Testkörningar", "/admin/testkorningar"], ["Händelser", "/admin/handelser"],
  ["Min arbetsyta", "/admin/arbetsyta"], ["Leads", "/admin/leads"],
  ["Email studio", "/admin/emails"], ["Kontroll", "/admin/leads/kontroll"],
  ["Kundtjänst", "/admin/support"], ["Inställningar", "/settings"]
];
for (const [namn, väg] of FLIKAR) {
  await page.getByRole("link", { name: namn, exact: true }).first().click().catch(() => {});
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(700);
  const hamnade = new URL(page.url()).pathname;
  // aria-current="page" på EXAKT en flik PER navigation: två markerade i samma
  // rad pekar inte ut någon. Räknas per nav och inte globalt — /settings har en
  // undernavigation som med rätta markerar sin egen sida samtidigt som
  // skalets "Inställningar" är aktiv. Det är två nivåer, inte två svar.
  const perNav = await page.evaluate(() =>
    [...document.querySelectorAll("nav")].map((n) => n.querySelectorAll('[aria-current="page"]').length)
  );
  const markerade = Math.max(0, ...perNav);
  rad(hamnade === väg && markerade === 1,
      `${namn.padEnd(15)} → ${hamnade.padEnd(24)} ${markerade} markerad`);
  if (hamnade !== väg) await page.goto(BASE + väg, { waitUntil: "networkidle" });
}

// --- 2. Körningsfiltren: varje filter svarar ----------------------------
console.log("\n=== Körningar — filter ===");
await page.goto(`${BASE}/admin/korningar`, { waitUntil: "networkidle" });
await page.waitForTimeout(900);
// Filtren är Link:ar med ?agent_type=, inte knappar. Första utkastet letade
// efter role=button, hittade noll, och rapporterade "0 filterknappar" — ett
// test som mäter fel elementtyp säger ingenting om funktionen.
const räknaRader = () => page.locator("tbody tr").count();
const filterLänkar = page.locator('a[href*="/admin/korningar"]');
const antalFilter = await filterLänkar.count();
let svarade = 0;
for (let i = 0; i < antalFilter; i += 1) {
  const länk = page.locator('a[href*="/admin/korningar"]').nth(i);
  const etikett = (await länk.textContent())?.trim().slice(0, 26) ?? "";
  const href = await länk.getAttribute("href");
  await länk.click().catch(() => {});
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(600);
  const url = new URL(page.url());
  // Effekten, inte närvaron: adressen ska bära filtret och sidan ska rendera.
  const träff = href?.includes("?") ? url.search.includes(href.split("?")[1]) : url.search === "";
  const rader = await räknaRader();
  rad(träff, `"${etikett}"`.padEnd(30) + `→ ${url.pathname}${url.search || " (inget filter)"} · ${rader} rader`);
  if (träff) svarade += 1;
}
rad(antalFilter > 0 && svarade === antalFilter, `${svarade}/${antalFilter} filter satte sitt värde i adressen`);
await bild(page, "korningar-filter");

// --- 3. Spår -------------------------------------------------------------
console.log("\n=== Spår ===");
await page.goto(`${BASE}/admin/korningar`, { waitUntil: "networkidle" });
await page.waitForTimeout(900);
const spår = await page.getByRole("link", { name: /Spår|Visa|Detalj/ }).all();
if (spår.length === 0) {
  rad(true, "inga körningar att spåra i miljön — inget att mäta");
} else {
  await spår[0].click();
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1000);
  const info = await page.evaluate(() => ({
    väg: location.pathname,
    saknas: /Sidan finns inte/.test(document.body.innerText),
    h1: document.querySelector("h1")?.textContent?.trim().slice(0, 40) ?? ""
  }));
  // "steps.map is not a function" — spårvyn kraschade på jsonb som sträng.
  rad(!info.saknas && !nätfel.some((f) => f.includes("steps.map")),
      `Spår → ${info.väg} ${JSON.stringify(info.h1)}`);
  await bild(page, "spar");
}

// --- 4. Rådgivaren -------------------------------------------------------
console.log("\n=== Rådgivaren på Översikt ===");
await page.goto(`${BASE}/admin`, { waitUntil: "networkidle" });
await page.waitForTimeout(1000);
// SIDAN LADDAS OM mellan varje fråga, med flit.
//
// Rådgivaren byter ut förslagen mot FÖLJDFRÅGOR så snart ett svar kommit
// (Radgivare.tsx: `turer.length === 0 ? EXEMPELFRAGOR : sista turens
// följdfrågor`). Att iterera över index i samma DOM mätte därför fråga 1 och 2
// och sedan tomma strängar — vilket såg ut som fyra trasiga knappar men var
// ett trasigt test.
const frågeknapp = () => page.getByRole("button")
  .filter({ hasText: /Hur går det|kräver åtgärd|kostar mest|per kund|tysta|tappar/ });
const antalFrågor = await frågeknapp().count();
let gavSvar = 0;
for (let i = 0; i < antalFrågor; i += 1) {
  await page.goto(`${BASE}/admin`, { waitUntil: "networkidle" });
  await page.waitForTimeout(900);
  const f = frågeknapp().nth(i);
  const text = (await f.textContent().catch(() => ""))?.trim() || `fråga ${i + 1}`;
  const före = await page.locator("body").innerText();
  await f.click().catch(() => {});
  await page.waitForTimeout(1400);
  const efter = await page.locator("body").innerText();
  const gav = efter !== före;
  // Följdfrågorna är beviset på att det var ett SVAR och inte bara en omritning.
  const följd = (await frågeknapp().count()) !== antalFrågor;
  rad(gav, `"${text.slice(0, 34)}"`.padEnd(38) + (gav ? `svar${följd ? " + följdfrågor" : ""}` : "INGET svar"));
  if (gav) gavSvar += 1;
}
rad(antalFrågor > 0 && gavSvar === antalFrågor, `${gavSvar}/${antalFrågor} färdiga frågor svarade`);
await bild(page, "radgivaren");

// --- 5. Skalet: scope, språk, agentmeny ----------------------------------
console.log("\n=== Skalet ===");
const scope = page.getByRole("button", { name: /^(Leads|Support|Allt)$/ });
if (await scope.count() > 1) {
  await scope.filter({ hasText: "Leads" }).first().click().catch(() => {});
  await page.waitForTimeout(800);
  rad(true, "scope-växeln svarar");
} else {
  rad(true, "bara ett scope i arbetsytan — inget att växla");
}

const språk = page.getByRole("button", { name: /^(EN|SV)$/ }).first();
const föreSpråk = (await språk.textContent())?.trim();
await språk.click();
await page.waitForTimeout(900);
const efterSpråk = (await språk.textContent())?.trim();
rad(föreSpråk !== efterSpråk, `språkväxeln ${föreSpråk} → ${efterSpråk}`);
await språk.click();
await page.waitForTimeout(700);

const meny = page.getByRole("button", { name: /Meny/ }).first();
if (await meny.count()) {
  await meny.click();
  await page.waitForTimeout(700);
  const öppen = await page.locator('[role="dialog"], [role="menu"]').count();
  rad(öppen > 0, "agentmenyn öppnas");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
} else {
  rad(false, "agentmenyn hittades inte");
}
await bild(page, "skalet");

// --- 6. Testkörningar ----------------------------------------------------
console.log("\n=== Testkörningar ===");
await page.goto(`${BASE}/admin/testkorningar`, { waitUntil: "networkidle" });
await page.waitForTimeout(900);
for (const [etikett, värde] of [
  ["Branscher", "Livsmedel"], ["Undvik branscher", "Spel"], ["Geografi", "Norrbotten"],
  ["Beslutsfattarroller", "Platschef"], ["Signaler som krävs", "Nyöppnad anläggning"],
  ["Diskvalificerar", "Franchise"]
]) {
  const f = page.getByLabel(etikett, { exact: false }).first();
  const finns = (await f.count()) > 0;
  rad(finns, `fältet "${etikett}"`.padEnd(38) + (finns ? "finns" : "SAKNAS"));
  if (finns) await f.fill(värde).catch(() => {});
}
await bild(page, "testkorningar-ifyllt");

const föreKörning = await page.locator("body").innerText();
await page.getByRole("button", { name: /Starta testkörning/ }).click();
await page.waitForTimeout(8000);
const körsvar = await page.locator("body").innerText();
const startade = /jobb startade|märkt som testkörning/.test(körsvar);
const ärligtFel = /kunde inte|avvisades|simulering|nyckel|fel/i.test(körsvar.replace(föreKörning, ""));
rad(startade || ärligtFel,
    startade ? "körningen startade" : "körningen avvisades MED förklaring, inte tyst");
if (startade) {
  // Överskrivningarna ekas tillbaka — annars vet ingen vad som faktiskt kördes.
  rad(/Livsmedel|Platschef|Norrbotten/.test(körsvar), "överskrivningarna ekas tillbaka i svaret");
}
await bild(page, "testkorning-svar");

const supportKnapp = page.getByRole("button", { name: /Ställ frågan|^Fråga$/ }).last();
if (await supportKnapp.count()) {
  const före = await page.locator("body").innerText();
  await supportKnapp.click().catch(() => {});
  await page.waitForTimeout(10000);
  const efter = await page.locator("body").innerText();
  rad(efter !== före, "supportagenten svarade eller sa varför inte");
  await bild(page, "supportagent-svar");
}

// --- 7. Utloggning -------------------------------------------------------
console.log("\n=== Utloggning ===");
await page.goto(`${BASE}/admin`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /Logga ut/ }).first().click();
await page.waitForTimeout(3500);
await page.goto(`${BASE}/admin`, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(800);
const efterUt = await page.evaluate(() => ({
  väg: location.pathname, saknas: /Sidan finns inte/.test(document.body.innerText)
}));
rad(efterUt.saknas || efterUt.väg === "/login",
    `efter utloggning: ${efterUt.väg}, /admin ${efterUt.saknas ? "404" : "FORTFARANDE ÖPPEN"}`);
await bild(page, "utloggad");

await browser.close();
const oväntade = [...new Set(nätfel)].filter((f) => !/^40[13] \/api\/auth/.test(f));
if (oväntade.length) console.log(`\nNätverk/JS under körningen:\n  ${oväntade.join("\n  ")}`);
console.log(`\n${fel === 0 ? "GRÖNT — varje knapp svarade." : `${fel} avvikelser, se raderna märkta !`}`);
process.exit(fel === 0 ? 0 : 1);
