// Node-variant av scripts/shoot.py (python-playwright saknas i venv).
// node shoot.mjs <utkatalog> <url> [<url> ...]
import fs from "node:fs";
import { chromium } from "playwright";

const [outDir, ...urls] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const slug = (u) => u.replace(/^https?:\/\//, "").replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "") || "page";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
for (const url of urls) {
  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${outDir}/${slug(url)}--fold.png` });
  await page.screenshot({ path: `${outDir}/${slug(url)}--full.png`, fullPage: true });
  console.log(`${url} -> ${slug(url)} (fold+full)`);
}
// Mobilbredd för layoutkontrollen (en kolumn under xl).
await page.setViewportSize({ width: 390, height: 844 });
for (const url of urls) {
  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${outDir}/${slug(url)}--mobil.png`, fullPage: true });
  console.log(`${url} -> ${slug(url)}--mobil`);
}
await browser.close();
