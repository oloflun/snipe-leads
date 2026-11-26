/**
 * Hjälprutans servergräns. Kör: node --test lib/snajp/hjalp.test.ts
 *
 * Det här är det enda stället där klientens kropp möter identiteten: varje
 * Next-väg under app/api/snajp-support/hjalp skickar kroppen hit och får
 * tillbaka det som går till backenden. Testet låser vad som tas från
 * klienten, vad som kastas och vad servern alltid sätter själv
 * (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 2 och 5).
 *
 * hjalp.ts är server-only och importerar via "@/" och "next/server", som
 * nodens testkörare inte löser. Krokarna pekar dem på stubbar, så att det är
 * de riktiga funktionerna som prövas.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { registerHooks } from "node:module";

const STUBBAR: Record<string, string> = {
  "server-only": "",
  "next/server":
    "export const NextResponse = { json: (b, i) => new Response(JSON.stringify(b), { status: i?.status ?? 200 }) };" +
    " export class NextRequest {}",
  "@/lib/vy": 'export async function aktivVy() { return globalThis.__lage ?? { vy: "admin", slug: null }; }',
  "@/lib/db":
    "export function hasDatabase() { return true; }" +
    " export async function sqlAsUser(user, text, params) { globalThis.__sql = { user, text, params };" +
    " return globalThis.__arbetsytor?.[params[0]] ? [{ id: globalThis.__arbetsytor[params[0]] }] : []; }",
  "@/app/api/snajp-support/_lib":
    "export async function proxyWithApiKey(path, init, key, user) { globalThis.__anrop = { path, init, key, user };" +
    " return new Response(globalThis.__svar ?? '{}', { status: 200 }); }",
  // Vägarna själva (ägarkontrollen nedan): sessionen är en stubbe, resten är riktigt.
  "@/lib/workspace": "export async function getWorkspaceContext() { return globalThis.__context ?? null; }"
};

/** Vägarnas import av biblioteket går till den riktiga filen, inte en stubbe. */
const RIKTIGA: Record<string, string> = {
  "@/lib/snajp/hjalp": new URL("./hjalp.ts", import.meta.url).href
};

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier in STUBBAR) return { url: `stub:${specifier}`, shortCircuit: true };
    if (specifier in RIKTIGA) return { url: RIKTIGA[specifier], shortCircuit: true };
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url.startsWith("stub:")) {
      return { format: "module", source: STUBBAR[url.slice(5)], shortCircuit: true };
    }
    return nextLoad(url, context);
  }
});

const hjalp = await import("./hjalp.ts");

const ID = {
  userId: "11111111-2222-4333-8444-555555555555",
  namn: "Ada Andersson",
  workspaceId: "66666666-7777-4888-9999-000000000000",
  tenantSlug: "buddy",
  vy: "egen",
  roll: "owner",
  besokAvAdmin: false
} as const;

test("avsändaren är alltid den inloggades id på kunddomänen", () => {
  assert.equal(hjalp.hjalpAvsandare(ID.userId), `${ID.userId}@kund.snajp.se`);
});

test("chattkroppen tar bara texten och bilden ur klienten", () => {
  const kropp = hjalp.hjalpChattkropp(
    {
      message: "  Hur lägger jag till en kollega?  ",
      customer_email: "annan.kund@example.se",
      customer_name: "Någon annan",
      arbetsyta: true,
      is_test: true,
      tenant: "nordlys-handel",
      subject: "x",
      attachments: [{ data_url: "data:image/png;base64,iVBORw0KGgo=" }, { data_url: "data:image/png;base64,AAAA" }]
    },
    ID
  );
  assert.deepEqual(kropp, {
    message: "Hur lägger jag till en kollega?",
    channel: "web",
    customer_email: `${ID.userId}@kund.snajp.se`,
    customer_name: "Ada Andersson",
    attachments: [{ data_url: "data:image/png;base64,iVBORw0KGgo=" }],
    is_test: false
  });
  assert.equal("arbetsyta" in (kropp ?? {}), false);
  assert.equal("tenant" in (kropp ?? {}), false);
});

