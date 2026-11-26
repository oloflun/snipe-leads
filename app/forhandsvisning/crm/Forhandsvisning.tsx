"use client";

import { BolagVy } from "@/components/crm/app/BolagVy";
import { CrmRam, type CrmVy } from "@/components/crm/app/CrmRam";
import { OversiktVy } from "@/components/crm/app/OversiktVy";
import { PersonerVy } from "@/components/crm/app/PersonerVy";
import { SynkVy } from "@/components/crm/app/SynkVy";
import { UtvecklareVy } from "@/components/crm/app/UtvecklareVy";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { orgnrVisning, type Anslutning, type Bolag, type Handelse, type Korning, type Leverans, type Nyckel, type Relation, type Webhook } from "@/lib/crm/api";
import type { DashboardState } from "@/lib/data/dashboard";
import type { Personpost } from "@/lib/crm/person";
import type { Tema } from "@/lib/tema";

/**
 * Förhandsvisning av Snajp CRM utan databas och utan inloggning. Anropen mot
 * /api/snajp-support/crm besvaras här i webbläsaren, med påhittade bolag och
 * personer. Ändringar lever bara tills sidan laddas om.
 */

const nu = Date.now();
const iso = (timmar: number) => new Date(nu - timmar * 36e5).toISOString();

const NAMN = [
  "Fiktiv Telefoni", "Exempelbolaget", "Nordisk Påhitt", "Låtsas Logistik", "Hittepå Bygg", "Provkörning Media",
  "Testgränd Fastigheter", "Attrapp Energi", "Skenbar Redovisning", "Modellverket", "Utkast Arkitekter", "Dummy Transport",
  "Skissad Verkstad", "Övningsbolaget", "Prototyp Livsmedel", "Mockup Mode", "Skenet Konsult", "Kuliss Event"
];
const ORTER = ["Umeå", "Göteborg", "Stockholm", "Malmö", "Luleå", "Halmstad", "Uppsala", "Örebro"];
const ANSVARIGA = ["Kim Exempel", "Robin Prov", "Alex Test"];
const RELATIONSFOLJD: Relation[] = ["customer", "customer", "customer", "prospect", "former_customer", "customer", "partner", "customer"];

/** Nio siffror plus Luhn-siffran, som falt.orgnr kontrollerar. */
function medKontrollsiffra(nio: string): string {
  for (let d = 0; d < 10; d++) if (luhn(nio + d)) return nio + d;
  return nio + "0";
}

function bolag(i: number): Bolag {
  const stam = NAMN[i % NAMN.length];
  const namn = i < NAMN.length ? `${stam} AB` : `${stam} ${Math.floor(i / NAMN.length) + 1} AB`;
  const doman = `${stam.toLowerCase().replace(/[^a-z]+/g, "")}${i < NAMN.length ? "" : Math.floor(i / NAMN.length) + 1}.test`;
  // Påhittade nummer i 5599-serien, med rätt kontrollsiffra så att en krock går att visa.
  const nummer = medKontrollsiffra(String(559900000 + i * 13).slice(0, 9));
  return {
    id: `b${i}`,
    name: namn,
    org_number: nummer,
    vat_number: `SE${nummer}01`,
    legal_form: "AB",
    sni_code: i % 3 === 0 ? "61100" : i % 3 === 1 ? "41200" : "69201",
    // Några bolag saknar uppgifter, så att tomma värden och avstängda snabbval syns.
    website: i % 7 === 4 ? null : `https://${doman}`,
    domain: i % 7 === 4 ? null : doman,
    email: i % 7 === 4 ? null : `info@${doman}`,
    phone: i % 5 === 3 ? null : `+4690${String(1000000 + i * 7919).slice(0, 7)}`,
    employees: 4 + ((i * 13) % 180),
    revenue_sek: 2_400_000 + i * 1_730_000,
    relation: RELATIONSFOLJD[i % RELATIONSFOLJD.length],
    customer_since: i % 4 === 3 ? null : `20${18 + (i % 8)}-0${1 + (i % 9)}-15`,
    contract_end: i % 5 === 0 ? "2027-03-31" : null,
    owner: i % 9 === 2 ? null : ANSVARIGA[i % ANSVARIGA.length],
    do_not_contact: i % 11 === 10,
    sole_proprietor: false,
    private_person: false,
    address: { street: `Exempelgatan ${1 + i}`, co: null, postal_code: `9${String(1000 + i * 3).slice(0, 2)} ${String(20 + i).slice(-2)}`, city: ORTER[i % ORTER.length], country: "SE" },
    source: i % 10 === 7 ? "app" : "synk",
    external_ids: i % 10 === 7 ? [] : [{ connection: i % 6 === 5 ? "fortnox" : "hubspot", id: String(48000 + i * 17), last_seen_at: iso(3) }],
    created_at: iso(24 * 40),
    updated_at: iso(2 + i * 5),
    deleted_at: null,
    purge_at: null
  };
}

/**
 * Två privatpersoner, som en anslutning med "Synka privatpersoner" på sparar dem
 * (crm_v1.bolag_ut): märkta, utan organisationsnummer, alltid kontakta inte.
 * Påhittade namn, märkta som exempel här och bara här.
 */
function privatperson(i: number, namn: string, ort: string, timmar: number): Bolag {
  return {
    ...bolag(500 + i),
    id: `pp${i}`,
    name: namn,
    org_number: null,
    vat_number: null,
    legal_form: null,
    sni_code: null,
    website: null,
    domain: null,
    email: null,
    employees: null,
    revenue_sek: null,
    relation: "customer",
    owner: null,
    do_not_contact: true,
    private_person: true,
    address: { street: null, co: null, postal_code: null, city: ort, country: "SE" },
    external_ids: [{ connection: "fortnox", id: String(77000 + i), last_seen_at: iso(27) }],
    updated_at: iso(timmar)
  };
}

