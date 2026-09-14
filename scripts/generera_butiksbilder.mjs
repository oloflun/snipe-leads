import { chromium, devices } from "playwright";

/**
 * Butiksbilderna till manifestets `screenshots`.
 *
 * Chrome på desktop visar den RIKA installationsdialogen — namn, beskrivning
 * och förhandsbild — bara om manifestet har minst en skärmbild med
 * form_factor "wide". Utan dem erbjuds "Skapa genväg", och en genväg öppnas i
 * en vanlig flik. Det är skillnaden mellan att installera en app och att
 * spara ett bokmärke.
 *
 * Måtten i manifestet MÅSTE stämma med filernas faktiska pixlar, annars
 * ignoreras posten tyst.
 */
const BAS = "http://localhost:3005";
const UT = process.argv[2];
const browser = await chromium.launch();

for (const [namn, vag] of [["oversikt", "/demo"], ["analys", "/demo/analytics"], ["bolag", "/demo/companies"]]) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const s = await ctx.newPage();
  await s.goto(BAS + vag, { waitUntil: "networkidle" });
  await s.waitForTimeout(1500);
  await s.screenshot({ path: `${UT}/wide-${namn}.png` });
  await ctx.close();
}

for (const [namn, vag] of [["oversikt", "/demo"], ["analys", "/demo/analytics"]]) {
  const ctx = await browser.newContext({ ...devices["iPhone 13"], deviceScaleFactor: 1 });
  const s = await ctx.newPage();
  await s.goto(BAS + vag, { waitUntil: "networkidle" });
  await s.waitForTimeout(1500);
  await s.screenshot({ path: `${UT}/narrow-${namn}.png` });
  await ctx.close();
}

await browser.close();
console.log("klart");
