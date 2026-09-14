/**
 * Hela kundresan GENOM YTAN, i en riktig webbläsare mot development.
 *
 *   BASE=https://web-development-6c85.up.railway.app BILDER=<dir> node scripts/qa_kundresa.mjs
 *
 * Fortsättningen på scripts/qa_testkund.mjs: den bevisar att ett konto kan
 * SKAPAS — den här bevisar att kontot kan ANVÄNDAS. Ny kund, sedan varje
 * uppgift en riktig kund utför, i den ordning en riktig kund utför dem:
 *
 *   1. Skapa konto + onboarding (testarbetsyta — körningarna märks is_test)
 *   2. Skriva en kunskapsbasartikel (utan den har testchatten inget att grunda i)
 *   3. Ställa en fråga i Testchatt och få ett grundat svar
 *   4. Starta en leads-körning och se den gå klart
 *   5. Öppna bokföringen (eller mötas av en ärlig entitlement-grind)
 *
 * Varje steg är sitt eget try/catch: en död deluppgift fäller inte mätningen
 * av de andra. Ett eskalerat chattsvar är INTE ett fel — agenten som hellre
 * lämnar över än gissar är produktlöftet — men ett svar som aldrig kommer är.
 */
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3000";
const BILDER = process.env.BILDER || null;
if (BILDER) fs.mkdirSync(BILDER, { recursive: true });

const STAMP = process.env.STAMP ?? String(Date.now()).slice(-8);
//: Sätt ATERANVAND=<epost> för att hoppa över kontoskapandet och logga in på
//: ett konto en tidigare körning skapade — annars skräpar varje omkörning ner
//: spegel-databasen med en ny testtenant.
const ATERANVAND = process.env.ATERANVAND || null;
const EPOST = ATERANVAND ?? `testkund+${STAMP}@snajp.se`;
const LOSEN = "Testkund123!";

let fel = 0;
const rad = (ok, text) => {
  if (!ok) fel++;
  console.log(`  ${ok ? " " : "!"} ${text}`);
};
const bild = async (page, namn) => {
  if (BILDER) await page.screenshot({ path: `${BILDER}/resa-${namn}.png`, fullPage: true }).catch(() => {});
};

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();

// --- 1. Konto + onboarding (samma väg som qa_testkund.mjs) ----------------
console.log(`\n=== 1. ${ATERANVAND ? "Logga in" : "Skapa konto"} (${EPOST}) ===`);
if (ATERANVAND) {
  try {
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    const losenfalt = page.getByPlaceholder("•".repeat(8));
    await losenfalt.waitFor({ state: "visible", timeout: 30000 });
    await page.getByPlaceholder("du@bolag.se").fill(EPOST);
    await losenfalt.fill(LOSEN);
    await page.waitForTimeout(1500);
    await page.getByRole("button", { name: /Logga in/ }).last().click();
    await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 45000 });
    rad(true, "inloggad på befintligt konto");
  } catch (e) {
    rad(false, `inloggning: ${String(e).slice(0, 160)}`);
  }
} else try {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Skapa konto" }).first().click();
  await page.waitForTimeout(800);
  await page.getByPlaceholder("du@bolag.se").fill(EPOST);
  await page.getByPlaceholder("•".repeat(8)).fill(LOSEN);
  const namnfält = page.locator('input[name="name"], input[autocomplete="name"]').first();
  if (await namnfält.count()) await namnfält.fill(`Testkund ${STAMP}`);
  await page.waitForTimeout(1200);
  await page.getByRole("button", { name: /Skapa konto/ }).last().click();
  await page.waitForURL((u) => u.pathname.startsWith("/onboarding"), { timeout: 45000 });
  rad(true, "registreringen landar på /onboarding");

  await page.locator('input[type="checkbox"]').first().check(); // testarbetsyta
  for (const [etikett, värde] of [
    ["Webbplats", "https://testkund.example.se"],
    ["Vad ni säljer", "Vi säljer besiktning av lyftanordningar till industri och bygg."],
    ["Något extra att fokusera på (valfritt)", "Helst bolag i Skåne med egen produktion."]
  ]) {
    await page.getByLabel(etikett).fill(värde);
  }
  await page.getByRole("button", { name: /Spara och läs in/ }).click();
  await page.waitForURL((u) => u.pathname === "/dashboard", { timeout: 45000 });
  await page.waitForLoadState("networkidle").catch(() => {});
  rad(true, "onboardingen landar på /dashboard");
  await bild(page, "01-dashboard");
} catch (e) {
  rad(false, `konto/onboarding: ${String(e).slice(0, 160)}`);
  await bild(page, "01-fel");
}

