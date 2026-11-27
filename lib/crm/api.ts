/**
 * Snajp CRM: det appen läser och skriver.
 *
 * Appen talar med samma API som en extern integration (`/api/crm/v1`, se
 * docs/crm/API.md), plus två interna vägar för nycklar och översikt
 * (`/api/crm`). Allt går genom `/api/snajp-support/…`, som bär inloggningen och
 * kundens nyckel. Appen har alltså inga egna genvägar förbi kundisoleringen.
 */
import type { Localized } from "@/lib/i18n";

export type Relation = "customer" | "former_customer" | "prospect" | "partner" | "supplier" | "not_relevant" | "other";

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
  /**
   * Kunden är en privatperson, inte ett bolag. Inget personnummer sparas, och
   * posten är alltid `do_not_contact`: den lämnas utanför varje utskick och lista.
   */
  private_person: boolean;
  address: { street: string | null; co: string | null; postal_code: string | null; city: string | null; country: string | null };
  /** Bolagets status i SCB:s företagsregister, och när den lästes. Null tills bolaget hämtats ur registret. */
  registry_status?: "active" | "inactive" | "never_active" | "deregistered" | "unknown" | null;
  registry_checked_at?: string | null;
  source: string | null;
  external_ids: { connection: string; id: string; last_seen_at: string | null }[];
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
  /** När en raderad post töms för gott (30 dagar efter raderingen). Null för en levande post. */
  purge_at?: string | null;
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
  deleted_at?: string | null;
  /** När en raderad person töms för gott. Null för en levande post. */
  purge_at?: string | null;
};

export type Sida<T> = { data: T[]; next_cursor: string | null };

/** Listornas ordning i API:t: ändringsordning (äldst först), senast ändrad först, eller namn. */
export type Ordning = "updated" | "-updated" | "name";

export type Anslutning = {
  id: string;
  name: string;
  system: string;
  conflict_rule: "source_wins" | "snajp_wins" | "newest_wins";
  missing_records: "keep" | "mark_former_customer" | "delete";
  default_relation: Relation;
  /**
   * Av som standard: poster som källan märker som privatpersoner hoppas över
   * (`orsak: privatperson`). På: de sparas märkta, utan personnummer, och
   * går aldrig att kontakta.
   */
  include_private_persons?: boolean;
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
  /** Bolagets namn, så att den som läser felen ser vilken rad det gäller. Saknas för privatpersoner. */
  namn?: string;
  orsak?: string;
  /** Id på posten i Snajp som redan har numret eller adressen, när krocken går att peka ut. */
  krockar_med?: string;
  faltfel?: { falt: string; kod: string; varde?: string }[];
};

/**
 * Körningens fel i enkla ord (`issues`), grupperade efter sort, objekt och
 * fält, störst först. Appen sätter orden (`lib/crm/felkoder.ts`: `ENKLA`).
 */
export type Korningsfraga = {
  kind: "ogiltigt_varde" | "saknar_uppgift" | "dubblett" | "begransad" | "privatperson" | "undantagen" | "redan_borta" | "annat" | (string & {});
  object: "company" | "person" | (string & {});
  /** API:ts fältnamn (`phone`, `address.postal_code`) för `ogiltigt_varde` och `saknar_uppgift`. */
  field: string | null;
  count: number;
};

/** Satt när körningen hade fel: rapporten har då gått vidare till Snajps support. */
export type Supportbesked = { forwarded_at: string; ticket: string | null };

export type Korning = {
  id: string;
  connection_id: string | null;
  mode: "delta" | "full";
  status: "queued" | "processing" | "completed" | "failed";
  started_by: string | null;
  counts: { total: number; created: number; updated: number; unchanged: number; skipped: number; conflicts: number; removed: number };
  errors: Korningsfel[];
  error: string | null;
  /** Samma fel i enkla ord, för kunden. Äldre svar saknar fältet. */
  issues?: Korningsfraga[];
  support?: Supportbesked | null;
  created_at: string | null;
  completed_at: string | null;
};

/** En händelse i postens historik eller ändringsflödet (`handelse_ut`). Loggen bär aldrig värdena. */
export type Handelse = {
  seq: number;
  object: "company" | "person" | (string & {});
  id: string;
  type: "created" | "updated" | "deleted" | "restored" | "purged";
  /** API:ts fältnamn för det som ändrades. Tomt för skapad och raderad. */
  fields: string[];
  /** `api`, `app`, `synk` eller `system`. */
  source: string | null;
  /** `anslutning:<namn>`, `anvandare:<id>`, `nyckel:<id>` eller inget. */
  actor: string | null;
  at: string | null;
};

/** En webhook (`webhook_ut`). `secret` finns bara i svaret när den skapas. */
export type Webhook = {
  id: string;
  url: string;
  description: string | null;
  events: string[];
  active: boolean;
  consecutive_failures: number;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_error: string | null;
  /** `for_manga_fel` när Snajp stängt av den efter tjugo fel i rad. */
  disabled_reason: string | null;
  created_at: string | null;
  updated_at: string | null;
  secret?: string;
};

/** En leverans i webhookens logg (`leverans_ut`). */
export type Leverans = {
  id: string;
  event: string;
  status: "pending" | "delivered" | "failed";
  attempts: number;
  status_code: number | null;
  error: string | null;
  next_attempt_at: string | null;
  created_at: string | null;
  delivered_at: string | null;
  payload: Record<string, unknown>;
};

/** `GET /v1/me`: vilken kund nyckeln hör till. */
export type Jag = { tenant: string; scopes: string[]; rate_limit: { requests: number; window_seconds: number }; api_version: string };

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

