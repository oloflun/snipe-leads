/**
 * Kundresan: registrering → onboarding → arbetsyta → kunskapsbas → supportagenten
 * → Iris → utloggning, som en riktig ny kund i webbläsaren.
 *
 *   npm i --no-save @playwright/test && npx playwright install chromium webkit
 *   BASE=http://localhost:3100 npx playwright test -c tests/e2e --project=chromium
 *   BASE=... npx playwright test -c tests/e2e --project=chromium --repeat-each=3
 *
 * Körd mot development 2026-11-24: tre gröna körningar i rad i Chromium, varav en
 * med KUNDRESA_LIVE=1. Lokalt går den inte att köra på en maskin utan pgvector
 * (se docs/startsidan-2026-11-23/RAPPORT.md). WebKit, telefon och surfplatta
 * finns som projekt men är inte körda.
 *
 * ## Vad som fäller testet
 *
 * Varje steg fälls av ett konsolfel, ett okänt JS-fel eller ett svar med 4xx
 * eller 5xx, oavsett om sidan "ser rätt ut". Undantagen står i TILLATNA nedan,
 * vart och ett med sitt skäl. En ny post där ska ha ett lika tydligt skäl.
 *
 * ## Inget mejl kan lämna huset
 *
 * `sparraUtskick` avbryter varje anrop till en sändväg (godkänn, skicka,
 * skicka-nu, skicka-jobb, provmejl) innan det når servern, och testet fäller
 * om ett sådant anrop ens försöktes. Testet klickar aldrig på en sändknapp;
 * spärren finns för att ett framtida steg inte ska kunna göra det av misstag.
 *
 * ## Vad som kräver en riktig modell
 *
 * Iris körning och supportagentens svar kostar modellanrop. De stegen körs bara
 * med KUNDRESA_LIVE=1. Utan den prövas allt fram till startknappen, och att en
 * miljö utan modell svarar med en begriplig mening i stället för en feltext.
 *
 * Varje körning skapar ETT nytt konto med egen adress (STAMP), så att körningar
 * efter varandra inte krockar. Kontona städas i development med
 * scripts/qa_radera_konto.py --epost <adressen> --radera.
 */
import { expect, test, type BrowserContext, type Page, type Response } from "@playwright/test";
import { kund } from "./testkund";

const LIVE = process.env.KUNDRESA_LIVE === "1";

// ---------------------------------------------------------------- felvakten

type Fynd = { sort: "konsol" | "sidfel" | "svar"; text: string };

/**
 * Svar som får vara 4xx utan att vara fel. Mönstret prövas mot "<status> <väg>".
 */
const TILLATNA: { monster: RegExp; skal: string }[] = [
  // Webbläsaren frågar själv efter en favicon som appen serverar som ikonfil.
  { monster: /^404 \/favicon\.ico/, skal: "webbläsarens egen förfrågan" },
  // Sidan för nästa steg förhämtas av Next; en avbruten förhämtning är inget fel.
  { monster: /^(401|403) \/api\/auth\/session/, skal: "sessionsfråga utan session, före inloggning" },
  // Identitetskontrollen (INV-SEC-014) efter en utloggning: 401:an är just det
  // som får en öppen flik att ladda om till inloggningen.
  { monster: /^401 \/api\/snajp-support\/identitet/, skal: "identitetskontrollen utan session" }
];

function vakta(page: Page): Fynd[] {
  const fynd: Fynd[] = [];
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const text = m.text();
    // Chromium loggar varje 4xx/5xx som ett konsolfel också; de räknas en gång, som svar.
    if (/Failed to load resource/.test(text)) return;
    fynd.push({ sort: "konsol", text: text.slice(0, 300) });
  });
  page.on("pageerror", (e) => fynd.push({ sort: "sidfel", text: String(e).slice(0, 300) }));
  page.on("response", (svar: Response) => {
    const status = svar.status();
    if (status < 400) return;
    const url = new URL(svar.url());
    const rad = `${status} ${url.pathname}`;
    if (TILLATNA.some((t) => t.monster.test(rad))) return;
    fynd.push({ sort: "svar", text: `${rad}${url.search ? " " + url.search.slice(0, 80) : ""}` });
  });
  return fynd;
}