test("chattkroppen utan text, eller med en bilaga som inte är en bild, avvisas eller rensas", () => {
  assert.equal(hjalp.hjalpChattkropp({ message: "   " }, ID), null);
  assert.equal(hjalp.hjalpChattkropp("inte ett objekt", ID), null);
  const kropp = hjalp.hjalpChattkropp(
    { message: "Hej", attachments: [{ data_url: "data:text/html;base64,PHNjcmlwdD4=" }] },
    ID
  );
  assert.deepEqual(kropp?.attachments, []);
});

test("samtalet läses alltid under den inloggades egen adress", () => {
  assert.deepEqual(hjalp.hjalpSamtalskropp(ID), { customer_email: `${ID.userId}@kund.snajp.se` });
});

test("sidan är bara sökvägen: ingen söksträng, inget fragment, högst 300 tecken", () => {
  assert.equal(hjalp.renSida("/dashboard/leads?token=hemligt#x"), "/dashboard/leads");
  assert.equal(hjalp.renSida("https://snajp.se/settings/kunskapsbas?a=1"), "/settings/kunskapsbas");
  assert.equal(hjalp.renSida("settings"), "/settings");
  assert.equal(hjalp.renSida(42), "/");
  assert.equal(hjalp.renSida(`/${"a".repeat(500)}`).length, 300);
});

test("felrapporten: identiteten ur sessionen, bara fem fält ur klienten", () => {
  const kropp = hjalp.rapportkropp(
    {
      sida: "/dashboard/leads?q=1",
      gjorde: "Startade en körning",
      hande: "Inget hände",
      vantade: "Leads",
      bild: "data:image/jpeg;base64,/9j/4AAQ",
      rapportor_user_id: "99999999-9999-4999-8999-999999999999",
      kund_workspace_id: "99999999-9999-4999-8999-999999999999",
      kund_tenant_slug: "annan-kund",
      roll: "owner",
      besok_av_admin: false,
      vy: "admin"
    },
    { ...ID, roll: "viewer", vy: "kund", besokAvAdmin: true }
  );
  assert.deepEqual(kropp, {
    rapportor_user_id: ID.userId,
    rapportor_namn: "Ada Andersson",
    kund_workspace_id: ID.workspaceId,
    kund_tenant_slug: "buddy",
    vy: "kund",
    roll: "viewer",
    besok_av_admin: true,
    sida: "/dashboard/leads",
    gjorde: "Startade en körning",
    hande: "Inget hände",
    vantade: "Leads",
    bild: "data:image/jpeg;base64,/9j/4AAQ"
  });
});

test("felrapporten utan något ifyllt avvisas, och en främmande bild blir null", () => {
  assert.equal(hjalp.rapportkropp({ gjorde: " ", hande: "", vantade: "" }, ID), null);
  const kropp = hjalp.rapportkropp({ hande: "Det kraschade", bild: "javascript:alert(1)" }, ID);
  assert.equal(kropp?.bild, null);
  assert.equal(kropp?.gjorde, "");
  assert.equal(kropp?.sida, "/");
});

test("svar och utslag bär alltid rapportören ur sessionen", () => {
  assert.deepEqual(hjalp.svarkropp({ text: " Det var på mobilen ", rapportor_user_id: "x" }, ID), {
    rapportor_user_id: ID.userId,
    text: "Det var på mobilen"
  });
  assert.equal(hjalp.svarkropp({ text: "" }, ID), null);
  assert.deepEqual(hjalp.utslagskropp({ fungerar: false, kommentar: " Samma fel ", rapportor_user_id: "x" }, ID), {
    rapportor_user_id: ID.userId,
    fungerar: false,
    kommentar: "Samma fel"
  });
  assert.deepEqual(hjalp.utslagskropp({ fungerar: true, kommentar: "" }, ID), {
    rapportor_user_id: ID.userId,
    fungerar: true,
    kommentar: null
  });
  assert.equal(hjalp.utslagskropp({ fungerar: "ja" }, ID), null);
});

