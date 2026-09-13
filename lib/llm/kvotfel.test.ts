/**
 * Felklassningen i Email Studio. Kör: node --test "lib/llm/*.test.ts"
 *
 * Feltexterna är Googles egna, ur samma uppmätta svar som
 * snajp-support/tests/test_kvotfel.py använder — de två testfilerna ska
 * klassa samma text likadant.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { arKreditslut, arKvotfel, kanForsokasOm, klassaModellfel } from "./kvotfel.ts";

/** Formen AI-SDK:ns APICallError har. */
function apiFel(statusCode: number, message: string, responseBody = "") {
  const e = new Error(message) as Error & { statusCode: number; responseBody: string; isRetryable: boolean };
  e.name = "AI_APICallError";
  e.statusCode = statusCode;
  e.responseBody = responseBody;
  e.isRetryable = statusCode === 429 || statusCode >= 500;
  return e;
}

const KREDITSLUT_429 = apiFel(
  429,
  "Your prepayment credits are depleted. Please go to AI Studio at https://ai.studio/projects to manage your project and billing. Learn more at https://ai.google.dev/gemini-api/docs/billing#prepay."
);
const VANLIG_KVOT_429 = apiFel(429, "You exceeded your current quota, please check your plan and billing details.");
const VERTEX_UTAN_FAKTURERING = apiFel(
  403,
  "Permission denied",
  '{"error":{"code":403,"message":"This API method requires billing to be enabled. Please enable billing on project #123 then retry.","status":"PERMISSION_DENIED","details":[{"reason":"BILLING_DISABLED"}]}}'
);
const VERTEX_RESURS_SLUT = apiFel(429, "Resource exhausted. Please try again later.", '{"error":{"code":429,"status":"RESOURCE_EXHAUSTED"}}');

test("kreditslut klassas som kreditslut, inte som vanlig kvot", () => {
  assert.equal(klassaModellfel(KREDITSLUT_429), "kreditslut");
  assert.equal(arKvotfel(KREDITSLUT_429), true, "det ÄR ett 429 — därför prövas kreditslut först");
});

test("Vertex utan fakturering (403 BILLING_DISABLED) är kreditslut", () => {
  assert.equal(klassaModellfel(VERTEX_UTAN_FAKTURERING), "kreditslut");
});

test("Googles vanliga kvottext nämner 'billing' men är INTE kreditslut", () => {
  assert.equal(arKreditslut(VANLIG_KVOT_429), false);
  assert.equal(klassaModellfel(VANLIG_KVOT_429), "kvot");
  assert.equal(klassaModellfel(VERTEX_RESURS_SLUT), "kvot");
});

test("Vertex: stängt faktureringskonto, avstängt projekt och utgiftstak är kreditslut", () => {
  assert.equal(klassaModellfel(apiFel(403, "The billing account for the owning project is disabled in state closed")), "kreditslut");
  assert.equal(klassaModellfel(apiFel(403, "Permission denied", '{"error":{"details":[{"reason":"CONSUMER_SUSPENDED"}]}}')), "kreditslut");
  assert.equal(klassaModellfel(apiFel(429, "Your project has exceeded its monthly spending cap.")), "kreditslut");
});

test("orsakskedjan följs: ett omslaget kreditslut är fortfarande kreditslut", () => {
  const omslaget = new Error("Failed after 3 attempts", { cause: VERTEX_UTAN_FAKTURERING });
  assert.equal(klassaModellfel(omslaget), "kreditslut");
  assert.equal(kanForsokasOm(omslaget), false);
  const omslagenKvot = new Error("wrapper", { cause: VANLIG_KVOT_429 });
  assert.equal(klassaModellfel(omslagenKvot), "kvot");
});

test("en cyklisk orsakskedja hänger inte klassningen", () => {
  const a = new Error("a") as Error & { cause?: unknown };
  const b = new Error("b", { cause: a });
  a.cause = b;
  assert.equal(klassaModellfel(a), "tillfälligt fel");
});

test("text: RESOURCE_EXHAUSTED räknas bara bredvid en 429 (som i kvotfel.py)", () => {
  assert.equal(arKvotfel("429 Resource exhausted. Please try again later."), true);
  assert.equal(arKvotfel("resource_exhausted"), false);
});

test("lagrad feltext utan statuskod klassas också", () => {
  assert.equal(arKreditslut("Error code: 429 - Your prepayment credits are depleted"), true);
  assert.equal(klassaModellfel("Error code: 429 - [{'error': {'message': 'You exceeded your current quota'}}]"), "kvot");
});

test("ett belopp är inte en statuskod", () => {
  assert.equal(arKvotfel(new Error("429 kr exklusive moms")), false);
  assert.equal(klassaModellfel(new Error("429 kr exklusive moms")), "tillfälligt fel");
});

test("övriga fel är tillfälliga", () => {
  assert.equal(klassaModellfel(apiFel(500, "Internal error")), "tillfälligt fel");
  assert.equal(klassaModellfel(new Error("fetch failed")), "tillfälligt fel");
  assert.equal(klassaModellfel(null), "tillfälligt fel");
});

test("omtag: aldrig vid kreditslut, ja vid kvot, 5xx och nätverksfel", () => {
  assert.equal(kanForsokasOm(KREDITSLUT_429), false, "tre anrop mot en tom kredit är tre avvisningar");
  assert.equal(kanForsokasOm(VERTEX_UTAN_FAKTURERING), false);
  assert.equal(kanForsokasOm(VANLIG_KVOT_429), true);
  assert.equal(kanForsokasOm(apiFel(503, "unavailable")), true);
  assert.equal(kanForsokasOm(new Error("fetch failed")), true);
  assert.equal(kanForsokasOm(apiFel(400, "bad request")), false);
});
