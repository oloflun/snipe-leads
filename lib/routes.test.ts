/**
 * Proxyns inloggningsgrind. Kör: node --test lib/routes.test.ts
 *
 * Kunddemon 2026-11-24: bakåtknappen efter utloggning landade på
 * /admin/arbetsyta, och sidan svarade "Sidan finns inte". /admin stod i
 * proxyns matcher men inte i protectedRoutePrefixes, så proxyn släppte en
 * besökare utan session vidare till layoutens 404. Anton: har sessionen gått
 * ut ska man till inloggningen, aldrig till en felsida.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { isProtectedRoute } from "./routes.ts";

test("adminytan kräver inloggning, även själva /admin", () => {
  assert.equal(isProtectedRoute("/admin"), true);
  assert.equal(isProtectedRoute("/admin/arbetsyta"), true);
  assert.equal(isProtectedRoute("/admin/kunder/snajp"), true);
});

test("arbetsytan, inställningarna och onboardingen är skyddade som förut", () => {
  assert.equal(isProtectedRoute("/dashboard"), true);
  assert.equal(isProtectedRoute("/dashboard/leads"), true);
  assert.equal(isProtectedRoute("/settings/tvafaktor"), true);
  assert.equal(isProtectedRoute("/onboarding"), true);
});

test("ett prefix är ett helt segment, inte början på ett ord", () => {
  assert.equal(isProtectedRoute("/adminx"), false);
  assert.equal(isProtectedRoute("/administration"), false);
});

test("publika sidor och inbäddningen går aldrig till inloggningen", () => {
  assert.equal(isProtectedRoute("/embed/x"), false);
  assert.equal(isProtectedRoute("/leads"), false);
  assert.equal(isProtectedRoute("/"), false);
  assert.equal(isProtectedRoute("/login"), false);
});
