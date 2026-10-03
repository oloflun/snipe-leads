/**
 * CSV-importens mallgissning. Kör: node --test "lib/**\/*.test.ts"
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseCsv } from "./csv.ts";
import { gissaKarta, radTillImportrad } from "./importmallar.ts";

test("Pipedrive-export känns igen och mappas", () => {
  const [rubriker, rad] = parseCsv(
    'Organization - Name,Person - Name,Person - Email,Organization - Website\n"Bygg AB, Väst",Anna,anna@bygg.se,bygg.se\n'
  );
  const { mall, karta } = gissaKarta(rubriker);
  assert.equal(mall, "pipedrive");
  assert.deepEqual(radTillImportrad(rad, karta), {
    company_name: "Bygg AB, Väst",
    contact_name: "Anna",
    contact_email: "anna@bygg.se",
    website: "bygg.se"
  });
});

test("Salesforce förnamn och efternamn slås ihop, okänd status utelämnas", () => {
  const [rubriker, rad] = parseCsv("Account Name;First Name;Last Name;Title;Status\nAcme;Eva;Ek;VD;Open\n");
  const { mall, karta, efternamn } = gissaKarta(rubriker);
  assert.equal(mall, "salesforce");
  assert.deepEqual(radTillImportrad(rad, karta, efternamn), {
    company_name: "Acme",
    contact_name: "Eva Ek",
    contact_role: "VD"
  });
});

test("rad utan bolagsnamn hoppas över", () => {
  const { karta } = gissaKarta(["Företag", "Kontakt"]);
  assert.equal(radTillImportrad(["", "Per"], karta), null);
});