/**
 * Ett fält som API:t inte kunde tolka (`detail.fields` vid 422 `invalid_fields`):
 * fältets engelska namn (`org_number`, `address.postal_code`) och felkoden, som
 * `lib/crm/felkoder.ts` (`FALTKODER`) översätter.
 */
export type Faltfel = { field: string; code: string };

/** Ett fel från API:t, med texten på båda språken när API:t ger den. */
export class CrmFel extends Error {
  constructor(
    readonly text: Localized,
    readonly status: number,
    readonly kod: string | null,
    readonly falt: Faltfel[] = [],
    /** Vid 409 `conflict`: id på posten som redan har numret eller adressen, när API:t kan peka ut den. */
    readonly krockarMed: string | null = null
  ) {
    super(text.sv);
  }
}

type Felkropp = {
  detail?: string | { code?: string; message?: string; meddelande?: string; fields?: Faltfel[]; conflicting_id?: string };
};

export async function crmAnrop<T>(vag: string, init?: RequestInit): Promise<T> {
  const svar = await fetch(`/api/snajp-support/crm${vag}`, {
    cache: "no-store",
    ...init,
    headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers
  });
  return tolka<T>(svar);
}

/** En bilaga som API:t lämnar den (`bilaga_ut`): metadata, aldrig innehållet. */
export type Bilaga = {
  id: string;
  filename: string | null;
  content_type: string | null;
  size: number | null;
  uploaded_by: string | null;
  company_id: string | null;
  person_id: string | null;
  deal_id: string | null;
  note_id: string | null;
  created_at: string | null;
  deleted_at: string | null;
};

/** API:ts gränser för en bilaga (`objekt.MAX_BILAGA` och de tillåtna typerna), så att beskedet kommer före uppladdningen. */
export const BILAGA_MAX = 10 * 1024 * 1024;
export const BILAGETYPER = ["pdf", "png", "jpg", "jpeg", "webp", "gif", "txt", "csv", "docx", "xlsx", "pptx"];

/**
 * Laddar upp en fil och knyter den till en post (`POST /v1/attachments`,
 * `multipart/form-data`). Webbläsaren sätter själv rubriken med gränsmärket,
 * så anropet går inte genom `crmAnrop`, som skickar JSON.
 */
export async function crmLaddaUpp(fil: File, koppling: Partial<Record<"company_id" | "person_id" | "deal_id" | "note_id", string>>): Promise<Bilaga> {
  const formular = new FormData();
  formular.append("file", fil, fil.name);
  for (const [falt, id] of Object.entries(koppling)) if (id) formular.append(falt, id);
  const svar = await fetch("/api/snajp-support/crm/v1/attachments", { method: "POST", body: formular, cache: "no-store" });
  return tolka<Bilaga>(svar);
}

/** Svaret som värde, eller ett `CrmFel` med API:ts text på båda språken. */
async function tolka<T>(svar: Response): Promise<T> {
  if (svar.status === 204) return null as T;
  const kropp = (await svar.json().catch(() => null)) as (T & Felkropp) | null;
  if (!svar.ok) {
    const d = kropp?.detail;
    const okant = { sv: `Anropet gick inte igenom (HTTP ${svar.status}).`, en: `The request failed (HTTP ${svar.status}).` };
    const text =
      typeof d === "string" ? { sv: d, en: d } : d ? { sv: d.meddelande ?? d.message ?? okant.sv, en: d.message ?? d.meddelande ?? okant.en } : okant;
    const objekt = typeof d === "object" && d ? d : null;
    const fel = new CrmFel(
      text,
      svar.status,
      objekt?.code ?? null,
      Array.isArray(objekt?.fields) ? objekt.fields : [],
      typeof objekt?.conflicting_id === "string" ? objekt.conflicting_id : null
    );
    // Tillägget saknas: skalet byter vyn mot sitt helsidesläge (CrmRam, Tillagg.tsx).
    if (fel.kod === TILLAGG_SAKNAS && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent(TILLAGG_SAKNAS));
    }
    throw fel;
  }
  return kropp as T;
}

/**
 * En dag utan klockslag (`2026-12-15`, eller början av en tidsstämpel) som text:
 * "15 dec. 2026", och med `kort` utan årtal när det är i år. Dagen räknas aldrig
 * om mellan tidszoner: en kalenderdag är samma dag var läsaren än sitter.
 */
export function dagtext(v: string, sprak: "sv" | "en", kort = false): string {
  const [ar, manad, dag] = v.slice(0, 10).split("-").map(Number);
  const d = new Date(ar, (manad || 1) - 1, dag || 1, 12);
  const utanAr = kort && ar === new Date().getFullYear();
  return d.toLocaleDateString(sprak === "sv" ? "sv-SE" : "en-GB", utanAr ? { day: "numeric", month: "short" } : { day: "numeric", month: "short", year: "numeric" });
}

/** Dagens datum i läsarens tidszon, som `ÅÅÅÅ-MM-DD`. Inte UTC: mellan midnatt och ett på natten är UTC fortfarande i går. */
export function idagLokalt(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Koden API:t svarar med när arbetsytan varken har tillägget eller en pågående provperiod. */
export const TILLAGG_SAKNAS = "addon_missing";

export const RELATIONER: Record<Relation, Localized> = {
  customer: { sv: "Kund", en: "Customer" },
  former_customer: { sv: "Tidigare kund", en: "Former customer" },
  prospect: { sv: "Prospekt", en: "Prospect" },
  partner: { sv: "Partner", en: "Partner" },
  supplier: { sv: "Leverantör", en: "Supplier" },
  // Ett bolag som sagt nej eller inte passar: skilt från ett prospekt, och inte fritt för Iris.
  not_relevant: { sv: "Ej aktuell", en: "Not relevant" },
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
