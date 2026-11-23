/**
 * Listimportens värdetolkning. Kör: node --test "lib/**\/*.test.ts"
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { datumordning, tolkaDatum, tolkaEpost, tolkaOrgnr, tolkaTelefon, tolkaWebb } from "./importvarden.ts";

test("org.nr: bindestreck, sekelprefix och momsnummer blir samma nummer", () => {
  for (const v of ["569900-1219", "5699001219", "165699001219", "SE569900121901", " 569900 1219 "]) {
    assert.deepEqual(tolkaOrgnr(v), { varde: "569900-1219" }, v);
  }
});

test("org.nr: personnummer sparas inte, fel kontrollsiffra och Excel-tal anmärks", () => {
  assert.deepEqual(tolkaOrgnr("811218-9876"), { fel: "personnummer" });
  assert.deepEqual(tolkaOrgnr("19811218-9876"), { fel: "personnummer" });
  assert.deepEqual(tolkaOrgnr("569900-1218"), { fel: "orgnr" });
  assert.deepEqual(tolkaOrgnr("5,699E+09"), { fel: "excel" });
  assert.deepEqual(tolkaOrgnr("12345"), { fel: "orgnr" });
  // Utländska nummer (norskt org.nr, danskt CVR) står kvar som de skrevs.
  assert.deepEqual(tolkaOrgnr("923 609 016"), { varde: "923 609 016" });
  assert.deepEqual(tolkaOrgnr("saknas"), {});
  assert.deepEqual(tolkaOrgnr(""), {});
});

test("e-post: första giltiga adressen, utan namn, hakar och mailto", () => {
  assert.deepEqual(tolkaEpost("Eva Ek <eva.ek@example.se>"), { varde: "eva.ek@example.se" });
  assert.deepEqual(tolkaEpost("eva@example.se; per@example.se"), { varde: "eva@example.se" });
  assert.deepEqual(tolkaEpost('["eva@example.se","per@example.se"]'), { varde: "eva@example.se" });
  assert.deepEqual(tolkaEpost("mailto:eva@example.se"), { varde: "eva@example.se" });
  assert.deepEqual(tolkaEpost("eva@example"), { fel: "epost" });
  assert.deepEqual(tolkaEpost("eva(at)example.se"), { fel: "epost" });
  assert.deepEqual(tolkaEpost("noreply@example.se"), { fel: "epost" });
  assert.deepEqual(tolkaEpost("-"), {});
});

test("telefon: etiketter bort, tappad nolla tillbaka, landskod som +46", () => {
  assert.deepEqual(tolkaTelefon("070-174 06 05"), { varde: "070-174 06 05" });
  assert.deepEqual(tolkaTelefon("701740605"), { varde: "0701740605" });
  assert.deepEqual(tolkaTelefon("0046 70 174 06 05"), { varde: "+46701740605" });
  assert.deepEqual(tolkaTelefon("46701740605"), { varde: "+46701740605" });
  assert.deepEqual(tolkaTelefon("+46 (0)70-174 06 05"), { varde: "+46 70-174 06 05" });
  assert.deepEqual(tolkaTelefon("'+46 70 174 06 05"), { varde: "+46 70 174 06 05" });
  assert.deepEqual(tolkaTelefon("Mobil: 070-174 06 05 (direkt)"), { varde: "070-174 06 05" });
  assert.deepEqual(tolkaTelefon("08-465 004 01, 070-174 06 05"), { varde: "08-465 004 01" });
  assert.deepEqual(tolkaTelefon("08-465 004 01 / 070-174 06 05"), { varde: "08-465 004 01" });
  assert.deepEqual(tolkaTelefon("4,67017E+10"), { fel: "excel" });
  assert.deepEqual(tolkaTelefon("ring växeln"), { fel: "telefon" });
  assert.deepEqual(tolkaTelefon("n/a"), {});
});

test("webbplats: värdnamnet, aldrig en adress eller en profil", () => {
  assert.deepEqual(tolkaWebb("https://www.Bygg-Test.example.se/om-oss?x=1"), { varde: "bygg-test.example.se" });
  assert.deepEqual(tolkaWebb("bygg.example.se"), { varde: "bygg.example.se" });
  assert.deepEqual(tolkaWebb("skänninge-bygg.example.se"), { varde: "skänninge-bygg.example.se" });
  assert.deepEqual(tolkaWebb("eva@example.se"), { fel: "webb" });
  assert.deepEqual(tolkaWebb("https://www.linkedin.com/company/x"), { fel: "webb" });
  assert.deepEqual(tolkaWebb("ja"), { fel: "webb" });
  assert.deepEqual(tolkaWebb(""), {});
});

test("datum: alla format i korpusen blir ÅÅÅÅ-MM-DD", () => {
  const fall: [string, string][] = [
    ["2027-03-31", "2027-03-31"],
    ["2027-03-31 00:00:00", "2027-03-31"],
    ["2027-03-31T00:00:00Z", "2027-03-31"],
    ["2027/03/31", "2027-03-31"],
    ["20270331", "2027-03-31"],
    ["31/3/2027", "2027-03-31"],
    ["31.03.2027", "2027-03-31"],
    ["31-03-27", "2027-03-31"],
    ["3/31/2027", "2027-03-31"],
    ["31 mars 2027", "2027-03-31"],
    ["31 mar. 2027", "2027-03-31"],
    ["March 31, 2027", "2027-03-31"],
    ["31-Mar-27", "2027-03-31"],
    ["2027-03", "2027-03-31"],
    ["mars 2027", "2027-03-31"],
    ["2/2028", "2028-02-29"],
    ["46477", "2027-03-31"]
  ];
  for (const [ra, vantat] of fall) assert.deepEqual(tolkaDatum(ra), { varde: vantat }, ra);
});

test("datum: det som inte är ett datum anmärks", () => {
  for (const ra of ["31/2/2027", "24 mån", "löpande", "2027-13-01", "1850-01-01"]) assert.deepEqual(tolkaDatum(ra), { fel: "datum" }, ra);
  assert.deepEqual(tolkaDatum("tillsvidare"), { fel: "datum" });
  assert.deepEqual(tolkaDatum(""), {});
});

test("datum: tvetydiga datum följer kolumnens ordning", () => {
  assert.equal(datumordning(["1/2/2027", "25/3/2027"]), "dm");
  assert.equal(datumordning(["1/2/2027", "3/25/2027"]), "md");
  assert.equal(datumordning(["1/2/2027", "5/6/2027"]), "dm");
  assert.deepEqual(tolkaDatum("4/5/2027", "dm"), { varde: "2027-05-04" });
  assert.deepEqual(tolkaDatum("4/5/2027", "md"), { varde: "2027-04-05" });
});
