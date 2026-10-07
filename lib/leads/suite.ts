import { arEjAktiverad } from "@/components/EjAktiverad";
import { readJsonBody } from "@/lib/http/json";
import type { Locale, Localized } from "@/lib/i18n";
import type { Utkastfalt } from "@/lib/leads/utkast";

/**
 * Leads Suite (Fas 10, plan del F): typerna och anropet som tabellen,
 * pipelinen, tidslinjen, importen och automationen delar. Kontraktet står i
 * `snajp-support/app/api/leads_suite.py`; allt går genom proxyn
 * `/api/snajp-support/...` med `cache: "no-store"`.
 */

export type SuiteProspekt = {
  id: string;
  company_name: string;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  status: string;
  origin?: string | null;
  niva?: "A" | "B" | "C" | null;
  score_total?: number | null;
  icp_fit?: number | null;
  created_at?: string | null;
  /** Senaste statusbyte ur loggen, annars created_at (GET /leads/prospects). */
  senaste_handelse_at?: string | null;
  website?: string | null;
  ort?: string | null;
  motivering?: string | null;
  disqualifiers?: string[] | null;
  /** Webbrevisionen (migration 094): bildbedömningens betyg och synliga brister. */
  webbrevision?: { modernitet?: number | null; brister?: string[] | null } | null;
  /** Arkiverad (migration 107): dold i Iris-listan, nåbar under Arkiverade. */
  arkiverad_at?: string | null;
} & Utkastfalt;

export type Uppgift = {
  id: string;
  prospect_id: string;
  titel: string;
  forfaller: string | null;
  klar: boolean;
  klar_at?: string | null;
  created_at?: string | null;
};

export type VyFilter = { status?: string; niva?: string; typ?: string; sok?: string };

export type Vy = { id: string; namn: string; filter: VyFilter; created_at?: string | null };

export type Handelse = {
  typ: "skapad" | "status" | "mejl_ut" | "mejl_in" | "anteckning" | "uppgift" | "samtal";
  nar: string;
  rubrik: string;
  text: string | null;
  id: string | null;
  klar: boolean | null;
};

/** Samtalens utfall (snajp-support/app/leads/samtal.py, migration 107). */
export type Utfall = "ej_svar" | "aterkom" | "ej_intresserad" | "kontakta_inte" | "mote";

export const UTFALL_ETIKETT: Record<Utfall, Localized> = {
  ej_svar: { sv: "Ej svar", en: "No answer" },
  aterkom: { sv: "Återkom", en: "Call back" },
  ej_intresserad: { sv: "Ej intresserad", en: "Not interested" },
  kontakta_inte: { sv: "Kontakta inte", en: "Do not contact" },
  mote: { sv: "Möte bokat", en: "Meeting booked" }
};

/** En rad i återkopplingen eller ringlistan (GET /leads/samtal). */
export type Samtalsrad = {
  prospect_id: string;
  company_name: string | null;
  ort: string | null;
  website: string | null;
  contact_name: string | null;
  contact_role: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  anstallda: number | null;
  status: string | null;
  kontaktad: string | null;
  antal_samtal: number;
  senaste_utfall: Utfall | null;
  senaste_samtal: string | null;
  aterkom_datum: string | null;
  nasta: string | null;
  ring_idag: boolean;
};

/** Ett fel från backenden: meddelandet ur `detail` när det finns, och läget
 *  "arbetsytan aktiveras" (409 `ej_aktiverad`) som egen flagga. */
export class LeadsFel extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly ejAktiverad: boolean
  ) {
    super(message);
    this.name = "LeadsFel";
  }
}

function detaljtext(kropp: unknown): string | null {
  if (!kropp || typeof kropp !== "object") return null;
  const k = kropp as { detail?: unknown; error?: unknown };
  if (typeof k.detail === "string") return k.detail;
  if (Array.isArray(k.detail)) {
    return k.detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
      .join("; ");
  }
  return typeof k.error === "string" ? k.error : null;
}

/** `vag` utan prefix, t.ex. `/leads/vyer`. Kastar LeadsFel vid felstatus. */
export async function leadsAnrop<T>(vag: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/snajp-support${vag}`, {
    cache: "no-store",
    ...init,
    headers: init?.body ? { "Content-Type": "application/json" } : undefined
  });
  const kropp = await readJsonBody<T>(response);
  if (!response.ok) {
    throw new LeadsFel(
      detaljtext(kropp) ?? `HTTP ${response.status}`,
      response.status,
      arEjAktiverad(response.status, kropp)
    );
  }
  return kropp as T;
}

export function datumFormat(locale: Locale): string {
  return locale === "en" ? "en-GB" : "sv-SE";
}

/** "för 3 dagar sedan" / "3 days ago". */
export function relativTid(iso: string | null | undefined, locale: Locale): string {
  if (!iso) return "";
  const sekunder = (new Date(iso).getTime() - Date.now()) / 1000;
  if (Number.isNaN(sekunder)) return "";
  const rtf = new Intl.RelativeTimeFormat(datumFormat(locale), { numeric: "auto" });
  const steg: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["week", 604_800],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60]
  ];
  for (const [enhet, langd] of steg) {
    if (Math.abs(sekunder) >= langd) return rtf.format(Math.round(sekunder / langd), enhet);
  }
  return rtf.format(0, "minute");
}

export function poangAv(p: SuiteProspekt): string {
  if (typeof p.score_total === "number") return String(p.score_total);
  if (typeof p.icp_fit === "number") return String(Math.round(p.icp_fit * 100));
  return "";
}

export type Kontaktvag = "bada" | "telefon" | "mejl" | "saknas";

export function kontaktvagAv(p: SuiteProspekt): Kontaktvag {
  const tel = Boolean(p.contact_phone?.trim());
  const mejl = Boolean(p.contact_email?.trim());
  return tel && mejl ? "bada" : tel ? "telefon" : mejl ? "mejl" : "saknas";
}
