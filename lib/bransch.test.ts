/**
 * Branschlistan och paketkartan. Kör: node --test "lib/*.test.ts"
 *
 * Två kontrakt onboardingen står på:
 *  - varje val i branschsteget passerar serversidans arBransch-grind,
 *  - varje paketkort i steg fyra ger en produktlista som RPC:n
 *    set_workspace_products accepterar (delmängd av productKeys, aldrig tom).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { BRANSCHER, arBransch } from "./bransch.ts";
import { PAKET, PRODUKTER_FOR_PAKET, arPaketId } from "./pricing.ts";

test("varje bransch i listan passerar grinden", () => {
  for (const b of BRANSCHER) {
    assert.ok(arBransch(b), `${b} avvisas av arBransch`);
  }
});

test("ett påhittat värde avvisas — grinden är en allowlist, inte en ordkontroll", () => {
  assert.equal(arBransch("Raketforskning"), false);
  assert.equal(arBransch(""), false);
});

test("varje paket i prislistan har en produktmappning", () => {
  for (const paket of PAKET) {
    assert.ok(arPaketId(paket.id), `${paket.id} saknas i PRODUKTER_FOR_PAKET`);
    const produkter = PRODUKTER_FOR_PAKET[paket.id];
    assert.ok(produkter.length >= 1, `${paket.id} ger en tom produktlista`);
    for (const produkt of produkter) {
      assert.ok(
        ["leads", "support", "bookkeeping"].includes(produkt),
        `${paket.id} pekar på okänd produkt ${produkt}`
      );
    }
  }
});

test("trio är alla tre, duo är leads+support — paketen ÄR entitlementen", () => {
  assert.deepEqual([...PRODUKTER_FOR_PAKET.trio].sort(), ["bookkeeping", "leads", "support"]);
  assert.deepEqual([...PRODUKTER_FOR_PAKET.duo].sort(), ["leads", "support"]);
});
