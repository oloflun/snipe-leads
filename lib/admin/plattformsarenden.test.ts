/**
 * Felrapporterna i adminytan. Kör: node --test "lib/**\/*.test.ts"
 *
 * Det som avgör om plattformsadmin ser rätt sak först och om ett byte kan
 * skickas: sorteringen (öppna först, stängda sist), filterchipen och vad
 * varje åtgärd kräver innan backenden får den.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ATGARDER,
  STATUSAR,
  antalOppna,
  atgard,
  atgarderFor,
  passarFilter,
  sorteraArenden,
  statuskropp,
  validera,
  vantarPaKund,
  ersatt,
  synligaArenden,
  aktorNyckel,
  bildadress,
  lasBild,
  type Arendestatus
} from "./plattformsarenden.ts";

const rad = (id: string, status: Arendestatus, updated_at: string, created_at = "2026-11-20T08:00:00Z") => ({
  id,
  status,
  updated_at,
  created_at
});

test("öppna ärenden först, det som väntar på kunden sedan, stängda sist", () => {
  const sorterade = sorteraArenden([
    rad("stangd", "stangd", "2026-11-25T10:00:00Z"),
    rad("redo", "redo_att_testa", "2026-11-25T09:00:00Z"),
    rad("mottagen", "mottagen", "2026-11-24T09:00:00Z"),
    rad("ute", "i_main", "2026-11-25T11:00:00Z"),
    rad("rattning", "rattning_pagar", "2026-11-25T08:00:00Z"),
    rad("fraga", "behover_mer", "2026-11-23T08:00:00Z")
  ]).map((x) => x.id);
  assert.deepEqual(sorterade, ["rattning", "mottagen", "redo", "fraga", "ute", "stangd"]);
});

test("sorteringen rör inte indata", () => {
  const indata = [rad("a", "stangd", "2026-11-25T10:00:00Z"), rad("b", "mottagen", "2026-11-24T10:00:00Z")];
  sorteraArenden(indata);
  assert.deepEqual(indata.map((x) => x.id), ["a", "b"]);
});

test("vantar_pa_kund är sant för behover_mer och redo_att_testa, inget annat", () => {
  const sanna = STATUSAR.filter(vantarPaKund);
  assert.deepEqual([...sanna].sort(), ["behover_mer", "redo_att_testa"]);
});

test("filtret Öppna döljer stängda och utsläppta, Alla visar allt", () => {
  assert.equal(passarFilter("stangd", "oppna"), false);
  assert.equal(passarFilter("i_main", "oppna"), false);
  assert.equal(passarFilter("kund_godkand", "oppna"), true);
  assert.equal(passarFilter("behover_mer", "hos_kunden"), true);
  assert.equal(passarFilter("behover_mer", "hos_oss"), false);
  for (const s of STATUSAR) assert.equal(passarFilter(s, "alla"), true);
  assert.equal(antalOppna([{ status: "mottagen" }, { status: "stangd" }, { status: "i_main" }, { status: "behover_mer" }]), 2);
});

test("Fråga kunden och Stäng kräver meddelande, Redo att testa kräver adress", () => {
  const krav = Object.fromEntries(ATGARDER.map((x) => [x.id, [x.kraverMeddelande, x.kraverAdress]]));
  assert.deepEqual(krav, {
    undersok: [false, false],
    rattning: [false, false],
    redo: [false, true],
    fraga: [true, false],
    stang: [true, false],
    development: [false, false],
    ute: [false, false]
  });
  assert.equal(atgard("fraga").status, "behover_mer");
  assert.equal(atgard("stang").status, "stangd");
  assert.equal(atgard("ute").status, "i_main");
});

test("validera säger varför ett byte inte får skickas", () => {
  assert.equal(validera(atgard("fraga"), "  ", ""), "meddelandeKravs");
  assert.equal(validera(atgard("stang"), "", ""), "meddelandeKravs");
  assert.equal(validera(atgard("stang"), "Inte ett fel: filtret var på.", ""), null);
  assert.equal(validera(atgard("redo"), "", ""), "adressKravs");
  assert.equal(validera(atgard("redo"), "", "forhand.snajp"), "adressOgiltig");
  assert.equal(validera(atgard("redo"), "", "javascript:alert(1)"), "adressOgiltig");
  assert.equal(validera(atgard("redo"), "", "http://forhand.example"), "adressOgiltig");
  assert.equal(validera(atgard("redo"), "", "https://forhand.example/arende"), null);
  assert.equal(validera(atgard("undersok"), "", ""), null);
});

test("statuskroppen: tomt meddelande blir null, adressen följer bara Redo att testa", () => {
  assert.deepEqual(statuskropp(atgard("undersok"), "   ", "https://x.example"), {
    status: "undersoks",
    meddelande_till_kund: null,
    testversion_url: null
  });
  assert.deepEqual(statuskropp(atgard("redo"), " Prova nu. ", " https://forhand.example "), {
    status: "redo_att_testa",
    meddelande_till_kund: "Prova nu.",
    testversion_url: "https://forhand.example"
  });
});

test("en öppnad rad erbjuder alla byten utom det läge ärendet står i", () => {
  const ids = atgarderFor("rattning_pagar").map((x) => x.id);
  assert.ok(!ids.includes("rattning"));
  assert.equal(ids.length, ATGARDER.length - 1);
  assert.equal(atgarderFor("kund_godkand").length, ATGARDER.length);
});

test("en nyss ändrad rad står kvar fast det nya läget inte passar filtret", () => {
  const lista = [rad("stangd", "stangd", "2026-11-25T10:00:00Z"), rad("oppen", "mottagen", "2026-11-25T09:00:00Z")];
  assert.deepEqual(synligaArenden(lista, "oppna", new Set()).map((x) => x.id), ["oppen"]);
  assert.deepEqual(synligaArenden(lista, "oppna", new Set(["stangd"])).map((x) => x.id), ["oppen", "stangd"]);
  assert.deepEqual(synligaArenden(lista, "klara", new Set(["stangd"])).map((x) => x.id), ["stangd"]);
});

test("aktorn admin:<id> slås upp som admin, övriga som de är", () => {
  assert.equal(aktorNyckel("admin:11111111-2222-4333-8444-555555555555"), "admin");
  assert.equal(aktorNyckel("kund"), "kund");
  assert.equal(aktorNyckel("plattformsadmin"), "plattformsadmin");
});

test("ersatt byter bara ärendet med samma id", () => {
  const lista = [{ id: "a", v: 1 }, { id: "b", v: 1 }];
  assert.deepEqual(ersatt(lista, { id: "b", v: 2 }), [{ id: "a", v: 1 }, { id: "b", v: 2 }]);
});

test("bilden hämtas per ärende och bara i de fyra formaten inlämningen tillåter", () => {
  assert.equal(
    bildadress("00000000-0000-4000-a000-0000000000f1"),
    "/api/admin/plattformsarenden/00000000-0000-4000-a000-0000000000f1/bild"
  );
  assert.equal(bildadress("a/b"), "/api/admin/plattformsarenden/a%2Fb/bild");
  for (const typ of ["png", "jpeg", "webp", "gif"]) {
    assert.equal(lasBild({ bild: `data:image/${typ};base64,iVBORw0KGgo=` }), `data:image/${typ};base64,iVBORw0KGgo=`);
  }
  assert.equal(lasBild({ bild: "data:image/svg+xml;base64,PHN2Zz4=" }), null);
  assert.equal(lasBild({ bild: "data:image/svg+xml;utf8,<svg onload=alert(1)>" }), null);
  assert.equal(lasBild({ bild: "data:text/html;base64,PGI+" }), null);
  assert.equal(lasBild({ bild: "javascript:alert(1)" }), null);
  assert.equal(lasBild({ bild: 42 }), null);
  assert.equal(lasBild({}), null);
  assert.equal(lasBild(null), null);
});
