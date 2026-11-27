/**
 * Bolagsuppgifter ur SCB:s företagsregister som API:t lämnar dem
 * (`GET /lookup/companies`, `POST /companies/{id}/enrich`; docs/crm/API.md).
 * Bara bolagsnivå: registret lämnar aldrig personer till Snajp.
 */
import type { Bolag } from "@/lib/crm/api";
import type { Localized } from "@/lib/i18n";

export type Registerstatus = "active" | "inactive" | "never_active" | "deregistered" | "unknown";

export type Registerpost = {
  org_number: string;
  name: string | null;
  legal_form: string | null;
  registry_status: Registerstatus;
  sni_codes: string[];
  postal_address: { street: string | null; co: string | null; postal_code: string | null; city: string | null };
  employee_class: { code: string; label: string } | null;
  advertising_block: boolean | null;
};

/** Svaret från `POST /companies/{id}/enrich`. `filled` och `skipped` är API:ts fältnamn. */
export type Berikning = {
  company: Bolag;
  filled: string[];
  skipped: string[];
  registry_status: Registerstatus;
  deregistered: boolean;
  advertising_block: boolean | null;
  registry: Registerpost;
};

export const REGISTERSTATUS: Record<Registerstatus, { namn: Localized; badge: "green" | "neutral" | "error" }> = {
  active: { namn: { sv: "Verksamt", en: "Active" }, badge: "green" },
  inactive: { namn: { sv: "Inte verksamt", en: "Not active" }, badge: "neutral" },
  never_active: { namn: { sv: "Har aldrig varit verksamt", en: "Has never been active" }, badge: "neutral" },
  deregistered: { namn: { sv: "Avregistrerat", en: "Deregistered" }, badge: "error" },
  unknown: { namn: { sv: "Okänd status", en: "Unknown status" }, badge: "neutral" }
};

export const REGISTERNAMN: Localized = { sv: "SCB:s företagsregister", en: "Statistics Sweden's business register" };
