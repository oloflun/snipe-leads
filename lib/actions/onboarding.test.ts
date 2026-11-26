/**
 * Testarbetsytans namn. Kör: node --test "lib/**\/*.test.ts"
 *
 * Före (kunddemon 2026-11-24): tenanten hette "Testarbetsyta https://buddy.se".
 * Namnet går som tenant_name in i Iris prompt ("åt …") och i signaturen, och
 * grundprompten tillåter Snajps agentnamn bara "om företaget är Snajp", något
 * modellen inte kan avgöra ur en webbadress. Testmärket bärs av sluggen
 * (`testkund-<8>`) och `is_demo`, aldrig av namnet (lib/admin/statistik.ts).
 *
 * Server-actionen drar in auth, databas och Next, så den läses som källa.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

const kalla = readFileSync(path.join(import.meta.dirname, "onboarding.ts"), "utf8");

test("testtenanten får företagets namn, inte webbadressen", () => {
  const anrop = kalla.match(/skapaTesttenant\(([^)]*)\)/g) ?? [];
  assert.equal(anrop.length, 1, "ett enda anrop till skapaTesttenant väntas");
  assert.match(anrop[0], /^skapaTesttenant\(payload\.workspace_id, foretag\)$/);
  assert.doesNotMatch(kalla, /`Testarbetsyta \$\{/);
});
