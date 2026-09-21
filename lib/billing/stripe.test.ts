/**
 * Stripe-klientens säkerhetsbärande delar. Kör: node --test "lib/**\/*.test.ts"
 *
 * Signaturkontrollen är webhookens enda autentisering — faller den öppen kan
 * vem som helst posta "betalning genomförd" och ge sig själv ett paket. Därför
 * prövas varje sätt den ska säga nej på, inte bara att den säger ja.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { formkoda, paketForPris, prisForPaket, verifieraSignatur } from "./stripe.ts";

const HEMLIGHET = "whsec_test_hemlighet";
const NU = 1_800_000_000;
const KROPP = '{"id":"evt_1","type":"checkout.session.completed"}';

function signera(kropp: string, tid: number, hemlighet = HEMLIGHET): string {
  const sig = createHmac("sha256", hemlighet).update(`${tid}.${kropp}`, "utf8").digest("hex");
  return `t=${tid},v1=${sig}`;
}

test("en korrekt signerad händelse godkänns", () => {
  const svar = verifieraSignatur(KROPP, signera(KROPP, NU), { hemligheten: HEMLIGHET, nu: NU });
  assert.deepEqual(svar, { giltig: true });
});

test("en ändrad kropp fälls — signaturen gäller exakta bytes", () => {
  const huvud = signera(KROPP, NU);
  const svar = verifieraSignatur(KROPP.replace("evt_1", "evt_2"), huvud, { hemligheten: HEMLIGHET, nu: NU });
  assert.equal(svar.giltig, false);
});

test("fel hemlighet fälls", () => {
  const huvud = signera(KROPP, NU, "whsec_nagon_annans");
  assert.equal(verifieraSignatur(KROPP, huvud, { hemligheten: HEMLIGHET, nu: NU }).giltig, false);
});

test("en gammal händelse fälls (replayskydd)", () => {
  const huvud = signera(KROPP, NU - 301);
  const svar = verifieraSignatur(KROPP, huvud, { hemligheten: HEMLIGHET, nu: NU });
  assert.equal(svar.giltig, false);
  assert.match(svar.orsak ?? "", /gammal/);
});

test("saknat huvud, trasigt huvud och saknad hemlighet fälls alla", () => {
  assert.equal(verifieraSignatur(KROPP, null, { hemligheten: HEMLIGHET, nu: NU }).giltig, false);
  assert.equal(verifieraSignatur(KROPP, "skrap", { hemligheten: HEMLIGHET, nu: NU }).giltig, false);
  assert.equal(verifieraSignatur(KROPP, signera(KROPP, NU), { hemligheten: "", nu: NU }).giltig, false);
});

test("en av flera v1-signaturer räcker (nyckelrotation)", () => {
  const ratt = signera(KROPP, NU).split("v1=")[1];
  const huvud = `t=${NU},v1=${"0".repeat(64)},v1=${ratt}`;
  assert.equal(verifieraSignatur(KROPP, huvud, { hemligheten: HEMLIGHET, nu: NU }).giltig, true);
});

test("formkodningen skriver nästlade fält och arrayer som Stripe vill ha dem", () => {
  const delar = formkoda({
    mode: "subscription",
    line_items: [{ price: "price_1", quantity: 1 }],
    metadata: { workspace_id: "w1" },
    ignoreras: undefined
  });
  assert.deepEqual(delar, [
    "mode=subscription",
    `${encodeURIComponent("line_items[0][price]")}=price_1`,
    `${encodeURIComponent("line_items[0][quantity]")}=1`,
    `${encodeURIComponent("metadata[workspace_id]")}=w1`
  ]);
});

test("pris och paket slås upp åt båda hållen, och okänt pris ger null", () => {
  process.env.STRIPE_PRICE_DUO = "price_duo_test";
  try {
    assert.equal(prisForPaket("duo"), "price_duo_test");
    assert.equal(paketForPris("price_duo_test"), "duo");
    assert.equal(paketForPris("price_okant"), null);
    assert.equal(paketForPris(null), null);
    // Ett paket utan satt pris får aldrig matcha ett tomt pris-id.
    assert.equal(paketForPris(""), null);
  } finally {
    delete process.env.STRIPE_PRICE_DUO;
  }
});
