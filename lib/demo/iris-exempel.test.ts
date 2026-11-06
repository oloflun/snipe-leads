/**
 * De sex exempelbolagens handskrivna utkast och åtgärdssvar.
 * Kör: node --test "lib/demo/*.test.ts"
 *
 * Bugghistorien (2026-09-18, /demo/leads): mallgenererad text med gemen
 * begynnelsebokstav mitt i mejlet, ett em-dash-tungt AI-röstläge, och
 * knappar vars svar var näst intill identiska. Testerna nedan är den
 * kontrollen, körd över ALLA sex bolag × ALLA åtta åtgärder.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { halsning } from "../agent/halsning.ts";
import { arStrukturB } from "../leads/struktur.ts";
import {
  EXEMPELBOLAG,
  EXEMPEL_ACTIONS,
  exempelOmgang,
  exempelVariant,
  finnExempelbolag,
  forvantadHalsning,
  kontaktnamn,
  medStruktur
} from "./iris-exempel.ts";

/** Varje icke-tom rad ska inledas med versal (eller vara en siffra/citat) — aldrig gemen. */
function raderMedGemenStart(text: string): string[] {
  return text
    .split("\n")
    .map((rad) => rad.trim())
    .filter(Boolean)
    .filter((rad) => !/^[A-ZÅÄÖ0-9"'(]/.test(rad));
}

test("det finns sex exempelbolag att mäta", () => {
  assert.equal(EXEMPELBOLAG.length, 6);
});

for (const bolag of EXEMPELBOLAG) {
  test(`${bolag.companyName}: hälsar på kontaktens förnamn, inte rollen`, () => {
    const forvantat = `Hej ${bolag.contactFirstName},`;
    assert.equal(halsning(kontaktnamn(bolag)), forvantat);
    assert.equal(forvantadHalsning(bolag), forvantat);
    // Basutkastet ska faktiskt inledas med den hälsningen.
    assert.ok(
      bolag.draft.body.startsWith(forvantat),
      `${bolag.companyName}: basutkastet inleds inte med "${forvantat}"`
    );
  });

  test(`${bolag.companyName}: basutkastet har ingen gemen radstart och inget em-dash`, () => {
    assert.deepEqual(raderMedGemenStart(bolag.draft.body), []);
    assert.ok(!bolag.draft.body.includes("—"), "basutkastet innehåller ett em-dash");
  });

  for (const action of EXEMPEL_ACTIONS) {
    test(`${bolag.companyName} / ${action}: versal radstart, inget em-dash`, () => {
      const resultat = bolag.resultat[action];
      assert.deepEqual(raderMedGemenStart(resultat.new_version), []);
      assert.ok(!resultat.new_version.includes("—"), `${action}: new_version innehåller ett em-dash`);
      assert.ok(!resultat.explanation.includes("—"), `${action}: explanation innehåller ett em-dash`);
      for (const forslag of resultat.subject_suggestions) {
        assert.ok(!forslag.includes("—"), `${action}: en ämnesrad innehåller ett em-dash`);
      }
    });
  }

  test(`${bolag.companyName}: samtliga åtta åtgärder skiljer sig åt`, () => {
    const svar = EXEMPEL_ACTIONS.map((a) => bolag.resultat[a].new_version);
    const unika = new Set(svar);
    assert.equal(unika.size, svar.length, "två åtgärder gav identisk text");
  });

  test(`${bolag.companyName}: shorter är verkligen kortare än basutkastet`, () => {
    assert.ok(bolag.resultat.shorter.new_version.length < bolag.draft.body.length);
  });

  test(`${bolag.companyName}: translate är skrivet på engelska`, () => {
    const text = bolag.resultat.translate.new_version.toLowerCase();
    assert.ok(text.includes("hi ") || text.startsWith("hi,"), "translate-svaret inleds inte på engelska");
    assert.ok(!/\boch\b|\bär\b|\bni\b/.test(text), "translate-svaret innehåller kvarglömd svenska");
  });

  test(`${bolag.companyName}: ab_variants ger två riktiga varianter`, () => {
    const text = bolag.resultat.ab_variants.new_version;
    assert.ok(text.includes("Variant A") && text.includes("Variant B"), "saknar två märkta varianter");
  });

  test(`${bolag.companyName}: analyze är en bedömning, inte en omskrivning`, () => {
    assert.equal(bolag.resultat.analyze.new_version, bolag.draft.body);
    assert.ok(bolag.resultat.analyze.explanation.length > 40, "analyze saknar en faktisk bedömning");
  });

  test(`${bolag.companyName}: har minst en källa`, () => {
    assert.ok(bolag.kallor.length >= 1, `${bolag.companyName} saknar källor`);
    for (const kalla of bolag.kallor) {
      assert.ok(kalla.label, `${bolag.companyName}: en källa saknar etikett`);
      assert.ok(kalla.url, `${bolag.companyName}: en källa saknar url`);
    }
  });

  test(`${bolag.companyName}: followup är ett fristående uppföljningsmejl`, () => {
    const text = bolag.resultat.followup.new_version;
    assert.ok(text.includes("förra veckan"), "followup refererar inte till ett tidigare mejl");
    assert.notEqual(text, bolag.draft.body);
  });
}

test("finnExempelbolag matchar på companyId", () => {
  const traff = finnExempelbolag({ companyId: "3" });
  assert.equal(traff?.companyName, "Hammarnäs Bygg Sverige AB");
});

test("finnExempelbolag matchar på bolagsnamn (skiftlägesokänsligt) om id saknas", () => {
  const traff = finnExempelbolag({ companyName: "almnäs fastighet ab" });
  assert.equal(traff?.id, "6");
});

test("finnExempelbolag returnerar undefined för ett okänt bolag (t.ex. marknadssidans E-Tech)", () => {
  assert.equal(finnExempelbolag({ companyName: "E-Tech" }), undefined);
  assert.equal(finnExempelbolag({}), undefined);
  assert.equal(finnExempelbolag(null), undefined);
});


// -- Fler körningar i demon (Sebbe 2026-10-29) --------------------------------

test("demons körning tar aldrig slut: varje omgång ger tre nya bolag", () => {
  const ids = new Set<string>();
  for (let omgang = 0; omgang < 12; omgang++) {
    const bolag = exempelOmgang(omgang);
    assert.equal(bolag.length, 3);
    for (const b of bolag) {
      assert.ok(!ids.has(b.id), `samma bolag två gånger: ${b.id}`);
      ids.add(b.id);
    }
  }
  assert.deepEqual(exempelOmgang(0), EXEMPELBOLAG.slice(0, 3));
});

test("en variant byter namn, ort och kontakt överallt, också i utkasten och svaren", () => {
  for (let n = 6; n < 30; n++) {
    const bas = EXEMPELBOLAG[n % EXEMPELBOLAG.length];
    const v = exempelVariant(bas, n);
    const allt = JSON.stringify(v);
    const stam = bas.companyName.split(" ")[0];
    assert.ok(!allt.includes(stam), `${v.id} bär kvar ${stam}`);
    assert.ok(!allt.includes(bas.contactLastName), `${v.id} bär kvar ${bas.contactLastName}`);
    assert.ok(v.draft.body.startsWith(`Hej ${v.contactFirstName},`), `${v.id}: ${v.draft.body.slice(0, 20)}`);
    assert.ok(!v.website.includes(stam.toLowerCase()));
    assert.equal(v.status, "new");
    // Email Studio-routen hittar samma variant ur id:t.
    assert.deepEqual(finnExempelbolag({ companyId: v.id }), v);
  }
});

// Struktur A/B (Sebbe 2026-11-07): de flesta exempelutkasten är B, några A,
// och båda formerna finns för varje bolag så att demons Kör Iris kan visa valet.
test("de flesta exempelbolagen visar struktur B, men inte alla", () => {
  const b = EXEMPELBOLAG.filter((x) => x.struktur === "b").length;
  assert.ok(b > EXEMPELBOLAG.length / 2, `bara ${b} av ${EXEMPELBOLAG.length} är B`);
  assert.ok(b < EXEMPELBOLAG.length, "inget bolag visar A");
});

for (const bolag of EXEMPELBOLAG) {
  test(`${bolag.companyName}: standardutkastet är utkast[struktur], och formen stämmer`, () => {
    assert.equal(bolag.draft, bolag.utkast[bolag.struktur]);
    assert.equal(arStrukturB(bolag.utkast.b.body), true, "B-utkastet känns inte igen som B");
    // A är det utförliga utkastet. (Demons A-utkast slutar med en fråga,
    // skrivna före B-regeln, så igenkänningen på text skiljer dem inte alltid
    // åt; längden gör det.)
    assert.ok(
      bolag.utkast.a.body.split(/\s+/).length > bolag.utkast.b.body.split(/\s+/).length + 15,
      "A-utkastet är inte tydligt längre än B-utkastet"
    );
    for (const u of [bolag.utkast.a, bolag.utkast.b]) {
      assert.ok(u.body.startsWith(`Hej ${bolag.contactFirstName},`));
      assert.deepEqual(raderMedGemenStart(u.body), []);
      assert.ok(!u.body.includes("—"));
    }
  });

  if (bolag.struktur === "b") {
    test(`${bolag.companyName}: åtgärderna som behåller strukturen svarar i B-form`, () => {
      for (const a of ["shorter", "rewrite", "improve", "personalize"] as const) {
        assert.equal(arStrukturB(bolag.resultat[a].new_version), true, `${a} svarar inte i B-form`);
      }
    });
  }
}

test("medStruktur byter utkastet men inte bolaget", () => {
  const b = EXEMPELBOLAG.find((x) => x.struktur === "a")!;
  const som_b = medStruktur(b, "b");
  assert.equal(som_b.struktur, "b");
  assert.equal(som_b.draft, b.utkast.b);
  assert.equal(som_b.companyName, b.companyName);
  assert.equal(medStruktur(b, "a"), b);
  assert.equal(medStruktur(b, undefined), b);
});

test("exempelOmgang följer valet i Kör Iris", () => {
  for (const omgang of [0, 1, 2]) {
    assert.ok(exempelOmgang(omgang, "b").every((x) => arStrukturB(x.draft.body)));
    assert.ok(exempelOmgang(omgang, "a").every((x) => x.struktur === "a" && x.draft === x.utkast.a));
  }
});
