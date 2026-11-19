/**
 * Inloggningens två steg: korrekt kod, fel kod, återställningskod, återspelning
 * och spärren som täcker andra steget. Kör: node --test lib/auth/inloggningssteg.test.ts
 *
 * Databasen ersätts av en minnesmodell med samma regler som migration 125
 * (5 misslyckade försök per adress spärrar) och 128 (ett tidssteg och en
 * återställningskod förbrukas en gång). TOTP och kryptot är de riktiga.
 * Funktionerna i databasen prövas för sig i snajp-support/tests/db/.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { loggaIn, type Beroenden } from "./inloggningssteg.ts";
import { nyTotpHemlighet, provaTotp, serUtSomTotp, totpKod } from "./totp.ts";
import {
  dekrypteraHemlighet,
  hashaAterstallningskod,
  krypteraHemlighet,
  nyaAterstallningskoder,
  serUtSomAterstallningskod
} from "./tvafaktor-krypto.ts";

const NYCKEL = "test-auth-secret-0123456789abcdef";
const ID = "6f1c2a7e-0000-4000-8000-0000000000aa";
const LOSENORD = "rätt-lösenord";
const TROSKEL = 5;

type Lage = { aktiv: boolean; hemlighet: string; senasteSteg: number | null };

/** Minnesmodellen av databasen för ett konto. */
function varld(opts: { tvafaktor: boolean }) {
  const hemlighet = nyTotpHemlighet();
  const koder = nyaAterstallningskoder(3);
  const s = {
    forsok: 0,
    sparrad: false,
    nollstallningar: 0,
    losenordProvat: 0,
    koderProvade: 0,
    lage: opts.tvafaktor
      ? ({ aktiv: true, hemlighet: krypteraHemlighet(hemlighet, ID, NYCKEL), senasteSteg: null } as Lage)
      : null,
    oanvanda: new Set(koder.map((k) => hashaAterstallningskod(k, NYCKEL)))
  };
  const b: Beroenden<Lage> = {
    arSparrad: async () => s.sparrad,
    hittaKonto: async () => ({ id: ID, losenordshash: "hash" }),
    provaLosenord: async () => {
      s.losenordProvat++;
      return aktuelltLosenord === LOSENORD;
    },
    registreraMisslyckat: async () => {
      s.forsok++;
      if (s.forsok >= TROSKEL) {
        s.sparrad = true;
        s.forsok = 0;
        return true;
      }
      return false;
    },
    nollstall: async () => {
      s.forsok = 0;
      s.nollstallningar++;
    },
    lasTvafaktor: async () => s.lage,
    // Samma väg som lib/auth/tvafaktor.ts:provaOchForbruka, mot minnet.
    provaKod: async (userId, lage, kod) => {
      s.koderProvade++;
      if (serUtSomTotp(kod)) {
        const klar = dekrypteraHemlighet(lage.hemlighet, userId, NYCKEL);
        if (!klar) return "fel";
        const steg = provaTotp(klar, kod, Date.now(), lage.senasteSteg);
        if (steg === null || !s.lage) return "fel";
        s.lage.senasteSteg = steg;
        return "ok";
      }
      if (serUtSomAterstallningskod(kod)) {
        return s.oanvanda.delete(hashaAterstallningskod(kod, NYCKEL)) ? "ok" : "fel";
      }
      return "fel";
    }
  };
  let aktuelltLosenord = LOSENORD;
  return {
    s,
    b,
    hemlighet,
    koder,
    medLosenord(l: string) {
      aktuelltLosenord = l;
    }
  };
}

test("utan tvåfaktor: rätt lösenord räcker, räknaren nollställs", async () => {
  const v = varld({ tvafaktor: false });
  const u = await loggaIn("", v.b);
  assert.equal(u.typ, "ok");
  assert.equal(u.typ === "ok" && u.tvafaktor, false, "sessionen markeras inte som tvåstegsverifierad");
  assert.equal(v.s.nollstallningar, 1);
});

