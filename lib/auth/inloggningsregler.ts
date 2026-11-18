/**
 * Spärren mot upprepade inloggningsförsök: reglerna och nycklarna (ISO 27001
 * A.8.5, 2026-11-18). Ren logik utan databas, så att den går att testa med
 * `node --test lib/auth/inloggningsregler.test.ts`. Räkningen och spärren sker i
 * databasen (migration 125), anropen i `lib/auth/inloggningsforsok.ts`.
 *
 * Reglerna:
 *  - Lösenordsinloggning: 5 misslyckade försök per e-postadress, eller 20 per
 *    IP, inom 15 minuter ger en spärr.
 *  - Återställningsbegäran: 3 begäranden per e-postadress, eller 10 per IP,
 *    inom en timme ger en spärr.
 *  - Spärren är 1 minut första gången, sedan 5, 15 och 60 minuter för varje ny
 *    spärr på samma nyckel inom ett dygn (`inloggningsforsok_vantetid`).
 *  - En lyckad inloggning nollställer adressens räknare, inte IP:ts.
 *  - Adressen räknas likadant med och utan konto, så spärren avslöjar inte
 *    vilka adresser som finns. Ett spärrat försök prövar aldrig lösenordet.
 *
 * IP-tröskeln är högre än adressens eftersom ett kontor bakom en NAT delar IP.
 */

import { createHash, createHmac } from "node:crypto";

export type Handling = "inloggning" | "aterstallning";
export type Omfang = "epost" | "ip";

export type Regel = Readonly<{ troskel: number; fonsterSekunder: number }>;

export const REGLER: Readonly<Record<Handling, Readonly<Record<Omfang, Regel>>>> = {
  inloggning: {
    epost: { troskel: 5, fonsterSekunder: 15 * 60 },
    ip: { troskel: 20, fonsterSekunder: 15 * 60 }
  },
  aterstallning: {
    epost: { troskel: 3, fonsterSekunder: 60 * 60 },
    ip: { troskel: 10, fonsterSekunder: 60 * 60 }
  }
};

/** Adressen jämförs som `auth.users` gör: utan blanktecken, gemener. */
export function normaliseraEpost(epost: string): string {
  return epost.trim().toLowerCase();
}

/**
 * Nyckeln i databasen: `handling:omfång:HMAC(värde)`. Hemligheten är
 * `AUTH_SECRET`, så att en läst tabell inte går att slå upp mot en adresslista.
 * Saknas den (då går ingen inloggning alls) blir det en vanlig sha256.
 */
export function nyckel(handling: Handling, omfang: Omfang, varde: string, hemlighet?: string): string {
  const v = omfang === "epost" ? normaliseraEpost(varde) : varde.trim();
  const sammandrag = hemlighet
    ? createHmac("sha256", hemlighet).update(`${omfang}:${v}`).digest("hex")
    : createHash("sha256").update(`${omfang}:${v}`).digest("hex");
  return `${handling}:${omfang}:${sammandrag}`;
}

/**
 * Klientens IP bakom Railways kant.
 *
 * `x-real-ip` sätts av kanten. Annars den SISTA posten i `x-forwarded-for`: den
 * lade kanten till, de tidigare kan klienten ha skrivit själv och används
 * därför aldrig. Utan någon av dem: null, och bara adressen räknas.
 */
export function klientIp(headers: Pick<Headers, "get"> | null | undefined): string | null {
  if (!headers) return null;
  const real = headers.get("x-real-ip")?.trim();
  if (real) return real.slice(0, 64);
  const fwd = headers.get("x-forwarded-for");
  if (!fwd) return null;
  const poster = fwd
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
  const sista = poster[poster.length - 1];
  return sista ? sista.slice(0, 64) : null;
}

/** Adressen maskerad för loggen: `a***@bolag.se`. */
export function maskeraEpost(epost: string): string {
  const v = normaliseraEpost(epost);
  const at = v.lastIndexOf("@");
  if (at <= 0) return "***";
  return `${v[0]}***${v.slice(at)}`;
}