/** I papperskorgen: raderade för några dagar sedan, töms 30 dagar efter raderingen. */
function iKorgen(b: Bolag, dagarSedan: number): Bolag {
  const raderad = nu - dagarSedan * 864e5;
  return { ...b, deleted_at: new Date(raderad).toISOString(), purge_at: new Date(raderad + 30 * 864e5).toISOString() };
}

const BOLAG: Bolag[] = [
  ...Array.from({ length: 73 }, (_, i) => bolag(i)),
  privatperson(1, "Kim Påhittsson", "Umeå", 1),
  privatperson(2, "Robin Exempeldotter", "Luleå", 30),
  iKorgen({ ...bolag(80), id: "r1", name: "Raderat Exempel AB" }, 4),
  iKorgen({ ...bolag(81), id: "r2", name: "Gammal Attrapp AB" }, 18),
  // Samma organisationsnummer som ett levande bolag: återställningen krockar (409 med conflicting_id).
  iKorgen({ ...bolag(82), id: "r3", name: "Dubblett Påhitt AB", org_number: bolag(5).org_number }, 26)
].sort((a, b) => (a.name ?? "").localeCompare(b.name ?? "", "sv"));

// Påhittade personer, märkta som exempel med namn som inte finns: samma form som
// person_ut i crm_v1.py. Några saknar uppgifter, så att tomma värden syns.
const FORNAMN = ["Anna", "Erik", "Maja", "Johan", "Sara", "Ola", "Linnea", "Karim", "Elin", "Jonas", "Noor", "Viktor"];
const EFTERNAMN = ["Exempelsson", "Påhittsdotter", "Provström", "Testberg", "Skisslund", "Låtsasson", "Utkastare", "Modellén", "Attrappius"];
const TITLAR = ["VD", "Inköpschef", "Ekonomichef", "Driftansvarig", "Säljchef", null];
const GRUNDER: Personpost["legal_basis"][] = ["contract", "legitimate_interest", "contract", null, "consent"];

function person(i: number, b: Bolag | null): Personpost {
  const fornamn = FORNAMN[i % FORNAMN.length];
  const efternamn = EFTERNAMN[(i * 4 + Math.floor(i / FORNAMN.length)) % EFTERNAMN.length];
  const ascii = (s: string) => s.toLowerCase().replace(/[åä]/g, "a").replace(/ö/g, "o").replace(/é/g, "e").replace(/[^a-z]+/g, "");
  const synk = b && b.external_ids.length > 0;
  return {
    id: `p${i}`,
    first_name: fornamn,
    last_name: efternamn,
    title: TITLAR[i % TITLAR.length],
    email: i % 9 === 5 ? null : `${ascii(fornamn)}.${ascii(efternamn)}@${b?.domain ?? "exempelpost.test"}`,
    phone: i % 4 === 1 ? `+4690${String(2000000 + i * 3119).slice(0, 7)}` : null,
    mobile: i % 6 === 4 ? null : `+4670${String(1000000 + i * 4391).slice(0, 7)}`,
    company_id: b?.id ?? null,
    do_not_contact: i % 13 === 7,
    legal_basis: GRUNDER[i % GRUNDER.length],
    source: synk ? "synk" : i % 2 ? "api" : "app",
    external_ids: synk ? [{ connection: b!.external_ids[0].connection, id: String(91000 + i * 23), last_seen_at: iso(3) }] : [],
    created_at: iso(24 * 30 + i),
    updated_at: iso(6 + i * 3),
    deleted_at: null,
    purge_at: null
  };
}

const LEVANDE_BOLAG = BOLAG.filter((b) => !b.deleted_at && !b.private_person);
const PERSONER: Personpost[] = [
  ...LEVANDE_BOLAG.slice(0, 40).flatMap((b, i) => (i % 3 === 0 ? [person(i * 2, b), person(i * 2 + 1, b)] : [person(i * 2, b)])),
  person(200, null),
  person(201, null),
  person(202, null)
];
{
  const raderad = (p: Personpost, dagar: number): Personpost => ({
    ...p,
    deleted_at: new Date(nu - dagar * 864e5).toISOString(),
    purge_at: new Date(nu - dagar * 864e5 + 30 * 864e5).toISOString()
  });
  PERSONER.push(raderad({ ...person(300, null), id: "rp1" }, 2));
  // Samma e-post som en levande person: återställningen krockar.
  PERSONER.push(raderad({ ...person(301, null), id: "rp2", email: PERSONER[0].email }, 9));
}

const ANSLUTNINGAR: Anslutning[] = [
  { id: "a1", name: "hubspot", system: "hubspot", conflict_rule: "source_wins", missing_records: "mark_former_customer", default_relation: "customer", include_private_persons: false, active: true, last_sync_at: iso(3), created_at: iso(24 * 40) },
  { id: "a2", name: "fortnox", system: "fortnox", conflict_rule: "source_wins", missing_records: "keep", default_relation: "customer", include_private_persons: true, active: true, last_sync_at: iso(27), created_at: iso(24 * 12) }
];

const rakning = (o: Partial<Korning["counts"]>): Korning["counts"] => ({ total: 0, created: 0, updated: 0, unchanged: 0, skipped: 0, conflicts: 0, removed: 0, ...o });

