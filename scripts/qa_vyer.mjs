/**
 * Besiktning av varje vy, i tre roller, i en riktig webbläsare.
 *
 *   node scripts/qa_vyer.mjs                        # mot http://localhost:3000
 *   BASE=https://web-development-6c85.up.railway.app node scripts/qa_vyer.mjs
 *
 * ## Varför en egen fil och inte ett testramverk
 *
 * Det här är en BESIKTNING, inte en svit. Den ställer en fråga sviten inte kan
 * ställa: renderar varje inloggad yta för rätt roll, och bara för rätt roll?
 * Svaret beror på databasrader (platform_admins), på RLS, och på en backend
 * som kan vara nere — alltså på drift, inte på kod. En grön svit sa
 * ingenting om att /admin svarade 404 för rätt person i tre veckor.
 *
 * ## Beroendet är AVSIKTLIGT odeklarerat
 *
 * `playwright` står inte i package.json. Railway och Vercel installerar
 * devDependencies under bygget, och en browser-runtime på ~50 MB i en image
 * som aldrig öppnar en webbläsare är ren kostnad. Installera lokalt när du
 * behöver den:
 *
 *   npm i --no-save playwright && npx playwright install chromium
 *
 * Redan installerad browser: sätt PW_CHROMIUM till binären.
 *
 * ## Vad "grönt" betyder
 *
 * Varje rad visar HTTP-status, vart man HAMNADE (inte vart man bad om — en
 * redirect är ofta hela svaret), sidans h1, och om något 4xx/5xx eller
 * JS-fel utlöstes under laddningen. Sista raden summerar.
 */
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3000";
// BILDER=<katalog> sparar en skärmdump per besiktad väg. Avstängt som default:
// 46 PNG per körning är brus när man bara vill se om raden är grön, och guld
// när någon ska granska ytan utan att köra den själv.
const BILDER = process.env.BILDER || null;
if (BILDER) fs.mkdirSync(BILDER, { recursive: true });
const EXEC = process.env.PW_CHROMIUM || undefined;
const PROXY = process.env.HTTPS_PROXY && !BASE.includes("localhost")
  ? { server: process.env.HTTPS_PROXY }
  : undefined;

const ADMIN = [process.env.QA_ADMIN_EPOST ?? "snajpsupport@gmail.com",
               process.env.QA_ADMIN_LOSEN ?? "Snajpen123!"];
const KUND = [process.env.QA_KUND_EPOST ?? "kund@example.com",
              process.env.QA_KUND_LOSEN ?? "Kundtest123!"];

const PUBLIKA = ["/", "/leads", "/support", "/login", "/duo-demo", "/auth/reset",
  "/demo", "/demo/leads", "/demo/emails", "/demo/support", "/demo/kontroll",
  "/demo/companies", "/demo/contacts", "/demo/inbox", "/demo/analytics", "/demo/assistant",
  "/chat/livrustning", "/chat/snajp",
  "/design-drafts/editorial-clean", "/design-drafts/editorial-clean/portal"];

const ARBETSYTA = ["/dashboard", "/dashboard/leads", "/dashboard/leads/kontroll",
  "/dashboard/emails", "/dashboard/support",
  "/settings", "/settings/team", "/settings/billing", "/settings/addons",
  "/settings/mailboxes", "/settings/soul"];

const ADMINYTA = ["/admin", "/admin/kunder", "/admin/korningar", "/admin/testkorningar",
  "/admin/handelser", "/admin/arbetsyta", "/admin/leads", "/admin/leads/kontroll",
  "/admin/emails", "/admin/support", "/admin/companies", "/admin/contacts",
  "/admin/inbox", "/admin/analytics", "/admin/assistant"];

/**
 * Fel som ÄR det önskade beteendet.
 *
 * `/api/snajp-support/*` kräver inloggning med flit — tenanten härleds ur
 * sessionen, och att ytan en gång var anonymt nåbar var Fas 1:s hela poäng
 * (se app/api/snajp-support/[...path]/route.ts). Demo-ytorna är anonyma och
 * anropar den ändå; svaret blir 401 och vyn faller tillbaka på mockdata. Det
 * är rätt, och en besiktning som flaggar det varje körning lär folk att
 * ignorera flaggan.
 */
const FORVANTADE_FEL = {
  "/demo": [/401 \/api\/snajp-support\//],
  "/duo-demo": [/401 \/api\/snajp-support\//]
};

let avvikelser = 0;

async function loggaIn(page, [epost, losen]) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  const lösenfält = page.getByPlaceholder("•".repeat(8));
  await lösenfält.waitFor({ state: "visible", timeout: 30000 });
  await page.getByPlaceholder("du@bolag.se").fill(epost);
  await lösenfält.fill(losen);
  // Klicket måste vänta på hydrering. Utan pausen träffar det en knapp som
  // ännu inte har någon onClick, och hela körningen rapporterar "inte inloggad".
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: /Logga in/ }).last().click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30000 }).catch(() => {});
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1200);
  return new URL(page.url()).pathname;
}

function bildnamn(rubrik, väg) {
  const rent = (s) => s.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase();
  return `${rent(rubrik)}__${rent(väg) || "rot"}.png`;
}

