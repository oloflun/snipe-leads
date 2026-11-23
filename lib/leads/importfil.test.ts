/**
 * Listimportens filläsare: teckenkodningar, avgränsare och kalkylblad.
 * Kör: node --test "lib/**\/*.test.ts"
 *
 * Kalkylbladen i fixtures/kalkylblad är skrivna av två oberoende program
 * (XlsxWriter och LibreOffice), inte av läsaren själv: en läsare som bara
 * klarar sina egna filer bevisar ingenting.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gissaAvgransare, parseCsv } from "./csv.ts";
import { ImportFel, avkoda, excelDatum, lasImportfil } from "./importfil.ts";
import { gissaKolumner, tolkaTabell } from "./importmallar.ts";
import { tolkaRader } from "./importrader.ts";

const SV = "Företagsnamn;Org nr;Kontaktperson;Mobil;Mail\nÅkesson Test AB;569900-1219;Örjan Ek;070-174 06 05;orjan@example.se\n";
const VANTAT = [
  ["Företagsnamn", "Org nr", "Kontaktperson", "Mobil", "Mail"],
  ["Åkesson Test AB", "569900-1219", "Örjan Ek", "070-174 06 05", "orjan@example.se"]
];

const kalkylblad = (namn: string) => readFileSync(new URL(`./fixtures/kalkylblad/${namn}`, import.meta.url));
const rader = async (bytes: Uint8Array) => (await lasImportfil(bytes)).blad[0].rader;

async function felkod(bytes: Uint8Array): Promise<string> {
  try {
    await lasImportfil(bytes);
    return "ingen";
  } catch (fel) {
    return fel instanceof ImportFel ? fel.kod : "annat";
  }
}

test("UTF-8 med och utan BOM, CRLF och gamla Mac-radslut", async () => {
  assert.deepEqual(await rader(Buffer.from(SV, "utf-8")), VANTAT);
  assert.deepEqual(await rader(Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(SV, "utf-8")])), VANTAT);
  assert.deepEqual(await rader(Buffer.from(SV.replace(/\n/g, "\r\n"), "utf-8")), VANTAT);
  assert.deepEqual(await rader(Buffer.from(SV.replace(/\n/g, "\r"), "utf-8")), VANTAT);
});

test("Windows-1252: svensk Excels CSV (avgränsad) behåller å, ä och ö", async () => {
  const fil = await lasImportfil(Buffer.from(SV, "latin1"));
  assert.equal(fil.kodning, "windows-1252");
  assert.deepEqual(fil.blad[0].rader, VANTAT);
});

test("UTF-16 med BOM (Excels Unicode-text), åt båda hållen och utan BOM", async () => {
  const tab = SV.replace(/;/g, "\t");
  const le = Buffer.from(tab, "utf16le");
  assert.deepEqual(await rader(Buffer.concat([Buffer.from([0xff, 0xfe]), le])), VANTAT);
  assert.deepEqual(await rader(Buffer.concat([Buffer.from([0xfe, 0xff]), Buffer.from(le).swap16()])), VANTAT);
  assert.deepEqual(await rader(le), VANTAT);
});

test("Mac Roman: Excel för Mac skriver ö som 0x9A", () => {
  // "Företag;Örebro" i Mac Roman: ö = 0x9A, Ö = 0x85.
  const bytes = Uint8Array.from([0x46, 0x9a, 0x72, 0x65, 0x74, 0x61, 0x67, 0x3b, 0x85, 0x72, 0x65, 0x62, 0x72, 0x6f]);
  assert.deepEqual(avkoda(bytes), { text: "Företag;Örebro", kodning: "macintosh" });
});

test("sep=; på första raden styr avgränsaren och stryks", () => {
  assert.deepEqual(parseCsv(`sep=;\n${SV}`), VANTAT);
  assert.deepEqual(parseCsv("sep=,\r\nBolag,Ort\r\nAlfa Test AB,Umeå\r\n"), [
    ["Bolag", "Ort"],
    ["Alfa Test AB", "Umeå"]
  ]);
});

test("avgränsaren avgörs med citaten lästa", () => {
  assert.equal(gissaAvgransare('"Bolag, namn";"Kontakt, namn";"E-post"\n"Alfa Test AB";"Ek, Eva";"eva@example.se"\n'), ";");
  assert.equal(gissaAvgransare("Company|Email|Phone\nAlfa Test AB|eva@example.se|08-465 004 01\n"), "|");
  assert.equal(gissaAvgransare("Bolag\tAdress\nAlfa Test AB\tStorgatan 1, 2 tr; Umeå\n"), "\t");
  // En enda kolumn: kommat i bolagsnamnet får inte dela raden.
  assert.deepEqual(parseCsv("Bolag\nBygg AB, Väst\nAlfa Test AB\n"), [["Bolag"], ["Bygg AB, Väst"], ["Alfa Test AB"]]);
});

test("citat: radbrytning i fält, dubblerade citat och udda citattecken", () => {
  assert.deepEqual(parseCsv('Bolag,Adress,Not\n"Alfa ""Gruppen"" Test AB","Storgatan 1\nUmeå","a,b"\n'), [
    ["Bolag", "Adress", "Not"],
    ['Alfa "Gruppen" Test AB', "Storgatan 1\nUmeå", "a,b"]
  ]);
  // Ett citattecken mitt i ett fält är text och slukar inte resten av filen.
  assert.deepEqual(parseCsv('Bolag;Produkt\nBygg "Kalle" AB;5" skärm\nBeta Test AB;x\n'), [
    ["Bolag", "Produkt"],
    ['Bygg "Kalle" AB', '5" skärm'],
    ["Beta Test AB", "x"]
  ]);
  // Oescapade citat inne i ett citerat fält (trasig export).
  assert.deepEqual(parseCsv('Bolag,Ort\n"Bygg "Kalle" AB",Umeå\n'), [
    ["Bolag", "Ort"],
    ['Bygg "Kalle" AB', "Umeå"]
  ]);
});

test("xlsx från XlsxWriter: titelrad, tal, datumceller, flera blad, dolt blad", async () => {
  const fil = await lasImportfil(kalkylblad("xlsxwriter-kundlista.xlsx"));
  assert.equal(fil.format, "xlsx");
  assert.deepEqual(
    fil.blad.map((b) => b.namn),
    ["Kunder", "Anteckningar"]
  );
  const tabell = tolkaTabell(fil.blad[0].rader);
  assert.equal(tabell.rubrikrad, 1);
  assert.deepEqual(tabell.rubriker, ["Företag", "Org.nr", "Kontaktperson", "Mobil", "E-post", "Hemsida", "Avtalsslut", "Antal abonnemang", "Status"]);
  // Org.nr och mobilnummer är tal i filen: inget E+09, och nollan Excel tog
  // från mobilnumret kommer tillbaka i radbyggaren.
  assert.deepEqual(tabell.data[0], ["Alfa Akustik Test AB", "5699001219", "Eja Gran", "701740606", "eja.gran@example.se", "www.alfa-akustik.example.se", "2027-03-31", "12", "Kund"]);
  const [alfa, beta, gamma] = tolkaRader(tabell, gissaKolumner(tabell)).map((u) => u.rad);
  assert.deepEqual(alfa, {
    company_name: "Alfa Akustik Test AB",
    orgnr: "569900-1219",
    contact_name: "Eja Gran",
    contact_email: "eja.gran@example.se",
    contact_phone: "0701740606",
    website: "alfa-akustik.example.se",
    avtalsslut: "2027-03-31",
    extra: { "Antal abonnemang": "12", Status: "Kund" }
  });
  assert.equal(beta?.avtalsslut, "2026-12-31");
  assert.equal(beta?.company_name, "Beta Bygg & Montage Test AB");
  assert.equal(gamma?.company_name, 'Gamma "Gruppen" Test AB');
  assert.equal(gamma?.avtalsslut, "2027-06-30");
});

test("samma lista ur LibreOffice som xlsx, Excel 2003-XML och HTML ger samma rader som CSV-filen", async () => {
  const csv = tolkaTabell(await rader(readFileSync(new URL("./fixtures/crm-export/telekom-avtalsslut-iso.csv", import.meta.url))));
  const facit = tolkaRader(csv, gissaKolumner(csv)).map((u) => u.rad);
  assert.equal(facit.length > 3, true);
  for (const [namn, format] of [
    ["libreoffice-telekom.xlsx", "xlsx"],
    ["libreoffice-telekom.xml", "xml"],
    ["libreoffice-telekom.html", "html"]
  ] as const) {
    const fil = await lasImportfil(kalkylblad(namn));
    assert.equal(fil.format, format, namn);
    const tabell = tolkaTabell(fil.blad[0].rader);
    assert.deepEqual(tabell.rubriker, csv.rubriker, namn);
    assert.deepEqual(
      tolkaRader(tabell, gissaKolumner(tabell)).map((u) => u.rad),
      facit,
      namn
    );
  }
});

test("filer som inte går att läsa avvisas med en kod", async () => {
  assert.equal(await felkod(kalkylblad("libreoffice-telekom.xls")), "xls");
  assert.equal(await felkod(kalkylblad("libreoffice-telekom.ods")), "format");
  assert.equal(await felkod(Buffer.from("%PDF-1.7\n1 0 obj")), "format");
  assert.equal(await felkod(Buffer.from('<?xml version="1.0"?><rss></rss>')), "format");
  assert.equal(await felkod(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13])), "format");
  assert.equal(await felkod(Buffer.from("\n\n  \n")), "tom");
  assert.equal(await felkod(Buffer.from("PK\u0003\u0004trasig zip utan katalog")), "trasig");
});

test("Excels löpnummer blir datum, även i 1904-systemet", () => {
  assert.equal(excelDatum(46477), "2027-03-31");
  assert.equal(excelDatum(46477.5), "2027-03-31 12:00");
  assert.equal(excelDatum(45015, true), "2027-03-31");
});
