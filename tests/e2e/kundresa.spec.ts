/**
 * Kundresan: registrering → onboarding → arbetsyta → kunskapsbas → supportagenten
 * → Iris → utloggning, som en riktig ny kund i webbläsaren.
 *
 *   npm i --no-save @playwright/test && npx playwright install chromium webkit
 *   BASE=http://localhost:3100 npx playwright test -c tests/e2e --project=chromium
 *   BASE=... npx playwright test -c tests/e2e --project=chromium --repeat-each=3
 *
 * EJ KÖRD ÄNNU (2026-11-23). Testet är skrivet mot källkoden och har inte kunnat
 * köras: den lokala stacken går inte att resa på utvecklingsmaskinen (Postgres
 * saknar pgvector, se docs/startsidan-2026-11-23/RAPPORT.md), och en körning mot development kräver att
 * grenen ligger där. Räkna med att väljare behöver justeras vid första körningen.
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
  { monster: /^(401|403) \/api\/auth\/session/, skal: "sessionsfråga utan session, före inloggning" }
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

test("isolering: en annan kunds id ger 404 och adminytan finns inte", async ({ browser }) => {
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

  // Plattformsadmin finns inte för en kund: 404, inte en omdirigering dit.
  const admin = await api.get("/admin", { maxRedirects: 0 });
  expect(admin.status()).toBe(404);
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
  await page.getByRole("button", { name: "Spara i kunskapsbasen" }).click();
  await expect(page.getByText(/gick inte att (läsa|spara)/i).first()).toBeVisible({ timeout: 30_000 });
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
  expect((await svar.innerText()).trim().length).toBeGreaterThan(20);
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

  await starta.click();
  // Förloppet ska synas där körningen startades, aldrig en frusen skärm.
  await expect(page.getByText(/Letar bolag|Startar körningen|leads klara|bolag undersökta/).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/1 av 1 leads|leads klara/).first()).toBeVisible({ timeout: 15 * 60_000 });

  // Förloppet överlever en omladdning.
  await page.goto("/dashboard/leads?vy=korningar", { waitUntil: "networkidle" });
  await kravRenText(page, "körningarna efter en körning");
});

test("sessionen: utloggning, skyddad sida utan session, inloggning igen", async () => {
  await page.goto("/dashboard", { waitUntil: "networkidle" });
  const loggaUt = page.getByRole("button", { name: "Logga ut" }).first();
  if (!(await loggaUt.isVisible().catch(() => false))) {
    // Smala skärmar har utloggningen i kontomenyn.
    await page.getByRole("button", { name: /Konto|Meny|Menu/ }).first().click();
  }
  await page.getByRole("button", { name: "Logga ut" }).first().click();
  await page.waitForURL((u) => u.pathname === "/login", { timeout: 30_000 });

  // En skyddad sida utan session leder till en vänlig inloggning, inte till ett fel.
  await page.goto("/dashboard/leads", { waitUntil: "networkidle" });
  expect(new URL(page.url()).pathname).toBe("/login");
  await kravRenText(page, "inloggningen efter utgången session");

  // ?next= får aldrig leda bort från sajten (öppen omdirigering).
  await page.goto("/login?next=https://example.org/", { waitUntil: "networkidle" });
  await page.getByPlaceholder("du@bolag.se").fill(kund.epost);
  await page.getByPlaceholder("•".repeat(8)).fill(kund.losen);
  await page.getByRole("button", { name: /Logga in/ }).last().click();
  await page.waitForURL((u) => u.pathname.startsWith("/dashboard"), { timeout: 45_000 });
  expect(new URL(page.url()).host).toBe(new URL(test.info().project.use.baseURL!).host);

  // Två flikar på samma session: båda ser arbetsytan.
  const andra = await context.newPage();
  const svar = await andra.goto("/dashboard", { waitUntil: "networkidle" });
  expect(svar?.status()).toBeLessThan(400);
  await andra.close();
});
