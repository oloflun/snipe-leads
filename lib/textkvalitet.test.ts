/**
 * Email Studios motivering utan tekniska referenser. Kör: node --test lib/textkvalitet.test.ts
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { utanReferenser } from "./textkvalitet.ts";

test("en mening som hänvisar till en skill eller fil stryks, resten står kvar", () => {
  assert.equal(
    utanReferenser("Kortare och rakare. Ruthlessly short enligt cold-email/SKILL.md. Frågan på slutet är lätt att svara ja på."),
    "Kortare och rakare. Frågan på slutet är lätt att svara ja på."
  );
  assert.equal(utanReferenser("Bunden till marketingskills-principer."), "");
});

test("en vanlig motivering lämnas orörd", () => {
  const ren = "Tydligare varför just nu, ett konkret erbjudande och en fråga som är lätt att svara ja på.";
  assert.equal(utanReferenser(ren), ren);
  assert.equal(utanReferenser(undefined), "");
});
