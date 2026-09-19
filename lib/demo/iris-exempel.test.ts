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
import {
  EXEMPELBOLAG,
  EXEMPEL_ACTIONS,
  finnExempelbolag,
  forvantadHalsning,
  kontaktnamn
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
