/**
 * TOTP: RFC 6238:s testvektorer, fönstret, återspelningsskyddet och base32.
 * Kör: node --test lib/auth/totp.test.ts
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  base32Avkoda,
  base32Koda,
  grupperadHemlighet,
  hotp,
  nyTotpHemlighet,
  otpauthAdress,
  provaTotp,
  serUtSomTotp,
  totpKod,
  totpSteg
} from "./totp.ts";

// RFC 6238, bilaga B: SHA-1, nyckeln "12345678901234567890", åtta siffror.
const RFC_NYCKEL = Buffer.from("12345678901234567890", "ascii");
const RFC_VEKTORER: [number, string][] = [
  [59, "94287082"],
  [1111111109, "07081804"],
  [1111111111, "14050471"],
  [1234567890, "89005924"],
  [2000000000, "69279037"],
  [20000000000, "65353130"]
];

test("RFC 6238:s testvektorer (SHA-1, åtta siffror)", () => {
  for (const [sekunder, vantat] of RFC_VEKTORER) {
    assert.equal(hotp(RFC_NYCKEL, totpSteg(sekunder * 1000), 8), vantat, `T=${sekunder}`);
  }
});

test("base32 åt båda hållen, och RFC-nyckeln i base32", () => {
  assert.equal(base32Koda(RFC_NYCKEL), "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ");
  assert.deepEqual(base32Avkoda("gezd gnbv gy3t qojq gezd gnbv gy3t qojq"), RFC_NYCKEL);
  assert.equal(base32Avkoda("ABC1"), null, "1 finns inte i base32");
  const hemlighet = nyTotpHemlighet();
  assert.equal(hemlighet.length, 32);
  assert.equal(base32Avkoda(hemlighet)?.length, 20);
});

test("rätt kod godtas och svarar med sitt tidssteg", () => {
  const hemlighet = nyTotpHemlighet();
  const nu = Date.UTC(2026, 10, 18, 12, 0, 10);
  const kod = totpKod(hemlighet, nu);
  assert.equal(provaTotp(hemlighet, kod, nu), totpSteg(nu));
  assert.equal(provaTotp(hemlighet, `${kod.slice(0, 3)} ${kod.slice(3)}`, nu), totpSteg(nu), "blanksteg tillåts");
});

test("fel kod, fel format och fel hemlighet vägras", () => {
  const hemlighet = nyTotpHemlighet();
  const nu = Date.UTC(2026, 10, 18, 12, 0, 10);
  const kod = totpKod(hemlighet, nu);
  const fel = String((Number(kod) + 1) % 1_000_000).padStart(6, "0");
  assert.equal(provaTotp(hemlighet, fel, nu), null);
  assert.equal(provaTotp(hemlighet, "12345", nu), null);
  assert.equal(provaTotp(hemlighet, "abcdef", nu), null);
  assert.equal(provaTotp(nyTotpHemlighet(), kod, nu), null);
});

test("ett steg åt varje håll godtas, två gör det inte", () => {
  const hemlighet = nyTotpHemlighet();
  const nu = Date.UTC(2026, 10, 18, 12, 0, 10);
  assert.notEqual(provaTotp(hemlighet, totpKod(hemlighet, nu - 30_000), nu), null);
  assert.notEqual(provaTotp(hemlighet, totpKod(hemlighet, nu + 30_000), nu), null);
  assert.equal(provaTotp(hemlighet, totpKod(hemlighet, nu - 90_000), nu), null);
  assert.equal(provaTotp(hemlighet, totpKod(hemlighet, nu + 90_000), nu), null);
});

test("en använd kod godtas inte igen (återspelning)", () => {
  const hemlighet = nyTotpHemlighet();
  const nu = Date.UTC(2026, 10, 18, 12, 0, 10);
  const kod = totpKod(hemlighet, nu);
  const steg = provaTotp(hemlighet, kod, nu);
  assert.notEqual(steg, null);
  assert.equal(provaTotp(hemlighet, kod, nu, steg), null, "samma steg");
  assert.equal(provaTotp(hemlighet, kod, nu + 20_000, steg), null, "samma kod, nästa sekunder");
  assert.equal(provaTotp(hemlighet, totpKod(hemlighet, nu - 30_000), nu, steg), null, "äldre steg");
  assert.notEqual(provaTotp(hemlighet, totpKod(hemlighet, nu + 30_000), nu + 30_000, steg), null, "nästa steg");
});

test("otpauth-adressen bär hemlighet, utfärdare och parametrar", () => {
  const adress = otpauthAdress("Snajp", "admin@example.test", "GEZDGNBV");
  assert.ok(adress.startsWith("otpauth://totp/Snajp:admin%40example.test?"));
  const p = new URL(adress).searchParams;
  assert.equal(p.get("secret"), "GEZDGNBV");
  assert.equal(p.get("issuer"), "Snajp");
  assert.equal(p.get("digits"), "6");
  assert.equal(p.get("period"), "30");
});

test("formkontroll och gruppering", () => {
  assert.ok(serUtSomTotp("123 456"));
  assert.ok(!serUtSomTotp("ABCDE-FGHJK"));
  assert.equal(grupperadHemlighet("ABCDEFGHIJ"), "ABCD EFGH IJ");
});