const KORNINGAR: Korning[] = [
  { id: "k4", connection_id: "a1", mode: "delta", status: "processing", started_by: "api", counts: rakning({ total: 900, created: 3, updated: 41, unchanged: 452, skipped: 4 }), errors: [], error: null, issues: [], support: null, created_at: iso(0.02), completed_at: null },
  {
    id: "k3", connection_id: "a1", mode: "full", status: "completed", started_by: "api",
    counts: rakning({ total: 73, created: 2, updated: 8, unchanged: 58, skipped: 4, conflicts: 1, removed: 1 }),
    // Samma form som synken sparar (app/crm/synk.py): koder, inga färdiga meningar.
    // Namnet följer med utom för privatpersoner; krockar_med när krocken går att peka ut.
    errors: [
      { objekt: "bolag", index: 13, externt_id: "48221", namn: "Hittepå Bygg 2 AB", faltfel: [{ falt: "telefon", kod: "telefon_ogiltig" }] },
      { objekt: "bolag", index: 22, externt_id: "48302", namn: "Låtsas Logistik 3 AB", faltfel: [{ falt: "telefon", kod: "telefon_saknar_riktnummer" }] },
      { objekt: "bolag", index: 30, externt_id: "48390", orsak: "saknar_namn" },
      { objekt: "bolag", index: 44, externt_id: "48431", namn: "Attrapp Energi 2 AB", orsak: "orgnr_tillhor_annat_bolag", krockar_med: "b5" },
      { objekt: "bolag", index: 51, externt_id: "48467", faltfel: [{ falt: "orgnr", kod: "orgnr_ar_personnummer" }] }
    ],
    // crm_v1.korning_ut: supportrapport.enkelt, störst först.
    issues: [
      { kind: "ogiltigt_varde", object: "company", field: "phone", count: 2 },
      { kind: "dubblett", object: "company", field: null, count: 1 },
      { kind: "ogiltigt_varde", object: "company", field: "org_number", count: 1 },
      { kind: "saknar_uppgift", object: "company", field: null, count: 1 }
    ],
    support: { forwarded_at: iso(3), ticket: null },
    error: null, created_at: iso(3.1), completed_at: iso(3)
  },
  {
    id: "k2", connection_id: "a2", mode: "delta", status: "completed", started_by: "api",
    counts: rakning({ total: 19, created: 2, updated: 4, unchanged: 8, skipped: 5 }),
    errors: [
      { objekt: "bolag", index: 2, externt_id: "77010", orsak: "privatperson" },
      { objekt: "bolag", index: 5, externt_id: "77013", orsak: "privatperson" },
      { objekt: "bolag", index: 9, externt_id: "77017", orsak: "privatperson" },
      { objekt: "bolag", index: 11, externt_id: "77019", orsak: "privatperson" },
      { objekt: "person", index: 3, externt_id: "91550", orsak: "behandlingen_ar_begransad" }
    ],
    issues: [
      { kind: "privatperson", object: "company", field: null, count: 4 },
      { kind: "begransad", object: "person", field: null, count: 1 }
    ],
    support: { forwarded_at: iso(26.9), ticket: "4821" },
    error: null, created_at: iso(27.1), completed_at: iso(27)
  },
  { id: "k1", connection_id: "a1", mode: "full", status: "failed", started_by: "api", counts: rakning({}), errors: [], error: "tom_full_synk", issues: [], support: { forwarded_at: iso(51), ticket: null }, created_at: iso(51), completed_at: iso(51) }
];

// ---------------------------------------------------------------------------
// Historik och webhooks (handelse_ut, webhook_ut, leverans_ut i crm_v1.py)
// ---------------------------------------------------------------------------

/** Postens historik, påhittad men i API:ts form och ordning (nyast först). Fälten bär aldrig värden. */
function historik(objekt: "company" | "person", id: string, skapad: string | null, andrad: string | null, kalla?: string): Handelse[] {
  const synk = `anslutning:${kalla ?? "hubspot"}`;
  const t = (timmar: number) => new Date(new Date(andrad ?? iso(10)).getTime() - timmar * 36e5).toISOString();
  const falt = objekt === "company" ? [["phone", "address.city"], ["owner"], ["email", "website"]] : [["title"], ["mobile", "email"], ["company_id"]];
  return [
    { seq: 9, object: objekt, id, type: "updated", fields: falt[0], source: "synk", actor: synk, at: t(0) },
    { seq: 7, object: objekt, id, type: "updated", fields: falt[1], source: "app", actor: "anvandare:exempel", at: t(26) },
    { seq: 5, object: objekt, id, type: "restored", fields: [], source: "app", actor: "anvandare:exempel", at: t(70) },
    { seq: 4, object: objekt, id, type: "deleted", fields: [], source: "app", actor: "anvandare:exempel", at: t(74) },
    { seq: 3, object: objekt, id, type: "updated", fields: falt[2], source: "api", actor: "nyckel:n1", at: t(200) },
    { seq: 1, object: objekt, id, type: "created", fields: [], source: "synk", actor: synk, at: skapad ?? t(400) }
  ];
}

const HANDELSETYPER = [
  ...["company", "person", "deal", "task", "note"].flatMap((o) => ["created", "updated", "deleted", "restored", "purged"].map((t) => `${o}.${t}`)),
  "sync.completed"
];

const WEBHOOKAR: Webhook[] = [
  {
    id: "w1", url: "https://hooks.exempelbolaget.test/snajp", description: "Ekonomisystemet", events: ["*"], active: true,
    consecutive_failures: 0, last_success_at: iso(0.4), last_failure_at: iso(30), last_error: null, disabled_reason: null,
    created_at: iso(24 * 20), updated_at: iso(0.4)
  },
  {
    id: "w2", url: "https://intern.exempelbolaget.test/crm-handelser", description: null, events: ["company.created", "company.updated", "sync.completed"], active: false,
    consecutive_failures: 20, last_success_at: iso(24 * 6), last_failure_at: iso(5), last_error: "HTTP 503", disabled_reason: "for_manga_fel",
    created_at: iso(24 * 9), updated_at: iso(5)
  }
];

let leveransnummer = 100;
const leverans = (event: string, status: Leverans["status"], timmar: number, mer: Partial<Leverans> = {}): Leverans => ({
  id: `l${leveransnummer++}`, event, status, attempts: status === "failed" ? 7 : 1, status_code: status === "delivered" ? 200 : status === "failed" ? 503 : null,
  error: status === "failed" ? "HTTP 503" : null, next_attempt_at: null, created_at: iso(timmar), delivered_at: status === "delivered" ? iso(timmar) : null,
  payload: { id: `l${leveransnummer}` }, ...mer
});
const LEVERANSER: Record<string, Leverans[]> = {
  w1: [
    leverans("company.updated", "delivered", 0.4),
    leverans("sync.completed", "delivered", 3),
    leverans("company.created", "failed", 30, { attempts: 7, status_code: 500, error: "HTTP 500" }),
    leverans("person.updated", "delivered", 31)
  ],
  w2: [leverans("company.updated", "failed", 5), leverans("sync.completed", "failed", 27), leverans("company.created", "delivered", 24 * 6)]
};
/** En väntande leverans blir levererad efter två hämtningar, så att förloppet syns. */
const VANTAR: Record<string, number> = {};