function kravRent(fynd: Fynd[], steg: string) {
  expect(fynd, `${steg}: konsolfel eller felsvar\n${fynd.map((f) => `  ${f.sort}: ${f.text}`).join("\n")}`).toEqual([]);
}

/** Text som aldrig får synas för en kund, i någon vy. */
const FULTEXT = /\[object Object\]|\bundefined\b|\bNaN\b|Unhandled|Traceback|at \w+ \(.*:\d+:\d+\)|Internal Server Error|Application error/;

async function kravRenText(page: Page, steg: string) {
  const text = await page.locator("body").innerText();
  const traff = text.match(FULTEXT);
  expect(traff?.[0] ?? null, `${steg}: teknisk text i vyn nära "${traff ? text.slice(Math.max(0, traff.index! - 60), traff.index! + 80) : ""}"`).toBeNull();
}

/** Ett utkast får aldrig bära en ofylld platshållare eller modellens egna anteckningar. */
async function kravRenUtkast(text: string) {
  const traff = text.match(/\{\{.*?\}\}|\[(?:namn|företag|bolag|förnamn)\]|undefined|\bnull\b|Som AI|As an AI/i);
  expect(traff?.[0] ?? null, `utkastet bär en platshållare eller modellrest: ${traff?.[0]}`).toBeNull();
}

// ------------------------------------------------------------- utskicksspärren

const SANDVAGAR = /\/api\/snajp-support\/.*(\/approve|\/skicka|\/skicka-nu|\/skicka-jobb|\/provmejl|\/godkann)(\?|$)/;

async function sparraUtskick(context: BrowserContext): Promise<string[]> {
  const forsok: string[] = [];
  await context.route(SANDVAGAR, async (route) => {
    forsok.push(`${route.request().method()} ${new URL(route.request().url()).pathname}`);
    await route.abort("blockedbyclient");
  });
  return forsok;
}

// ------------------------------------------------------------------- resan

test.describe.configure({ mode: "serial" });

let context: BrowserContext;
let page: Page;
let fynd: Fynd[];
let sandforsok: string[];

test.beforeAll(async ({ browser }) => {
  context = await browser.newContext();
  sandforsok = await sparraUtskick(context);
  page = await context.newPage();
  fynd = vakta(page);
});

test.afterAll(async () => {
  await context?.close();
});

test.beforeEach(() => {
  fynd.length = 0;
});

test.afterEach(async ({}, info) => {
  kravRent(fynd, info.title);
  expect(sandforsok, "ett utskick försöktes under testet").toEqual([]);
});

test("publika sidor laddar utan fel", async () => {
  for (const vag of ["/", "/leads", "/support", "/faq", "/integritetspolicy", "/villkor", "/cookies", "/boka-demo", "/vart-team"]) {
    const svar = await page.goto(vag, { waitUntil: "load" });
    expect(svar?.status(), vag).toBe(200);
    await expect(page.locator("h1").first(), vag).toBeVisible();
    await kravRenText(page, vag);
  }
});

test("registreringen landar i onboardingen", async () => {
  await page.goto("/login?mode=signup", { waitUntil: "networkidle" });
  await page.locator('input[autocomplete="name"], input[name="name"]').first().fill(kund.kontakt);
  await page.getByPlaceholder("du@bolag.se").fill(kund.epost);
  await page.getByPlaceholder("•".repeat(8)).fill(kund.losen);
  await page.getByRole("button", { name: /Skapa konto/ }).last().click();
  await page.waitForURL((u) => u.pathname === "/onboarding", { timeout: 45_000 });
  await expect(page.getByLabel("Företagets namn")).toBeVisible();
});

