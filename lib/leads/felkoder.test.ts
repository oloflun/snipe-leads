/**
 * Ett fallet utkastjobbs besked. Kör: node --test "lib/**\/*.test.ts"
 *
 * Före (2026-11-25): utkastrutorna för Iris-bolagen visade backendens råa
 * svenska feltext även på engelska. Körningsformuläret översatte redan koden
 * saknar_produkt; nu går rutorna genom samma tabell.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { JOBBFEL_ALLMANT, JobbFel, KUNDFELKODER, jobbfel, kundfelkod } from "./felkoder.ts";

const RA_SVENSKA = "Iris vet inte vilken av era produkter mejlen ska sälja.";

test("en känd kod ger tabellens text på båda språken, inte backendens", () => {
  for (const kod of ["saknar_produkt", "saknar_beskrivning", "kreditslut", "kvot", "tidsgrans"]) {
    const besked = jobbfel(kod, RA_SVENSKA);
    assert.deepEqual(besked, KUNDFELKODER[kod]);
    assert.notEqual(besked.en, RA_SVENSKA);
    assert.ok(besked.sv.length > 0 && besked.en.length > 0);
  }
  assert.match(jobbfel("saknar_produkt").en, /Add at least one product/);
  assert.match(jobbfel("saknar_produkt").sv, /Lägg till minst en produkt/);
});

test("en okänd kod: svenskan får backendens text, engelskan den allmänna", () => {
  const besked = jobbfel("ny_kod_som_ingen_kanner", RA_SVENSKA);
  assert.equal(besked.sv, RA_SVENSKA);
  assert.equal(besked.en, JOBBFEL_ALLMANT.en);
});

test("ingen kod och ingen text: den allmänna texten på båda språken", () => {
  assert.deepEqual(jobbfel(undefined, undefined), JOBBFEL_ALLMANT);
  assert.deepEqual(jobbfel(null, "   "), JOBBFEL_ALLMANT);
  assert.deepEqual(jobbfel("", ""), JOBBFEL_ALLMANT);
});

test("en egen reserv används när koden är okänd", () => {
  const reserv = { sv: "Kunde inte skapa utkast.", en: "Could not create a draft." };
  assert.deepEqual(jobbfel(undefined, null, reserv), reserv);
  assert.deepEqual(jobbfel("okand", RA_SVENSKA, reserv), { sv: RA_SVENSKA, en: reserv.en });
});

test("prototypens namn räknas inte som koder", () => {
  assert.deepEqual(jobbfel("toString", RA_SVENSKA), { sv: RA_SVENSKA, en: JOBBFEL_ALLMANT.en });
  assert.equal(kundfelkod({ detail: { kod: "constructor" } }), null);
});

test("kundfelkod läser detail.kod ur ett felsvar", () => {
  assert.deepEqual(kundfelkod({ detail: { message: RA_SVENSKA, kod: "saknar_produkt" } }), KUNDFELKODER.saknar_produkt);
  assert.equal(kundfelkod({ detail: "text" }), null);
  assert.equal(kundfelkod(null), null);
});

test("JobbFel bär beskedet på båda språken", () => {
  const fel = new JobbFel(KUNDFELKODER.kvot);
  assert.ok(fel instanceof Error);
  assert.deepEqual(fel.besked, KUNDFELKODER.kvot);
});