// --- 2. Kunskapsbasartikel ------------------------------------------------
console.log("\n=== 2. Kunskapsbasartikel ===");
if (ATERANVAND) {
  console.log("    (hoppas över — kontot har redan artikeln från första körningen)");
} else try {
  await page.goto(`${BASE}/settings/kunskapsbas`, { waitUntil: "networkidle" });
  await page.getByPlaceholder("Rubrik — t.ex. Ångerrätt och returer").fill("Priser och offert");
  await page
    .getByPlaceholder("Texten agenterna ska svara ur. Skriv som ni skulle svarat en kund.")
    .fill(
      "En årsbesiktning av en lyftanordning kostar från 4 900 kr exklusive moms. " +
        "Offert lämnas inom två arbetsdagar efter förfrågan. Vi besiktigar i hela " +
        "Skåne och ombesiktning efter anmärkning ingår i priset."
    );
  await page.getByRole("button", { name: /Spara i kunskapsbasen/ }).click();
  await page.waitForSelector("text=Sparat. Agenterna kan svara ur texten", { timeout: 20000 });
  rad(true, "artikeln sparad — agenterna kan svara ur den");
  await bild(page, "02-kunskapsbas");
} catch (e) {
  rad(false, `kunskapsbas: ${String(e).slice(0, 160)}`);
  await bild(page, "02-fel");
}

// --- 3. Testchatt ---------------------------------------------------------
console.log("\n=== 3. Testchatt ===");
try {
  await page.goto(`${BASE}/dashboard/support`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /Testchatt/ }).first().click();
  await page.waitForTimeout(800);
  const fält = page.getByPlaceholder(/Skriv här/).first();
  await fält.waitFor({ state: "visible", timeout: 15000 });
  await fält.fill("Hej! Vad kostar en årsbesiktning av en lyftanordning?");
  await fält.press("Enter");
  await bild(page, "03a-testchatt-skickad");

  // Riktig AI-kedja. Första versionen av den här checken matchade mot HELA
  // sidtexten och blev grön på kundens EGEN bubbla ("årsbesiktning") medan
  // "Agenten arbetar" fortfarande snurrade — en falsk grön som bara
  // skärmbilden avslöjade. Nu: vänta tills arbetar-indikatorn är BORTA och
  // läs då vad som faktiskt står sist i tråden. Priset ur kunskapsbasen
  // (4 900) kan inte komma ur frågan, och ett svenskt kvotfel är ett ÄRLIGT
  // utfall som rapporteras som sådant — det som fäller är tystnad.
  const utfall = await page
    .waitForFunction(
      () => {
        const t = document.body.innerText;
        if (/Agenten arbetar/i.test(t)) return false;
        const svans = t.split("Skriv här")[0].slice(-800);
        if (/4\s?900/.test(svans)) return { slag: "grundat", text: svans.slice(-300) };
        if (/kvot|överbelastad|försök igen|tillfälligt/i.test(svans))
          return { slag: "kvotfel", text: svans.slice(-300) };
        if (/eskaler|kollega|återkommer/i.test(svans))
          return { slag: "eskalerat", text: svans.slice(-300) };
        return { slag: "annat", text: svans.slice(-300) };
      },
      { timeout: 180000 }
    )
    .then((h) => h.jsonValue())
    .catch(() => ({ slag: "tystnad", text: "(Agenten arbetar kvar efter 3 min)" }));
  await bild(page, "03b-testchatt-svar");
  rad(
    utfall.slag === "grundat" || utfall.slag === "kvotfel" || utfall.slag === "eskalerat",
    `chatten: ${utfall.slag} — »${utfall.text.trim().replace(/\s+/g, " ").slice(-180)}«`
  );
} catch (e) {
  rad(false, `testchatt: ${String(e).slice(0, 160)}`);
  await bild(page, "03-fel");
}

