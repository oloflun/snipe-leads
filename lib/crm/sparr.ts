/**
 * Spärrlistan som API:t lämnar den (`/api/crm/v1/suppressions`, docs/crm/API.md).
 * En spärr gäller en kanal (mejl, telefon eller alla) och ett värde: en
 * e-postadress, en domän, ett telefonnummer eller ett organisationsnummer.
 */
import type { Localized } from "@/lib/i18n";

export type Sparrkanal = "email" | "phone" | "all";
export type Sparrslag = "email" | "phone" | "domain" | "org_number";
export type Sparrorsak = "objection" | "unsubscribe" | "nix" | "customer_request" | "bounce" | "other";

export type Sparr = {
  id: string;
  channel: Sparrkanal;
  kind: Sparrslag;
  value: string;
  reason: Sparrorsak;
  note: string | null;
  /** `app`, `api`, `outcome` (ett utfall på bolaget), `import` eller `sync`. */
  source: string;
  company_id: string | null;
  person_id: string | null;
  created_at: string | null;
  /** En hävd spärr står kvar som bevis men gäller inte. */
  lifted_at: string | null;
};

/** Svaret från `POST /suppressions/import`. */
export type Importsvar = { added: number; already_blocked: number; invalid: { index: number; code: string }[] };

/** Svaret från `POST /suppressions/check`: om något spärrar, och vilka källor. Aldrig något om kontakten själv. */
export type Sparrkontroll = { blocked: boolean; sources: string[]; suppression_ids?: string[] };

export const SPARRKANALER: Record<Sparrkanal, Localized> = {
  email: { sv: "Mejl", en: "Email" },
  phone: { sv: "Telefon", en: "Phone" },
  all: { sv: "Alla kanaler", en: "All channels" }
};

export const SPARRSLAG: Record<Sparrslag, Localized> = {
  email: { sv: "E-postadress", en: "Email address" },
  domain: { sv: "Domän", en: "Domain" },
  phone: { sv: "Telefonnummer", en: "Phone number" },
  org_number: { sv: "Organisationsnummer", en: "Organisation number" }
};

/** Slagen som går att spärra i varje kanal (`slag_passar_inte_kanalen` i API:t). */
export const SLAG_I_KANAL: Record<Sparrkanal, Sparrslag[]> = {
  email: ["email", "domain", "org_number"],
  phone: ["phone", "org_number"],
  all: ["email", "domain", "phone", "org_number"]
};

export const SPARRORSAKER: Record<Sparrorsak, Localized> = {
  objection: { sv: "Invändning", en: "Objection" },
  unsubscribe: { sv: "Avregistrering", en: "Unsubscribe" },
  nix: { sv: "NIX", en: "NIX" },
  customer_request: { sv: "Egen begäran", en: "Own request" },
  bounce: { sv: "Studs", en: "Bounce" },
  other: { sv: "Annat", en: "Other" }
};

/** Vad varje orsak betyder, under väljaren. */
export const SPARRORSAK_VAD: Record<Sparrorsak, Localized> = {
  objection: { sv: "Personen har invänt mot direktmarknadsföring (GDPR artikel 21).", en: "The person has objected to direct marketing (GDPR article 21)." },
  unsubscribe: { sv: "Avregistrerad från utskick.", en: "Unsubscribed from mailings." },
  nix: { sv: "Träff i er egen kontroll mot NIX-registret.", en: "A hit in your own check against the NIX registry." },
  customer_request: { sv: "Bolaget eller personen har bett att slippa kontakt.", en: "The company or the person has asked not to be contacted." },
  bounce: { sv: "Adressen tar inte emot mejl.", en: "The address does not accept email." },
  other: { sv: "Ett annat skäl. Skriv det i anteckningen.", en: "Another reason. Write it in the note." }
};

export const SPARRKALLOR: Record<string, Localized> = {
  app: { sv: "Appen", en: "The app" },
  api: { sv: "API", en: "API" },
  outcome: { sv: "Utfall på bolaget", en: "Outcome on the company" },
  import: { sv: "Uppladdad lista", en: "Uploaded list" },
  sync: { sv: "Synk", en: "Sync" }
};

/** Källorna som `POST /suppressions/check` kan svara med. */
export const SPARRGRINDAR: Record<string, Localized> = {
  suppression_list: { sv: "spärrlistan", en: "the block list" },
  record: { sv: "ett bolag eller en person märkt Kontakta inte", en: "a company or person marked Do not contact" },
  unsubscribed: { sv: "en avregistrering", en: "an unsubscribe" },
  lead: { sv: "ett lead hos Iris som bett att slippa kontakt", en: "a lead with Iris that asked not to be contacted" }
};

/** Gissar slaget ur det som skrivits: en adress med @, ett tal, annars en domän. */
export function gissaSlag(varde: string): Sparrslag {
  const v = varde.trim();
  if (v.includes("@")) return "email";
  const siffror = v.replace(/[\s()+-]/g, "");
  if (/^\d+$/.test(siffror)) return /^(16)?[2-9]\d{9}$/.test(siffror) && !v.trim().startsWith("0") && !v.trim().startsWith("+") ? "org_number" : "phone";
  return "domain";
}
