import { test } from "node:test";
import assert from "node:assert/strict";
import { sandtid } from "./utkast.ts";

// Måndag 2026-11-16 09:00 svensk tid.
const NU = new Date("2026-11-16T08:00:00Z");

test("sändtiden: klockslag i dag, veckodag inom en vecka, datum längre fram", () => {
  assert.equal(sandtid("2026-11-16T09:14:00Z", "sv", NU), "10:14");
  assert.match(sandtid("2026-11-17T07:00:00Z", "sv", NU), /^tis 08:00$/);
  const langt = sandtid("2026-12-18T07:00:00Z", "sv", NU);
  assert.match(langt, /^18 dec/);
  assert.doesNotMatch(langt, /08:00/);
  assert.match(sandtid("2026-12-18T07:00:00Z", "en", NU), /^18 Dec/);
});
