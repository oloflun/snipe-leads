/**
 * Onboardingens första produkt. Kör: node --test "lib/**\/*.test.ts"
 *
 * Före (kunddemon 2026-11-24): onboardingen skrev aldrig `settings.produkter`.
 * Med tom produktlista valde Iris varken produkt eller erbjudande, och en ny
 * kund fick ett utkast som sålde Snajps egen Supportagent. "Vad vi säljer" är
 * obligatoriskt i onboardingen och blir nu kundens första produkt, men bara
 * när listan är tom.
 *
 * standard.ts är server-only och importerar via "@/", som nodens testkörare
 * inte löser (och lib/http/json.ts har syntax som typstrippningen inte tar).
 * Krokarna nedan pekar de tre importerna på stubbar, så att det är den riktiga
 * funktionen som prövas.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { registerHooks } from "node:module";

const STUBBAR: Record<string, string> = {
  "server-only": "",
  "@/app/api/snajp-support/_lib": 'export const SNAJP_SUPPORT_URL = "http://backend";',
  "@/lib/http/json":
    "export async function readJsonBody(r) { const t = await r.text(); return t ? JSON.parse(t) : null; }"
};

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier in STUBBAR) return { url: `stub:${specifier}`, shortCircuit: true };
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url.startsWith("stub:")) {
      return { format: "module", source: STUBBAR[url.slice(5)], shortCircuit: true };
    }
    return nextLoad(url, context);
  }
});

const { sattStandardinstallningar } = await import("./standard.ts");

type Anrop = { metod: string; vag: string; kropp: unknown };

/** Backenden som fetch-stubbe: GET-svar per väg, och alla anrop sparade. */
function backend(produkter: unknown[]): Anrop[] {
  const anrop: Anrop[] = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    const vag = String(input).replace("http://backend", "");
    const metod = init?.method ?? "GET";
    anrop.push({ metod, vag, kropp: init?.body ? JSON.parse(String(init.body)) : null });
    const svar: Record<string, unknown> = {
      "/api/leads/context-docs?kind=product_marketing": { docs: [{ content: "finns" }] },
      "/api/leads/soul": { content: "finns" },
      "/api/leads/config": { icp: { roles: ["VD"] }, produkter }
    };
    return new Response(JSON.stringify(metod === "GET" ? (svar[vag] ?? {}) : {}), { status: 200 });
  }) as typeof fetch;
  return anrop;
}

const UNDERLAG = {
  produkt: [
    "Vårt företag: Buddy",
    "Webbplats: https://buddy.se",
    "Vad vi säljer: Upphandling av företagstelefoni. Vi förhandlar fram lägre priser åt småföretag.",
    "Kontaktperson: Test Testsson — test@example.se"
  ].join("\n"),
  namn: "Buddy"
};

function produktskrivningar(anrop: Anrop[]) {
  return anrop.filter(
    (a) => a.metod === "PUT" && a.vag === "/api/leads/config" && a.kropp && typeof a.kropp === "object" && "produkter" in a.kropp
  );
}

test("en tom produktlista får en rad ur Vad vi säljer", async () => {
  const anrop = backend([]);
  const utfall = await sattStandardinstallningar("nyckel", UNDERLAG);

  const skrivna = produktskrivningar(anrop);
  assert.equal(skrivna.length, 1);
  const { produkter } = skrivna[0].kropp as { produkter: { namn: string; nytta: string }[] };
  assert.deepEqual(produkter, [
    {
      namn: "Upphandling av företagstelefoni",
      nytta: "Upphandling av företagstelefoni. Vi förhandlar fram lägre priser åt småföretag."
    }
  ]);
  assert.equal(utfall.produkter, true);
});

test("en befintlig produktlista skrivs aldrig över", async () => {
  const anrop = backend([{ namn: "Kundens egen", nytta: "det kunden själv skrev" }]);
  const utfall = await sattStandardinstallningar("nyckel", UNDERLAG);

  assert.equal(produktskrivningar(anrop).length, 0);
  assert.equal(utfall.produkter, false);
});

test("utan raden Vad vi säljer och utan egna ord skrivs ingen produkt", async () => {
  const anrop = backend([]);
  await sattStandardinstallningar("nyckel", { produkt: "Vårt företag: Buddy\nWebbplats: https://buddy.se", namn: "Buddy" });
  assert.equal(produktskrivningar(anrop).length, 0);
});

// Produktionen 2026-11-25: 9 av 10 kunder saknade produktlista. Äldre kunder
// (före 400fa150, 2026-08-17) sparade fri text utan raden "Vad vi säljer:".
test("en äldre kund utan raden får sin första egna rad som produkt", async () => {
  const anrop = backend([]);
  const utfall = await sattStandardinstallningar("nyckel", {
    produkt: "\n Redovisning och lönehantering för små byggföretag. Fast pris per månad.\nVi finns i Umeå.",
    namn: "Siffror AB"
  });

  const skrivna = produktskrivningar(anrop);
  assert.equal(skrivna.length, 1);
  assert.deepEqual((skrivna[0].kropp as { produkter: unknown[] }).produkter, [
    {
      namn: "Redovisning och lönehantering för små byggföretag",
      nytta: "Redovisning och lönehantering för små byggföretag. Fast pris per månad."
    }
  ]);
  assert.equal(utfall.produkter, true);
});

test("den äldre kundens rad skriver aldrig över en befintlig lista", async () => {
  const anrop = backend([{ namn: "Kundens egen", nytta: "det kunden själv skrev" }]);
  await sattStandardinstallningar("nyckel", { produkt: "Redovisning för byggföretag.", namn: "Siffror AB" });
  assert.equal(produktskrivningar(anrop).length, 0);
});

test("en tom Vad vi säljer-rad tar aldrig nästa rad som produkt", async () => {
  const anrop = backend([]);
  await sattStandardinstallningar("nyckel", {
    produkt: "Vårt företag: Buddy\nVad vi säljer: \nSärskilt fokus: Norrland",
    namn: "Buddy"
  });
  assert.equal(produktskrivningar(anrop).length, 0);
});
