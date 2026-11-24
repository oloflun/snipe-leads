/**
 * Playwright för kundresan (tests/e2e/kundresa.spec.ts).
 *
 *   npm i --no-save @playwright/test && npx playwright install chromium webkit
 *   BASE=http://localhost:3100 npx playwright test -c tests/e2e
 *   BASE=... npx playwright test -c tests/e2e --project=chromium --repeat-each=3
 *
 * Playwright är med flit inget beroende i package.json (samma val som
 * scripts/qa_*.mjs): det är ett besiktningsverktyg, inte en del av bygget.
 *
 * BASE ska peka på ett PRODUKTIONSBYGGE (`npm run build && npx next start`)
 * mot en egen databas. Peka den aldrig mot produktionen: testet skapar konton.
 */
import { defineConfig, devices } from "@playwright/test";

const BASE = process.env.BASE ?? "http://localhost:3100";

if (/snajp\.se|web-main|-main\./i.test(BASE) && process.env.TILLAT_PRODUKTION !== "ja-jag-vet") {
  throw new Error(
    `BASE=${BASE} ser ut som produktionen. Kundresan skapar konton och kör agenter och ska inte köras där.`
  );
}

export default defineConfig({
  testDir: ".",
  testMatch: /.*\.spec\.ts$/,
  // Resan är ett flöde: ett konto, steg för steg, i ordning.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 4 * 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "../../.playwright-rapport" }]],
  outputDir: "../../.playwright-utfall",
  use: {
    baseURL: BASE,
    locale: "sv-SE",
    timezoneId: "Europe/Stockholm",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off"
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "webkit", use: { ...devices["Desktop Safari"], viewport: { width: 1440, height: 900 } } },
    { name: "mobil", use: { ...devices["iPhone 14"] } },
    { name: "surfplatta", use: { ...devices["iPad (gen 7)"] } }
  ]
});
