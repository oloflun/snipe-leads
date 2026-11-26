import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { HttpJsonError, readJson, sattInloggningsnavigering } from "./json.ts";

const g = globalThis as Record<string, unknown>;

/** Next-sidans eget 401 när sessionen saknas (svarForTenantfel, ejInloggadSvar). */
const UTLOGGAD = { error: "Du måste vara inloggad.", kod: "ej_inloggad" };

function iWebblasaren(pathname: string, search = "", lang = "sv"): void {
  g.window = { location: { pathname, search } };
  g.document = { documentElement: { lang } };
}

function svar(status: number, kropp: unknown = { error: "nekad" }): Response {
  return new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } });
}

async function kastar(response: Response): Promise<HttpJsonError> {
  try {
    await readJson(response);
  } catch (fel) {
    assert.ok(fel instanceof HttpJsonError);
    return fel;
  }
  assert.fail("readJson kastade inte");
}

afterEach(() => {
  delete g.window;
  delete g.document;
  sattInloggningsnavigering(null);
});

test("401 i webbläsaren leder till inloggningen med sökväg och söksträng i next", async () => {
  const besok: string[] = [];
  sattInloggningsnavigering((url) => besok.push(url));
  iWebblasaren("/dashboard/leads", "?vy=korningar");

  const fel = await kastar(svar(401, UTLOGGAD));

  assert.equal(fel.status, 401);
  assert.deepEqual(besok, ["/login?next=%2Fdashboard%2Fleads%3Fvy%3Dkorningar"]);
});

test("högst en navigering per sidladdning", async () => {
  const besok: string[] = [];
  sattInloggningsnavigering((url) => besok.push(url));
  iWebblasaren("/dashboard");

  await kastar(svar(401, UTLOGGAD));
  await kastar(svar(401, UTLOGGAD));

  assert.equal(besok.length, 1);
});

test("ingen navigering när sidan redan är /login", async () => {
  const besok: string[] = [];
  sattInloggningsnavigering((url) => besok.push(url));
  iWebblasaren("/login", "?next=%2Fdashboard");

  await kastar(svar(401, UTLOGGAD));

  assert.deepEqual(besok, []);
});

test("ett 401 som inte säger ej_inloggad (backendens nyckelfel) navigerar inte", async () => {
  const besok: string[] = [];
  sattInloggningsnavigering((url) => besok.push(url));
  iWebblasaren("/dashboard/kvitton");

  const fel = await kastar(svar(401, { detail: "Ogiltig API-nyckel" }));
  await kastar(new Response("", { status: 401 }));

  assert.equal(fel.status, 401);
  assert.deepEqual(besok, []);
});

test("ingen navigering utanför webbläsaren", async () => {
  const besok: string[] = [];
  sattInloggningsnavigering((url) => besok.push(url));

  const fel = await kastar(svar(401, UTLOGGAD));

  assert.equal(fel.status, 401);
  assert.deepEqual(besok, []);
});

test("403 navigerar inte och säger behörighet, inte utgången session", async () => {
  const besok: string[] = [];
  sattInloggningsnavigering((url) => besok.push(url));
  iWebblasaren("/dashboard");

  const fel = await kastar(new Response("", { status: 403 }));

  assert.deepEqual(besok, []);
  assert.match(fel.message, /behörighet/);
  assert.doesNotMatch(fel.message, /session/i);
});

test("403-texten följer sidans språk", async () => {
  iWebblasaren("/dashboard", "", "en");

  const fel = await kastar(new Response("", { status: 403 }));

  assert.match(fel.message, /permission/);
});

test("401-texten är oförändrad", async () => {
  const fel = await kastar(new Response("", { status: 401 }));

  assert.match(fel.message, /session har gått ut/);
});