async function svep(page, rubrik, vagar, forvantat) {
  console.log(`\n=== ${rubrik} ===`);
  for (const väg of vagar) {
    const fel = [];
    const påLyssnare = (r) => {
      const u = r.url().replace(BASE, "");
      if (r.status() >= 400 && !u.includes("favicon")) fel.push(`${r.status()} ${u}`);
    };
    const påKrasch = (e) => fel.push(`js: ${e.message.slice(0, 90)}`);
    page.on("response", påLyssnare);
    page.on("pageerror", påKrasch);

    let status = "?";
    try {
      const r = await page.goto(BASE + väg, { waitUntil: "domcontentloaded", timeout: 45000 });
      status = r ? r.status() : "?";
    } catch (e) {
      status = "ERR";
      fel.push(e.message.split("\n")[0].slice(0, 70));
    }
    await page.waitForTimeout(600);

    const info = await page.evaluate(() => ({
      hamnade: location.pathname,
      h1: document.querySelector("h1")?.textContent?.trim().slice(0, 40) ?? "",
      saknas: /Sidan finns inte/.test(document.body.innerText)
    }));

    // En FÖRVÄNTAD 404 är inte en avvikelse — och sidans egen 404-respons ska
    // därför inte heller räknas som ett fel. Utan den här strykningen
    // rapporterade besiktningen 14 avvikelser för att grinden fungerade.
    const tillatna = FORVANTADE_FEL[väg] ?? [];
    const oväntadeFel = (forvantat === "404"
      ? fel.filter((f) => !f.startsWith(`404 ${väg}`))
      : fel
    ).filter((f) => !tillatna.some((m) => m.test(f)));
    const somFörväntat = forvantat === "404" ? info.saknas : !info.saknas && status === 200;
    if (!somFörväntat || oväntadeFel.length) avvikelser++;

    if (BILDER) {
      await page
        .screenshot({ path: `${BILDER}/${bildnamn(rubrik, väg)}`, fullPage: true })
        .catch(() => {});
    }

    page.off("response", påLyssnare);
    page.off("pageerror", påKrasch);

    console.log(
      `  ${somFörväntat && !oväntadeFel.length ? " " : "!"} ${String(status).padEnd(4)} ${väg.padEnd(34)}` +
      ` → ${info.hamnade.padEnd(30)} ${JSON.stringify(info.h1)}` +
      (oväntadeFel.length ? `  [${[...new Set(oväntadeFel)].join(" ; ")}]` : "")
    );
  }
}

const browser = await chromium.launch({ executablePath: EXEC, proxy: PROXY });

// 1. Anonym: publika ytor renderar, skyddade gör det inte.
{
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await svep(page, "ANONYM — publika ytor", PUBLIKA, "ok");
  await svep(page, "ANONYM — adminytan (ska vara 404)", ADMINYTA.slice(0, 5), "404");
  await page.context().close();
}

// 2. Kund: arbetsytan renderar, adminytan finns inte.
{
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  const landade = await loggaIn(page, KUND);
  console.log(`\nkund landar på: ${landade}`);
  if (landade === "/login") { console.log("  ! inloggningen misslyckades"); avvikelser++; }
  await svep(page, "KUND — arbetsytan", ARBETSYTA, "ok");
  await svep(page, "KUND — adminytan (ska vara 404)", ADMINYTA.slice(0, 6), "404");

  // INV-SEC-011. Vyväxeln Admin / Demo styrs av cookien `snajp.vy`, och en
  // cookie är något klienten skickar. Grinden är getPlatformAdmin(), alltså ett
  // uppslag i platform_admins — för en kund ska raden inte betyda något alls.
  // Mäts som EFFEKT och inte som frånvaron av en knapp: en manipulerad cookie
  // som gav demokontots data hade inte ändrat en enda sak i menyn.
  await page.context().addCookies([{ name: "snajp.vy", value: "demo", url: BASE }]);
  await page.goto(BASE + "/dashboard", { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(800);
  const efter = await page.evaluate(() => ({
    hamnade: location.pathname,
    text: document.body.innerText.slice(0, 600)
  }));
  console.log(`
KUND med snajp.vy=demo → ${efter.hamnade}`);
  if (/Nordlys Handel/.test(efter.text)) {
    console.log("  ! LÄCKA: kunden ser demokontot. INV-SEC-011 är bruten.");
    avvikelser++;
  } else if (efter.hamnade !== "/dashboard") {
    console.log(`  ! kunden hamnade på ${efter.hamnade} i stället för /dashboard`);
    avvikelser++;
  } else {
    console.log("  ok — cookien betyder ingenting för en kund");
  }

  await page.context().close();
}

// 3. Admin: adminytan renderar hela vägen, inklusive arbetsytans flikar.
{
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  const landade = await loggaIn(page, ADMIN);
  console.log(`\nadmin landar på: ${landade}${landade === "/admin" ? "" : "   ! förväntat /admin"}`);
  if (landade !== "/admin") avvikelser++;
  await svep(page, "ADMIN — adminytan", ADMINYTA, "ok");
  await page.context().close();
}

await browser.close();
console.log(`\n${avvikelser === 0 ? "GRÖNT — inga avvikelser." : `${avvikelser} avvikelser, se raderna märkta !`}`);
process.exit(avvikelser === 0 ? 0 : 1);