test("onboardingen: tomma fält, ogiltigt orgnr, tillbaka och omladdning", async () => {
  // Tomt formulär: Fortsätt stannar på steget och säger vad som saknas.
  await page.getByRole("button", { name: /Fortsätt/ }).click();
  await expect(page.getByLabel("Företagets namn")).toBeVisible();

  // Ogiltigt organisationsnummer (fel kontrollsiffra) ger ett fältfel, inget kast.
  await page.getByLabel("Organisationsnummer").fill("556677-8890");
  await page.getByLabel("Företagets namn").click();
  await expect(page.getByText(/organisationsnum/i).first()).toBeVisible();

  // Omladdning mitt i flödet: sidan står kvar i onboardingen utan fel. Det som
  // fyllts i sparas inte förrän sista steget; det är känt och står i rapporten.
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByLabel("Företagets namn")).toBeVisible();
  await kravRenText(page, "onboarding efter omladdning");
});

test("onboardingen: sex steg till arbetsytan", async () => {
  await page.getByLabel("Företagets namn").fill(kund.foretag);
  await page.getByLabel("Webbplats").fill(kund.webbplats);
  await page.getByLabel("Organisationsnummer").fill(kund.orgnr);
  await page.getByLabel("Vad ni säljer").fill(kund.produkt);
  await page.getByLabel("Faktureringsadress").fill(kund.adress);
  await page.getByLabel("Postnummer").fill(kund.postnummer);
  await page.getByLabel("Ort").fill(kund.ort);
  await page.getByRole("button", { name: /Fortsätt/ }).click();

  // Steg 2, bransch. Tillbaka ska bära kvar det som fyllts i.
  await page.getByRole("radio", { name: kund.bransch }).click();
  await page.getByRole("button", { name: /Tillbaka/ }).click();
  await expect(page.getByLabel("Företagets namn")).toHaveValue(kund.foretag);
  await page.getByRole("button", { name: /Fortsätt/ }).click();
  await expect(page.getByRole("radio", { name: kund.bransch })).toBeChecked();
  await page.getByRole("button", { name: /Fortsätt/ }).click();

  // Steg 3, kontaktperson (förifylld ur kontot).
  const namn = page.getByLabel(/^Namn/);
  if (!(await namn.inputValue())) await namn.fill(kund.kontakt);
  const mejl = page.getByLabel(/^E-post/);
  if (!(await mejl.inputValue())) await mejl.fill(kund.epost);
  await page.getByRole("button", { name: /Fortsätt/ }).click();

  // Steg 4, målgruppen.
  if (kund.malgrupp.branscher) await page.getByLabel("Branscher att söka i").fill(kund.malgrupp.branscher);
  if (kund.malgrupp.orter) await page.getByLabel("Orter och områden").fill(kund.malgrupp.orter);
  await page.getByLabel("Särskilt fokus").fill(kund.malgrupp.fokus);
  await page.getByRole("button", { name: /Fortsätt/ }).click();

  // Steg 5, röst och ton (eget steg sedan 2026-11-23). Förifyllt med ett utkast;
  // kunden ska kunna gå vidare utan att ha skrivit något.
  await expect(page.getByLabel("Röst och tonläge")).not.toHaveValue("");
  await page.getByRole("button", { name: /Fortsätt/ }).click();

  // Steg 6, paketet. Duo är förvalt; villkoren startar okryssade. Notismejlen
  // slås av: kontot är ett testkonto och ska inte få påminnelser.
  const notis = page.locator('label:has-text("Ja, mejla mig") input[type="checkbox"]');
  if ((await notis.count()) && (await notis.isChecked())) await notis.uncheck();
  await page.locator('label:has-text("Jag godkänner") input[type="checkbox"]').check();

  // Dubbelklick: två klick i rad får inte ge två arbetsytor eller ett fel.
  const oppna = page.getByRole("button", { name: /Öppna arbetsytan/ });
  await oppna.dblclick();
  await page.waitForURL((u) => u.pathname === "/dashboard", { timeout: 90_000 });
  await expect(page.locator("main").first()).toBeVisible();
  await kravRenText(page, "översikten efter onboarding");
});