test("ett ärende-id i sökvägen måste vara ett uuid", () => {
  assert.equal(hjalp.arUuid(ID.userId), true);
  assert.equal(hjalp.arUuid("../admin/plattformsarenden"), false);
  assert.equal(hjalp.arUuid(undefined), false);
});

test("identiteten: kundens egen vy, och ett adminbesök märks som besök", async () => {
  const context = {
    user: { id: ID.userId, email: "ada@buddy.se", name: "Ada från sessionen" },
    profile: { id: ID.userId, workspace_id: ID.workspaceId, full_name: "Ada Andersson", role: "owner", created_at: "" },
    workspace: { id: ID.workspaceId, slug: "buddy" },
    businessContext: null,
    isPlatformAdmin: false
  };
  (globalThis as { __lage?: unknown }).__lage = { vy: "admin", slug: null };
  // Typerna i hjalp.ts är Nexts; här räcker formen som identiteten läser.
  const egen = await hjalp.hjalpIdentitet(context as never);
  assert.deepEqual(egen, { ...ID });

  const BESOKT = "abcdefab-cdef-4abc-8def-abcdefabcdef";
  (globalThis as { __arbetsytor?: unknown }).__arbetsytor = { livrustning: BESOKT };
  (globalThis as { __lage?: unknown }).__lage = { vy: "kund", slug: "livrustning" };
  const besok = await hjalp.hjalpIdentitet({ ...context, isPlatformAdmin: true } as never);
  assert.equal(besok.tenantSlug, "livrustning");
  assert.equal(besok.vy, "kund");
  assert.equal(besok.besokAvAdmin, true);
  assert.equal(besok.userId, ID.userId);
  // Arbetsytan och sluggen pekar på samma kund: den besöktas, inte adminens.
  assert.equal(besok.workspaceId, BESOKT);
  assert.deepEqual((globalThis as { __sql?: { params: unknown[] } }).__sql?.params, ["livrustning"]);

  // Syns inte raden (RLS, eller demokontot utan arbetsyta) står adminens kvar.
  (globalThis as { __arbetsytor?: unknown }).__arbetsytor = {};
  const osynlig = await hjalp.hjalpIdentitet({ ...context, isPlatformAdmin: true } as never);
  assert.equal(osynlig.workspaceId, ID.workspaceId);
  assert.equal(osynlig.tenantSlug, "livrustning");
});

test("utan hjälpens nyckel svarar vägen 503 och når aldrig backenden", async () => {
  (globalThis as { __anrop?: unknown }).__anrop = undefined;
  const svar = await hjalp.tillHjalpen(undefined, "/api/chat", { method: "POST" }, ID.userId);
  assert.equal(svar.status, 503);
  const kropp = (await svar.json().catch(() => ({}))) as { kod: string; error: string };
  assert.equal(kropp.kod, "hjalp_av");
  assert.match(kropp.error, /påslagen/);
  assert.match(kropp.error, /not switched on/);
  assert.equal((globalThis as { __anrop?: unknown }).__anrop, undefined);

  await hjalp.tillHjalpen("hjalpnyckel", "/api/chat", { method: "POST" }, ID.userId);
  assert.deepEqual((globalThis as { __anrop?: { key: string; user: string } }).__anrop?.key, "hjalpnyckel");
});

/*
 * Ägarkontrollen på hjälpens jobb. Alla kunders frågor går under samma
 * hjälpkund, så backendens tenantkontroll skiljer dem inte åt; jobbet får
 * bara läsas av den användare och arbetsyta som startade det. Här körs de
 * riktiga vägarna (app/api/snajp-support/hjalp/route.ts och jobb/[jobId]) med
 * sessionen och backenden som stubbar.
 */
const HEMLIGHET = "testhemlighet-som-bara-finns-i-testet";
const JOBB = "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d";
const ANNAN = {
  ...ID,
  userId: "99999999-8888-4777-8666-555555555555",
  workspaceId: "12121212-3434-4565-8787-909090909090"
};

