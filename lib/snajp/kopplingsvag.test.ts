/**
 * Onboardingens val av kopplingsväg. Kör: node --test "lib/**\/*.test.ts"
 *
 * Före (produktion 2026-11-23, kund-ad046232): en testarbetsyta som redan var
 * kopplad gick ändå testvägen. `link_test_tenant` nekade, felet svaldes, och
 * webbplatsskanningen, målgruppen och erbjudandena skrevs aldrig.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { kopplingsvag } from "./kopplingsvag.ts";

test("en redan kopplad arbetsyta behåller sin kund, även när testrutan är kryssad", () => {
  assert.equal(kopplingsvag("kund-ad046232", true), "befintlig");
  assert.equal(kopplingsvag("kund-ad046232", false), "befintlig");
  assert.equal(kopplingsvag("testkund-ad046232", true), "befintlig");
});

test("en okopplad arbetsyta får testtenant eller kundtenant efter testrutan", () => {
  assert.equal(kopplingsvag(null, true), "testtenant");
  assert.equal(kopplingsvag(undefined, true), "testtenant");
  assert.equal(kopplingsvag("", false), "kundtenant");
  assert.equal(kopplingsvag(null, false), "kundtenant");
});
