/**
 * Spärren mot upprepade inloggningsförsök: nycklar, IP och loggmaskering.
 * Kör: node --test lib/auth/inloggningsregler.test.ts
 *
 * Räkningen och väntetiderna prövas mot databasen i
 * snajp-support/tests/db/test_inloggningsforsok.py (CI-jobbet `databas`).
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { REGLER, klientIp, maskeraEpost, nyckel } from "./inloggningsregler.ts";

function h(varden: Record<string, string>): Pick<Headers, "get"> {
  return { get: (namn: string) => varden[namn.toLowerCase()] ?? null };
}

test("reglerna: adressens tröskel är lägre än IP:ts, återställning strängare än inloggning", () => {
  assert.ok(REGLER.inloggning.epost.troskel < REGLER.inloggning.ip.troskel);
  assert.ok(REGLER.aterstallning.epost.troskel <= REGLER.inloggning.epost.troskel);
  assert.equal(REGLER.inloggning.epost.troskel, 5);
  assert.equal(REGLER.inloggning.epost.fonsterSekunder, 900);
});

test("nyckeln är densamma oavsett skiftläge och blanktecken i adressen", () => {
  const a = nyckel("inloggning", "epost", "Anna@Bolag.se ", "hemlig");
  const b = nyckel("inloggning", "epost", "anna@bolag.se", "hemlig");
  assert.equal(a, b);
});

test("nyckeln bär aldrig adressen eller IP:t i klartext", () => {
  const n = nyckel("inloggning", "epost", "anna@bolag.se", "hemlig");
  assert.ok(n.startsWith("inloggning:epost:"));
  assert.ok(!n.includes("anna"));
  assert.ok(!nyckel("inloggning", "ip", "203.0.113.7", "hemlig").includes("203.0.113.7"));
});

test("nyckeln skiljer handling, omfång och hemlighet", () => {
  const bas = nyckel("inloggning", "epost", "a@b.se", "x");
  assert.notEqual(bas, nyckel("aterstallning", "epost", "a@b.se", "x"));
  assert.notEqual(bas, nyckel("inloggning", "ip", "a@b.se", "x"));
  assert.notEqual(bas, nyckel("inloggning", "epost", "a@b.se", "y"));
  assert.ok(nyckel("inloggning", "epost", "a@b.se").length < 200);
});

test("klientens IP: x-real-ip först, annars sista posten i x-forwarded-for", () => {
  assert.equal(klientIp(h({ "x-real-ip": "198.51.100.2" })), "198.51.100.2");
  // Den första posten kan klienten ha skrivit själv; den sista lade kanten till.
  assert.equal(klientIp(h({ "x-forwarded-for": "1.1.1.1, 198.51.100.9" })), "198.51.100.9");
  assert.equal(klientIp(h({})), null);
  assert.equal(klientIp(null), null);
});

test("loggen får bara en maskerad adress", () => {
  assert.equal(maskeraEpost("Anna.Svensson@Bolag.se"), "a***@bolag.se");
  assert.equal(maskeraEpost("utan-snabel"), "***");
});