type G = {
  __context?: unknown;
  __lage?: unknown;
  __arbetsytor?: unknown;
  __anrop?: { path: string; key: string; user: string };
  __svar?: string;
};
const g = globalThis as G;

function sessionFor(id: { userId: string; workspaceId: string; tenantSlug: string }) {
  return {
    user: { id: id.userId, email: "x@exempel.se", name: "X" },
    profile: { id: id.userId, workspace_id: id.workspaceId, full_name: "X", role: "owner", created_at: "" },
    workspace: { id: id.workspaceId, slug: id.tenantSlug },
    businessContext: null,
    isPlatformAdmin: false
  };
}

const startvag = await import("../../app/api/snajp-support/hjalp/route.ts");
const jobbvag = await import(new URL("../../app/api/snajp-support/hjalp/jobb/[jobId]/route.ts", import.meta.url).href);

async function polla(token: string): Promise<Response> {
  return jobbvag.GET(new Request("http://x/") as never, { params: Promise.resolve({ jobId: token }) });
}

test("jobbtoken: rätt användare får tillbaka id:t, annan användare, annan arbetsyta och fel hemlighet får null", () => {
  const token = hjalp.signeraJobb(JOBB, ID, HEMLIGHET);
  assert.ok(token);
  assert.match(token, /^0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d\.[A-Za-z0-9_-]{43}$/);
  assert.equal(hjalp.lasJobb(token, ID, HEMLIGHET), JOBB);
  assert.equal(hjalp.lasJobb(token, ANNAN, HEMLIGHET), null);
  assert.equal(hjalp.lasJobb(token, { ...ID, workspaceId: ANNAN.workspaceId }, HEMLIGHET), null);
  // En kollega i SAMMA arbetsyta: användaren ensam ska räcka för ett nej.
  assert.equal(hjalp.lasJobb(token, { ...ID, userId: ANNAN.userId }, HEMLIGHET), null);
  assert.equal(hjalp.lasJobb(token, ID, "en-annan-hemlighet"), null);
  // En token har exakt en stavning: versaler i id:t ger id:t i gemener, och
  // varje annan stavning av signaturens sista tecken (utfyllnadsbitarna) vägras.
  const [jobbdel, sig] = token.split(".");
  assert.equal(hjalp.lasJobb(`${jobbdel.toUpperCase()}.${sig}`, ID, HEMLIGHET), JOBB);
  const alfabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  for (const tecken of alfabet) {
    if (tecken === sig.at(-1)) continue;
    assert.equal(hjalp.lasJobb(`${jobbdel}.${sig.slice(0, -1)}${tecken}`, ID, HEMLIGHET), null, tecken);
  }
  assert.equal(hjalp.lasJobb(token, ID, undefined), null);
  // Det nakna id:t, som klienten fick förut, godtas inte längre.
  assert.equal(hjalp.lasJobb(JOBB, ID, HEMLIGHET), null);
  // Utan hemlighet eller med ett id som inte är ett uuid signeras inget.
  assert.equal(hjalp.signeraJobb(JOBB, ID, undefined), null);
  assert.equal(hjalp.signeraJobb("../admin", ID, HEMLIGHET), null);
});