test("arbetsytan är kundens egen och bär det kunden skrev", async () => {
  const hamta = async (vag: string) => {
    const svar = await page.request.get(vag);
    return { status: svar.status(), kropp: (await svar.json().catch(() => null)) as Record<string, any> | null };
  };

  const docs = await hamta("/api/snajp-support/leads/context-docs?kind=product_marketing");
  expect(docs.status).toBe(200);
  const produkttext = ((docs.kropp?.docs ?? []) as { content?: string }[]).map((d) => d.content ?? "").join("\n");
  expect(produkttext).toContain(kund.produkt.slice(0, 40));

  // En ny kund ser inga andras leads, körningar, chattar eller kunskap.
  for (const [vag, nyckel] of [
    ["/api/snajp-support/leads/prospects?limit=5", "prospects"],
    ["/api/snajp-support/leads/korningar?limit=5", "korningar"],
    ["/api/snajp-support/kb", "articles"]
  ] as const) {
    const svar = await hamta(vag);
    expect(svar.status, vag).toBe(200);
    const rader = (svar.kropp?.[nyckel] ?? []) as unknown[];
    expect(rader.length, `${vag}: en nyskapad kund ska börja tom, fick ${rader.length} rader`).toBe(0);
  }
});

test("varje vy i arbetsytan öppnas utan fel", async () => {
  const vyer = [
    "/dashboard",
    "/dashboard/att-gora",
    "/dashboard/leads",
    "/dashboard/leads?vy=korningar",
    "/dashboard/leads?vy=konversationer",
    "/dashboard/leads?vy=uppfoljningar",
    "/dashboard/leads?vy=samtal",
    "/dashboard/leads?vy=erbjudanden",
    "/dashboard/support",
    "/settings",
    "/settings/affarskontext",
    "/settings/kunskapsbas",
    "/settings/soul",
    "/settings/leads",
    "/settings/regler",
    "/settings/mailboxes",
    "/settings/team",
    "/settings/billing",
    "/settings/addons",
    "/settings/notiser",
    "/settings/tema"
  ];
  for (const vag of vyer) {
    const svar = await page.goto(vag, { waitUntil: "networkidle" });
    expect(svar?.status(), vag).toBeLessThan(400);
    await expect(page.locator("main").first(), vag).toBeVisible();
    await expect(page.getByText(/Något gick fel/i), `${vag}: felgränsen visas`).toHaveCount(0);
    await kravRenText(page, vag);
  }
});

test("isolering: en annan kunds id ger 404 och adminytan skickar kunden hem", async ({ browser }) => {
  // Påhittade id:n i varje väg som tar ett: svaret ska vara 404, aldrig 200
  // och aldrig 500. Anropen går via en egen begäran så att de avsiktliga
  // 404:orna inte räknas som fel i sidan.
  const okant = "00000000-0000-4000-8000-000000000000";
  const api = page.context().request;
  for (const vag of [
    `/api/snajp-support/leads/prospects/${okant}`,
    `/api/snajp-support/leads/korningar/${okant}`,
    `/api/snajp-support/tickets/${okant}`,
    `/api/snajp-support/chattar/${okant}`
  ]) {
    const svar = await api.get(vag);
    expect([404, 422], `${vag} svarade ${svar.status()}`).toContain(svar.status());
  }
  const radera = await api.delete(`/api/snajp-support/kb/${okant}`);
  expect([404, 422], `DELETE kb svarade ${radera.status()}`).toContain(radera.status());

  // Utan session: varje inloggad API-väg svarar 401, aldrig med data.
  const anonym = await browser.newContext();
  for (const vag of ["/api/snajp-support/leads/prospects?limit=1", "/api/snajp-support/kb", "/api/snajp-support/chattar"]) {
    const svar = await anonym.request.get(vag);
    expect(svar.status(), `${vag} utan session`).toBe(401);
  }
  await anonym.close();

  // Adminytan för en kund: tillbaka till den egna arbetsytan, aldrig en
  // felsida (ändrat 2026-11-24 efter kunddemon; förut 404). Bakåtknappen efter
  // ett kontobyte landar annars på "Sidan finns inte".
  const admin = await api.get("/admin", { maxRedirects: 0 });
  expect([303, 307, 308], `/admin svarade ${admin.status()}`).toContain(admin.status());
  expect(new URL(admin.headers()["location"] ?? "", "http://x").pathname).toBe("/dashboard");
  await page.goto("/admin/arbetsyta", { waitUntil: "networkidle" });
  expect(new URL(page.url()).pathname).toBe("/dashboard");
  await expect(page.getByText("Sidan finns inte")).toHaveCount(0);
});

