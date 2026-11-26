/**
 * Varje svar från proxyAsTenant säger vilken identitet det gäller (INV-SEC-014).
 * Kör: node --test lib/identitet-proxy.test.ts
 *
 * Kunddemon 2026-11-24: en flik visade kundens skal med adminens data, eftersom
 * klienten aldrig märkte att sessionen i webbläsaren bytts. Huvudet
 * X-Snajp-Identitet är det klienten jämför med layoutens identitet. Det måste
 * finnas också på felsvaren: en utgången session svarar 401, och det är just
 * då fliken ska ladda om.
 *
 * Tenant-modulen och backendproxyn byts mot stubbar (tests/fixtures/identitet-proxy).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { register } from "node:module";

register("../tests/fixtures/identitet-proxy/hooks.mjs", import.meta.url);

const { proxyAsTenant } = await import("../app/api/snajp-support/_auth.ts");

type Prov = { tenantfel?: { status: number; kod: string }; roll?: string };
function satt(prov: Prov) {
  (globalThis as { __identitetsprov?: Prov }).__identitetsprov = prov;
}

test("ett lyckat svar bär identiteten", async () => {
  satt({});
  const svar = await proxyAsTenant("/leads/korningar", { method: "GET" });
  assert.equal(svar.status, 200);
  assert.equal(svar.headers.get("X-Snajp-Identitet"), "identitet-u1");
});

test("ett tenantfel bär identiteten", async () => {
  satt({ tenantfel: { status: 401, kod: "ej_inloggad" } });
  const svar = await proxyAsTenant("/leads/korningar", { method: "GET" });
  assert.equal(svar.status, 401);
  assert.equal(svar.headers.get("X-Snajp-Identitet"), "identitet-u1");
});

test("läsrollens spärr bär identiteten", async () => {
  satt({ roll: "viewer" });
  const svar = await proxyAsTenant("/leads/korningar", { method: "POST", body: "{}" });
  assert.equal(svar.status, 403);
  assert.equal(svar.headers.get("X-Snajp-Identitet"), "identitet-u1");
});
