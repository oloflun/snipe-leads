/**
 * Supportportalens nyckelval. Kör: node --test "lib/*.test.ts"
 *
 * Fas 0-fyndet H13 (2026-11-09): en kund vars session gått ut, eller vars
 * kaka pekade på en backend som inte längre är tillåten, föll tyst tillbaka
 * på miljöns delade nyckel och arbetade då i en annan kunds data utan att
 * veta om det. Utan inloggningsvägg gav samma reserv hela internet den
 * delade kundens data.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { valjNyckel } from "../support-webb/lib/proxynyckel.ts";

const NU = 1_800_000_000_000;
const TOLV_TIMMAR = 12 * 60 * 60 * 1000;
const kund = { apiKey: "sk_kundens", backendUrl: "https://api.example", utfardad: NU - 1000 };
const grund = {
  nu: NU,
  maxAlderMs: TOLV_TIMMAR,
  tillatna: ["https://api.example"],
  vaggPa: true,
  produktion: true
};

test("en giltig kundsession ger kundens egen nyckel och backend", () => {
  assert.deepEqual(valjNyckel({ ...grund, harKundkaka: true, kund }), {
    slag: "kund",
    nyckel: "sk_kundens",
    bas: "https://api.example"
  });
});

test("en kundsession som gått ut får aldrig den delade nyckeln", () => {
  const gammal = { ...kund, utfardad: NU - TOLV_TIMMAR - 1 };
  assert.deepEqual(valjNyckel({ ...grund, harKundkaka: true, kund: gammal }), {
    slag: "avvisad",
    skal: "kundsession"
  });
});

test("en kundkaka som inte går att läsa får aldrig den delade nyckeln", () => {
  assert.deepEqual(valjNyckel({ ...grund, harKundkaka: true, kund: null }), {
    slag: "avvisad",
    skal: "kundsession"
  });
});

test("en kundsession mot en backend som inte är tillåten avvisas", () => {
  const annan = { ...kund, backendUrl: "https://annan.example" };
  assert.deepEqual(valjNyckel({ ...grund, harKundkaka: true, kund: annan }), {
    slag: "avvisad",
    skal: "kundsession"
  });
});

test("utan kundkaka, bakom inloggningsväggen: den delade nyckeln", () => {
  assert.deepEqual(valjNyckel({ ...grund, harKundkaka: false, kund: null }), { slag: "delad" });
});

test("utan kundkaka och utan vägg i en driftsatt miljö: ingen nyckel alls", () => {
  assert.deepEqual(valjNyckel({ ...grund, vaggPa: false, harKundkaka: false, kund: null }), {
    slag: "avvisad",
    skal: "oppen"
  });
});

test("lokal utveckling utan vägg får den delade nyckeln som förut", () => {
  assert.deepEqual(
    valjNyckel({ ...grund, vaggPa: false, produktion: false, harKundkaka: false, kund: null }),
    { slag: "delad" }
  );
});