test("kunskapsbasen: spara, och för lång text ger en begriplig mening", async () => {
  await page.goto("/settings/kunskapsbas", { waitUntil: "networkidle" });
  await page.getByPlaceholder(/Rubrik/).fill(kund.kunskap.rubrik);
  await page.getByPlaceholder("Texten agenterna ska svara ur").fill(kund.kunskap.text);
  await page.getByRole("button", { name: "Spara i kunskapsbasen" }).click();
  await expect(page.getByText("Sparat.")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(kund.kunskap.rubrik).first()).toBeVisible();

  // Över 8000 tecken fäller backendens validering. Kunden ska få en mening,
  // aldrig "[object Object]". Det avsiktliga 422-svaret räknas inte som fel.
  await page.getByPlaceholder(/Rubrik/).fill("För lång text");
  await page.getByPlaceholder("Texten agenterna ska svara ur").fill("a ".repeat(4100));
  // Svaret väntas in uttryckligen: en feltext som redan står på sidan får inte
  // se ut som utfallet av det här klicket.
  const avvisat = page.waitForResponse(
    (r) => new URL(r.url()).pathname === "/api/snajp-support/kb" && r.request().method() === "POST"
  );
  await page.getByRole("button", { name: "Spara i kunskapsbasen" }).click();
  expect((await avvisat).status()).toBe(422);
  await expect(page.getByText(/Uppgifterna gick inte att läsa|Texten gick inte att spara/).first()).toBeVisible();
  await kravRenText(page, "kunskapsbasen, för lång text");
  const ovantade = fynd.filter((f) => !(f.sort === "svar" && /^422 \/api\/snajp-support\/kb/.test(f.text)));
  fynd.length = 0;
  fynd.push(...ovantade);
});