test("med tvåfaktor: utan kod krävs andra steget, inget räknas eller nollställs", async () => {
  const v = varld({ tvafaktor: true });
  v.s.forsok = 3;
  assert.equal((await loggaIn("", v.b)).typ, "tvafaktor_kravs");
  assert.equal(v.s.forsok, 3, "inget nytt försök räknas");
  assert.equal(v.s.nollstallningar, 0, "räknaren nollställs inte av ett halvt steg");
});

test("korrekt kod loggar in och nollställer räknaren", async () => {
  const v = varld({ tvafaktor: true });
  v.s.forsok = 2;
  const u = await loggaIn(totpKod(v.hemlighet), v.b);
  assert.equal(u.typ, "ok");
  assert.equal(u.typ === "ok" && u.tvafaktor, true, "sessionen bär att andra steget gick igenom");
  assert.equal(v.s.forsok, 0);
});

test("fel kod vägras och räknas som ett misslyckat försök", async () => {
  const v = varld({ tvafaktor: true });
  const ratt = totpKod(v.hemlighet);
  const fel = String((Number(ratt) + 500_000) % 1_000_000).padStart(6, "0");
  assert.equal((await loggaIn(fel, v.b)).typ, "tvafaktor_fel");
  assert.equal(v.s.forsok, 1);
  assert.equal((await loggaIn("skräp", v.b)).typ, "tvafaktor_fel");
  assert.equal(v.s.forsok, 2);
});

test("samma kod två gånger: andra gången vägras (återspelning)", async () => {
  const v = varld({ tvafaktor: true });
  const kod = totpKod(v.hemlighet);
  assert.equal((await loggaIn(kod, v.b)).typ, "ok");
  assert.equal((await loggaIn(kod, v.b)).typ, "tvafaktor_fel");
});

test("återställningskod loggar in en gång, sedan inte igen", async () => {
  const v = varld({ tvafaktor: true });
  const [kod] = v.koder;
  assert.equal((await loggaIn(kod.toLowerCase(), v.b)).typ, "ok");
  assert.equal((await loggaIn(kod, v.b)).typ, "tvafaktor_fel");
  assert.equal((await loggaIn(v.koder[1], v.b)).typ, "ok", "nästa kod fungerar");
});

test("spärren täcker andra steget: fem fel koder spärrar, och sedan prövas ingenting", async () => {
  const v = varld({ tvafaktor: true });
  const ratt = totpKod(v.hemlighet);
  const fel = String((Number(ratt) + 500_000) % 1_000_000).padStart(6, "0");
  for (let i = 0; i < TROSKEL - 1; i++) {
    assert.equal((await loggaIn(fel, v.b)).typ, "tvafaktor_fel");
  }
  assert.equal((await loggaIn(fel, v.b)).typ, "sparrad", "femte fel koden utlöser spärren");

  const losenord = v.s.losenordProvat;
  const koder = v.s.koderProvade;
  // Spärrad: också den RÄTTA koden vägras, och varken lösenord eller kod prövas.
  assert.equal((await loggaIn(ratt, v.b)).typ, "sparrad");
  assert.equal(v.s.losenordProvat, losenord);
  assert.equal(v.s.koderProvade, koder);
});

test("fel lösenord och fel kod räknas i samma räknare", async () => {
  const v = varld({ tvafaktor: true });
  v.medLosenord("fel");
  for (let i = 0; i < 3; i++) assert.equal((await loggaIn("", v.b)).typ, "fel");
  v.medLosenord(LOSENORD);
  const fel = String((Number(totpKod(v.hemlighet)) + 500_000) % 1_000_000).padStart(6, "0");
  assert.equal((await loggaIn(fel, v.b)).typ, "tvafaktor_fel");
  assert.equal((await loggaIn("abc", v.b)).typ, "sparrad", "3 lösenord + 2 koder = tröskeln");
});

test("fel lösenord ger aldrig andra steget (avslöjar inte att kontot har tvåfaktor)", async () => {
  const v = varld({ tvafaktor: true });
  v.medLosenord("fel");
  assert.equal((await loggaIn("", v.b)).typ, "fel");
  assert.equal((await loggaIn(totpKod(v.hemlighet), v.b)).typ, "fel");
  assert.equal(v.s.koderProvade, 0);
});
