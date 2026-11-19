/**
 * Tvåstegsverifieringens kryptering och återställningskoder.
 * Kör: node --test lib/auth/tvafaktor-krypto.test.ts
 *
 * Inloggningssteget, spärren och lagringen prövas mot databasen i
 * snajp-support/tests/db/test_tvafaktor.py (CI-jobbet `databas`).
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  ANTAL_ATERSTALLNINGSKODER,
  TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN,
  dekrypteraHemlighet,
  hashaAterstallningskod,
  krypteraHemlighet,
  normaliseraAterstallningskod,
  nyaAterstallningskoder,
  serUtSomAterstallningskod
} from "./tvafaktor-krypto.ts";

const NYCKEL = "test-auth-secret-0123456789abcdef";
const ANVANDARE = "6f1c2a7e-0000-4000-8000-000000000001";
const HEMLIGHET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ";

test("tvånget är av som standard (Antons beslut)", () => {
  assert.equal(TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN, false);
});

test("krypteringen åt båda hållen", () => {
  const blob = krypteraHemlighet(HEMLIGHET, ANVANDARE, NYCKEL);
  assert.ok(blob.startsWith("v1."));
  assert.ok(!blob.includes(HEMLIGHET), "klartexten syns inte i chiffertexten");
  assert.equal(dekrypteraHemlighet(blob, ANVANDARE, NYCKEL), HEMLIGHET);
});

test("samma hemlighet ger olika chiffertext (slumpad iv)", () => {
  assert.notEqual(krypteraHemlighet(HEMLIGHET, ANVANDARE, NYCKEL), krypteraHemlighet(HEMLIGHET, ANVANDARE, NYCKEL));
});

test("fel nyckel (bytt AUTH_SECRET) ger null, inte ett undantag", () => {
  const blob = krypteraHemlighet(HEMLIGHET, ANVANDARE, NYCKEL);
  assert.equal(dekrypteraHemlighet(blob, ANVANDARE, "en-annan-auth-secret-0123456789"), null);
});

test("fel användare ger null: raden är bunden till kontot", () => {
  const blob = krypteraHemlighet(HEMLIGHET, ANVANDARE, NYCKEL);
  assert.equal(dekrypteraHemlighet(blob, "6f1c2a7e-0000-4000-8000-000000000002", NYCKEL), null);
});

test("en ändrad chiffertext eller ett okänt format ger null", () => {
  const blob = krypteraHemlighet(HEMLIGHET, ANVANDARE, NYCKEL);
  const [v, iv, tagg, data] = blob.split(".");
  const andrad = `${v}.${iv}.${tagg}.${data.slice(0, -2)}${data.slice(-2) === "AA" ? "AB" : "AA"}`;
  assert.equal(dekrypteraHemlighet(andrad, ANVANDARE, NYCKEL), null);
  assert.equal(dekrypteraHemlighet(`v2.${iv}.${tagg}.${data}`, ANVANDARE, NYCKEL), null);
  assert.equal(dekrypteraHemlighet("skräp", ANVANDARE, NYCKEL), null);
});

test("utan AUTH_SECRET krypteras ingenting", () => {
  assert.throws(() => krypteraHemlighet(HEMLIGHET, ANVANDARE, undefined));
});

test("återställningskoderna: antal, format, unika", () => {
  const koder = nyaAterstallningskoder();
  assert.equal(koder.length, ANTAL_ATERSTALLNINGSKODER);
  assert.equal(new Set(koder).size, koder.length);
  for (const kod of koder) {
    assert.match(kod, /^[A-HJ-NP-Z2-9]{5}-[A-HJ-NP-Z2-9]{5}$/);
    assert.ok(serUtSomAterstallningskod(kod));
  }
  assert.ok(!serUtSomAterstallningskod("123456"));
  assert.ok(!serUtSomAterstallningskod("ABCDE-FGHI0"), "0 och I används inte");
});

test("hashen: normaliserad, nyckelbunden och utan klartext", () => {
  const [kod] = nyaAterstallningskoder(1);
  const hash = hashaAterstallningskod(kod, NYCKEL);
  assert.match(hash, /^[0-9a-f]{64}$/);
  assert.equal(hashaAterstallningskod(` ${kod.toLowerCase().replace("-", " ")} `, NYCKEL), hash);
  assert.notEqual(hashaAterstallningskod(kod, "en-annan-auth-secret-0123456789"), hash);
  assert.equal(normaliseraAterstallningskod("abcde-fghjk"), "ABCDEFGHJK");
});
