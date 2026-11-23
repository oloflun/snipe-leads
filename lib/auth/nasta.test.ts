import assert from "node:assert/strict";
import { test } from "node:test";
import { sakerNasta } from "./nasta.ts";

test("egna vägar släpps igenom", () => {
  assert.equal(sakerNasta("/dashboard/leads?vy=korningar"), "/dashboard/leads?vy=korningar");
  assert.equal(sakerNasta("/onboarding"), "/onboarding");
  assert.equal(sakerNasta("/settings/billing#plan"), "/settings/billing#plan");
});

test("en annan sajt blir startsidan", () => {
  for (const farlig of [
    "https://annan-sajt.se",
    "http://annan-sajt.se/login",
    "//annan-sajt.se",
    "/\\annan-sajt.se",
    "javascript:alert(1)",
    "annan-sajt.se",
    "/\n/annan-sajt.se",
    " //annan-sajt.se"
  ]) {
    assert.equal(sakerNasta(farlig), "/dashboard", farlig);
  }
});

test("saknat värde ger standarden", () => {
  assert.equal(sakerNasta(null), "/dashboard");
  assert.equal(sakerNasta(undefined), "/dashboard");
  assert.equal(sakerNasta(""), "/dashboard");
  assert.equal(sakerNasta("https://x.se", "/onboarding"), "/onboarding");
});
