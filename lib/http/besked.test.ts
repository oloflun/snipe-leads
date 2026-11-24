import assert from "node:assert/strict";
import { test } from "node:test";
import { kroppsbesked } from "./besked.ts";

test("en textdetalj visas som den är", () => {
  assert.equal(kroppsbesked({ detail: "Timtaket är nått." }), "Timtaket är nått.");
});

test("pydantics lista blir aldrig [object Object]", () => {
  const kropp = {
    detail: [{ type: "string_too_long", loc: ["body", "articles", 0, "content"], msg: "String should have at most 8000 characters" }]
  };
  const besked = kroppsbesked(kropp);
  assert.equal(typeof besked, "string");
  assert.doesNotMatch(besked ?? "", /object Object/);
  // Pydantics engelska utvecklartext visas inte för kunden.
  assert.doesNotMatch(besked ?? "", /String should have/);
});

test("proxyns läsbara error vinner över en lista", () => {
  const kropp = { detail: [{ msg: "x" }], error: "Uppgifterna gick inte att läsa." };
  assert.equal(kroppsbesked(kropp), "Uppgifterna gick inte att läsa.");
});

test("detail som objekt med message", () => {
  assert.equal(kroppsbesked({ detail: { message: "Leadet saknar adress.", saknas: ["e-post"] } }), "Leadet saknar adress.");
});

test("bara error", () => {
  assert.equal(kroppsbesked({ error: "Du måste vara inloggad." }), "Du måste vara inloggad.");
});

test("inget besked ger null, så att anroparens egen text används", () => {
  assert.equal(kroppsbesked(null), null);
  assert.equal(kroppsbesked({}), null);
  assert.equal(kroppsbesked({ detail: "" }), null);
  assert.equal(kroppsbesked("fel"), null);
});
