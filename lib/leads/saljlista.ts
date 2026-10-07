/**
 * Snajps säljlista — typer och de rena reglerna som både server actions
 * (lib/actions/saljlista.ts) och komponenten (components/leads/Saljlista.tsx)
 * delar. Inget här rör databasen, så det går att testa och köra i webbläsaren.
 */

/** Kolumnerna i den ordning kalkylarket hade dem. Namnen är tabellens. */
export const SALJLISTA_FALT = [
  "foretagsnamn",
  "orgnr",
  "kontaktperson",
  "kontaktnummer",
  "kontaktmail",
  "senast_kontaktad",
  "anteckningar"
] as const;

export type Saljfalt = (typeof SALJLISTA_FALT)[number];

/**
 * Radens statusfärg: hur samtalet gick. Koden lagras i databasen (104),
 * färgen och etiketten bor i komponenten. '' = ingen färg.
 */
export const SALJSTATUSAR = ["salt", "signering", "nej", "ej_svar"] as const;
export type Saljstatus = "" | (typeof SALJSTATUSAR)[number];

export function arSaljstatus(varde: string): varde is Saljstatus {
  return varde === "" || (SALJSTATUSAR as readonly string[]).includes(varde);
}

export type Saljrad = {
  id: string;
  foretagsnamn: string;
  orgnr: string;
  kontaktperson: string;
  kontaktnummer: string;
  kontaktmail: string;
  /** YYYY-MM-DD eller null. */
  senast_kontaktad: string | null;
  anteckningar: string;
  status: Saljstatus;
  created_at: string;
  updated_at: string;
};

export type Saljfel =
  | "ej_inloggad"
  | "fel_vy"
  | "saknar_tillagg"
  | "las_roll"
  | "migration_saknas"
  | "databasfel"
  | "namn_saknas"
  | "okant_falt"
  | "ogiltig_mejl"
  | "ogiltigt_datum"
  | "for_lang"
  | "finns_inte";

export type Saljsvar<T> = { ok: true; data: T } | { ok: false; fel: Saljfel; detalj?: string };

const MAXLANGD: Record<Saljfalt, number> = {
  foretagsnamn: 200,
  orgnr: 20,
  kontaktperson: 200,
  kontaktnummer: 50,
  kontaktmail: 254,
  senast_kontaktad: 10,
  anteckningar: 5000
};

/** Radens id. Kontrolleras före databasen så att skräp ger "finns inte", inte ett databasfel. */
export const RAD_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const MEJL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DATUM = /^(\d{4})-(\d{2})-(\d{2})$/;

/** 5566778899 → 556677-8899; 165566778899 → 16556677-8899. Annat lämnas som det skrevs. */
export function formateraOrgnr(varde: string): string {
  const siffror = varde.replace(/\D/g, "");
  if (/^[\d\s-]+$/.test(varde)) {
    if (siffror.length === 10) return `${siffror.slice(0, 6)}-${siffror.slice(6)}`;
    if (siffror.length === 12) return `${siffror.slice(0, 8)}-${siffror.slice(8)}`;
  }
  return varde;
}

function giltigtDatum(varde: string): boolean {
  const m = DATUM.exec(varde);
  if (!m) return false;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return (
    d.getUTCFullYear() === Number(m[1]) &&
    d.getUTCMonth() === Number(m[2]) - 1 &&
    d.getUTCDate() === Number(m[3])
  );
}

/**
 * Ett fältvärde som det sparas. Tomt datum blir null; övriga tomma fält blir
 * tom sträng hos anroparen. Felen är koder som komponenten översätter.
 */
export function normaliseraFalt(
  namn: Saljfalt,
  varde: string | null | undefined
): { ok: true; varde: string | null } | { ok: false; fel: Saljfel } {
  // Anteckningar behåller sina radbrytningar; resten är enradiga.
  const trimmat = namn === "anteckningar" ? (varde ?? "").trim() : (varde ?? "").replace(/\s+/g, " ").trim();
  if (trimmat.length > MAXLANGD[namn]) return { ok: false, fel: "for_lang" };

  if (namn === "senast_kontaktad") {
    if (!trimmat) return { ok: true, varde: null };
    return giltigtDatum(trimmat) ? { ok: true, varde: trimmat } : { ok: false, fel: "ogiltigt_datum" };
  }
  if (namn === "kontaktmail" && trimmat && !MEJL.test(trimmat)) {
    return { ok: false, fel: "ogiltig_mejl" };
  }
  if (namn === "orgnr") return { ok: true, varde: formateraOrgnr(trimmat) };
  return { ok: true, varde: trimmat };
}

/** `tel:`-länk ur ett nummer som det skrevs ("070-123 45 67" → "tel:0701234567"). */
export function telefonlank(nummer: string): string | null {
  const rent = nummer.replace(/[^\d+]/g, "");
  return rent.replace(/\D/g, "").length >= 5 ? `tel:${rent}` : null;
}

/** Nyckeln dubblettkontrollen jämför: orgnr om det finns, annars namnet utan bolagsform. */
export function dubblettnycklar(rad: Pick<Saljrad, "foretagsnamn" | "orgnr">): string[] {
  const nycklar: string[] = [];
  const siffror = rad.orgnr.replace(/\D/g, "").slice(-10);
  if (siffror.length === 10) nycklar.push(`org:${siffror}`);
  const namn = rad.foretagsnamn
    .toLowerCase()
    .replace(/\b(aktiebolag|ab|hb|kb)\b/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, "");
  if (namn) nycklar.push(`namn:${namn}`);
  return nycklar;
}

/** Hela dagar sedan ett datum (YYYY-MM-DD), räknat mot dagens lokala datum. */
export function dagarSedan(datum: string, idag: string): number | null {
  if (!giltigtDatum(datum) || !giltigtDatum(idag)) return null;
  const a = Date.UTC(+datum.slice(0, 4), +datum.slice(5, 7) - 1, +datum.slice(8, 10));
  const b = Date.UTC(+idag.slice(0, 4), +idag.slice(5, 7) - 1, +idag.slice(8, 10));
  return Math.round((b - a) / 86_400_000);
}

/** Dagens datum i webbläsarens tidszon, som YYYY-MM-DD. */
export function idagLokalt(nu: Date = new Date()): string {
  const y = nu.getFullYear();
  const m = String(nu.getMonth() + 1).padStart(2, "0");
  const d = String(nu.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function csvFalt(varde: string | null): string {
  const s = varde ?? "";
  return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * Semikolonseparerad CSV med BOM — öppnas rätt i svensk Excel. `status` är
 * radens statusetikett i klartext ("Sålt", inte koden), sist på raden.
 */
export function byggSaljCsv(
  rader: Saljrad[],
  rubriker: string[],
  status: (rad: Saljrad) => string
): string {
  const rader2 = rader.map((rad) =>
    [...SALJLISTA_FALT.map((namn) => csvFalt(rad[namn])), csvFalt(status(rad))].join(";")
  );
  return `﻿${[rubriker.map(csvFalt).join(";"), ...rader2].join("\r\n")}\r\n`;
}