test("ägarkontrollen: rätt användare får sitt jobb, annan användare och manipulerat id får 404, utloggad 401", async () => {
  process.env.AUTH_SECRET = HEMLIGHET;
  process.env.SNAJP_KEY_SNAJP_HJALP = "hjalpnyckel";
  g.__lage = { vy: "admin", slug: null };
  g.__arbetsytor = {};

  // Ada startar en fråga. Backenden svarar med ett naket jobb-id; klienten får en token.
  g.__context = sessionFor(ID);
  g.__svar = JSON.stringify({ job_id: JOBB, status: "processing" });
  const start = await startvag.POST(
    new Request("http://x/", { method: "POST", body: JSON.stringify({ message: "Hur bjuder jag in en kollega?" }) }) as never
  );
  assert.equal(start.status, 200);
  const { job_id: token, status } = (await start.json().catch(() => ({}))) as { job_id: string; status: string };
  assert.equal(status, "processing");
  assert.notEqual(token, JOBB, "det nakna jobb-id:t får aldrig nå klienten");
  assert.equal(hjalp.lasJobb(token, ID, HEMLIGHET), JOBB);

  // Ada pollar: anropet når backenden med det nakna id:t, under hjälpens nyckel.
  g.__anrop = undefined;
  g.__svar = JSON.stringify({ status: "completed", result: { svar: "Så här." } });
  const egen = await polla(token);
  assert.equal(egen.status, 200);
  assert.equal(g.__anrop?.path, `/api/jobs/${JOBB}`);
  assert.equal(g.__anrop?.key, "hjalpnyckel");
  assert.equal(g.__anrop?.user, ID.userId);

  // En annan kund med Adas token: 404, och backenden nås aldrig.
  g.__context = sessionFor(ANNAN);
  g.__anrop = undefined;
  const annan = await polla(token);
  assert.equal(annan.status, 404);
  assert.equal(((await annan.json().catch(() => ({}))) as { kod?: string }).kod, "saknas");
  assert.equal(g.__anrop, undefined);

  // Manipulerat: ett annat jobb-id med Adas signatur, en ändrad signatur, det nakna id:t och skräp.
  g.__context = sessionFor(ID);
  const [, signatur] = token.split(".");
  // Första tecknet bär bara data (det sista bär utfyllnadsbitar).
  const vandSignatur = `${signatur.startsWith("A") ? "B" : "A"}${signatur.slice(1)}`;
  for (const fel of [
    `aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee.${signatur}`,
    `${JOBB}.${vandSignatur}`,
    JOBB,
    "../admin/plattformsarenden",
    `${token}x`
  ]) {
    g.__anrop = undefined;
    const svar = await polla(fel);
    assert.equal(svar.status, 404, `"${fel}" ska ge 404`);
    assert.equal(g.__anrop, undefined, `"${fel}" ska aldrig nå backenden`);
  }

  // Utloggad: 401 som de andra hjälpvägarna, innan något annat prövas.
  g.__context = null;
  g.__anrop = undefined;
  const utloggad = await polla(token);
  assert.equal(utloggad.status, 401);
  assert.equal(((await utloggad.json().catch(() => ({}))) as { kod?: string }).kod, "ej_inloggad");
  assert.equal(g.__anrop, undefined);
});

test("utan AUTH_SECRET startas ingen fråga och ingen token godtas", async () => {
  process.env.SNAJP_KEY_SNAJP_HJALP = "hjalpnyckel";
  g.__lage = { vy: "admin", slug: null };
  g.__context = sessionFor(ID);
  const token = hjalp.signeraJobb(JOBB, ID, HEMLIGHET)!;
  delete process.env.AUTH_SECRET;
  try {
    g.__anrop = undefined;
    const start = await startvag.POST(
      new Request("http://x/", { method: "POST", body: JSON.stringify({ message: "Hej" }) }) as never
    );
    assert.equal(start.status, 503);
    assert.equal(g.__anrop, undefined, "en fråga vars jobb inte går att signera ska aldrig skickas");
    const poll = await polla(token);
    assert.equal(poll.status, 404);
    assert.equal(g.__anrop, undefined);
  } finally {
    process.env.AUTH_SECRET = HEMLIGHET;
  }
});

test("ett svar utan job_id (fel, kvot) går vidare utan att signeras", async () => {
  const fel = new Response(JSON.stringify({ error: "Kvoten är slut." }), { status: 429 });
  assert.equal(await hjalp.medSigneratJobb(fel, ID, HEMLIGHET), fel);
  const utan = await hjalp.medSigneratJobb(new Response(JSON.stringify({ offline: true })), ID, HEMLIGHET);
  assert.deepEqual(await utan.json().catch(() => null), { offline: true });
});
