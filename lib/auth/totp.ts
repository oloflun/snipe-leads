/**
 * TOTP (RFC 6238) för tvåstegsverifieringen: base32, HOTP, koden för ett
 * tidssteg, prövningen och `otpauth://`-adressen som QR-koden bär.
 *
 * Ren logik utan databas och utan andra moduler än `node:crypto`, så att den
 * går att testa med `node --test lib/auth/totp.test.ts` (RFC 6238:s
 * testvektorer står där). Lagringen och inloggningssteget: `lib/auth/tvafaktor.ts`.
 *
 * Parametrarna är de som alla vanliga autentiseringsappar förstår utan
 * inställningar: SHA-1, sex siffror, 30 sekunder. Ett steg åt varje håll
 * godtas, för klockor som går lite fel; ett steg som redan använts godtas
 * aldrig igen (`senasteSteg`), så en avlyssnad kod går inte att spela upp.
 */

import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

export const TOTP_SIFFROR = 6;
export const TOTP_PERIOD_SEKUNDER = 30;
/** Antal steg före och efter det aktuella som godtas. */
export const TOTP_FONSTER = 1;
/** 20 byte = 160 bitar, RFC 4226:s rekommendation för SHA-1. */
const HEMLIGHET_BYTE = 20;

const BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

export function base32Koda(data: Uint8Array): string {
  let bitar = 0;
  let varde = 0;
  let ut = "";
  for (const byte of data) {
    varde = (varde << 8) | byte;
    bitar += 8;
    while (bitar >= 5) {
      ut += BASE32[(varde >>> (bitar - 5)) & 31];
      bitar -= 5;
    }
  }
  if (bitar > 0) {
    ut += BASE32[(varde << (5 - bitar)) & 31];
  }
  return ut;
}

/** Avkodar base32 (versaler eller gemener, blanksteg och `=` ignoreras). Ogiltigt tecken ger null. */
export function base32Avkoda(text: string): Buffer | null {
  const ren = text.replace(/[\s=]/g, "").toUpperCase();
  let bitar = 0;
  let varde = 0;
  const ut: number[] = [];
  for (const tecken of ren) {
    const index = BASE32.indexOf(tecken);
    if (index < 0) return null;
    varde = (varde << 5) | index;
    bitar += 5;
    if (bitar >= 8) {
      ut.push((varde >>> (bitar - 8)) & 255);
      bitar -= 8;
    }
  }
  return Buffer.from(ut);
}

/** En ny slumpad hemlighet, base32-kodad (32 tecken). */
export function nyTotpHemlighet(): string {
  return base32Koda(randomBytes(HEMLIGHET_BYTE));
}

/** HOTP (RFC 4226): koden för räknaren `steg`. */
export function hotp(nyckel: Uint8Array, steg: number, siffror = TOTP_SIFFROR): string {
  const raknare = Buffer.alloc(8);
  raknare.writeUInt32BE(Math.floor(steg / 2 ** 32), 0);
  raknare.writeUInt32BE(steg % 2 ** 32, 4);
  const hmac = createHmac("sha1", nyckel).update(raknare).digest();
  const forskjutning = hmac[hmac.length - 1] & 0x0f;
  const tal =
    ((hmac[forskjutning] & 0x7f) << 24) |
    (hmac[forskjutning + 1] << 16) |
    (hmac[forskjutning + 2] << 8) |
    hmac[forskjutning + 3];
  return String(tal % 10 ** siffror).padStart(siffror, "0");
}

/** Tidssteget för en tidpunkt (millisekunder sedan 1970). */
export function totpSteg(nuMs: number): number {
  return Math.floor(nuMs / 1000 / TOTP_PERIOD_SEKUNDER);
}

/** Koden för en tidpunkt. Används av testerna och av den lokala genomgången. */
export function totpKod(hemlighetBase32: string, nuMs: number = Date.now()): string {
  const nyckel = base32Avkoda(hemlighetBase32);
  if (!nyckel) throw new Error("ogiltig TOTP-hemlighet");
  return hotp(nyckel, totpSteg(nuMs));
}

/** Ser `kod` ut som en TOTP-kod (sex siffror, blanksteg tillåtna)? */
export function serUtSomTotp(kod: string): boolean {
  return /^\d{6}$/.test(kod.replace(/\s/g, ""));
}

/**
 * Prövar en kod. Svarar med tidssteget koden gällde för, eller null.
 *
 * Steg som är lika med eller äldre än `senasteSteg` hoppas över: en kod som
 * redan använts godtas inte igen, inte ens inom sitt eget fönster.
 */
export function provaTotp(
  hemlighetBase32: string,
  kod: string,
  nuMs: number = Date.now(),
  senasteSteg: number | null = null
): number | null {
  const ren = kod.replace(/\s/g, "");
  if (!/^\d{6}$/.test(ren)) return null;
  const nyckel = base32Avkoda(hemlighetBase32);
  if (!nyckel || nyckel.length === 0) return null;
  const nu = totpSteg(nuMs);
  const givet = Buffer.from(ren);
  let traff: number | null = null;
  // Alla steg i fönstret prövas, också efter en träff, så att svarstiden inte
  // säger vilket steg som träffade.
  for (let d = -TOTP_FONSTER; d <= TOTP_FONSTER; d++) {
    const steg = nu + d;
    const lika = timingSafeEqual(Buffer.from(hotp(nyckel, steg)), givet);
    if (lika && traff === null && (senasteSteg === null || steg > senasteSteg)) {
      traff = steg;
    }
  }
  return traff;
}

/**
 * Adressen QR-koden bär (Key Uri Format, som Google Authenticator, Microsoft
 * Authenticator, 1Password och Bitwarden läser). `konto` är adressen som syns
 * i appen; den lämnar aldrig sidan annat än i QR-koden.
 */
export function otpauthAdress(utfardare: string, konto: string, hemlighetBase32: string): string {
  const etikett = `${encodeURIComponent(utfardare)}:${encodeURIComponent(konto)}`;
  const parametrar = new URLSearchParams({
    secret: hemlighetBase32,
    issuer: utfardare,
    algorithm: "SHA1",
    digits: String(TOTP_SIFFROR),
    period: String(TOTP_PERIOD_SEKUNDER)
  });
  return `otpauth://totp/${etikett}?${parametrar.toString()}`;
}

/** Hemligheten i grupper om fyra, för den som skriver in den för hand. */
export function grupperadHemlighet(hemlighetBase32: string): string {
  return hemlighetBase32.replace(/(.{4})/g, "$1 ").trim();
}
