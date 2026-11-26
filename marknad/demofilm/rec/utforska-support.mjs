// What the public demo's customer-service section shows (example data only), to plan the support part.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
const APP = "https://web-development-6c85.up.railway.app";
// Screenshots and page text land in explore/support (gitignored).
const OUT = path.join(path.resolve(path.dirname(fileURLToPath(import.meta.url)), ".."), "explore", "support");
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
try {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1, locale: "sv-SE", timezoneId: "Europe/Stockholm" });
  const p = await ctx.newPage();
  for (const [namn, url] of [["support", "/demo/support"], ["support-drift", "/demo/support?drift=1"], ["regler", "/demo/regler"], ["oversikt", "/demo"], ["attgora", "/demo/att-gora"]]) {
    await p.goto(APP + url, { waitUntil: "networkidle", timeout: 120000 });
    await p.waitForTimeout(1200);
    await p.screenshot({ path: `${OUT}/${namn}.png` });
    await p.screenshot({ path: `${OUT}/${namn}-full.png`, fullPage: true });
    console.log(`== ${namn} TABS:`, (await p.getByRole("tab").allInnerTexts()).join(" | "));
    console.log(`== ${namn} BUTTONS:`, (await p.getByRole("button").allInnerTexts()).filter(Boolean).join(" | ").replace(/\n/g, " ").slice(0, 700));
    console.log(`== ${namn} TEXT:`, (await p.locator("main").innerText()).replace(/\n+/g, " / ").slice(0, 1600));
  }
  // The support tabs, one by one.
  await p.goto(APP + "/demo/support", { waitUntil: "networkidle" });
  await p.waitForTimeout(1000);
  const tabs = await p.getByRole("tab").allInnerTexts();
  for (const t of tabs) {
    await p.getByRole("tab", { name: t }).first().click().catch(() => {});
    await p.waitForTimeout(1200);
    const slug = t.replace(/[^a-zåäö0-9]+/gi, "-").toLowerCase();
    await p.screenshot({ path: `${OUT}/flik-${slug}.png` });
    console.log(`== flik ${t}:`, (await p.locator("main").innerText()).replace(/\n+/g, " / ").slice(0, 1200));
  }
} finally {
  await browser.close();
}
