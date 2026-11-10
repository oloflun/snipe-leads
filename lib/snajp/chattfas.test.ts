/**
 * Chattens väntläge. Kör: node --test "lib/**\/*.test.ts"
 *
 * Före (fas 2, 2026-11-10): "Agenten arbetar" stod stilla i omkring tio
 * sekunder, och svaret hämtades med två sekunders mellanrum efter de första
 * fyra sekunderna, så ett färdigt svar väntade i snitt en sekund på att bli
 * hämtat.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { fastext, pollpaus, POLL_FORSOK } from "./chattfas.ts";

test("varje skede har en egen text på båda språken", () => {
  const texter = ["laser", "soker", "skriver", "kontrollerar"].map((f) => fastext(f));
  assert.equal(new Set(texter.map((t) => t.sv)).size, 4);
  assert.equal(new Set(texter.map((t) => t.en)).size, 4);
  for (const t of texter) assert.ok(t.sv && t.en);
});

test("okänt eller saknat skede ger den allmänna texten", () => {
  assert.deepEqual(fastext(undefined), { sv: "Agenten arbetar", en: "The agent is working" });
  assert.deepEqual(fastext("arbetar"), fastext(undefined));
  assert.deepEqual(fastext("nagot-nytt"), fastext(undefined));
});

test("svaret hämtas tätt medan ett vanligt svar blir klart", () => {
  // Ett svar tar 8–12 sekunder i median: under den tiden högst 700 ms mellan hämtningarna.
  let tid = 0;
  for (let forsok = 0; tid < 12_000; forsok += 1) {
    assert.ok(pollpaus(forsok) <= 700, `försök ${forsok}`);
    tid += pollpaus(forsok);
  }
});

test("pollningen glesnar och ger inte upp tidigare än förut", () => {
  assert.ok(pollpaus(POLL_FORSOK - 1) >= 2000);
  let total = 0;
  for (let forsok = 0; forsok < POLL_FORSOK; forsok += 1) total += pollpaus(forsok);
  // Förut: 5 × 0,8 s + 85 × 2 s = 174 s.
  assert.ok(total >= 174_000, `väntar bara ${total} ms`);
});
