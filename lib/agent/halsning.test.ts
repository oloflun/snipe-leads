/**
 * Hälsningsraden i Email Studio. Kör: node --test "lib/agent/*.test.ts"
 *
 * Bugghistorien: exempelbolagens `contact_name` var en ROLL ("Inköpschef"),
 * och den gamla demogeneratorn skrev ändå "Hej Inköpschef," rakt av. Testerna
 * här är precis den kontrollen: en roll ska ALDRIG bli en hälsning.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { halsning } from "./halsning.ts";

test("ett förnamn ger 'Hej <förnamn>,'", () => {
  assert.equal(halsning("Karin Öhman"), "Hej Karin,");
  assert.equal(halsning("Erik"), "Hej Erik,");
});

test("roller och titlar ger 'Hej,' — aldrig hälsning på rollen", () => {
  for (const roll of ["Inköpschef", "VD", "Platschef", "CFO", "Ekonomichef", "Kontakt"]) {
    assert.equal(halsning(roll), "Hej,", `${roll} ska inte hälsas som ett namn`);
  }
});

test("tomt, null eller undefined ger 'Hej,'", () => {
  assert.equal(halsning(""), "Hej,");
  assert.equal(halsning("   "), "Hej,");
  assert.equal(halsning(null), "Hej,");
  assert.equal(halsning(undefined), "Hej,");
});

test("helt gemen text räknas inte som ett namn", () => {
  assert.equal(halsning("karin öhman"), "Hej,");
  assert.equal(halsning("info"), "Hej,");
});

test("bara förnamnet används, aldrig efternamnet", () => {
  assert.equal(halsning("Sara Lindqvist"), "Hej Sara,");
});