test("supportagenten: testchatten öppnas och tar emot en fråga", async () => {
  await page.goto("/dashboard/support", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Testchatt" }).click();
  const ruta = page.getByPlaceholder("Skriv här…");
  await expect(ruta).toBeVisible();

  // Tomt meddelande går inte att skicka.
  await expect(page.getByRole("button", { name: "Skicka" })).toBeDisabled();

  test.skip(!LIVE, "svaret kräver en riktig modell (KUNDRESA_LIVE=1)");

  await ruta.fill("Hur kommer jag i kontakt med er?");
  await page.getByRole("button", { name: "Skicka" }).click();
  const svar = page.locator('[data-chatt-roll="agent"]').last();
  await expect(svar).toBeVisible({ timeout: 180_000 });
  await expect(page.locator('[data-chatt-roll="system"]'), "chatten visade ett fel").toHaveCount(0);
  const text = (await svar.innerText()).trim();
  expect(text.length).toBeGreaterThan(20);
  // Svaret skrivs ut: att en bubbla dök upp säger inte att svaret är rimligt.
  console.log(`    supportagentens svar: ${text.replace(/\s+/g, " ").slice(0, 400)}`);
});

test("Iris: körformuläret öppnas, och en körning ger leads med utkast", async () => {
  await page.goto("/dashboard/leads", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Kör Iris" }).click();
  const antal = page.getByLabel("Antal leads");
  await expect(antal).toBeVisible();
  await antal.fill("1");
  const starta = page.getByRole("button", { name: /Starta körning/ });
  await expect(starta).toBeEnabled();

  test.skip(!LIVE, "körningen kräver en riktig modell och kostar pengar (KUNDRESA_LIVE=1)");
  // Motorn fortsätter tills ett leverbart lead finns, högst tolv undersökta bolag.
  test.setTimeout(20 * 60_000);

  await starta.click();
  // Förloppet ska synas där körningen startades, aldrig en frusen skärm.
  await expect(page.getByText(/Letar bolag|Startar körningen|leads klara|bolag undersökta/).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/1 av 1 leads/).first()).toBeVisible({ timeout: 15 * 60_000 });

  // Raden i vyn räcker inte som bevis. Körningen och leadet läses ur API:t:
  // ett levererat lead är ett bolag med kontaktadress, lägesbild och ett utkast i kön.
  const korningar = await page.request.get("/api/snajp-support/leads/korningar?limit=5");
  expect(korningar.status()).toBe(200);
  const senaste = ((await korningar.json()).korningar ?? [])[0];
  expect(senaste, "körningen syns inte i listan").toBeTruthy();
  // `error` är en tom sträng på en körning som gick bra, inte null.
  expect(String(senaste.error ?? ""), "körningen bär ett fel").toBe("");
  expect(senaste.korning?.levererade ?? 0, "inget lead levererades").toBeGreaterThanOrEqual(1);
  const prospekt = await page.request.get("/api/snajp-support/leads/prospects?limit=5");
  const rader = ((await prospekt.json()).prospects ?? []) as Record<string, any>[];
  expect(rader.length, "körningen gav inget bolag i listan").toBeGreaterThanOrEqual(1);
  const lead = rader[0];
  expect(String(lead.company_name ?? "").trim(), "leadet saknar bolagsnamn").not.toBe("");
  expect(String(lead.motivering ?? lead.lagesbeskrivning ?? "").trim(), "leadet saknar motivering").not.toBe("");
  console.log(
    `    körningen: ${senaste.korning.levererade} av ${senaste.korning.mal} leads, ${senaste.korning.undersokta} bolag undersökta, status ${senaste.status}`
  );
  // Utkastet: ämnesrad och en brödtext som är ett mejl och inte en mall på en rad.
  const utkastsvar = await page.request.get(`/api/snajp-support/leads/prospects/${lead.id}/utkast`);
  expect(utkastsvar.status()).toBe(200);
  const utkast = (await utkastsvar.json()).utkast as { subject?: string; brodtext?: string; body?: string } | null;
  expect(utkast, "leadet har inget utkast").toBeTruthy();
  expect(String(utkast!.subject ?? "").trim(), "utkastet saknar ämnesrad").not.toBe("");
  const brodtext = String(utkast!.brodtext ?? utkast!.body ?? "").trim();
  expect(brodtext.length, "utkastets brödtext är för kort för att vara ett mejl").toBeGreaterThan(120);
  await kravRenUtkast(brodtext);
  console.log(`    utkastet: "${utkast!.subject}" · ${brodtext.replace(/\s+/g, " ").slice(0, 420)}`);
  console.log(`    leadet: ${lead.company_name} · ${String(lead.motivering ?? "").replace(/\s+/g, " ").slice(0, 220)}`);

  // Förloppet överlever en omladdning.
  await page.goto("/dashboard/leads?vy=korningar", { waitUntil: "networkidle" });
  await kravRenText(page, "körningarna efter en körning");
});

async function loggaUt(flik: Page) {
  const knapp = flik.getByRole("button", { name: "Logga ut" }).first();
  if (!(await knapp.isVisible().catch(() => false))) {
    // Smala skärmar har utloggningen i kontomenyn.
    await flik.getByRole("button", { name: /Konto|Meny|Menu/ }).first().click();
  }
  await flik.getByRole("button", { name: "Logga ut" }).first().click();
  await flik.waitForURL((u) => u.pathname === "/login", { timeout: 30_000 });
}

async function loggaIn(flik: Page, epost: string, losen: string) {
  await flik.getByPlaceholder("du@bolag.se").fill(epost);
  await flik.getByPlaceholder("•".repeat(8)).fill(losen);
  await flik.getByRole("button", { name: /Logga in/ }).last().click();
}

test("sessionen: utloggning, skyddad sida utan session, inloggning igen", async () => {
  await page.goto("/dashboard/leads", { waitUntil: "networkidle" });
  await page.goto("/dashboard", { waitUntil: "networkidle" });
  await loggaUt(page);

  // Bakåt efter utloggningen: inloggningen, aldrig en felsida (kunddemon
  // 2026-11-24). Utloggningen ersatte /dashboard i historiken, så bakåt går
  // till /dashboard/leads, som utan session ska leda till /login.
  await page.goBack({ waitUntil: "networkidle" });
  expect(new URL(page.url()).pathname).toBe("/login");
  await expect(page.getByText("Sidan finns inte")).toHaveCount(0);

  // En skyddad sida utan session leder till en vänlig inloggning, inte till ett fel.
  await page.goto("/dashboard/leads", { waitUntil: "networkidle" });
  expect(new URL(page.url()).pathname).toBe("/login");
  await kravRenText(page, "inloggningen efter utgången session");

  // Adminytan utan session: samma inloggning, med vägen tillbaka i next.
  await page.goto("/admin/arbetsyta?vy=korningar", { waitUntil: "networkidle" });
  const inloggning = new URL(page.url());
  expect(inloggning.pathname).toBe("/login");
  expect(inloggning.searchParams.get("next")).toBe("/admin/arbetsyta?vy=korningar");
  await expect(page.getByText("Sidan finns inte")).toHaveCount(0);
  await page.goto("/admin", { waitUntil: "networkidle" });
  expect(new URL(page.url()).pathname).toBe("/login");

  // En kund som loggar in med next under /admin landar i sin arbetsyta.
  await page.goto("/login?next=/admin/arbetsyta", { waitUntil: "networkidle" });
  await loggaIn(page, kund.epost, kund.losen);
  await page.waitForURL((u) => u.pathname.startsWith("/dashboard"), { timeout: 45_000 });
  await expect(page.getByText("Sidan finns inte")).toHaveCount(0);
  await loggaUt(page);

  // ?next= får aldrig leda bort från sajten (öppen omdirigering).
  await page.goto("/login?next=https://example.org/", { waitUntil: "networkidle" });
  await loggaIn(page, kund.epost, kund.losen);
  await page.waitForURL((u) => u.pathname.startsWith("/dashboard"), { timeout: 45_000 });
  expect(new URL(page.url()).host).toBe(new URL(test.info().project.use.baseURL!).host);

  // Två flikar på samma session: båda ser arbetsytan.
  const andra = await context.newPage();
  const svar = await andra.goto("/dashboard", { waitUntil: "networkidle" });
  expect(svar?.status()).toBeLessThan(400);
  await andra.close();
});

/**
 * Tvåfliksfallet från kunddemon 2026-11-24 (INV-SEC-014). Flik A visar kundens
 * arbetsyta. Sedan blir plattformsadminens session den aktiva i webbläsaren,
 * utan att flik A säger något. Nästa mjuka navigering i A ska ladda om sidan,
 * så att skalet och raderna tillhör samma identitet: aldrig kundens skal över
 * adminens data.
 *
 * Bytet görs med cookies, inte med en inloggning i flik B: då prövas
 * jämförelsen i A och inte BroadcastChannel, som en inloggning i B också hade
 * väckt. Adminens session hämtas ur ett eget kontext. Kanalvägen prövas i
 * nästa test. Kräver ett syntetiskt adminkonto i lokal_stack (QA_ADMIN_EPOST,
 * QA_ADMIN_LOSEN); utan båda hoppas testet över. Pekas aldrig mot
 * development-spegeln.
 */
const adminEpost = process.env.QA_ADMIN_EPOST;
const adminLosen = process.env.QA_ADMIN_LOSEN;
const UTAN_ADMIN = "kräver ett syntetiskt adminkonto i lokal_stack (QA_ADMIN_EPOST och QA_ADMIN_LOSEN)";

test("identitetsbyte i en annan flik: mjuk navigering laddar om den gamla fliken", async ({ browser }) => {
  test.skip(!adminEpost || !adminLosen, UTAN_ADMIN);

  // Flik A: kunden.
  await page.goto("/dashboard", { waitUntil: "networkidle" });
  await expect(page.getByText(kund.foretag).first()).toBeVisible();

  // Adminens session i ett eget kontext, sedan in i webbläsarens cookies.
  const adminKontext = await browser.newContext();
  const adminFlik = await adminKontext.newPage();
  await adminFlik.goto("/login", { waitUntil: "networkidle" });
  await loggaIn(adminFlik, adminEpost!, adminLosen!);
  await adminFlik.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 45_000 });
  const adminKakor = await adminKontext.cookies();
  await adminKontext.close();
  await context.clearCookies();
  await context.addCookies(adminKakor);

  // Mjuk navigering i A: ett klick i menyn, ingen page.goto.
  const laddning = page.waitForEvent("load", { timeout: 30_000 });
  await page.getByRole("link", { name: /Leads/ }).first().click();
  await laddning;
  await page.waitForLoadState("networkidle");

  // Efter omladdningen hör hela sidan till adminen: layouten skickar den till
  // /admin, och kundens namn står varken i skalet eller i raderna.
  expect(new URL(page.url()).pathname.startsWith("/admin")).toBe(true);
  await expect(page.getByText(kund.foretag)).toHaveCount(0);
  await kravRenText(page, "flik A efter identitetsbytet");
});

