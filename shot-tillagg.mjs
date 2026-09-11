import { chromium } from "playwright";
const UT =
  "C:/Users/sebbe/AppData/Local/Temp/claude/C--Users-sebbe-Desktop-snipe-leads/c498f2b8-f121-47ef-8e7c-a1ab04f77eb6/scratchpad";
const BAS = "https://web-development-6c85.up.railway.app";
const KUND = "ce659621-820c-40dc-a49e-850cffbf8ca2";

const browser = await chromium.launch();

async function loggaIn(page, epost, losen) {
  await page.goto(`${BAS}/login`, { waitUntil: "networkidle" });
  await page.getByPlaceholder("du@bolag.se").fill(epost);
  await page.locator('input[type="password"]').fill(losen);
  await page.locator('form button[type="submit"]').filter({ hasText: "Logga in" }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30000 });
}

for (const bredd of [1280, 768, 375]) {
  const ctx = await browser.newContext({ viewport: { width: bredd, height: 900 } });
  const page = await ctx.newPage();
  const fel = [];
  page.on("pageerror", (e) => fel.push(String(e)));
  page.on("console", (m) => m.type() === "error" && fel.push(m.text()));

  await loggaIn(page, "snajpsupport@gmail.com", "Snajpen123!");
  await page.goto(`${BAS}/admin/kunder/${KUND}`, { waitUntil: "networkidle" });
  await page.waitForSelector("#tillagg-rubrik", { timeout: 20000 });
  await page.locator("#tillagg-rubrik").scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);

  const spill = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  const pa = await page.evaluate(
    () => [...document.querySelectorAll("[role=switch]")].filter((v) => v.getAttribute("aria-checked") === "true").length
  );
  console.log(`${bredd}px — horisontellt spill: ${spill}, påslagna växlar: ${pa}, sidfel: ${fel.length ? fel.join(" | ") : "inga"}`);

  await page.screenshot({ path: `${UT}/tillagg-${bredd}.png` });
  await ctx.close();
}

// Kundens vy: tillägget tänt = riktig listvy, inte upsell-kortet.
const kundCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const kund = await kundCtx.newPage();
await loggaIn(kund, "testkund+qa0904fable@snajp.se", "Testkund123!");
await kund.goto(`${BAS}/dashboard/leads/listor`, { waitUntil: "networkidle" });
await kund.waitForTimeout(1200);
const text = await kund.evaluate(() => document.body.innerText);
console.log("kundvyn — upsell-kort kvar:", text.includes("Hör av dig om leadslistor"));
console.log("kundvyn — riktig vy:", text.includes("Beställ en lista"));
await kund.screenshot({ path: `${UT}/tillagg-kundvy.png` });
await kundCtx.close();

await browser.close();
console.log("klart");
