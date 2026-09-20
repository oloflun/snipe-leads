/**
 * Livrustning-piloten: logga in som kontakt@livrustning.se mot development och
 * bevisa att alla tre agenterna är öppna och fungerar.
 *
 * Lösenordet läses ur .env.deploy (RAILWAY_DEVELOPMENT_LIVRUSTNING_LOSEN) och
 * skrivs ALDRIG ut.
 */
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "https://web-development-6c85.up.railway.app";
const BILDER = process.env.BILDER || null;
if (BILDER) fs.mkdirSync(BILDER, { recursive: true });

const EPOST = "kontakt@livrustning.se";
const rawEnv = fs.readFileSync("C:/Users/sebbe/Desktop/snipe-leads/.env.deploy", "utf8");
const m = rawEnv.match(/^RAILWAY_DEVELOPMENT_LIVRUSTNING_LOSEN=(.+)$/m);
if (!m) {
  console.error("RAILWAY_DEVELOPMENT_LIVRUSTNING_LOSEN saknas i .env.deploy");
  process.exit(2);
}
const LOSEN = m[1].trim();

let fel = 0;
const rad = (ok, text) => {
  if (!ok) fel += 1;
  console.log(`  ${ok ? " " : "!"} ${text}`);
};
async function bild(page, namn) {
  if (BILDER) await page.screenshot({ path: `${BILDER}/livr-${namn}.png`, fullPage: true }).catch(() => {});
}

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();

try {
  // --- 1. Logga in --------------------------------------------------------
  console.log(`\n=== 1. Logga in (${EPOST}) ===`);
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.getByPlaceholder("du@bolag.se").fill(EPOST);
  await page.getByPlaceholder("•".repeat(8)).fill(LOSEN);
  await page.waitForTimeout(1000);
  await page.getByRole("button", { name: /Logga in/ }).last().click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 45000 }).catch(() => {});
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);
  const väg = new URL(page.url()).pathname;
  rad(väg === "/dashboard", `inloggningen landar på ${väg}   (förväntat /dashboard, INTE /onboarding)`);
  await bild(page, "01-dashboard");

  // --- 2. Inga mörklagda agenter ------------------------------------------
  console.log("\n=== 2. Menyn ===");
  const morka = await page
    .locator('a[title="Ingår inte i ert paket ännu — klicka och läs mer"]')
    .count();
  rad(morka === 0, `mörklagda agenter i menyn: ${morka}   (förväntat 0 — alla tre ingår)`);
  for (const namn of [/Iris/, /Support|Kundtjänst/, /Kvitto/]) {
    const finns = await page.getByRole("link", { name: namn }).count();
    rad(finns >= 1, `menylänken ${namn} finns (${finns})`);
  }

  // --- 3. Alla tre ytorna svarar ------------------------------------------
  console.log("\n=== 3. Agentytorna ===");
  for (const [v, krav] of [
    // Iris-vyn heter "Bolag"/"Kör Iris" — inte "prospekt". Uppmätt: den
    // första regexen fällde en frisk sida.
    ["/dashboard/leads", /Kör Iris|Alla bolag|Inga bolag/i],
    ["/dashboard/support", /inkorg|ärend|Testchatt/i],
    ["/dashboard/kvitton", /kvitto|verifikat|bokföring/i]
  ]) {
    const r = await page.goto(BASE + v, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(600);
    const info = await page.evaluate(() => ({
      text: document.body.innerText,
      vag: location.pathname
    }));
    const upsell = /Ingår inte i ert paket ännu/.test(info.text);
    const oppen = !upsell && krav.test(info.text);
    rad(
      r?.status() === 200 && oppen,
      `${v.padEnd(22)} → ${r?.status()} ${upsell ? "UPSELL-VY (fel)" : oppen ? "öppen" : "oväntat innehåll"}`
    );
    await bild(page, `03${v.replace(/\//g, "-")}`);
  }

  // --- 4. Testchatt grundad i Livrustnings KB ------------------------------
  console.log("\n=== 4. Testchatt ===");
  await page.goto(`${BASE}/dashboard/support`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /Testchatt/ }).first().click();
  await page.waitForTimeout(800);
  const falt = page.getByPlaceholder(/Skriv här/).first();
  await falt.waitFor({ state: "visible", timeout: 15000 });
  await falt.fill("Vad ingår i en Säkerhetsdag?");
  await falt.press("Enter");
  const utfall = await page
    .waitForFunction(
      () => {
        const t = document.body.innerText;
        // Racefritt: "annat" får bara dömas EFTER att arbetsindikatorn synts
        // och försvunnit. Uppmätt: utan flaggan dömdes "annat" millisekunder
        // efter Enter, innan agenten ens börjat.
        if (/Agenten arbetar/i.test(t)) {
          window.__sagsArbeta = true;
          return false;
        }
        const svans = t.split("Skriv här")[0].slice(-900);
        if (/station|fyra timmar|4 timmar|brand.*HLR|HLR.*brand/is.test(svans))
          return { slag: "grundat", text: svans.slice(-300) };
        if (/kvot|överbelastad|försök igen|tillfälligt/i.test(svans))
          return { slag: "kvotfel", text: svans.slice(-300) };
        if (/inte öppnad ännu/i.test(svans))
          return { slag: "avtalsgrind", text: svans.slice(-300) };
        if (/eskaler|kollega|återkommer/i.test(svans))
          return { slag: "eskalerat", text: svans.slice(-300) };
        if (!window.__sagsArbeta) return false;
        return { slag: "annat", text: svans.slice(-300) };
      },
      { timeout: 180000 }
    )
    .then((h) => h.jsonValue())
    .catch(() => ({ slag: "tystnad", text: "(Agenten arbetar kvar efter 3 min)" }));
  await bild(page, "04-testchatt");
  rad(
    utfall.slag === "grundat",
    `chatten: ${utfall.slag} — »${utfall.text.trim().replace(/\s+/g, " ").slice(-200)}«`
  );

  // --- 5. Admin är stängt --------------------------------------------------
  console.log("\n=== 5. Grinden ===");
  const r = await page.goto(`${BASE}/admin`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(600);
  const admin = await page.evaluate(() => ({
    vag: location.pathname,
    saknas: /Sidan finns inte/.test(document.body.innerText)
  }));
  rad(
    r?.status() === 404 && admin.saknas,
    `/admin → ${r?.status()} ${admin.vag}${admin.saknas ? ' "Sidan finns inte"' : " (ingen 404-text)"}`
  );
} finally {
  await browser.close();
}

console.log(fel === 0 ? "\nGRÖNT — Livrustning-inloggningen fungerar med alla tre agenterna." : `\n${fel} avvikelser.`);
process.exit(fel === 0 ? 0 : 1);