/**
 * Samma fall som demon, med kanalen: admin loggar in i flik B i SAMMA kontext.
 * Inloggningen postar på BroadcastChannel("snajp-identitet"), och flik A ska
 * ladda om utan att själv navigera.
 */
test("identitetsbyte via inloggning i flik B: flik A laddar om utan egen navigering", async () => {
  test.skip(!adminEpost || !adminLosen, UTAN_ADMIN);

  // Flik A: kunden igen (förra testet lämnade adminens session i kontextet).
  await context.clearCookies();
  await page.goto("/login", { waitUntil: "networkidle" });
  await loggaIn(page, kund.epost, kund.losen);
  await page.waitForURL((u) => u.pathname.startsWith("/dashboard"), { timeout: 45_000 });
  await page.waitForLoadState("networkidle");
  await expect(page.getByText(kund.foretag).first()).toBeVisible();

  // Flik B: kundens cookie bort i tysthet, sedan adminens inloggning. Flik A
  // får ingen händelse av cookiebytet, bara av meddelandet på kanalen.
  const flikB = await context.newPage();
  await context.clearCookies();
  await flikB.goto("/login", { waitUntil: "networkidle" });
  const laddning = page.waitForEvent("load", { timeout: 30_000 });
  await loggaIn(flikB, adminEpost!, adminLosen!);
  await flikB.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 45_000 });
  await laddning;
  await page.waitForLoadState("networkidle");

  expect(new URL(page.url()).pathname.startsWith("/admin")).toBe(true);
  await expect(page.getByText(kund.foretag)).toHaveCount(0);
  await kravRenText(page, "flik A efter inloggningen i flik B");
  await flikB.close();
});
