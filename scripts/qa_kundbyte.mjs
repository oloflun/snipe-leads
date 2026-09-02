/**
 * Besiktning av kundbytet: går varje kund i växeln FAKTISKT att öppna?
 *
 *   BASE=https://web-development-6c85.up.railway.app node scripts/qa_kundbyte.mjs
 *
 * ## Varför den här filen finns
 *
 * Felrapporten 2026-09-02 var tre symptom med en gemensam orsak: efter "Byt
 * kund" visade översikten streck i stället för siffror, `/settings/soul` sa
 * "Kunde inte hämta röstdokumentet", och `/settings/leads` renderade
 * "Ingen backend-nyckel för nordlys-handel". Alla tre var samma 409 ur
 * `requireSnajpTenant()`, och alla tre syns bara för en INLOGGAD
 * plattformsadmin som redan bytt kund — alltså inte i någon svit.
 *
 * `qa_vyer.mjs` besiktigar vyer per roll. Den här ställer den andra frågan:
 * för VARJE kund i växeln, svarar de tre endpoints som bär de tre symptomen?
 * Det är skillnaden mellan "det funkar för Nordlys" och "det funkar för varje
 * bolag", vilket var vad som beställdes.
 *
 * Beroendet på playwright är odeklarerat av samma skäl som i qa_vyer.mjs:
 *
 *   npm i --no-save playwright && npx playwright install chromium
 */
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3000";
const EXEC = process.env.PW_CHROMIUM || undefined;
const ADMIN = [
  process.env.QA_ADMIN_EPOST ?? "snajpsupport@gmail.com",
  process.env.QA_ADMIN_LOSEN ?? "Snajpen123!"
];

/**
 * De tre anropen som bär de tre symptomen. Sökvägarna går genom proxyn, alltså
 * genom `requireSnajpTenant()` — det är den grinden som mäts, inte backenden.
 */
const YTOR = [
  ["röstdokument", "/api/snajp-support/leads/soul"],
  ["målgrupp", "/api/snajp-support/leads/config"],
  ["översikt", "/api/snajp-support/leads/prospects?limit=1"]
];

async function loggaIn(sida) {
  await sida.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await sida.fill('input[type="email"]', ADMIN[0]);
  await sida.fill('input[type="password"]', ADMIN[1]);
  await Promise.all([
    sida.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 45_000 }),
    sida.click('button[type="submit"]')
  ]);
}

/** Sätter vy-cookien genom samma server action som knappen använder. */
async function bytTill(sida, slug) {
  await sida.goto(`${BASE}/admin`, { waitUntil: "domcontentloaded" });
  await sida.evaluate(async (varde) => {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = window.location.pathname;
    const falt = document.createElement("input");
    falt.name = "vy";
    falt.value = varde;
    form.appendChild(falt);
    document.body.appendChild(form);
    form.submit();
  }, `kund:${slug}`);
  await sida.waitForLoadState("domcontentloaded");
}

const sidaSvar = async (sida, vag) => {
  const svar = await sida.request.get(`${BASE}${vag}`);
  let text = "";
  try {
    const kropp = await svar.json();
    text = kropp?.error ?? "";
  } catch {
    text = "(ingen JSON-kropp)";
  }
  return { status: svar.status(), text };
};

const browser = await chromium.launch({ executablePath: EXEC });
const sida = await browser.newPage();
let fel = 0;

try {
  await loggaIn(sida);

  const lista = await sida.request.get(`${BASE}/api/admin/kunder`);
  if (!lista.ok()) {
    console.error(`/api/admin/kunder svarade ${lista.status()} — går inte att besikta.`);
    process.exit(1);
  }
  const { tenants = [] } = await lista.json();
  console.log(`${tenants.length} kunder i växeln.\n`);

  for (const kund of tenants) {
    await bytTill(sida, kund.slug);
    const rader = [];
    for (const [namn, vag] of YTOR) {
      const { status, text } = await sidaSvar(sida, vag);
      // 200 är rätt. 503 är backenden som sover — inte det fel som mäts här.
      const ok = status === 200 || status === 503;
      if (!ok) fel += 1;
      rader.push(`${ok ? "ok" : "FEL"} ${namn} ${status}${ok ? "" : ` — ${text}`}`);
    }
    console.log(`${kund.name} (${kund.slug})`);
    for (const rad of rader) console.log(`   ${rad}`);
  }
} finally {
  await browser.close();
}

console.log(fel === 0 ? "\nAlla kunder gick att öppna." : `\n${fel} anrop föll.`);
process.exit(fel === 0 ? 0 : 1);