const NYCKLAR: Nyckel[] = [
  { id: "n1", namn: "HubSpot-synken", prefix: "snajp_crm_4f2a", omfang: ["crm:las", "crm:synk"], created_at: iso(24 * 40), last_used_at: iso(3), revoked_at: null },
  { id: "n2", namn: "Fortnox", prefix: "snajp_crm_91c0", omfang: ["crm:synk"], created_at: iso(24 * 12), last_used_at: iso(27), revoked_at: null },
  { id: "n3", namn: "Provnyckel", prefix: "snajp_crm_07be", omfang: ["crm:las"], created_at: iso(24 * 70), last_used_at: null, revoked_at: iso(24 * 60) }
];

const DBNAMN: Record<Relation, string> = { customer: "kund", former_customer: "tidigare_kund", prospect: "prospekt", partner: "partner", supplier: "leverantor", other: "ovrigt" };

/** Luhn över tio siffror, som falt.orgnr kontrollerar. */
function luhn(siffror: string) {
  let summa = 0;
  for (let i = 0; i < siffror.length; i++) {
    let d = Number(siffror[i]) * (i % 2 === 0 ? 2 : 1);
    if (d > 9) d -= 9;
    summa += d;
  }
  return summa % 10 === 0;
}

/**
 * Fälten API:t inte kan tolka, i samma form som crm_v1._ogiltig: engelska
 * fältnamn (adressens delar som `address.<del>`) och falt.py:s koder.
 */
function ogiltigaFalt(k: Record<string, unknown>): { field: string; code: string }[] {
  const fel: { field: string; code: string }[] = [];
  const s = (v: unknown) => (typeof v === "string" ? v.trim() : "");
  if (s(k.org_number)) {
    let d = s(k.org_number).replace(/\D/g, "");
    if (d.length === 12 && d.startsWith("16")) d = d.slice(2);
    if (d.length !== 10) fel.push({ field: "org_number", code: "orgnr_fel_langd" });
    else if (!luhn(d)) fel.push({ field: "org_number", code: "orgnr_kontrollsiffra" });
  }
  if (s(k.email) && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s(k.email))) fel.push({ field: "email", code: "epost_ogiltig" });
  if (s(k.phone) && s(k.phone).replace(/\D/g, "").length < 7) fel.push({ field: "phone", code: "telefon_ogiltig" });
  if (s(k.website) && !/^(https?:\/\/)?[^\s/]+\.[^\s/]+/.test(s(k.website))) fel.push({ field: "website", code: "webbplats_ogiltig" });
  for (const datum of ["customer_since", "contract_end"]) {
    if (s(k[datum]) && !/^\d{4}-\d{2}-\d{2}$/.test(s(k[datum]))) fel.push({ field: datum, code: "datum_ogiltigt" });
  }
  const adress = (k.address ?? {}) as Record<string, unknown>;
  if (s(adress.postal_code) && s(adress.postal_code).replace(/\D/g, "").length !== 5) fel.push({ field: "address.postal_code", code: "postnr_ogiltigt" });
  return fel;
}

/** Skriver in ett anrops fält i ett bolag, som synk.andra: bara de fält som skickats, null tömmer. */
function andra(b: Bolag, k: Record<string, unknown>) {
  const enkla = ["name", "vat_number", "legal_form", "sni_code", "email", "owner", "customer_since", "contract_end", "employees", "revenue_sek", "do_not_contact", "relation"] as const;
  const mal = b as unknown as Record<string, unknown>;
  for (const f of enkla) if (f in k) mal[f] = k[f] ?? null;
  if ("org_number" in k) b.org_number = k.org_number ? String(k.org_number).replace(/\D/g, "").slice(-10) : null;
  if ("phone" in k) b.phone = k.phone ? String(k.phone).replace(/[^\d+]/g, "").replace(/^0/, "+46") : null;
  if ("website" in k) {
    const w = k.website ? String(k.website).trim() : "";
    b.website = w ? (/^https?:\/\//.test(w) ? w : `https://${w}`) : null;
    b.domain = w ? w.replace(/^https?:\/\//, "").replace(/^www\./, "").split("/")[0] : null;
  }
  if (k.address && typeof k.address === "object") {
    const a = k.address as Record<string, string | null>;
    b.address = { ...b.address, ...Object.fromEntries(Object.entries(a).map(([n, v]) => [n, v ?? null])) };
  }
  if (b.relation == null) b.relation = "customer";
  b.updated_at = new Date().toISOString();
}

/** Personens fält som API:t inte kan tolka, och krocken på e-post, i samma form som crm_v1. */
function ogiltigaPersonfalt(k: Record<string, unknown>, egen?: Personpost): Response | null {
  const fel: { field: string; code: string }[] = [];
  const s = (v: unknown) => (typeof v === "string" ? v.trim() : "");
  if (s(k.email) && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s(k.email))) fel.push({ field: "email", code: "epost_ogiltig" });
  for (const f of ["phone", "mobile"]) if (s(k[f]) && s(k[f]).replace(/\D/g, "").length < 7) fel.push({ field: f, code: "telefon_ogiltig" });
  if (fel.length) return json({ detail: { code: "invalid_fields", message: "One or more fields could not be interpreted.", meddelande: "Ett eller flera fält gick inte att tolka.", fields: fel } }, 422);
  if (k.company_id && !BOLAG.some((b) => b.id === k.company_id)) {
    return json({ detail: { code: "company_not_found", message: "company_id does not point at a company.", meddelande: "company_id pekar inte på ett bolag." } }, 422);
  }
  const annan = s(k.email) ? PERSONER.find((p) => p !== egen && !p.deleted_at && (p.email ?? "").toLowerCase() === s(k.email).toLowerCase()) : undefined;
  if (annan) return krock(annan.id);
  return null;
}

/** 409 som crm_v1._krock: med id på posten som redan har numret eller adressen. */
function krock(annan: string | null) {
  return json(
    {
      detail: {
        code: "conflict",
        message: "Another record already has this organisation number or email.",
        meddelande: "En annan post har redan det här organisationsnumret eller den här adressen.",
        ...(annan ? { conflicting_id: annan } : {})
      }
    },
    409
  );
}

/** Listans ordning som lagring.lista_poster: namn, ändringsordning eller senast ändrad först; papperskorgen senast raderad först. */
function ordna<T extends { updated_at: string | null; deleted_at?: string | null }>(lista: T[], sort: string, namn: (x: T) => string, korgen: boolean): T[] {
  if (korgen) return [...lista].sort((a, b) => (b.deleted_at ?? "").localeCompare(a.deleted_at ?? ""));
  if (sort === "name") return [...lista].sort((a, b) => namn(a).localeCompare(namn(b), "sv"));
  const stigande = [...lista].sort((a, b) => (a.updated_at ?? "").localeCompare(b.updated_at ?? ""));
  return sort === "-updated" ? stigande.reverse() : stigande;
}

/** Skriver in anropets fält i en person: bara de fält som skickats, null tömmer. */
function andraPerson(p: Personpost, k: Record<string, unknown>) {
  const falt = ["first_name", "last_name", "title", "email", "company_id", "legal_basis", "do_not_contact"] as const;
  const mal = p as unknown as Record<string, unknown>;
  for (const f of falt) if (f in k) mal[f] = k[f] ?? null;
  for (const f of ["phone", "mobile"] as const) if (f in k) p[f] = k[f] ? String(k[f]).replace(/[^\d+]/g, "").replace(/^0/, "+46") : null;
  p.updated_at = new Date().toISOString();
}

function json(kropp: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } });
}

