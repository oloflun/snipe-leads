import type { Localized } from "@/lib/i18n";
import { STATUS_ORDNING } from "../prospekt.ts";

/**
 * CSV-importens mallar (Fas 10, Leads Suite F): rubrikalias per CRM-export,
 * så att en fil ur HubSpot, Pipedrive, Salesforce eller Upsales mappas utan
 * handpåläggning. Kunden kan alltid ändra kartan i ImportCsv innan importen.
 */

export type ImportFalt =
  | "company_name"
  | "orgnr"
  | "contact_name"
  | "contact_role"
  | "contact_email"
  | "contact_phone"
  | "website"
  | "status";

export const IMPORTFALT: ImportFalt[] = [
  "company_name",
  "orgnr",
  "contact_name",
  "contact_role",
  "contact_email",
  "contact_phone",
  "website",
  "status"
];

export type Mall = "hubspot" | "pipedrive" | "salesforce" | "upsales" | "egen";

export type Karta = Partial<Record<ImportFalt, number>>;

/** Raden som `POST /leads/import` tar emot. */
export type Importrad = { company_name: string } & Partial<Record<Exclude<ImportFalt, "company_name">, string>>;

export const IMPORTMALLAR: Record<Mall, { namn: Localized; alias: Partial<Record<ImportFalt, string[]>> }> = {
  hubspot: {
    namn: { sv: "HubSpot", en: "HubSpot" },
    alias: {
      company_name: ["Company name", "Name"],
      website: ["Company Domain Name", "Website URL", "Domain"],
      contact_phone: ["Phone Number", "Phone"],
      contact_name: ["Contact name", "Full Name"],
      contact_role: ["Job Title"],
      contact_email: ["Email"],
      status: ["Lead Status"]
    }
  },
  pipedrive: {
    namn: { sv: "Pipedrive", en: "Pipedrive" },
    alias: {
      company_name: ["Organization - Name", "Organization"],
      contact_name: ["Person - Name"],
      contact_email: ["Person - Email"],
      contact_phone: ["Person - Phone"],
      website: ["Organization - Website"],
      contact_role: ["Person - Job title"]
    }
  },
  salesforce: {
    namn: { sv: "Salesforce", en: "Salesforce" },
    alias: {
      company_name: ["Account Name", "Company"],
      website: ["Website"],
      contact_phone: ["Phone"],
      contact_name: ["Full Name", "First Name"],
      contact_role: ["Title"],
      contact_email: ["Email"],
      status: ["Lead Status", "Status"]
    }
  },
  upsales: {
    namn: { sv: "Upsales", en: "Upsales" },
    alias: {
      company_name: ["Företag"],
      orgnr: ["Org.nr"],
      contact_name: ["Kontakt"],
      contact_role: ["Titel"],
      contact_email: ["E-post"],
      contact_phone: ["Telefon"],
      website: ["Hemsida"]
    }
  },
  egen: {
    namn: { sv: "Egen fil", en: "Own file" },
    alias: {
      company_name: ["company_name", "bolag", "företag", "företagsnamn", "company", "organisation", "organization"],
      orgnr: ["orgnr", "org.nr", "org nr", "organisationsnummer", "org number"],
      contact_name: ["contact_name", "kontakt", "kontaktperson", "contact", "contact name"],
      contact_role: ["contact_role", "roll", "titel", "title", "role"],
      contact_email: ["contact_email", "e-post", "epost", "email", "e-mail", "mejl"],
      contact_phone: ["contact_phone", "telefon", "tel", "phone", "mobil"],
      website: ["website", "webbplats", "hemsida", "webb", "url", "domän"],
      status: ["status"]
    }
  }
};

const MALLORDNING: Mall[] = ["hubspot", "pipedrive", "salesforce", "upsales", "egen"];

function norm(s: string): string {
  return s.trim().toLowerCase();
}

/**
 * Kartan för en given mall: varje fält pekar på första kolumnen vars rubrik
 * matchar ett alias (skiftlägesokänsligt). Fält mallen inte känner fylls ur
 * de generiska aliasen, så en HubSpot-fil med en egen kolumn "Orgnr" ändå
 * mappas. `efternamn` sätts när förnamn och efternamn står i varsin kolumn
 * (Salesforce, HubSpot).
 */
export function kartaForMall(rubriker: string[], mall: Mall): { karta: Karta; traffar: number; efternamn?: number } {
  const normade = rubriker.map(norm);
  const karta: Karta = {};
  let traffar = 0;
  for (const falt of IMPORTFALT) {
    for (const kalla of mall === "egen" ? ["egen" as const] : [mall, "egen" as const]) {
      const index = (IMPORTMALLAR[kalla].alias[falt] ?? []).map(norm).map((a) => normade.indexOf(a)).find((i) => i >= 0);
      if (index !== undefined) {
        karta[falt] = index;
        if (kalla === mall) traffar += 1;
        break;
      }
    }
  }
  const forIndex = normade.indexOf("first name");
  const efterIndex = normade.indexOf("last name");
  if (karta.contact_name === undefined && forIndex >= 0) karta.contact_name = forIndex;
  const efternamn = karta.contact_name === forIndex && efterIndex >= 0 ? efterIndex : undefined;
  return { karta, traffar, efternamn };
}

/** Mallen med flest träffar vinner; vid lika vinner den som står först. */
export function gissaKarta(rubriker: string[]): { mall: Mall; karta: Karta; efternamn?: number } {
  let bast: { mall: Mall; karta: Karta; traffar: number; efternamn?: number } | null = null;
  for (const mall of MALLORDNING) {
    const forsok = kartaForMall(rubriker, mall);
    if (!bast || forsok.traffar > bast.traffar) bast = { mall, ...forsok };
  }
  const { mall, karta, efternamn } = bast!;
  return { mall, karta, efternamn };
}

const STATUSAR = new Set<string>(STATUS_ORDNING);

/**
 * En CSV-rad som importrad, eller `null` när bolagsnamnet saknas (raden räknas
 * då som överhoppad). Tomma fält utelämnas och allt kapas vid 200 tecken,
 * backendens tak. En status utanför prospektets värdemängd utelämnas.
 */
export function radTillImportrad(rad: string[], karta: Karta, efternamn?: number): Importrad | null {
  const varde = (i: number | undefined) => (i === undefined ? "" : (rad[i] ?? "").trim());
  const company = varde(karta.company_name).slice(0, 200);
  if (!company) return null;
  const ut: Importrad = { company_name: company };
  for (const falt of IMPORTFALT) {
    if (falt === "company_name") continue;
    let v = varde(karta[falt]);
    if (falt === "contact_name" && efternamn !== undefined) v = [v, varde(efternamn)].filter(Boolean).join(" ");
    if (falt === "status") {
      v = v.toLowerCase();
      if (!STATUSAR.has(v)) continue;
    }
    if (v) ut[falt] = v.slice(0, 200);
  }
  return ut;
}
