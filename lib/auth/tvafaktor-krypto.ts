/**
 * Tvåstegsverifieringens krypto och återställningskoder (ISO 27001 A.8.5,
 * A.5.17; 2026-11-18). Ren logik utan databas, så att den går att testa med
 * `node --test lib/auth/tvafaktor-krypto.test.ts`. Lagringen:
 * `lib/auth/tvafaktor.ts` och migration 128.
 *
 * ## Nyckeln
 *
 * TOTP-hemligheten lagras krypterad med AES-256-GCM. Nyckeln härleds med HKDF
 * (SHA-256) ur `AUTH_SECRET` med ett eget info-värde per syfte, så att samma
 * hemlighet aldrig används direkt till två saker: sessionernas signatur
 * (Auth.js), spärrens HMAC-nycklar och de två nycklarna här är olika nycklar.
 *
 * Varför `AUTH_SECRET` och inte en annan befintlig nyckel: den finns bara på
 * tjänsten `web`, som är den enda som läser hemligheten, och den är redan
 * roten till inloggningens förtroende (en angripare med den kan förfalska
 * sessioner och behöver ingen tvåfaktor). `SNAJP_MASTER_API_KEY` finns också
 * på `api` och är en åtkomstnyckel, inte en krypteringsnyckel; `DATABASE_URL`
 * ligger bredvid datat den skulle skydda. Ingen ny Railway-variabel behövs.
 *
 * FÖLJD: byts `AUTH_SECRET` går de lagrade hemligheterna och
 * återställningskoderna inte längre att läsa eller pröva. Varje
 * plattformsadmin med tvåfaktor måste då rullas in på nytt (raden tas bort av
 * ägarrollen, se `AUTH.md`). Ett byte loggar dessutom ut alla, så det är redan
 * en planerad handling.
 *
 * Chiffertexten bär användarens id som AAD: en rad som flyttas till ett annat
 * konto går inte att dekryptera.
 */

import { createCipheriv, createDecipheriv, createHmac, hkdfSync, randomInt, randomBytes } from "node:crypto";

/**
 * Antonbeslut, inte agentens: ska plattformsadmin MÅSTE ha tvåfaktor?
 * `false` (standard): tvåfaktor är valfritt. `true`: en plattformsadmin utan
 * aktiv tvåfaktor förlorar adminrätten (`getPlatformAdmin()` svarar null) tills
 * inrullningen är gjord, och skickas efter inloggningen till inrullningen.
 */
export const TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN = false;

const INFO_HEMLIGHET = "snajp/tvafaktor/totp-hemlighet/v1";
const INFO_ATERSTALLNING = "snajp/tvafaktor/aterstallningskod/v1";
const SALT = "snajp-tvafaktor";
const VERSION = "v1";

function harled(authSecret: string | undefined, info: string): Buffer {
  if (!authSecret) {
    throw new Error("AUTH_SECRET saknas: tvåstegsverifieringens nyckel går inte att härleda.");
  }
  return Buffer.from(hkdfSync("sha256", authSecret, SALT, info, 32));
}

function aad(userId: string): Buffer {
  return Buffer.from(`tvafaktor:${userId}`, "utf8");
}

/** Krypterar TOTP-hemligheten. Format: `v1.<iv>.<tagg>.<chiffer>` (base64url). */
export function krypteraHemlighet(hemlighet: string, userId: string, authSecret: string | undefined): string {
  const iv = randomBytes(12);
  const chiffer = createCipheriv("aes-256-gcm", harled(authSecret, INFO_HEMLIGHET), iv);
  chiffer.setAAD(aad(userId));
  const data = Buffer.concat([chiffer.update(hemlighet, "utf8"), chiffer.final()]);
  const tagg = chiffer.getAuthTag();
  return [VERSION, iv.toString("base64url"), tagg.toString("base64url"), data.toString("base64url")].join(".");
}

/**
 * Dekrypterar. Fel nyckel (bytt `AUTH_SECRET`), fel användare eller en
 * ändrad rad ger null, aldrig ett undantag: anroparen behandlar det som att
 * hemligheten inte går att använda.
 */
export function dekrypteraHemlighet(
  blob: string,
  userId: string,
  authSecret: string | undefined
): string | null {
  const delar = blob.split(".");
  if (delar.length !== 4 || delar[0] !== VERSION) return null;
  try {
    const [, iv, tagg, data] = delar;
    const dechiffer = createDecipheriv("aes-256-gcm", harled(authSecret, INFO_HEMLIGHET), Buffer.from(iv, "base64url"));
    dechiffer.setAAD(aad(userId));
    dechiffer.setAuthTag(Buffer.from(tagg, "base64url"));
    return Buffer.concat([dechiffer.update(Buffer.from(data, "base64url")), dechiffer.final()]).toString("utf8");
  } catch {
    return null;
  }
}

/* ------------------------------------------------- Återställningskoder */

/** Inga tecken som går att förväxla (0/O, 1/I/L). 31 tecken, 10 per kod: cirka 50 bitar. */
const KODTECKEN = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const KODLANGD = 10;
export const ANTAL_ATERSTALLNINGSKODER = 10;

/** Nya engångskoder, formaterade `ABCDE-FGHJK`. Visas en gång; bara hashen lagras. */
export function nyaAterstallningskoder(antal = ANTAL_ATERSTALLNINGSKODER): string[] {
  const koder = new Set<string>();
  while (koder.size < antal) {
    let kod = "";
    for (let i = 0; i < KODLANGD; i++) kod += KODTECKEN[randomInt(KODTECKEN.length)];
    koder.add(`${kod.slice(0, 5)}-${kod.slice(5)}`);
  }
  return [...koder];
}

/** Versaler, utan bindestreck och blanksteg. */
export function normaliseraAterstallningskod(kod: string): string {
  return kod.toUpperCase().replace(/[\s-]/g, "");
}

/** Ser `kod` ut som en återställningskod (efter normalisering)? */
export function serUtSomAterstallningskod(kod: string): boolean {
  const ren = normaliseraAterstallningskod(kod);
  return ren.length === KODLANGD && [...ren].every((t) => KODTECKEN.includes(t));
}

/**
 * Hashen som lagras: HMAC-SHA256 med en egen nyckel härledd ur `AUTH_SECRET`.
 * En läst tabell räcker alltså inte för att pröva koder i lugn och ro.
 */
export function hashaAterstallningskod(kod: string, authSecret: string | undefined): string {
  return createHmac("sha256", harled(authSecret, INFO_ATERSTALLNING))
    .update(normaliseraAterstallningskod(kod))
    .digest("hex");
}