async function svara(url: URL, init?: RequestInit): Promise<Response> {
  await new Promise((r) => setTimeout(r, 180));
  const vag = url.pathname.replace("/api/snajp-support/crm", "");
  const metod = (init?.method ?? "GET").toUpperCase();
  const kropp = typeof init?.body === "string" ? (JSON.parse(init.body) as Record<string, unknown>) : {};

  // ?tillagg=saknas: arbetsytan har varken tillägget eller en provperiod (crm_v1.tillagg_saknas).
  if (tillaggSaknas) {
    return json({ detail: { code: "addon_missing", message: "Snajp CRM is an add-on that is not enabled for this workspace. Contact Snajp.", meddelande: "Snajp CRM är ett tillägg som inte är påslaget för arbetsytan. Kontakta Snajp." } }, 403);
  }
  if (vag === "/v1/me") {
    return json({ tenant: "Exempelbolaget AB", scopes: ["*"], rate_limit: { requests: 600, window_seconds: 60 }, api_version: "1" });
  }

  const levande = () => BOLAG.filter((b) => !b.deleted_at);
  if (vag === "/oversikt") {
    const antal: Record<string, number> = { alla: levande().length };
    for (const b of levande()) antal[DBNAMN[b.relation]] = (antal[DBNAMN[b.relation]] ?? 0) + 1;
    return json({ bolag: antal, personer: PERSONER.filter((p) => !p.deleted_at).length, anslutningar: ANSLUTNINGAR.length, korningar: KORNINGAR });
  }
  if (vag === "/v1/companies" && metod === "GET") {
    // Samma parametrar som API:t (crm_v1.py): limit 1 till 500 (50 utan), sort
    // "updated" (ändringsordning, äldst först, standard) eller "name", updated_since.
    // Fritexten söker samma kolumner som lagring.lista_poster: namn, orgnr, domän, postort.
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const rel = url.searchParams.get("relation");
    const start = Number(url.searchParams.get("cursor") ?? 0);
    const limit = Math.min(500, Math.max(1, Number(url.searchParams.get("limit") ?? 50)));
    const sedan = url.searchParams.get("updated_since");
    const sort = url.searchParams.get("sort") ?? "updated";
    const medRaderade = url.searchParams.get("include_deleted") === "true";
    const korgen = url.searchParams.get("only_deleted") === "true";
    const traffar = BOLAG.filter(
      (b) =>
        (korgen ? !!b.deleted_at : medRaderade || !b.deleted_at) &&
        (!rel || b.relation === rel) &&
        (!sedan || (b.updated_at ?? "") >= sedan) &&
        (!q || [b.name, b.org_number, orgnrVisning(b.org_number), b.domain, b.address.city].some((v) => (v ?? "").toLowerCase().includes(q)))
    );
    const ordnade = ordna(traffar, sort, (b) => b.name ?? "", korgen);
    return json({ data: ordnade.slice(start, start + limit), next_cursor: start + limit < ordnade.length ? String(start + limit) : null });
  }
  const bolagshistorik = vag.match(/^\/v1\/companies\/([^/]+)\/history$/);
  if (bolagshistorik) {
    const b = BOLAG.find((x) => x.id === decodeURIComponent(bolagshistorik[1]));
    if (!b) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    // Ett bolag skapat för hand i förhandsvisningen har bara sin skapelse.
    if (b.source === "api") return json({ data: [{ seq: 1, object: "company", id: b.id, type: "created", fields: [], source: "app", actor: null, at: b.created_at }] });
    return json({ data: historik("company", b.id, b.created_at, b.updated_at, b.external_ids[0]?.connection) });
  }
  const bolagsdel = vag.match(/^\/v1\/companies\/([^/]+)(\/restore)?$/);
  if (bolagsdel) {
    const b = BOLAG.find((x) => x.id === decodeURIComponent(bolagsdel[1]));
    const finns = b && (!b.deleted_at || url.searchParams.get("include_deleted") === "true" || bolagsdel[2]);
    if (!b || !finns) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    if (bolagsdel[2] && metod === "POST") {
      const annan = b.org_number ? BOLAG.find((x) => x !== b && !x.deleted_at && x.org_number === b.org_number) : undefined;
      if (annan) return krock(annan.id);
      b.deleted_at = null;
      b.purge_at = null;
      b.updated_at = new Date().toISOString();
      return json(b);
    }
    if (metod === "GET") return json(b);
    if (metod === "DELETE") {
      // Kvar i 30 dagar, går att återställa (crm_v1.py: radera_bolag).
      b.deleted_at = new Date().toISOString();
      b.purge_at = new Date(Date.now() + 30 * 864e5).toISOString();
      return json(null, 204);
    }
    if (metod === "PATCH") {
      const fel = ogiltigaFalt(kropp);
      if (fel.length) return json({ detail: { code: "invalid_fields", message: "One or more fields could not be interpreted.", meddelande: "Ett eller flera fält gick inte att tolka.", fields: fel } }, 422);
      const nyckel = kropp.org_number ? String(kropp.org_number).replace(/\D/g, "") : null;
      const annan = nyckel ? BOLAG.find((x) => x !== b && !x.deleted_at && x.org_number === nyckel) : undefined;
      if (annan) return krock(annan.id);
      andra(b, kropp);
      // En privatperson är alltid kontakta inte (crm_v1.CompanyIn.private_person).
      if (b.private_person) b.do_not_contact = true;
      return json(b);
    }
  }
  if (vag === "/v1/companies" && metod === "POST") {
    const fel = ogiltigaFalt(kropp);
    if (fel.length) return json({ detail: { code: "invalid_fields", message: "One or more fields could not be interpreted.", meddelande: "Ett eller flera fält gick inte att tolka.", fields: fel } }, 422);
    const nytt: Bolag = {
      ...bolag(900 + BOLAG.length),
      id: `b${900 + BOLAG.length}`,
      name: null, org_number: null, vat_number: null, legal_form: null, sni_code: null, website: null, domain: null, email: null, phone: null,
      employees: null, revenue_sek: null, relation: "customer", customer_since: null, contract_end: null, owner: null, do_not_contact: null,
      address: { street: null, co: null, postal_code: null, city: null, country: "SE" },
      source: "api", external_ids: [], created_at: new Date().toISOString()
    };
    andra(nytt, kropp);
    BOLAG.unshift(nytt);
    return json(nytt, 201);
  }
  if (vag === "/v1/people" && metod === "GET") {
    // Som lista_personer: company_id, q över förnamn, efternamn, e-post och titel,
    // sort "name" (efternamnet) eller "updated" (ändringsordning, äldst först).
    const bolagId = url.searchParams.get("company_id");
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const start = Number(url.searchParams.get("cursor") ?? 0);
    const limit = Math.min(500, Math.max(1, Number(url.searchParams.get("limit") ?? 50)));
    const sort = url.searchParams.get("sort") ?? "updated";
    const medRaderade = url.searchParams.get("include_deleted") === "true";
    const korgen = url.searchParams.get("only_deleted") === "true";
    const traffar = PERSONER.filter(
      (p) =>
        (korgen ? !!p.deleted_at : medRaderade || !p.deleted_at) &&
        (!bolagId || p.company_id === bolagId) &&
        (!q || [p.first_name, p.last_name, p.email, p.title].some((v) => (v ?? "").toLowerCase().includes(q)))
    );
    const ordnade = ordna(traffar, sort, (p) => `${p.last_name ?? ""} ${p.id}`, korgen);
    return json({ data: ordnade.slice(start, start + limit), next_cursor: start + limit < ordnade.length ? String(start + limit) : null });
  }
  const personhistorik = vag.match(/^\/v1\/people\/([^/]+)\/history$/);
  if (personhistorik) {
    const p = PERSONER.find((x) => x.id === decodeURIComponent(personhistorik[1]));
    if (!p) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    return json({ data: historik("person", p.id, p.created_at ?? null, p.updated_at, p.external_ids?.[0]?.connection) });
  }
  const persondel = vag.match(/^\/v1\/people\/([^/]+)(\/restore)?$/);
  if (persondel) {
    const p = PERSONER.find((x) => x.id === decodeURIComponent(persondel[1]));
    const finns = p && (!p.deleted_at || url.searchParams.get("include_deleted") === "true" || persondel[2]);
    if (!p || !finns) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    if (persondel[2] && metod === "POST") {
      const annan = p.email ? PERSONER.find((x) => x !== p && !x.deleted_at && (x.email ?? "").toLowerCase() === p.email!.toLowerCase()) : undefined;
      if (annan) return krock(annan.id);
      p.deleted_at = null;
      p.purge_at = null;
      p.updated_at = new Date().toISOString();
      return json(p);
    }
    if (metod === "GET") return json(p);
    if (metod === "DELETE") {
      p.deleted_at = new Date().toISOString();
      p.purge_at = new Date(Date.now() + 30 * 864e5).toISOString();
      return json(null, 204);
    }
    if (metod === "PATCH") {
      const fel = ogiltigaPersonfalt(kropp, p);
      if (fel) return fel;
      andraPerson(p, kropp);
      return json(p);
    }
  }
  if (vag === "/v1/people" && metod === "POST") {
    const fel = ogiltigaPersonfalt(kropp);
    if (fel) return fel;
    const ny: Personpost = { ...person(300 + PERSONER.length, null), first_name: null, last_name: null, title: null, email: null, phone: null, mobile: null, legal_basis: null, do_not_contact: false, source: "api", external_ids: [], created_at: new Date().toISOString() };
    andraPerson(ny, kropp);
    PERSONER.unshift(ny);
    return json(ny, 201);
  }
  if (vag === "/v1/connections" && metod === "GET") return json({ data: ANSLUTNINGAR });
  const anslutningsdel = vag.match(/^\/v1\/connections\/([^/]+)$/);
  if (anslutningsdel && anslutningsdel[1] !== "systems") {
    // På id eller på namn, som lagring.hamta_anslutning.
    const ref = decodeURIComponent(anslutningsdel[1]).toLowerCase();
    const a = ANSLUTNINGAR.find((x) => x.id === ref || x.name.toLowerCase() === ref);
    if (!a) return json({ detail: { code: "connection_not_found", message: "The connection does not exist.", meddelande: "Anslutningen finns inte." } }, 404);
    if (metod === "GET") return json(a);
    if (metod === "DELETE") {
      ANSLUTNINGAR.splice(ANSLUTNINGAR.indexOf(a), 1);
      for (const b of BOLAG) b.external_ids = b.external_ids.filter((x) => x.connection !== a.name);
      return json(null, 204);
    }
    if (metod === "PATCH") {
      if ("name" in kropp) {
        const namn = String(kropp.name ?? "").trim();
        if (namn.length < 1 || namn.length > 80) return json({ detail: { code: "invalid_fields", message: "name must be 1 to 80 characters.", meddelande: "name ska vara 1 till 80 tecken." } }, 422);
        if (ANSLUTNINGAR.some((x) => x !== a && x.name.toLowerCase() === namn.toLowerCase())) {
          return json({ detail: { code: "conflict", message: "A connection with this name already exists.", meddelande: "Det finns redan en anslutning med det namnet." } }, 409);
        }
        a.name = namn;
      }
      if (kropp.conflict_rule) a.conflict_rule = kropp.conflict_rule as Anslutning["conflict_rule"];
      if (kropp.missing_records) a.missing_records = kropp.missing_records as Anslutning["missing_records"];
      if (kropp.default_relation) a.default_relation = kropp.default_relation as Relation;
      if (typeof kropp.active === "boolean") a.active = kropp.active;
      if (typeof kropp.include_private_persons === "boolean") a.include_private_persons = kropp.include_private_persons;
      return json(a);
    }
  }
  if (vag === "/v1/connections" && metod === "POST") {
    const namn = String(kropp.name ?? "").trim();
    if (namn.length < 1 || namn.length > 80) return json({ detail: { code: "invalid_fields", message: "name must be 1 to 80 characters.", meddelande: "name ska vara 1 till 80 tecken." } }, 422);
    const ny: Anslutning = {
      id: `a${ANSLUTNINGAR.length + 1}`,
      name: namn,
      system: String(kropp.system ?? "generisk"),
      conflict_rule: (kropp.conflict_rule as Anslutning["conflict_rule"]) ?? "source_wins",
      missing_records: (kropp.missing_records as Anslutning["missing_records"]) ?? "keep",
      default_relation: (kropp.default_relation as Relation) ?? "customer",
      include_private_persons: kropp.include_private_persons === true,
      active: true,
      last_sync_at: null,
      created_at: new Date().toISOString()
    };
    if (ANSLUTNINGAR.some((a) => a.name.toLowerCase() === ny.name.toLowerCase())) {
      return json({ detail: { code: "conflict", message: "A connection with this name already exists.", meddelande: "Det finns redan en anslutning med det namnet." } }, 409);
    }
    ANSLUTNINGAR.push(ny);
    return json(ny, 201);
  }
  if (vag === "/v1/sync/runs") {
    // Den pågående körningen rör sig mellan hämtningarna, så att förloppet syns.
    const pagar = KORNINGAR[0];
    if (pagar.status === "processing") {
      pagar.counts.unchanged += 37;
      pagar.counts.total = Math.max(pagar.counts.total, 900);
      const klart = pagar.counts.created + pagar.counts.updated + pagar.counts.unchanged + pagar.counts.skipped;
      if (klart >= pagar.counts.total) {
        pagar.status = "completed";
        pagar.completed_at = new Date().toISOString();
      }
    }
    return json({ data: KORNINGAR });
  }
  const korningsdel = vag.match(/^\/v1\/sync\/runs\/([^/]+)$/);
  if (korningsdel && metod === "GET") {
    const k = KORNINGAR.find((x) => x.id === decodeURIComponent(korningsdel[1]));
    return k ? json(k) : json({ detail: { code: "run_not_found", message: "The run does not exist.", meddelande: "Körningen finns inte." } }, 404);
  }
  if (vag === "/nycklar" && metod === "GET") return json({ nycklar: NYCKLAR });
  if (vag === "/nycklar" && metod === "POST") {
    const ny: Nyckel = { id: `n${NYCKLAR.length + 1}`, namn: String(kropp.namn), prefix: "snajp_crm_e1d3", omfang: (kropp.omfang as string[]) ?? [], created_at: new Date().toISOString(), last_used_at: null, revoked_at: null };
    NYCKLAR.unshift(ny);
    return json({ ...ny, api_key: "snajp_crm_e1d3exempelnyckelsomintegar000000000000" }, 201);
  }
  if (vag.startsWith("/nycklar/") && metod === "DELETE") {
    const n = NYCKLAR.find((x) => x.id === vag.split("/")[2]);
    if (n) n.revoked_at = new Date().toISOString();
    return json(null, 204);
  }
  // ---- Webhooks (crm_v1.py, Webhooks) ----------------------------------------
  if (vag === "/v1/webhooks/events") return json({ events: HANDELSETYPER, signature_header: "X-Snajp-Signature" });
  if (vag === "/v1/webhooks" && metod === "GET") return json({ data: WEBHOOKAR });
  if (vag === "/v1/webhooks" && metod === "POST") {
    const adress = String(kropp.url ?? "").trim();
    if (!/^https:\/\/[^\s/]+\.[^\s/]+/.test(adress)) return json({ detail: { code: "invalid_url", message: "url must be a public https address.", meddelande: "url ska vara en publik https-adress." } }, 422);
    if (WEBHOOKAR.length >= 10) return json({ detail: { code: "too_many_webhooks", message: "At most 10 webhooks.", meddelande: "Högst 10 webhooks per arbetsyta." } }, 422);
    const handelser = Array.isArray(kropp.events) && kropp.events.length ? (kropp.events as string[]) : ["*"];
    const ny: Webhook = {
      id: `w${WEBHOOKAR.length + 10}`, url: adress, description: (kropp.description as string) ?? null, events: handelser, active: true,
      consecutive_failures: 0, last_success_at: null, last_failure_at: null, last_error: null, disabled_reason: null,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString()
    };
    WEBHOOKAR.push(ny);
    LEVERANSER[ny.id] = [];
    // Hemligheten följer bara med svaret när webhooken skapas (webhook_ut med hemlighet).
    return json({ ...ny, secret: "whsec_exempel4f2a9c0e1d7b3a5c8e6f0a2b4c6d8e0f" }, 201);
  }
  const webhookdel = vag.match(/^\/v1\/webhooks\/([^/]+)(\/test|\/deliveries(?:\/([^/]+)\/retry)?)?$/);
  if (webhookdel) {
    const w = WEBHOOKAR.find((x) => x.id === decodeURIComponent(webhookdel[1]));
    if (!w) return json({ detail: { code: "webhook_not_found", message: "The webhook does not exist.", meddelande: "Webhooken finns inte." } }, 404);
    const logg = (LEVERANSER[w.id] ??= []);
    if (webhookdel[2] === "/test" && metod === "POST") {
      const ping = leverans("ping", "pending", 0, { attempts: 0 });
      VANTAR[ping.id] = 2;
      logg.unshift(ping);
      return json(ping, 202);
    }
    if (webhookdel[3] && metod === "POST") {
      const gammal = logg.find((l) => l.id === decodeURIComponent(webhookdel[3]));
      if (!gammal) return json({ detail: { code: "delivery_not_found", message: "The delivery does not exist.", meddelande: "Leveransen finns inte." } }, 404);
      const igen = leverans(gammal.event, "pending", 0, { attempts: 0 });
      VANTAR[igen.id] = 2;
      logg.unshift(igen);
      return json(igen, 202);
    }
    if (webhookdel[2] === "/deliveries") {
      // En väntande leverans går fram efter två hämtningar.
      for (const l of logg) {
        if (l.status !== "pending" || VANTAR[l.id] == null) continue;
        VANTAR[l.id] -= 1;
        if (VANTAR[l.id] <= 0) {
          Object.assign(l, { status: "delivered", attempts: 1, status_code: 200, delivered_at: new Date().toISOString() });
          w.last_success_at = l.delivered_at;
          delete VANTAR[l.id];
        }
      }
      return json({ data: logg });
    }
    if (metod === "GET") return json(w);
    if (metod === "PATCH") {
      if (typeof kropp.active === "boolean") {
        w.active = kropp.active;
        // Att slå på en avstängd webhook nollställer räknaren (WebhookIn.active).
        if (kropp.active) Object.assign(w, { consecutive_failures: 0, disabled_reason: null });
      }
      w.updated_at = new Date().toISOString();
      return json(w);
    }
    if (metod === "DELETE") {
      WEBHOOKAR.splice(WEBHOOKAR.indexOf(w), 1);
      delete LEVERANSER[w.id];
      return json(null, 204);
    }
  }
  return json({ detail: "Förhandsvisningen har inget svar för den här vägen." }, 404);
}

