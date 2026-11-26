/**
 * Affärer och deras steg, som API:t lämnar dem (`/api/crm/v1/deals`,
 * `/deal-stages`, `/deals/board`; docs/crm/API.md).
 */
import type { Localized } from "@/lib/i18n";

export type Stegtyp = "open" | "won" | "lost";

export type Affarssteg = {
  id: string;
  name: string;
  position: number;
  /** Stegets egen sannolikhet i procent. Affären får den om den inte har en egen. */
  probability: number;
  type: Stegtyp;
  color: string | null;
};

export type Affar = {
  id: string;
  name: string | null;
  company_id: string | null;
  person_id: string | null;
  stage_id: string | null;
  /** Hela kronor (eller hela enheter av `currency`). */
  amount: number | null;
  currency: string | null;
  probability: number | null;
  expected_close_date: string | null;
  closed_at: string | null;
  lost_reason: string | null;
  owner: string | null;
  position: number | null;
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
  purge_at?: string | null;
};

/** Ett steg på tavlan: steget, dess affärer i tavlans ordning, antal och summa. */
export type Tavelsteg = Affarssteg & {
  deals: Affar[];
  count: number;
  amount_total: number;
  amount_by_currency: Record<string, number>;
};

export type Tavla = { stages: Tavelsteg[] };

export const STEGTYPER: Record<Stegtyp, Localized> = {
  open: { sv: "Öppen", en: "Open" },
  won: { sv: "Vunnen", en: "Won" },
  lost: { sv: "Förlorad", en: "Lost" }
};

/** `120000` blir `120 000 kr`. Annan valuta än SEK skrivs med sin kod. */
export function belopp(varde: number | null, valuta: string | null, sprak: "sv" | "en"): string | null {
  if (varde == null) return null;
  return new Intl.NumberFormat(sprak === "sv" ? "sv-SE" : "en-GB", {
    style: "currency",
    currency: valuta || "SEK",
    maximumFractionDigits: 0
  }).format(varde);
}

/** Summan per valuta som en rad: `1 240 000 kr` eller `1 240 000 kr + 12 000 €`. */
export function summa(perValuta: Record<string, number>, sprak: "sv" | "en"): string {
  const delar = Object.entries(perValuta)
    .filter(([, v]) => v > 0)
    .sort(([a], [b]) => (a === "SEK" ? -1 : b === "SEK" ? 1 : a.localeCompare(b)))
    .map(([valuta, v]) => belopp(v, valuta, sprak));
  return delar.length ? delar.join(" + ") : (belopp(0, "SEK", sprak) ?? "0");
}

/** Affärens sannolikhet: dess egen, annars stegets. */
export const sannolikhet = (a: Affar, steg: Affarssteg | undefined): number | null => a.probability ?? steg?.probability ?? null;
