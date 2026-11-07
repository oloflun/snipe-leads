import { test } from "node:test";
import assert from "node:assert/strict";
import { arStrukturB } from "./struktur.ts";

test("ett B-mejl känns igen, med och utan hälsning och hälsningsfras", () => {
  assert.equal(
    arStrukturB(
      "Hej Ulf,\n\nOm vår agent Iris kunde ta fram 40–50 nya företag i veckan som passar er, med ett färdigt första mejl till varje, skulle det vara till nytta för dig?\n\nVänliga hälsningar,"
    ),
    true
  );
  assert.equal(
    arStrukturB(
      "Vår Supportagent finns just nu i en kostnadsfri pilot för 20 företag. Om den svarade på era kunders frågor, låter det som något för er?"
    ),
    true
  );
});

test("ett A-mejl är aldrig B", () => {
  assert.equal(
    arStrukturB(
      "Hej,\n\nAtt stödja internationella leverantörer tar tid och fokus. Iris, vår leadsagent, effektiviserar er prospektering.\n\nJust nu tar vi in 20 företag i en kostnadsfri pilot. Titta gärna på demon på snajp.se/demo.\n\nVänliga hälsningar,"
    ),
    false
  );
  assert.equal(arStrukturB(""), false);
});

test("ett långt mejl som råkar sluta med en fråga är inte B", () => {
  assert.equal(arStrukturB(`Hej,\n\n${"Ord ".repeat(80)}skulle det hjälpa?`), false);
});

test("signaturens namnrad räknas inte in i brödtexten", () => {
  assert.equal(
    arStrukturB("Hej Karin,\n\nOm vi monterade en hjärtstartare hos er innan sommaren, skulle det vara till nytta?\n\nVänliga hälsningar,\nAnna, Hjärtsäker AB"),
    true
  );
  assert.equal(arStrukturB("Hej Karin,\n\nVi hör av oss nästa vecka.\n\nVänliga hälsningar,\nAnna, Hjärtsäker AB"), false);
});