/** Satt av `?tillagg=saknas`: varje anrop svarar då 403 addon_missing. */
let tillaggSaknas = false;

let fangar = false;

/**
 * Fångar CRM-anropen en gång per sidladdning, vid första renderingen och alltså
 * före vyernas första hämtning. Den återställs aldrig: en effekt som städade
 * hade i utvecklingsläge (där React kör effekter två gånger) lämnat vyerna att
 * hämta mot det riktiga API:t. Fångsten gäller bara medan adressen är en
 * förhandsvisning, så en riktig CRM-sida kan aldrig få låtsassvar.
 */
function fangaAnrop() {
  if (fangar || typeof window === "undefined") return;
  fangar = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (in_: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof in_ === "string" ? in_ : in_ instanceof URL ? in_.href : in_.url, window.location.origin);
    const galler = window.location.pathname.startsWith("/forhandsvisning/") && url.pathname.startsWith("/api/snajp-support/crm");
    return galler ? svara(url, init) : riktig(in_, init);
  };
}

/**
 * Vem som tittar. Plattformsadmin som standard (CRM:et släpps bara till admin i
 * dag); `?vy=kund` visar kundens nivå (synkens enkla ord, tilläggets besked).
 * Ett påhittat läge, aldrig en riktig session: ingen identitet att jämföra mot.
 */
