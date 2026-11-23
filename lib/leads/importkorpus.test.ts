/**
 * Hårdtestet av listimporten: varje exportfil i fixtures/crm-export körs genom
 * hela kedjan (filläsare, rubrikrad, kolumnmatchning, radbyggare) och jämförs
 * med manifestets facit. Kör: node --test "lib/**\/*.test.ts"
 *
 * Filerna är syntetiska. Manifestets `sakerhet` säger hur väl rubrikerna är
 * belagda: de flesta är `trolig` eller `osaker` (ur minnet, inte ur en riktig
 * export). En riktig exportfil som faller igenom läggs hit som ny fixtur.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { lasImportfil } from "./importfil.ts";
import { gissaKolumner, tolkaTabell } from "./importmallar.ts";
import { tolkaRader } from "./importrader.ts";
import { tolkaWebb } from "./importvarden.ts";

type Post = {
  fil: string;
  rubrikrad: number;
  forvantad: Record<string, string | [string, string]>;
  forsta_rad: Record<string, string>;
};

const mapp = new URL("./fixtures/crm-export/", import.meta.url);
const manifest = JSON.parse(readFileSync(new URL("manifest.json", mapp), "utf-8")) as Post[];

const siffror = (s: string | undefined) => (s ?? "").replace(/\D/g, "").slice(-8);

test("korpus: varje fil ger samma rader i Windows-1252, UTF-16, med BOM och med CRLF", async () => {
  for (const post of manifest) {
    const text = readFileSync(new URL(post.fil, mapp), "utf-8");
    const facit = (await lasImportfil(Buffer.from(text, "utf-8"))).blad[0].rader;
    const varianter: [string, Buffer][] = [
      ["utf-8 med BOM", Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(text, "utf-8")])],
      ["utf-16le med BOM", Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(text, "utf16le")])],
      ["utf-16le utan BOM", Buffer.from(text, "utf16le")],
      ["crlf", Buffer.from(text.replace(/\n/g, "\r\n"), "utf-8")]
    ];
    // Bara filer vars alla tecken finns i Windows-1252 går att spara så.
    if ([...text].every((tecken) => tecken.charCodeAt(0) < 256)) varianter.push(["windows-1252", Buffer.from(text, "latin1")]);
    for (const [namn, bytes] of varianter) {
      const fick = (await lasImportfil(bytes)).blad[0].rader;
      // Radbrytningar inne i celler normaliseras till \n i alla varianter.
      assert.deepEqual(fick, facit, `${post.fil} som ${namn}`);
    }
  }
});

for (const post of manifest) {
  test(`korpus: ${post.fil}`, async () => {
    const fil = await lasImportfil(readFileSync(new URL(post.fil, mapp)));
    const tabell = tolkaTabell(fil.blad[0].rader);
    const val = gissaKolumner(tabell);
    const karta = tabell.rubriker.map((r, i) => `${r}=${val[i]}`).join(" | ");

    /** Finns en kolumn med den rubriken som blev det valet? */
    const blev = (rubrik: string, mal: string) =>
      tabell.rubriker.some((r, i) => (r === rubrik || r.replace(/ \(\d+\)$/, "") === rubrik) && val[i] === mal);

    for (const [falt, rubrik] of Object.entries(post.forvantad)) {
      if (Array.isArray(rubrik)) {
        assert.ok(blev(rubrik[0], "fornamn") && blev(rubrik[1], "efternamn"), `${falt}: ${rubrik.join(" + ")} ska vara för- och efternamn. ${karta}`);
      } else if (falt === "status") {
        // Status har inget eget fält: kolumnen följer med som extra uppgift.
        assert.ok(blev(rubrik, "extra"), `status: ${rubrik} ska följa med som extra. ${karta}`);
      } else {
        assert.ok(blev(rubrik, falt), `${falt}: ${rubrik} ska vara ${falt}. ${karta}`);
      }
    }

    const forsta = tolkaRader(tabell, val).find((u) => u.rad)?.rad;
    assert.ok(forsta, "filen ska ge minst en rad");
    for (const [falt, vantat] of Object.entries(post.forsta_rad)) {
      if (falt === "status") continue;
      const fick = (forsta as Record<string, unknown>)[falt] as string | undefined;
      if (falt === "orgnr" || falt === "contact_phone") assert.equal(siffror(fick), siffror(vantat), `${falt}: ${fick} mot ${vantat}`);
      else if (falt === "website") assert.equal(fick, tolkaWebb(vantat).varde, `website: ${fick} mot ${vantat}`);
      else if (falt === "contact_email") assert.equal(fick?.toLowerCase(), vantat.toLowerCase());
      else assert.equal(fick, vantat, falt);
    }
  });
}