// --- 4. Leads-körning -----------------------------------------------------
console.log("\n=== 4. Leads-körning ===");
try {
  await page.goto(`${BASE}/dashboard/leads`, { waitUntil: "networkidle" });
  await page.getByLabel(/Antal bolag/).fill("2");
  await page.getByLabel(/^Branscher/).fill("Industri, bygg");
  await page.getByLabel(/^Stad/).fill("Skåne");
  await bild(page, "04a-leads-ifylld");
  await page.getByRole("button", { name: /Starta (test)?körning/ }).click();

  // Formuläret pollar jobben självt: sök-fasen, sedan research per bolag.
  // Första versionen matchade mot HELA sidtexten och blev grön på
  // exempelbolagspanelens "Öppna utkastet" medan knappen fortfarande sa
  // "Startar…". Nu: vänta tills knappen lämnat Startar-läget OCH antingen
  // ett role=alert-fel eller formulärets resultatblock finns — och citera
  // det som faktiskt står där i stället för att gissa en dom.
  const utfall = await page
    .waitForFunction(
      () => {
        const knapp = [...document.querySelectorAll("button")].find((b) =>
          /Starta|Startar/.test(b.textContent || "")
        );
        if (knapp && /Startar/.test(knapp.textContent || "")) return false;
        const alert = document.querySelector('[role="alert"]');
        if (alert?.textContent?.trim()) return { slag: "fel", text: alert.textContent.trim() };
        const t = document.body.innerText;
        const m = t.match(/(Research klar[^\n]*|Hittade \d+ bolag[^\n]*|\d+ av \d+ bolag[^\n]*)/);
        if (m) return { slag: "klart", text: m[1] };
        return false;
      },
      { timeout: 480000 }
    )
    .then((h) => h.jsonValue())
    .catch(() => ({ slag: "tystnad", text: "(varken resultat eller fel inom 8 min)" }));
  await bild(page, "04b-leads-resultat");
  rad(
    utfall.slag === "klart" || utfall.slag === "fel",
    `körningen: ${utfall.slag} — »${String(utfall.text).replace(/\s+/g, " ").slice(0, 200)}«`
  );
} catch (e) {
  rad(false, `leads: ${String(e).slice(0, 160)}`);
  await bild(page, "04-fel");
}

// --- 5. Bokföringen -------------------------------------------------------
console.log("\n=== 5. Bokföringen ===");
try {
  const r = await page.goto(`${BASE}/dashboard/bokforing`, { waitUntil: "networkidle", timeout: 45000 });
  const info = await page.evaluate(() => ({
    väg: location.pathname,
    text: document.body.innerText.slice(0, 400)
  }));
  // Entitlement-grinden ÄR en 404 (WorkspaceSection: !products.includes →
  // notFound()), samma designbeslut som /admin för en kund. Första körningen
  // 2026-09-08 dömde 404:an som avvikelse — det var skriptets fel, inte
  // produktens: en osåld produkt ska inte ens synas, inte visa en säljruta.
  const öppen = /Bokföringsassistent|underlag|kvitto/i.test(info.text);
  const grindad = r?.status() === 404 || /Sidan finns inte/i.test(info.text);
  rad(öppen || grindad, `bokföringen: ${öppen ? "öppen för kontot" : grindad ? "korrekt entitlement-grindad (404, som /admin)" : `oväntat läge (${r?.status()} ${info.väg})`}`);
  await bild(page, "05-bokforing");
} catch (e) {
  rad(false, `bokforing: ${String(e).slice(0, 160)}`);
  await bild(page, "05-fel");
}

await browser.close();
console.log(`\nKonto: ${EPOST} / ${LOSEN}`);
console.log(fel === 0 ? "GRÖNT — hela kundresan fungerar." : `${fel} avvikelser, se raderna märkta !`);
process.exit(fel === 0 ? 0 : 1);