function lage(kund: boolean): DashboardState {
  return {
    products: ["leads", "support"],
    addons: [],
    workspaceName: "Exempelbolaget AB",
    userEmail: null,
    signedIn: false,
    isDemo: false,
    isPlatformAdmin: !kund,
    vy: "admin",
    impersonation: null,
    arLasare: false,
    initialScope: "both"
  };
}

export function CrmForhandsvisning({ tema, vy, kund, utanTillagg }: Readonly<{ tema: Tema; vy: CrmVy; kund: boolean; utanTillagg: boolean }>) {
  tillaggSaknas = utanTillagg;
  fangaAnrop();

  return (
    <DashboardProvider state={lage(kund)}>
      <CrmRam tema={tema} bas="/forhandsvisning/crm" arbetsyta="Exempelbolaget AB">
        {vy === "oversikt" ? <OversiktVy bas="/forhandsvisning/crm" /> : null}
        {vy === "bolag" ? <BolagVy /> : null}
        {vy === "personer" ? <PersonerVy bas="/forhandsvisning/crm" /> : null}
        {vy === "synk" ? <SynkVy utvecklarvag="/forhandsvisning/crm/utvecklare" /> : null}
        {vy === "utvecklare" ? <UtvecklareVy /> : null}
      </CrmRam>
    </DashboardProvider>
  );
}
