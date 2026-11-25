/**
 * Snajp CRM: det appen läser och skriver.
 *
 * Appen talar med samma API som en extern integration (`/api/crm/v1`, se
 * docs/crm/API.md), plus två interna vägar för nycklar och översikt
 * (`/api/crm`). Allt går genom `/api/snajp-support/…`, som bär inloggningen och
 * kundens nyckel. Appen har alltså inga egna genvägar förbi kundisoleringen.
 */
import type { Localized } from "@/lib/i18n";

export type Relation = "customer" | "former_customer" | "prospect" | "partner" | "supplier" | "other";

export type Bolag = {
  id: string;
  name: string | null;
  org_number: string | null;
  vat_number: string | null;
  legal_form: string | null;
  sni_code: string | null;
  website: string | null;
  domain: string | null;
  email: string | null;
  phone: string | null;
  employees: number | null;
  revenue_sek: number | null;
  relation: Relation;
  customer_since: string | null;
  contract_end: string | null;
  owner: string | null;
  do_not_contact: boolean | null;
  sole_proprietor: boolean;
  address: { street: string | null; co: string | null; postal_code: string | null; city: string | null; country: string | null };
  source: string | null;
  external_ids: { connection: string; id: string; last_seen_at: string | null }[];
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
};

export type Person = {
  id: string;
  first_name: string | null;
  last_name: string | null;
  title: string | null;
  email: string | null;
  phone: string | null;
  mobile: string | null;
  company_id: string | null;
  do_not_contact: boolean | null;
  source: string | null;
  updated_at: string | null;
};

export type Sida<T> = { data: T[]; next_cursor: string | null };

export type Anslutning = {
  id: string;
  name: string;
  system: string;
  conflict_rule: "source_wins" | "snajp_wins" | "newest_wins";
  missing_records: "keep" | "mark_former_customer" | "delete";
  default_relation: Relation;
  active: boolean;
  last_sync_at: string | null;
  created_at: string | null;
};

/**
 * En post som inte kom in, som synken sparar den (app/crm/synk.py):
 * `index` är postens plats i satsen, `orsak` varför hela posten hoppades över
 * och `faltfel` vad som var fel på enskilda fält. Värdet som var fel sparas inte
 * för organisationsnummer, så att ett personnummer aldrig hamnar i loggen.
 */
export type Korningsfel = {
  objekt: "bolag" | "person";
  index: number;
  externt_id: string | null;
  orsak?: string;
  faltfel?: { falt: string; kod: string; varde?: string }[];
};

export type Korning = {
  id: string;
  connection_id: string | null;
  mode: "delta" | "full";
  status: "queued" | "processing" | "completed" | "failed";
  started_by: string | null;
  counts: { total: number; created: number; updated: number; unchanged: number; skipped: number; conflicts: number; removed: number };
  errors: Korningsfel[];
  error: string | null;
  created_at: string | null;
  completed_at: string | null;
};

export type Nyckel = {
  id: string;
  namn: string;
  prefix: string;
  omfang: string[];
  created_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  api_key?: string;
};

export type Oversikt = {
  bolag: { alla: number } & Record<string, number>;
  personer: number;
  anslutningar: number;
  korningar: Korning[];
};

/** Ett fel från API:t, med texten på båda språken när API:t ger den. */
export class CrmFel extends Error {
  constructor(
    readonly text: Localized,
    readonly status: number,
    readonly kod: string | null
  ) {
    super(text.sv);
  }
}

type Felkropp = { detail?: string | { code?: string; message?: string; meddelande?: string } };

export async function crmAnrop<T>(vag: string, init?: RequestInit): Promise<T> {
  const svar = await fetch(`/api/snajp-support/crm${vag}`, {
    cache: "no-store",
    ...init,
    headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers
  });
  if (svar.status === 204) return null as T;
  const kropp = (await svar.json().catch(() => null)) as (T & Felkropp) | null;
  if (!svar.ok) {
    const d = kropp?.detail;
    const okant = { sv: `Anropet gick inte igenom (HTTP ${svar.status}).`, en: `The request failed (HTTP ${svar.status}).` };
    const text =
      typeof d === "string" ? { sv: d, en: d } : d ? { sv: d.meddelande ?? d.message ?? okant.sv, en: d.message ?? d.meddelande ?? okant.en } : okant;
    throw new CrmFel(text, svar.status, typeof d === "object" && d ? (d.code ?? null) : null);
  }
  return kropp as T;
}

export const RELATIONER: Record<Relation, Localized> = {
  customer: { sv: "Kund", en: "Customer" },
  former_customer: { sv: "Tidigare kund", en: "Former customer" },
  prospect: { sv: "Prospekt", en: "Prospect" },
  partner: { sv: "Partner", en: "Partner" },
  supplier: { sv: "Leverantör", en: "Supplier" },
  other: { sv: "Övrigt", en: "Other" }
};

export const SYSTEMNAMN: Record<string, string> = {
  generisk: "JSON / CSV",
  hubspot: "HubSpot",
  pipedrive: "Pipedrive",
  lime: "Lime CRM",
  lime_go: "Lime Go",
  upsales: "Upsales",
  salesforce: "Salesforce",
  twenty: "Twenty",
  superoffice: "SuperOffice",
  dynamics: "Dynamics 365",
  fortnox: "Fortnox",
  visma: "Visma eEkonomi"
};

/** 5560360793 skrivs 556036-0793. Annat lämnas som det står. */
export function orgnrVisning(v: string | null): string {
  if (!v) return "";
  const siffror = v.replace(/\D/g, "");
  return siffror.length === 10 ? `${siffror.slice(0, 6)}-${siffror.slice(6)}` : v;
}
