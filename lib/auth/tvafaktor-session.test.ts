/**
 * Adminrätten och sessionens andra steg. Kör: node --test lib/auth/tvafaktor-session.test.ts
 *
 * Två parallella sessioner för samma konto: den ena från före aktiveringen
 * (utan markering), den andra inloggad med kod. Bara den andra blir admin.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { sessionenUppfyllerTvafaktor } from "./tvafaktor-session.ts";

const ID = "6f1c2a7e-0000-4000-8000-0000000000aa";

test("konto med tvåfaktor: sessionen utan andra steget blir ingen admin", async () => {
  const harAktiv = async () => true;
  assert.equal(await sessionenUppfyllerTvafaktor(ID, false, harAktiv), false);
  assert.equal(await sessionenUppfyllerTvafaktor(ID, true, harAktiv), true);
});

test("konto utan tvåfaktor: sessionen duger utan markering", async () => {
  assert.equal(await sessionenUppfyllerTvafaktor(ID, false, async () => false), true);
});

test("markerad session frågar inte databasen", async () => {
  let fragor = 0;
  const harAktiv = async () => {
    fragor += 1;
    return true;
  };
  assert.equal(await sessionenUppfyllerTvafaktor(ID, true, harAktiv), true);
  assert.equal(fragor, 0);
});

test("uppslagsfel stänger (fail closed)", async () => {
  const harAktiv = async (): Promise<boolean> => {
    throw new Error("databasen svarar inte");
  };
  assert.equal(await sessionenUppfyllerTvafaktor(ID, false, harAktiv), false);
});
