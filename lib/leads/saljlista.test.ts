/**
 * Säljlistans rena regler. Kör: node --test "lib/leads/*.test.ts"
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  byggSaljCsv,
  dagarSedan,
  dubblettnycklar,
  formateraOrgnr,
  normaliseraFalt,
  telefonlank,
  type Saljrad
} from "./saljlista.ts";

test("orgnr formateras med bindestreck, annat lämnas orört", () => {
  assert.equal(formateraOrgnr("5566778899"), "556677-8899");
  assert.equal(formateraOrgnr("556677 8899"), "556677-8899");
  assert.equal(formateraOrgnr("165566778899"), "16556677-8899");
  assert.equal(formateraOrgnr("okänt"), "okänt");
  assert.equal(formateraOrgnr("12345"), "12345");
});

test("normalisering: mejl, datum, längd och tomma värden", () => {
  assert.deepEqual(normaliseraFalt("kontaktmail", " vd@bolag.se "), { ok: true, varde: "vd@bolag.se" });
  assert.deepEqual(normaliseraFalt("kontaktmail", "inte-en-adress"), { ok: false, fel: "ogiltig_mejl" });
  assert.deepEqual(normaliseraFalt("kontaktmail", ""), { ok: true, varde: "" });
  assert.deepEqual(normaliseraFalt("senast_kontaktad", ""), { ok: true, varde: null });
  assert.deepEqual(normaliseraFalt("senast_kontaktad", "2026-10-06"), { ok: true, varde: "2026-10-06" });
  assert.deepEqual(normaliseraFalt("senast_kontaktad", "2026-02-30"), { ok: false, fel: "ogiltigt_datum" });
  assert.deepEqual(normaliseraFalt("foretagsnamn", "x".repeat(201)), { ok: false, fel: "for_lang" });
  assert.deepEqual(normaliseraFalt("foretagsnamn", "  Nordform   AB "), { ok: true, varde: "Nordform AB" });
  assert.deepEqual(normaliseraFalt("anteckningar", " rad 1\nrad 2 "), { ok: true, varde: "rad 1\nrad 2" });
});

test("telefonlänk tar bara siffror och plus", () => {
  assert.equal(telefonlank("070-123 45 67"), "tel:0701234567");
  assert.equal(telefonlank("+46 70 123 45 67"), "tel:+46701234567");
  assert.equal(telefonlank("—"), null);
});

test("dubbletter hittas på orgnr och på namn utan bolagsform", () => {
  const a = dubblettnycklar({ foretagsnamn: "Nordform AB", orgnr: "556677-8899" });
  const b = dubblettnycklar({ foretagsnamn: "Något annat", orgnr: "5566778899" });
  const c = dubblettnycklar({ foretagsnamn: "nordform", orgnr: "" });
  assert.ok(a.some((n) => b.includes(n)));
  assert.ok(a.some((n) => c.includes(n)));
  assert.deepEqual(dubblettnycklar({ foretagsnamn: "", orgnr: "" }), []);
});

test("dagar sedan räknas i hela dagar", () => {
  assert.equal(dagarSedan("2026-10-01", "2026-10-06"), 5);
  assert.equal(dagarSedan("2026-10-06", "2026-10-06"), 0);
  assert.equal(dagarSedan("trasigt", "2026-10-06"), null);
});

test("CSV har BOM, semikolon och citerar fält med radbrytning", () => {
  const rad: Saljrad = {
    id: "1",
    foretagsnamn: "Bolag; AB",
    orgnr: "556677-8899",
    kontaktperson: "Anna",
    kontaktnummer: "070",
    kontaktmail: "a@b.se",
    senast_kontaktad: null,
    anteckningar: "rad 1\nrad \"2\"",
    created_at: "",
    updated_at: ""
  };
  const csv = byggSaljCsv([rad], ["A", "B", "C", "D", "E", "F", "G"]);
  assert.ok(csv.startsWith("﻿A;B;C;D;E;F;G\r\n"));
  assert.ok(csv.includes('"Bolag; AB";556677-8899;Anna;070;a@b.se;;"rad 1\nrad ""2"""'));
});
