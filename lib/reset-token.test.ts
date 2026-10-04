/**
 * Engångstoken för lösenordsåterställning. Kör: node --test "lib/*.test.ts"
 *
 * Kontrakten återställningsflödet står på:
 *  - en genererad token passerar sin egen formgrind och hashas deterministiskt,
 *  - hashen är det enda som lagras, så två anrop får aldrig samma token,
 *  - formgrinden avvisar allt som inte är exakt en 43-teckens base64url-token
 *    (en manipulerad länk ska stoppas före databasfrågan).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { hashaResetToken, nyResetToken, serUtSomResetToken } from "./reset-token.ts";

test("en genererad token passerar formgrinden och hashar till sin lagrade hash", () => {
  const { token, hash } = nyResetToken();
  assert.ok(serUtSomResetToken(token), `token har fel form: ${token}`);
  assert.equal(hashaResetToken(token), hash);
  assert.match(hash, /^[0-9a-f]{64}$/);
});

test("två tokens är aldrig lika", () => {
  assert.notEqual(nyResetToken().token, nyResetToken().token);
});

test("formgrinden är en allowlist, inte en längdkontroll", () => {
  assert.equal(serUtSomResetToken(""), false);
  assert.equal(serUtSomResetToken(undefined), false);
  assert.equal(serUtSomResetToken("a".repeat(42)), false);
  assert.equal(serUtSomResetToken("a".repeat(44)), false);
  // Rätt längd men otillåtna tecken — t.ex. ett SQL- eller sökvägsförsök.
  assert.equal(serUtSomResetToken("a".repeat(40) + "../"), false);
  assert.equal(serUtSomResetToken("a".repeat(42) + "="), false);
});
