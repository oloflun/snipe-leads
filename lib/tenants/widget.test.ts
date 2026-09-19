/**
 * Widgetens uppslag och domänlista. Kör: node --test "lib/tenants/*.test.ts"
 *
 * Två kontrakt som inte får glida:
 *  - den publika nyckeln är enda vägen in i /embed, och en okänd nyckel
 *    ger null (→ 404 och frame-ancestors 'none'),
 *  - allowlisten renderas som en giltig CSP-rad med 'self' först, så att
 *    vår egen testsida alltid kan bädda in widgeten.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { frameAncestors, hittaTenantMedPublicKey } from "./widget.ts";
import { livrustning } from "./livrustning.ts";

const alla = [livrustning];

function getTenantByPublicKey(nyckel: string | null | undefined) {
  return hittaTenantMedPublicKey(alla, nyckel);
}

test("Livrustnings publika nyckel löser till Livrustning", () => {
  const tenant = getTenantByPublicKey(livrustning.publicKey);
  assert.equal(tenant?.slug, "livrustning");
});

test("okänd, tom eller saknad nyckel ger null", () => {
  assert.equal(getTenantByPublicKey("pk_paahittad_000000"), null);
  assert.equal(getTenantByPublicKey(""), null);
  assert.equal(getTenantByPublicKey(null), null);
  assert.equal(getTenantByPublicKey(undefined), null);
});

test("en slug är INTE en nyckel — /embed ska inte gå att gissa via kundnamn", () => {
  assert.equal(getTenantByPublicKey("livrustning"), null);
});

test("frame-ancestors bär 'self' plus kundens domäner", () => {
  const rad = frameAncestors(livrustning);
  assert.ok(rad.startsWith("frame-ancestors 'self' "));
  assert.ok(rad.includes("https://livrustning.se"));
  assert.ok(rad.includes("https://www.livrustning.se"));
});

test("okänd tenant ger 'none' — sidan ska inte ens renderas i främmande ram", () => {
  assert.equal(frameAncestors(null), "frame-ancestors 'none'");
});

test("en tenant utan publicKey ger 'none' även om objektet finns", () => {
  const utanNyckel = { ...livrustning, publicKey: undefined };
  assert.equal(frameAncestors(utanNyckel), "frame-ancestors 'none'");
});
