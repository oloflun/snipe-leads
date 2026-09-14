/**
 * En RIKTIG kund registrerar sig och kan använda produkten direkt.
 *
 *   BASE=https://web-development-6c85.up.railway.app node scripts/qa_ny_kund.mjs
 *
 * ## Vad den mäter som qa_testkund.mjs inte gör
 *
 * `qa_testkund.mjs` kryssar i "Testarbetsyta", och den vägen har haft en egen
 * tenant sedan migration 040. Den som INTE kryssar i rutan — alltså varje
 * riktig kund — fick tidigare `workspaces.slug = null` och möttes av 409 på
 * varje inloggad yta tills någon av oss körde `scripts/onboard_tenant.py` för
 * hand. Det felet syns bara för ett konto som är NYSKAPAT och inte är en
 * testarbetsyta, alltså i exakt det fall inget skript besiktigade.
 *
 * Tre påståenden, i tur och ordning:
 *
 *  1. Kontot går att skapa och onboardingen landar på /dashboard.
 *  2. De tre ytorna ur felrapporten svarar 200 för kundens EGEN session —
 *     röstdokument, målgrupp och översiktens prospektlista.
 *  3. Standardinställningarna är ifyllda ur det kunden skrev: en
 *     produktbeskrivning agenten faktiskt läser, ett röstdokument att ändra i,
 *     och ett ICP med storleksspann. Det är hela skillnaden mot att kunden ska
 *     konfigurera allt själv.
 *
 * Skapar ett konto i den miljö BASE pekar på. Kör den mot development, aldrig
 * mot main.
 *
 *   npm i --no-save playwright && npx playwright install chromium
 */
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3000";
const EXEC = process.env.PW_CHROMIUM || undefined;
const STAMP = process.env.STAMP ?? String(Date.now()).slice(-8);
const EPOST = process.env.QA_NY_EPOST ?? `nykund+${STAMP}@snajp.se`;
const LOSEN = process.env.QA_NY_LOSEN ?? "Nykund123!";

/**
 * Luhn-giltigt organisationsnummer. Kontrollsiffran är UTRÄKNAD — ett påhittat
 * nummer faller i fältvalideringen och mäter då Luhn, inte registreringen.
 */
const ORGNR = process.env.QA_NY_ORGNR ?? "556677-8899";

const PRODUKT =
  "Vi säljer besiktning och service av lyftanordningar till industri och bygg, " +
  "med jour dygnet runt och egna certifierade tekniker.";

let fel = 0;
const rad = (ok, text) => {
  if (!ok) fel += 1;
  console.log(`  ${ok ? " " : "!"} ${text}`);
};

const browser = await chromium.launch({ executablePath: EXEC });
const sida = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();

try {
  // --- 1. Registrering utan testarbetsyta --------------------------------
  console.log(`\n=== Ny kund (${EPOST}) ===`);
  await sida.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await sida.getByRole("button", { name: "Skapa konto" }).first().click();
  await sida.waitForTimeout(800);
  await sida.getByPlaceholder("du@bolag.se").fill(EPOST);
  await sida.getByPlaceholder("•".repeat(8)).fill(LOSEN);
  const namnfalt = sida.locator('input[name="name"], input[autocomplete="name"]').first();
  if (await namnfalt.count()) await namnfalt.fill(`Nykund ${STAMP}`);
  // Pausen är hydreringen, inte försiktighet — se qa_vyer.mjs.
  await sida.waitForTimeout(1200);
  await sida.getByRole("button", { name: /Skapa konto/ }).last().click();
  await sida.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 45_000 }).catch(() => {});
  await sida.waitForLoadState("networkidle").catch(() => {});
  await sida.waitForTimeout(1500);

  rad(new URL(sida.url()).pathname === "/onboarding", `registreringen landar på ${new URL(sida.url()).pathname}`);

  // Rutan lämnas OKRYSSAD med flit. Det är hela skillnaden mot qa_testkund.mjs.
  const ruta = sida.locator('input[type="checkbox"]').first();
  rad(!(await ruta.isChecked()), "testarbetsytan är INTE ikryssad — det här är en riktig kund");

  await sida.getByLabel("Organisationsnummer").fill(ORGNR);
  for (const [etikett, varde] of [
    ["Webbplats", `https://nykund-${STAMP}.example.se`],
    ["Vad ni säljer", PRODUKT],
    ["Något extra att fokusera på (valfritt)", "Helst bolag med egen produktion."]
  ]) {
    await sida.getByLabel(etikett).fill(varde);
  }
  await sida.waitForTimeout(400);
  await sida.getByRole("button", { name: /Spara och läs in/ }).click();
  await sida.waitForURL((u) => !u.pathname.startsWith("/onboarding"), { timeout: 60_000 }).catch(() => {});
  await sida.waitForLoadState("networkidle").catch(() => {});
  await sida.waitForTimeout(2500);

  rad(new URL(sida.url()).pathname === "/dashboard", `onboardingen landar på ${new URL(sida.url()).pathname}`);

  // --- 2. De tre ytorna ur felrapporten ----------------------------------
  console.log("\n=== Ytorna som föll ===");
  const hamta = async (vag) => {
    const svar = await sida.request.get(`${BASE}${vag}`);
    let kropp = null;
    try {
      kropp = await svar.json();
    } catch {
      /* icke-JSON hanteras av anroparen */
    }
    return { status: svar.status(), kropp };
  };

  const soul = await hamta("/api/snajp-support/leads/soul");
  rad(soul.status === 200, `röstdokument  ${soul.status}${soul.status === 200 ? "" : ` — ${soul.kropp?.error}`}`);

  const config = await hamta("/api/snajp-support/leads/config");
  rad(config.status === 200, `målgrupp      ${config.status}${config.status === 200 ? "" : ` — ${config.kropp?.error}`}`);

  const prospekt = await hamta("/api/snajp-support/leads/prospects?limit=1");
  rad(prospekt.status === 200, `översikt      ${prospekt.status}${prospekt.status === 200 ? "" : ` — ${prospekt.kropp?.error}`}`);

  // --- 3. Standardinställningarna ur kundens eget underlag ---------------
  console.log("\n=== Standardinställningar ===");
  const docs = await hamta("/api/snajp-support/leads/context-docs?kind=product_marketing");
  const produkttext = (docs.kropp?.docs ?? []).map((d) => d.content ?? "").join("\n");
  rad(
    produkttext.includes("lyftanordningar"),
    "produktbeskrivningen bär kundens egen text (det agenten faktiskt läser)"
  );
  // require_business_context avvisar under 120 tecken som "för tunt".
  rad(produkttext.trim().length >= 120, `produktbeskrivningen är ${produkttext.trim().length} tecken (minst 120 krävs)`);

  rad(Boolean((soul.kropp?.content ?? "").trim()), "röstdokumentet har ett utkast att ändra i");

  const icp = config.kropp?.icp ?? {};
  rad((icp.roles ?? []).length > 0, `beslutsfattarroller ifyllda: ${(icp.roles ?? []).join(", ") || "—"}`);
  rad(
    icp.company_size?.min != null && icp.company_size?.max != null,
    `storleksspann satt: ${icp.company_size?.min ?? "—"}–${icp.company_size?.max ?? "—"} anställda`
  );
  rad(
    (icp.industries ?? []).length === 0 && (icp.geography ?? []).length === 0,
    "bransch och geografi lämnas tomma — ett gissat filter smalnar av urvalet"
  );
} finally {
  await browser.close();
}

console.log(fel === 0 ? "\nAllt grönt." : `\n${fel} påståenden föll.`);
process.exit(fel === 0 ? 0 : 1);
