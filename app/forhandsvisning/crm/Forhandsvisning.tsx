"use client";

import { AffarerVy } from "@/components/crm/app/AffarerVy";
import { BolagVy } from "@/components/crm/app/BolagVy";
import { CrmRam } from "@/components/crm/app/CrmRam";
import { LeadsVy } from "@/components/crm/app/iris/LeadsVy";
import { UtkastVy } from "@/components/crm/app/iris/UtkastVy";
import { KorningVy } from "@/components/crm/app/iris/KorningVy";
import { KorningarVy } from "@/components/crm/app/iris/KorningarVy";
import type { Skalatgarder } from "@/components/crm/app/Skalet";
import { svaraIris } from "./svar/iris";
import { svaraKorningar } from "./svar/korningar";
import { svaraUtkast } from "./svar/utkast";
import { svaraSkalet } from "./svar/skalet";
import { OversiktVy } from "@/components/crm/app/OversiktVy";
import { PersonerVy } from "@/components/crm/app/PersonerVy";
import { SparrarVy } from "@/components/crm/app/SparrarVy";
import { SynkVy } from "@/components/crm/app/SynkVy";
import { UppgifterVy } from "@/components/crm/app/UppgifterVy";
import { UtvecklareVy } from "@/components/crm/app/UtvecklareVy";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { BILAGA_MAX, BILAGETYPER, orgnrVisning, type Anslutning, type Bilaga, type Bolag, type Handelse, type Korning, type Leverans, type Nyckel, type Relation, type Webhook } from "@/lib/crm/api";
import type { Affar, Affarssteg } from "@/lib/crm/affar";
import type { DashboardState } from "@/lib/data/dashboard";
import type { Personpost } from "@/lib/crm/person";
import { SLAG_I_KANAL, gissaSlag, type Sparr, type Sparrkanal, type Sparrorsak, type Sparrslag } from "@/lib/crm/sparr";
import type { Tema } from "@/lib/tema";
import type { Uppgift } from "@/lib/crm/uppgift";

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
    registry_status: i % 4 === 0 ? "active" : null,
    registry_checked_at: i % 4 === 0 ? iso(24 * 3) : null,
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
// Två bolag som sagt nej: relationen ej aktuell (skild från prospekt, och inte fri för Iris).
for (const id of ["b16", "b33"]) {
  const b = BOLAG.find((x) => x.id === id);
  if (b) b.relation = "not_relevant";
}

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
    // Var fjärde person saknar källa, så att vyn Utan källa har något att visa.
    source_type: i % 4 === 3 ? null : synk ? "sync" : i % 2 ? "company_website" : "manual",
    source_name: i % 4 === 3 ? null : synk ? b!.external_ids[0].connection : i % 2 ? `${b?.domain ?? "exempelpost.test"}/kontakt` : null,
    collected_at: iso(24 * 30 + i),
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
    support: { forwarded_at: iso(26.9), ticket: "F-0041" },
    error: null, created_at: iso(27.1), completed_at: iso(27)
  },
  { id: "k1", connection_id: "a1", mode: "full", status: "failed", started_by: "api", counts: rakning({}), errors: [], error: "tom_full_synk", issues: [], support: { forwarded_at: iso(51), ticket: "F-0046" }, created_at: iso(51), completed_at: iso(51) }
];

// ---------------------------------------------------------------------------
// Historik och webhooks (handelse_ut, webhook_ut, leverans_ut i crm_v1.py)
// ---------------------------------------------------------------------------

/** Postens historik, påhittad men i API:ts form och ordning (nyast först). Fälten bär aldrig värden. */
function historik(objekt: "company" | "person" | "deal", id: string, skapad: string | null, andrad: string | null, kalla?: string): Handelse[] {
  const synk = `anslutning:${kalla ?? "hubspot"}`;
  const t = (timmar: number) => new Date(new Date(andrad ?? iso(10)).getTime() - timmar * 36e5).toISOString();
  const falt =
    objekt === "company"
      ? [["phone", "address.city"], ["owner"], ["email", "website"]]
      : objekt === "deal"
        ? [["stage_id"], ["amount", "expected_close_date"], ["owner"]]
        : [["title"], ["mobile", "email"], ["company_id"]];
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

// ---------------------------------------------------------------------------
// Spärrlistan (sparr_ut i crm_v1_sparr.py). Påhittade adresser och nummer:
// domänen .test och PTS nummerserie för fiktion (070-174 06 xx).
// ---------------------------------------------------------------------------

const sparr = (i: number, channel: Sparrkanal, kind: Sparrslag, value: string, reason: Sparrorsak, source: string, timmar: number, note: string | null = null, havd: number | null = null): Sparr => ({
  id: `sp${i}`, channel, kind, value, reason, note, source, company_id: null, person_id: null, created_at: iso(timmar), lifted_at: havd == null ? null : iso(havd)
});

const SPARRAR: Sparr[] = [
  sparr(1, "all", "email", "inkop@fiktivtelefoni.test", "objection", "outcome", 5, "Sa nej i samtal, vill inte ha fler mejl."),
  sparr(2, "phone", "phone", "+46701740611", "nix", "import", 26),
  sparr(3, "phone", "phone", "+46701740624", "nix", "import", 26),
  sparr(4, "phone", "phone", "+46701740638", "nix", "import", 26),
  sparr(5, "email", "domain", "latsaslogistik.test", "customer_request", "app", 49, "Hela bolaget, enligt deras vd."),
  sparr(6, "email", "email", "anna@hittepabygg.test", "unsubscribe", "api", 74),
  sparr(7, "email", "email", "info@skenbarredovisning.test", "bounce", "sync", 120),
  sparr(8, "all", "org_number", "5560000019", "customer_request", "app", 190, "Avslutad kund."),
  sparr(9, "phone", "phone", "+46701740652", "objection", "outcome", 240),
  sparr(10, "email", "email", "kontakt@kulissevent.test", "other", "app", 300, "Tvist om faktura, vänta tills den är löst."),
  sparr(11, "email", "email", "vd@modellverket.test", "customer_request", "app", 500, null, 30),
  sparr(12, "phone", "phone", "+46701740699", "nix", "import", 700, null, 200)
];
let sparrlopnr = 100;

/** Samma skrivsätt som API:t sparar: gemener, och telefon i E.164. Returnerar null när värdet inte går att läsa. */
function sparrvarde(slag: Sparrslag, varde: string): string | null {
  const v = varde.trim();
  if (slag === "email") return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v) ? v.toLowerCase() : null;
  if (slag === "domain") return /^[a-z0-9-]+(\.[a-z0-9-]+)+$/i.test(v) ? v.toLowerCase() : null;
  const siffror = v.replace(/[^\d+]/g, "");
  if (slag === "phone") return /^(\+\d{8,15}|0\d{6,12})$/.test(siffror) ? siffror.replace(/^0/, "+46") : null;
  return /^\d{10}$/.test(siffror.replace("+", "")) ? siffror.replace("+", "") : null;
}

// ---------------------------------------------------------------------------
// Affärer och steg (steg_ut, affar_ut i crm_v1_objekt.py)
// ---------------------------------------------------------------------------

/** Standardstegen en arbetsyta får första gången (objekt.STANDARDSTEG). */
const STEG: Affarssteg[] = [
  { id: "s1", name: "Ny", position: 1, probability: 10, type: "open", color: null },
  { id: "s2", name: "Kvalificerad", position: 2, probability: 25, type: "open", color: null },
  { id: "s3", name: "Möte bokat", position: 3, probability: 40, type: "open", color: null },
  { id: "s4", name: "Offert skickad", position: 4, probability: 60, type: "open", color: null },
  { id: "s5", name: "Förhandling", position: 5, probability: 80, type: "open", color: null },
  { id: "s6", name: "Vunnen", position: 6, probability: 100, type: "won", color: null },
  { id: "s7", name: "Förlorad", position: 7, probability: 0, type: "lost", color: null }
];

/** Påhittade affärer: [steg, namn, belopp, väntat avslut, bolagets plats i listan]. */
const AFFARSRADER: [string, string, number | null, string | null, number][] = [
  ["s1", "Växel för nya kontoret", 48_000, "2027-01-29", 0],
  ["s1", "Mobilabonnemang, 12 anställda", 86_400, null, 3],
  ["s1", "Kundtjänst på kvällstid", null, "2027-02-12", 7],
  ["s2", "Telefoniavtal 2027", 240_000, "2026-12-18", 1],
  ["s2", "Svarsgrupp för supporten", 64_000, "2027-01-15", 9],
  ["s3", "Uppgradering till fiber", 132_000, "2026-11-14", 4],
  ["s3", "Supportagent på webben", 96_000, "2026-12-09", 12],
  ["s3", "Samtalsstatistik", 28_000, null, 15],
  ["s4", "Treårsavtal, hela koncernen", 720_000, "2026-12-22", 2],
  ["s4", "Leadslistor, första kvartalet", 54_000, "2026-12-04", 18],
  ["s5", "Förlängning av avtalet", 310_000, "2026-12-01", 6],
  ["s6", "Växel och mobiler", 188_000, "2026-11-10", 10],
  ["s6", "Supportagent, pilot", 36_000, "2026-10-28", 13],
  ["s7", "Callcenterlösning", 420_000, "2026-11-03", 21]
];

type Affarspost = Affar & { purge_at: string | null };

const AFFARER: Affarspost[] = AFFARSRADER.map(([steg, namn, summa, avslut, plats], i) => {
  const b = LEVANDE_BOLAG[plats % LEVANDE_BOLAG.length];
  const stangd = steg === "s6" || steg === "s7";
  return {
    id: `d${i}`,
    name: namn,
    company_id: b.id,
    person_id: PERSONER.find((p) => p.company_id === b.id && !p.deleted_at)?.id ?? null,
    stage_id: steg,
    amount: summa,
    currency: "SEK",
    // Två affärer har en egen sannolikhet; de andra följer stegets.
    probability: i === 3 ? 35 : i === 8 ? 70 : null,
    expected_close_date: avslut,
    closed_at: stangd ? iso(24 * (6 + i)) : null,
    lost_reason: steg === "s7" ? "Hade redan en växel hos sin mobiloperatör" : null,
    lost_reason_code: steg === "s7" ? "competitor" : null,
    owner: i % 5 === 2 ? null : ANSVARIGA[i % ANSVARIGA.length],
    position: (i + 1) * 1000,
    created_at: iso(24 * (20 + i * 2)),
    updated_at: iso(3 + i * 7),
    deleted_at: null,
    purge_at: null
  };
});
{
  const raderad = nu - 5 * 864e5;
  AFFARER.push({
    ...AFFARER[0], id: "rd1", name: "Gammalt telefoniavtal", stage_id: "s2", position: 99_000,
    deleted_at: new Date(raderad).toISOString(), purge_at: new Date(raderad + 30 * 864e5).toISOString()
  });
}

/** Tavlan som crm_v1_objekt.tavla: stegen i ordning, levande affärer i tavlans ordning, antal och summor. */
function tavlan() {
  return {
    stages: STEG.map((s) => {
      const deals = AFFARER.filter((a) => !a.deleted_at && a.stage_id === s.id).sort((x, y) => (x.position ?? 0) - (y.position ?? 0));
      const per: Record<string, number> = {};
      for (const a of deals) per[a.currency || "SEK"] = (per[a.currency || "SEK"] ?? 0) + (a.amount ?? 0);
      return { ...s, deals, count: deals.length, amount_total: Object.values(per).reduce((x, y) => x + y, 0), amount_by_currency: per };
    })
  };
}

/** Lägger affären i ett steg, före en annan affär eller sist, som objekt.flytta. Stängda steg sätter closed_at. */
function placera(a: Affarspost, stegId: string, foreId: string | null) {
  const iSteget = AFFARER.filter((x) => x !== a && !x.deleted_at && x.stage_id === stegId).sort((x, y) => (x.position ?? 0) - (y.position ?? 0));
  const plats = foreId ? iSteget.findIndex((x) => x.id === foreId) : -1;
  const ordning = plats < 0 ? [...iSteget, a] : [...iSteget.slice(0, plats), a, ...iSteget.slice(plats)];
  ordning.forEach((x, i) => (x.position = (i + 1) * 1000));
  if (a.stage_id !== stegId) {
    const typ = STEG.find((s) => s.id === stegId)?.type ?? "open";
    a.closed_at = typ === "open" ? null : new Date().toISOString();
  }
  a.stage_id = stegId;
  a.updated_at = new Date().toISOString();
}

/** Skriver in anropets fält i en affär: bara de fält som skickats, null tömmer. */
function andraAffar(a: Affarspost, k: Record<string, unknown>) {
  const falt = ["name", "company_id", "person_id", "amount", "currency", "probability", "expected_close_date", "lost_reason", "lost_reason_code", "owner"] as const;
  const mal = a as unknown as Record<string, unknown>;
  for (const f of falt) if (f in k) mal[f] = k[f] ?? null;
  if (typeof k.stage_id === "string" && k.stage_id !== a.stage_id) placera(a, k.stage_id, null);
  a.updated_at = new Date().toISOString();
}

/** Affärens fält som API:t inte tar emot, i samma form som crm_v1_objekt._objektfel. */
function ogiltigAffar(k: Record<string, unknown>, ny: boolean): Response | null {
  const fel: { field: string; code: string }[] = [];
  if (ny && !String(k.name ?? "").trim()) fel.push({ field: "name", code: "saknas" });
  if (typeof k.expected_close_date === "string" && !/^\d{4}-\d{2}-\d{2}$/.test(k.expected_close_date)) fel.push({ field: "expected_close_date", code: "datum_ogiltigt" });
  if (fel.length) return json({ detail: { code: "invalid_fields", message: "One or more fields could not be interpreted.", meddelande: "Ett eller flera fält gick inte att tolka.", fields: fel } }, 422);
  if (k.company_id && !BOLAG.some((b) => b.id === k.company_id && !b.deleted_at)) {
    return json({ detail: { code: "company_not_found", message: "company_id does not point at a company.", meddelande: "company_id pekar inte på något bolag." } }, 422);
  }
  if (k.stage_id && !STEG.some((s) => s.id === k.stage_id)) {
    return json({ detail: { code: "stage_not_found", message: "stage_id does not point at a deal stage.", meddelande: "stage_id pekar inte på något steg." } }, 422);
  }
  return null;
}

// ---------------------------------------------------------------------------
// Tidslinjen (tidslinjepost_ut i crm_v1_tidslinje.py)
// ---------------------------------------------------------------------------

type Tidsrad = { key: string; type: string; at: string; origin: "crm" | "iris" | "support"; title: string | null; text: string | null; data: Record<string, unknown>; link: { kind: string; id: string } | null };

/** Det som skrivits i förhandsvisningen (anteckningar, uppgifter, aktiviteter), per post. */
const SKRIVET: Record<string, Tidsrad[]> = {};
let radnummer = 500;

/** Postens egna ändringar i tidslinjens form. */
const egna = (h: Handelse[]): Tidsrad[] =>
  h.map((x) => ({ key: `crm:${x.id}:${x.seq}`, type: `record_${x.type}`, at: x.at ?? iso(1), origin: "crm", title: null, text: null, data: { fields: x.fields, source: x.source, actor: x.actor }, link: null }));

/** Bolagets tidslinje: egna ändringar, arbetet i CRM:et, ett lead hos Iris och ett supportärende. Allt påhittat. */
function bolagstidslinje(b: Bolag): Tidsrad[] {
  const affarer = AFFARER.filter((a) => a.company_id === b.id && !a.deleted_at);
  const rader: Tidsrad[] = [
    ...egna(b.source === "api" ? [] : historik("company", b.id, b.created_at, b.updated_at, b.external_ids[0]?.connection)),
    { key: `ant:${b.id}`, type: "note", at: iso(20), origin: "crm", title: "Efter mötet", text: "De vill samla telefonin hos en leverantör före årsskiftet. Offert på växel och tolv mobiler, och en fråga om bindningstid.", data: { author: ANSVARIGA[0] }, link: { kind: "note", id: `n-${b.id}` } },
    { key: `akt:${b.id}`, type: "activity", at: iso(44), origin: "crm", title: "Gick igenom dagens lösning", text: null, data: { activity_type: "meeting", duration_minutes: 45, result: "Vill ha offert", owner: ANSVARIGA[0] }, link: { kind: "activity", id: `ak-${b.id}` } },
    { key: `upp:${b.id}:1`, type: "task", at: iso(19), origin: "crm", title: "Skicka offerten", text: null, data: { done: false, due: "2026-11-20T08:00:00+00:00" }, link: { kind: "task", id: `t1-${b.id}` } },
    { key: `upp:${b.id}:2`, type: "task", at: iso(18), origin: "crm", title: "Boka uppföljning i januari", text: null, data: { done: false, due: "2027-01-12T08:00:00+00:00" }, link: { kind: "task", id: `t2-${b.id}` } },
    { key: `msg:${b.id}:2`, type: "reply_received", at: iso(70), origin: "iris", title: "Sara Modellén", text: "Hej! Det låter intressant, vi ser över telefonin i höst. Ring mig gärna på torsdag förmiddag.", data: {}, link: { kind: "conversation", id: "k1" } },
    { key: `msg:${b.id}:1`, type: "email_sent", at: iso(96), origin: "iris", title: "Telefonin inför 2027", text: "Hej Sara, jag såg att ni öppnar ett nytt kontor i vår. Många i er situation passar på att samla växel och mobiler.", data: {}, link: { kind: "conversation", id: "k1" } },
    { key: `samtal:${b.id}`, type: "call", at: iso(60), origin: "iris", title: null, text: "Bokade möte på kontoret.", data: { outcome: "mote" }, link: { kind: "lead", id: "l1" } },
    { key: `t:${b.id}`, type: "support_ticket", at: iso(24 * 12), origin: "support", title: "Fakturan stämmer inte", text: null, data: { channel: "email", status: "resolved" }, link: { kind: "ticket", id: "a1" } },
    { key: `p:${b.id}`, type: "lead_created", at: iso(24 * 9), origin: "iris", title: b.name, text: null, data: {}, link: { kind: "lead", id: "l1" } },
    ...affarer.flatMap((a): Tidsrad[] => [
      { key: `aff:${a.id}`, type: "deal_created", at: a.created_at ?? iso(100), origin: "crm", title: a.name, text: null, data: { amount: a.amount, currency: a.currency }, link: { kind: "deal", id: a.id } },
      ...(a.closed_at ? [{ key: `aff:${a.id}:slut`, type: "deal_closed", at: a.closed_at, origin: "crm" as const, title: a.name, text: null, data: { amount: a.amount, currency: a.currency, lost_reason: a.lost_reason }, link: { kind: "deal", id: a.id } }] : [])
    ])
  ];
  return rader;
}

/** Tidslinjen för en post: det skrivna och det påhittade, nyast först. Var tredje bolag är tomt på annat än sina egna ändringar. */
function tidslinje(objekt: "companies" | "people" | "deals", id: string, medBorttagna = false): Tidsrad[] | null {
  let bas: Tidsrad[];
  if (objekt === "companies") {
    const b = BOLAG.find((x) => x.id === id);
    if (!b) return null;
    bas = b.private_person || Number(id.slice(1)) % 3 === 2 ? egna(historik("company", b.id, b.created_at, b.updated_at, b.external_ids[0]?.connection)) : bolagstidslinje(b);
  } else if (objekt === "people") {
    const p = PERSONER.find((x) => x.id === id);
    if (!p) return null;
    bas = egna(historik("person", p.id, p.created_at ?? null, p.updated_at, p.external_ids?.[0]?.connection));
  } else {
    const a = AFFARER.find((x) => x.id === id);
    if (!a) return null;
    const skapad: Tidsrad = { key: `crm:${a.id}:1`, type: "record_created", at: a.created_at ?? iso(100), origin: "crm", title: null, text: null, data: { source: "app", actor: "anvandare:exempel" }, link: null };
    bas = Number(a.id.slice(1)) >= 100
      ? [skapad]
      : [
          ...egna(historik("deal", a.id, a.created_at, a.updated_at).filter((h) => h.type === "updated").map((h) => (h.source === "synk" ? { ...h, source: "app", actor: "anvandare:exempel" } : h))),
          { key: `ant:${a.id}`, type: "note", at: iso(30), origin: "crm", title: null, text: "Inköp vill ha tre års bindning om priset per användare går ned.", data: { author: ANSVARIGA[1] }, link: { kind: "note", id: `n-${a.id}` } },
          { key: `upp:${a.id}`, type: "task", at: iso(28), origin: "crm", title: "Räkna om priset på tre år", text: null, data: { done: false, due: "2026-12-03T08:00:00+00:00" }, link: { kind: "task", id: `t-${a.id}` } },
          skapad
        ];
  }
  const skrivet = SKRIVET[`${objekt}:${id}`] ?? [];
  const klara = new Set(KLARA);
  return [...skrivet, ...bas]
    .filter((r) => medBorttagna || !r.link || !BORTTAGET.has(r.link.id))
    .map((r) => (r.link && ANDRAT[r.link.id] ? { ...r, ...ANDRAT[r.link.id], data: { ...r.data, ...ANDRAT[r.link.id].data } } : r))
    .map((r) => (r.type === "task" && r.link && klara.has(r.link.id) ? { ...r, data: { ...r.data, done: true } } : r))
    .sort((x, y) => y.at.localeCompare(x.at));
}

/** Bolag som är ett lead hos Iris i förhandsvisningen: samma urval som får en full tidslinje. */
const harLead = (b: Bolag) => !b.private_person && !b.deleted_at && /^b\d+$/.test(b.id) && Number(b.id.slice(1)) % 3 !== 2;
/** Leadets läge per bolag, efter ett utfall. Utan utfall har leadet svarat. */
const LEADLAGEN: Record<string, string> = {};
const UTFALLSKOD: Record<string, string> = { no_answer: "ej_svar", call_back: "aterkom", not_interested: "ej_intresserad", do_not_contact: "kontakta_inte", meeting_booked: "mote" };
const UTFALLSLAGE: Record<string, string> = { not_interested: "lost", do_not_contact: "suppressed", meeting_booked: "meeting", won: "won" };

// ---- Bilagor (bilaga_ut i crm_v1_objekt.py): metadata, aldrig innehåll ---------
let bilagenummer = 1;
const bilaga = (namn: string, typ: string, storlek: number, timmar: number, koppling: Partial<Bilaga>): Bilaga => ({
  id: `f${bilagenummer++}`, filename: namn, content_type: typ, size: storlek, uploaded_by: "anvandare:exempel",
  company_id: null, person_id: null, deal_id: null, note_id: null, created_at: iso(timmar), deleted_at: null, ...koppling
});
const BILAGOR: Bilaga[] = [
  bilaga("Offert växel och mobiler.pdf", "application/pdf", 412_000, 20, { company_id: "b3" }),
  bilaga("Avtalsutkast 2027.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 86_300, 44, { company_id: "b3" }),
  bilaga("Planritning nya kontoret.png", "image/png", 2_340_000, 24 * 6, { company_id: "b3" }),
  bilaga("Prisbilaga tre år.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 31_200, 30, { deal_id: "d8" }),
  bilaga("Offert koncernen.pdf", "application/pdf", 655_000, 52, { deal_id: "d8" })
];

/** Uppgifter som bockats av i förhandsvisningen. */
const KLARA: string[] = [];

/** Den samlade uppgiftslistan (GET /v1/tasks). `timmar` framåt är negativt: förfaller om så många timmar. */
const uppgift = (i: number, title: string, omTimmar: number | null, koppling: Partial<Pick<Uppgift, "company_id" | "person_id" | "deal_id">>, owner: string | null, description: string | null = null, klar: number | null = null): Uppgift => ({
  id: `u${i}`, title, description, status: klar == null ? "todo" : "done", due_at: omTimmar == null ? null : iso(-omTimmar), completed_at: klar == null ? null : iso(klar),
  owner, company_id: null, person_id: null, deal_id: null, ...koppling, created_at: iso(24 * 9), updated_at: iso(klar ?? 30)
});
const UPPGIFTER: Uppgift[] = [
  uppgift(1, "Ring om offerten", -50, { company_id: "b3", deal_id: "d8" }, "Exempel Säljare", "De ville ha svar före månadsskiftet."),
  uppgift(2, "Skicka avtalsutkastet", -26, { company_id: "b5" }, "Exempel Säljare"),
  uppgift(3, "Boka uppföljning efter demon", 3, { company_id: "b1" }, "Exempel Säljare"),
  uppgift(4, "Stäm av prisbilagan med ekonomi", 6, { deal_id: "d8" }, "Exempel Kollega", "Tre år, årlig indexering."),
  uppgift(5, "Skicka referenskunder", 30, { person_id: "p2" }, "Exempel Säljare"),
  uppgift(6, "Förbered kvartalsgenomgång", 24 * 4, { company_id: "b7" }, "Exempel Kollega"),
  uppgift(7, "Uppdatera kontaktuppgifter efter flytten", 24 * 9, { company_id: "b12" }, null),
  uppgift(8, "Gå igenom vårens kampanjlista", null, {}, "Exempel Säljare"),
  uppgift(9, "Skicka mötesanteckningar", null, { company_id: "b3" }, "Exempel Säljare", null, 20),
  uppgift(10, "Bekräfta leveransdatum", null, { company_id: "b5" }, "Exempel Kollega", null, 75)
];
let uppgiftsnummer = 100;
/** Anteckningar, uppgifter och aktiviteter som ändrats eller tagits bort i förhandsvisningen, på länkens id. */
const ANDRAT: Record<string, Partial<Tidsrad> & { data?: Record<string, unknown> }> = {};
const BORTTAGET = new Set<string>();

/** Raden bakom en anteckning, uppgift eller aktivitet, var den än står. */
function hittaRad(id: string): Tidsrad | null {
  for (const [objekt, lista] of [["companies", BOLAG], ["deals", AFFARER], ["people", PERSONER]] as const) {
    for (const post of lista) {
      const rad = (tidslinje(objekt, post.id, true) ?? []).find((r) => r.link?.id === id);
      if (rad) return rad;
    }
  }
  return null;
}

/** POST /v1/notes, /v1/tasks och /v1/activities: raden läggs på postens tidslinje. */
function skriv(slag: "notes" | "tasks" | "activities", k: Record<string, unknown>): Response {
  const [objekt, id] = k.company_id ? ["companies", String(k.company_id)] : k.person_id ? ["people", String(k.person_id)] : k.deal_id ? ["deals", String(k.deal_id)] : [null, ""];
  if (!objekt) return json({ detail: { code: "target_required", message: "Link the record to at least one company, person or deal.", meddelande: "Koppla posten till minst ett bolag, en person eller en affär." } }, 422);
  const nr = `ny${radnummer++}`;
  const at = new Date().toISOString();
  const rad: Tidsrad =
    slag === "notes"
      ? { key: `ant:${nr}`, type: "note", at, origin: "crm", title: null, text: String(k.body ?? ""), data: { source: "app" }, link: { kind: "note", id: nr } }
      : slag === "tasks"
        ? { key: `upp:${nr}`, type: "task", at, origin: "crm", title: String(k.title ?? ""), text: null, data: { done: false, due: k.due_at ?? null, source: "app" }, link: { kind: "task", id: nr } }
        : { key: `akt:${nr}`, type: "activity", at, origin: "crm", title: String(k.subject ?? ""), text: k.body ? String(k.body) : null, data: { activity_type: k.type ?? "other", source: "app" }, link: { kind: "activity", id: nr } };
  (SKRIVET[`${objekt}:${id}`] ??= []).unshift(rad);
  return json({ id: nr }, 201);
}

const DBNAMN: Record<Relation, string> = { customer: "kund", former_customer: "tidigare_kund", prospect: "prospekt", partner: "partner", supplier: "leverantor", not_relevant: "ej_aktuell", other: "ovrigt" };

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
  const falt = ["first_name", "last_name", "title", "email", "company_id", "legal_basis", "source_type", "source_name", "do_not_contact"] as const;
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
  // ---- Den samlade kundlistan (GET /customers) ------------------------------------
  if (vag === "/v1/customers" && metod === "GET") {
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const origin = url.searchParams.get("origin") ?? "all";
    const limit = Math.min(2000, Math.max(1, Number(url.searchParams.get("limit") ?? 200)));
    const egna = BOLAG.filter((b) => !b.deleted_at && b.relation === "customer").map((b) => ({
      origin: "own", company_id: b.id, lead_id: LEADLAGEN[b.id] === "won" ? "l1" : null, name: b.name, org_number: b.org_number, customer_since: b.customer_since, private_person: b.private_person === true
    }));
    // Påhittade leads som Iris vunnit: de finns inte i registret och har därför inget company_id.
    const vunna = ["Påhittad Plåt AB", "Exempel Elektriska AB", "Låtsas Lackering AB", "Attrapp Åkeri AB", "Skiss Snickeri AB", "Modell Måleri AB"].map((namn, i) => ({
      origin: "iris", company_id: null, lead_id: `lv${i}`, name: namn, org_number: medKontrollsiffra(String(559920000 + i * 37).slice(0, 9)), customer_since: `2026-${String(6 + i).padStart(2, "0")}-1${i}`, private_person: false
    }));
    const alla = [...(origin === "iris" ? [] : egna), ...(origin === "own" ? [] : vunna)]
      .filter((k) => !q || [k.name, k.org_number, orgnrVisning(k.org_number)].some((v) => (v ?? "").toLowerCase().includes(q)))
      .sort((x, y) => (x.name ?? "").localeCompare(y.name ?? "", "sv"));
    return json({ data: alla.slice(0, limit), counts: { own: egna.length, iris: vunna.length } });
  }
  // ---- Bolaget hos Iris och utfallet (crm_v1_tidslinje.py) ----------------------
  const irisdel = vag.match(/^\/v1\/companies\/([^/]+)\/(iris|outcome)$/);
  if (irisdel) {
    const b = BOLAG.find((x) => x.id === decodeURIComponent(irisdel[1]) && !x.deleted_at);
    if (!b) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    const lage = LEADLAGEN[b.id] ?? "replied";
    if (irisdel[2] === "iris" && metod === "GET") {
      const leads = harLead(b) ? [{ id: "l1", name: b.name, status: lage, created_at: iso(24 * 9) }] : [];
      return json({ leads, latest: leads[leads.length - 1] ?? null, outcome: null, do_not_contact: b.do_not_contact === true || lage === "suppressed" });
    }
    if (irisdel[2] === "outcome" && metod === "POST") {
      const utfall = String(kropp.outcome ?? "");
      if (utfall === "call_back" && !kropp.call_back_on) {
        return json({ detail: { code: "call_back_date_required", message: "call_back needs call_back_on.", meddelande: "Återkom kräver ett datum i call_back_on." } }, 422);
      }
      const at = new Date().toISOString();
      if (harLead(b)) {
        if (UTFALLSLAGE[utfall]) LEADLAGEN[b.id] = UTFALLSLAGE[utfall];
        const rad: Tidsrad = utfall === "won"
          ? { key: `st:ny${radnummer++}`, type: "lead_status", at, origin: "iris", title: null, text: null, data: { from: lage, to: "won" }, link: { kind: "lead", id: "l1" } }
          : { key: `samtal:ny${radnummer++}`, type: "call", at, origin: "iris", title: null, text: kropp.note ? String(kropp.note) : null, data: { outcome: UTFALLSKOD[utfall], call_back_on: kropp.call_back_on ?? null }, link: { kind: "lead", id: "l1" } };
        (SKRIVET[`companies:${b.id}`] ??= []).unshift(rad);
      }
      if (utfall === "do_not_contact") b.do_not_contact = true;
      if (utfall === "won") {
        b.relation = "customer";
        b.customer_since ??= at.slice(0, 10);
      }
      if (utfall === "do_not_contact" || utfall === "won") b.updated_at = at;
      return json({ company: b, lead_ids: harLead(b) ? ["l1"] : [] });
    }
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
        (url.searchParams.get("missing_source") !== "true" || !p.source_type) &&
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
  // ---- Bilagor -------------------------------------------------------------------
  if (vag === "/v1/attachments" && metod === "GET") {
    const p = url.searchParams;
    const traffar = BILAGOR.filter(
      (b) => !b.deleted_at && (!p.get("company_id") || b.company_id === p.get("company_id")) && (!p.get("person_id") || b.person_id === p.get("person_id")) && (!p.get("deal_id") || b.deal_id === p.get("deal_id"))
    );
    return json({ data: [...traffar].sort((x, y) => (y.created_at ?? "").localeCompare(x.created_at ?? "")), next_cursor: null });
  }
  if (vag === "/v1/attachments" && metod === "POST" && init?.body instanceof FormData) {
    const fil = init.body.get("file");
    if (!(fil instanceof File)) return json({ detail: { code: "invalid_body", message: "Send multipart/form-data with a file field.", meddelande: "Skicka multipart/form-data med fältet file." } }, 422);
    // Samma gränser som objekt.skapa_bilaga, och en väntan så att förloppet syns.
    await new Promise((r) => setTimeout(r, 900));
    if (fil.size > BILAGA_MAX) return json({ detail: { code: "file_too_large", message: "The file is larger than 10 MB.", meddelande: "Filen är större än 10 MB." } }, 413);
    if (!BILAGETYPER.includes(fil.name.slice(fil.name.lastIndexOf(".") + 1).toLowerCase())) {
      return json({ detail: { code: "file_type_not_allowed", message: "The file type is not allowed.", meddelande: "Filtypen är inte tillåten." } }, 422);
    }
    const s = (n: string) => (typeof init.body === "object" && init.body instanceof FormData && typeof init.body.get(n) === "string" ? (init.body.get(n) as string) : null);
    const ny = bilaga(fil.name, fil.type || "application/octet-stream", fil.size, 0, { company_id: s("company_id"), person_id: s("person_id"), deal_id: s("deal_id") });
    BILAGOR.unshift(ny);
    return json(ny, 201);
  }
  const bilagedel = vag.match(/^\/v1\/attachments\/([^/]+)(\/restore)?$/);
  if (bilagedel) {
    const b = BILAGOR.find((x) => x.id === decodeURIComponent(bilagedel[1]));
    if (!b) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    if (bilagedel[2] && metod === "POST") {
      b.deleted_at = null;
      return json(b);
    }
    if (metod === "DELETE") {
      b.deleted_at = new Date().toISOString();
      return json(null, 204);
    }
    if (metod === "GET") return json(b);
  }
  // ---- Tidslinjen och det som skrivs på den ------------------------------------
  const linje = vag.match(/^\/v1\/(companies|people|deals)\/([^/]+)\/timeline$/);
  if (linje && metod === "GET") {
    const rader = tidslinje(linje[1] as "companies" | "people" | "deals", decodeURIComponent(linje[2]));
    return rader ? json({ data: rader }) : json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
  }
  // ---- Den samlade uppgiftslistan (GET /v1/tasks och uppgifterna i den) -------
  if (vag === "/v1/tasks" && metod === "GET") {
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const status = url.searchParams.get("status");
    const fore = url.searchParams.get("due_before");
    const traffar = UPPGIFTER.filter((u) => !u.deleted_at && (!status || u.status === status) && (!fore || (u.due_at != null && u.due_at < fore)) && (!q || (u.title ?? "").toLowerCase().includes(q)));
    const sort = url.searchParams.get("sort") ?? "updated";
    traffar.sort((a, b) => (sort === "due" ? (a.due_at ?? "9999").localeCompare(b.due_at ?? "9999") : (b.updated_at ?? "").localeCompare(a.updated_at ?? "")));
    return json({ data: traffar, next_cursor: null });
  }
  const iListan = vag.match(/^\/v1\/tasks\/([^/]+)(\/restore)?$/);
  const iListanPost = iListan ? UPPGIFTER.find((u) => u.id === decodeURIComponent(iListan[1])) : null;
  if (iListan && iListanPost) {
    const u = iListanPost;
    if (iListan[2] && metod === "POST") u.deleted_at = null;
    else if (metod === "DELETE") {
      u.deleted_at = new Date().toISOString();
      return json(null, 204);
    } else if (metod === "PATCH") {
      for (const f of ["title", "description", "due_at", "owner", "company_id"] as const) if (f in kropp) (u as Record<string, unknown>)[f] = kropp[f] ?? null;
      if (kropp.status === "done" || kropp.status === "todo") {
        u.status = kropp.status;
        u.completed_at = kropp.status === "done" ? new Date().toISOString() : null;
      }
      u.updated_at = new Date().toISOString();
    }
    return json(u);
  }
  if (vag === "/v1/tasks" && metod === "POST" && !kropp.person_id && !kropp.deal_id && ("description" in kropp || "owner" in kropp)) {
    // Från vyn Uppgifter: uppgiften får stå för sig själv eller höra till ett bolag.
    const ny = uppgift(++uppgiftsnummer, String(kropp.title ?? ""), null, { company_id: kropp.company_id ? String(kropp.company_id) : null }, kropp.owner ? String(kropp.owner) : null, kropp.description ? String(kropp.description) : null);
    ny.due_at = kropp.due_at ? String(kropp.due_at) : null;
    ny.created_at = ny.updated_at = new Date().toISOString();
    UPPGIFTER.unshift(ny);
    return json(ny, 201);
  }
  const skrivning = vag.match(/^\/v1\/(notes|tasks|activities)$/);
  if (skrivning && metod === "POST") return skriv(skrivning[1] as "notes" | "tasks" | "activities", kropp);
  const skriven = vag.match(/^\/v1\/(notes|tasks|activities)\/([^/]+)(\/restore)?$/);
  if (skriven) {
    const id = decodeURIComponent(skriven[2]);
    const rad = hittaRad(id);
    if (!rad) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    if (skriven[3] && metod === "POST") {
      BORTTAGET.delete(id);
      return json({ id });
    }
    if (metod === "DELETE") {
      BORTTAGET.add(id);
      return json(null, 204);
    }
    if (metod === "GET") {
      // Postens hela innehåll, i API:ts form för sitt slag.
      return json(
        skriven[1] === "notes"
          ? { id, title: rad.title, body: rad.text ?? "" }
          : skriven[1] === "tasks"
            ? { id, title: rad.title, due_at: rad.data.due ?? null, status: rad.data.done ? "done" : "todo" }
            : { id, type: rad.data.activity_type ?? "other", subject: rad.title, body: rad.text }
      );
    }
    if (metod === "PATCH") {
      if (kropp.status === "done" && !KLARA.includes(id)) KLARA.push(id);
      if (kropp.status === "todo" && KLARA.includes(id)) KLARA.splice(KLARA.indexOf(id), 1);
      const forr = ANDRAT[id] ?? {};
      ANDRAT[id] = {
        ...forr,
        ...("title" in kropp ? { title: (kropp.title as string) ?? null } : {}),
        ...("subject" in kropp ? { title: (kropp.subject as string) ?? null } : {}),
        ...("body" in kropp ? { text: (kropp.body as string) ?? null } : {}),
        data: { ...forr.data, ...("due_at" in kropp ? { due: kropp.due_at ?? null } : {}), ...("type" in kropp ? { activity_type: kropp.type } : {}) }
      };
      return json({ id });
    }
  }
  // ---- Affärer (crm_v1_objekt.py) ---------------------------------------------
  if (vag === "/v1/deal-stages" && metod === "GET") return json({ data: STEG });
  // Stegens egna ändpunkter, med API:ts regler: unika namn, inget steg med affärer tas bort, alltid ett av varje typ.
  const typerFinns = (lista: Affarssteg[]) => (["open", "won", "lost"] as const).every((t) => lista.some((s) => s.type === t));
  const stegfel = (status: number, code: string, sv: string) => json({ detail: { code, message: sv, meddelande: sv } }, status);
  if (vag === "/v1/deal-stages" && metod === "POST") {
    const namn = String(kropp.name ?? "").trim();
    if (STEG.some((s) => s.name.toLowerCase() === namn.toLowerCase())) return stegfel(409, "conflict", "Det finns redan ett steg med det namnet.");
    const ny: Affarssteg = { id: `s${100 + STEG.length}`, name: namn, position: STEG.length + 1, probability: Number(kropp.probability ?? 0), type: (kropp.type as Affarssteg["type"]) ?? "open", color: null };
    STEG.push(ny);
    return json(ny, 201);
  }
  if (vag === "/v1/deal-stages/reorder" && metod === "POST") {
    const ids = (kropp.ids as string[]) ?? [];
    STEG.sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id));
    STEG.forEach((s, i) => (s.position = i + 1));
    return json({ data: STEG });
  }
  const stegvag = vag.match(/^\/v1\/deal-stages\/([^/]+)$/);
  if (stegvag) {
    const s = STEG.find((x) => x.id === decodeURIComponent(stegvag[1]));
    if (!s) return stegfel(404, "stage_not_found", "Steget finns inte.");
    if (metod === "PATCH") {
      const namn = "name" in kropp ? String(kropp.name ?? "").trim() : s.name;
      if (STEG.some((x) => x !== s && x.name.toLowerCase() === namn.toLowerCase())) return stegfel(409, "conflict", "Det finns redan ett steg med det namnet.");
      const typ = (kropp.type as Affarssteg["type"]) ?? s.type;
      if (!typerFinns(STEG.map((x) => (x === s ? { ...x, type: typ } : x)))) return stegfel(409, "stage_required", "Det måste alltid finnas minst ett öppet, ett vunnet och ett förlorat steg.");
      Object.assign(s, { name: namn, type: typ, probability: "probability" in kropp ? Number(kropp.probability) : s.probability });
      return json(s);
    }
    if (metod === "DELETE") {
      if (AFFARER.some((a) => a.stage_id === s.id)) return stegfel(409, "stage_in_use", "Steget har affärer. Flytta dem först.");
      if (!typerFinns(STEG.filter((x) => x !== s))) return stegfel(409, "stage_required", "Det måste alltid finnas minst ett öppet, ett vunnet och ett förlorat steg.");
      STEG.splice(STEG.indexOf(s), 1);
      return json(null, 204);
    }
  }
  if (vag === "/v1/deals/board" && metod === "GET") return json(tavlan());
  if (vag === "/v1/deals" && metod === "GET") {
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const korgen = url.searchParams.get("only_deleted") === "true";
    const bolagId = url.searchParams.get("company_id");
    const traffar = AFFARER.filter((a) => (korgen ? !!a.deleted_at : !a.deleted_at) && (!bolagId || a.company_id === bolagId) && (!q || (a.name ?? "").toLowerCase().includes(q)));
    return json({ data: ordna(traffar, "-updated", (a) => a.name ?? "", korgen), next_cursor: null });
  }
  if (vag === "/v1/deals" && metod === "POST") {
    const fel = ogiltigAffar(kropp, true);
    if (fel) return fel;
    const ny: Affarspost = {
      id: `d${100 + AFFARER.length}`, name: null, company_id: null, person_id: null, stage_id: null, amount: null, currency: "SEK", probability: null,
      expected_close_date: null, closed_at: null, lost_reason: null, lost_reason_code: null, owner: null, position: null,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(), deleted_at: null, purge_at: null
    };
    AFFARER.push(ny);
    andraAffar(ny, { ...kropp, stage_id: kropp.stage_id ?? "s1" });
    return json(ny, 201);
  }
  const affarshistorik = vag.match(/^\/v1\/deals\/([^/]+)\/history$/);
  if (affarshistorik) {
    const a = AFFARER.find((x) => x.id === decodeURIComponent(affarshistorik[1]));
    if (!a) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    // En affär skapad i förhandsvisningen har bara sin skapelse. Affärer synkas inte in: allt är gjort i appen eller över API:t.
    const skapad = { seq: 1, object: "deal", id: a.id, type: "created", fields: [], source: "app", actor: "anvandare:exempel", at: a.created_at };
    if (Number(a.id.slice(1)) >= 100) return json({ data: [skapad] });
    const andringar = historik("deal", a.id, a.created_at, a.updated_at)
      .filter((h) => h.type === "updated")
      .map((h) => (h.source === "synk" ? { ...h, source: "app", actor: "anvandare:exempel" } : h));
    return json({ data: [...andringar, skapad] });
  }
  const affarsdel = vag.match(/^\/v1\/deals\/([^/]+)(\/restore|\/move)?$/);
  if (affarsdel) {
    const a = AFFARER.find((x) => x.id === decodeURIComponent(affarsdel[1]));
    if (!a || (a.deleted_at && affarsdel[2] !== "/restore")) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    if (affarsdel[2] === "/restore" && metod === "POST") {
      a.deleted_at = null;
      a.purge_at = null;
      a.updated_at = new Date().toISOString();
      return json(a);
    }
    if (affarsdel[2] === "/move" && metod === "POST") {
      const stegId = String(kropp.stage_id ?? "");
      if (!STEG.some((s) => s.id === stegId)) return json({ detail: { code: "stage_not_found", message: "stage_id does not point at a deal stage.", meddelande: "stage_id pekar inte på något steg." } }, 422);
      placera(a, stegId, typeof kropp.before_id === "string" ? kropp.before_id : null);
      return json(a);
    }
    if (metod === "GET") return json(a);
    if (metod === "DELETE") {
      a.deleted_at = new Date().toISOString();
      a.purge_at = new Date(Date.now() + 30 * 864e5).toISOString();
      return json(null, 204);
    }
    if (metod === "PATCH") {
      const fel = ogiltigAffar(kropp, false);
      if (fel) return fel;
      andraAffar(a, kropp);
      return json(a);
    }
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
  // ---- SCB:s företagsregister (crm_v1_berikning.py), med påhittade uppgifter ----
  const registerpost = (orgnr: string, namn: string | null, n: number) => ({
    org_number: orgnrVisning(orgnr), name: namn, legal_form: "AB", legal_form_code: "49", registry_status: n % 11 === 10 ? "deregistered" : "active",
    sni_codes: ["62010", "62020"], registered_office: { municipality: "2480", county: "24" },
    postal_address: { street: `Registergatan ${1 + (n % 40)}`, co: null, postal_code: "903 26", city: "Umeå" },
    employee_class: { code: "4", label: "10-19" }, advertising_block: n % 6 === 5, codes: {}
  });
  if (vag === "/v1/lookup/companies" && metod === "GET") {
    const d = (url.searchParams.get("org_number") ?? "").replace(/\D/g, "");
    const faltfel = (code: string) => json({ detail: { code: "invalid_fields", message: "One or more fields could not be interpreted.", meddelande: "Ett eller flera fält gick inte att tolka.", fields: [{ field: "org_number", code }] } }, 422);
    if (d.length === 12 && !d.startsWith("16")) return json({ detail: { code: "not_a_company", message: "A sole proprietorship or private person is not looked up.", meddelande: "En enskild firma eller privatperson slås inte upp: numret hör till en person." } }, 422);
    const nr = d.length === 12 ? d.slice(2) : d;
    if (nr.length !== 10) return faltfel("orgnr_fel_langd");
    if (!luhn(nr)) return faltfel("orgnr_kontrollsiffra");
    if (nr.startsWith("5560")) return json({ detail: { code: "company_not_in_registry", message: "The registry has no company with that number.", meddelande: "Registret har inget bolag med det numret." } }, 404);
    return json({ data: registerpost(nr, "Registrerat Exempel AB", Number(nr.slice(-3))) });
  }
  const berika = vag.match(/^\/v1\/companies\/([^/]+)\/enrich$/);
  if (berika && metod === "POST") {
    const b = BOLAG.find((x) => x.id === decodeURIComponent(berika[1]) && !x.deleted_at);
    if (!b) return json({ detail: { code: "not_found", message: "The record does not exist.", meddelande: "Posten finns inte." } }, 404);
    if (b.private_person || b.sole_proprietor) return json({ detail: { code: "not_a_company", message: "A sole proprietorship or private person is not looked up.", meddelande: "En enskild firma eller privatperson slås inte upp: numret hör till en person." } }, 422);
    if (!b.org_number) return json({ detail: { code: "org_number_required", message: "The company has no organisation number.", meddelande: "Bolaget saknar organisationsnummer." } }, 422);
    const n = Number(b.id.replace(/\D/g, "")) || 0;
    const r = registerpost(b.org_number, b.name, n);
    const skrivOver = url.searchParams.get("overwrite") === "true";
    const varden: [string, string | null, (v: string) => void][] = [
      ["legal_form", b.legal_form, (v) => (b.legal_form = v)],
      ["sni_code", b.sni_code, (v) => (b.sni_code = v)],
      ["address.street", b.address.street, (v) => (b.address.street = v)],
      ["address.postal_code", b.address.postal_code, (v) => (b.address.postal_code = v)],
      ["address.city", b.address.city, (v) => (b.address.city = v)]
    ];
    const ur: Record<string, string> = { legal_form: r.legal_form, sni_code: r.sni_codes[0], "address.street": r.postal_address.street, "address.postal_code": r.postal_address.postal_code, "address.city": r.postal_address.city };
    const filled: string[] = [];
    const skipped: string[] = [];
    for (const [namn, nu_, satt] of varden) {
      if (nu_ === ur[namn]) continue;
      if (!nu_ || skrivOver) {
        satt(ur[namn]);
        filled.push(namn);
      } else skipped.push(namn);
    }
    b.registry_status = r.registry_status as Bolag["registry_status"];
    b.registry_advertising_block = r.advertising_block;
    b.registry_checked_at = new Date().toISOString();
    if (filled.length) b.updated_at = b.registry_checked_at;
    // Vart sjunde bolag har namnet ändrat för hand: registret säger annat, och det skrivs aldrig över.
    const skyddade = n % 7 === 5 ? ["name"] : [];
    return json({ company: b, filled, skipped, protected: skyddade, registry_status: r.registry_status, deregistered: r.registry_status === "deregistered", advertising_block: r.advertising_block, registry: r });
  }
  // ---- Spärrlistan (crm_v1_sparr.py) ------------------------------------------
  if (vag === "/v1/suppressions" && metod === "GET") {
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const kanal = url.searchParams.get("channel");
    const galler = url.searchParams.get("applies_to");
    const baraHavda = url.searchParams.get("only_lifted") === "true";
    const medHavda = url.searchParams.get("include_lifted") === "true";
    const start = Number(url.searchParams.get("cursor") ?? 0);
    const limit = Math.min(500, Math.max(1, Number(url.searchParams.get("limit") ?? 50)));
    const traffar = SPARRAR.filter(
      (s) =>
        (baraHavda ? !!s.lifted_at : medHavda || !s.lifted_at) &&
        (!kanal || s.channel === kanal) &&
        (!galler || s.channel === galler || s.channel === "all") &&
        (!q || s.value.includes(q))
    ).sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
    return json({ data: traffar.slice(start, start + limit), next_cursor: start + limit < traffar.length ? String(start + limit) : null });
  }
  if (vag === "/v1/suppressions" && metod === "POST") {
    const kanal = String(kropp.channel ?? "all") as Sparrkanal;
    const slag = String(kropp.kind ?? "") as Sparrslag;
    const ogiltig = (field: string, code: string) => json({ detail: { code: "validation_failed", message: "The record is invalid.", meddelande: "Posten är ogiltig.", fields: [{ field, code }] } }, 422);
    if (!SLAG_I_KANAL[kanal]?.includes(slag)) return ogiltig("kind", "slag_passar_inte_kanalen");
    const varde = sparrvarde(slag, String(kropp.value ?? ""));
    if (!varde) return ogiltig("value", slag === "email" ? "epost_ogiltig" : slag === "domain" ? "doman_ogiltig" : slag === "phone" ? "telefon_ogiltig" : "orgnr_fel_langd");
    const redan = SPARRAR.find((s) => !s.lifted_at && s.channel === kanal && s.kind === slag && s.value === varde);
    if (redan) return json(redan, 200);
    const ny = sparr(++sparrlopnr, kanal, slag, varde, String(kropp.reason ?? "other") as Sparrorsak, "app", 0, kropp.note ? String(kropp.note) : null);
    ny.created_at = new Date().toISOString();
    SPARRAR.unshift(ny);
    return json(ny, 201);
  }
  if (vag === "/v1/suppressions/import" && metod === "POST") {
    const kanal = String(kropp.channel ?? "phone") as Sparrkanal;
    const varden = Array.isArray(kropp.values) ? (kropp.values as unknown[]).map(String) : [];
    const ut = { added: 0, already_blocked: 0, invalid: [] as { index: number; code: string }[] };
    varden.forEach((ratt, index) => {
      const slag = (kropp.kind as Sparrslag | undefined) ?? gissaSlag(ratt);
      const varde = SLAG_I_KANAL[kanal].includes(slag) ? sparrvarde(slag, ratt) : null;
      if (!varde) return void ut.invalid.push({ index, code: kanal === "phone" ? "telefon_ogiltig" : slag === "email" ? "epost_ogiltig" : "slag_passar_inte_kanalen" });
      if (SPARRAR.some((s) => !s.lifted_at && s.kind === slag && s.value === varde && (s.channel === kanal || s.channel === "all"))) return void (ut.already_blocked += 1);
      const ny = sparr(++sparrlopnr, kanal, slag, varde, String(kropp.reason ?? "nix") as Sparrorsak, "import", 0);
      ny.created_at = new Date().toISOString();
      SPARRAR.unshift(ny);
      ut.added += 1;
    });
    return json(ut);
  }
  if (vag === "/v1/suppressions/check" && metod === "POST") {
    const kanal = String(kropp.channel ?? "all");
    const [slag, ratt] = kropp.email ? ["email", String(kropp.email)] : kropp.phone ? ["phone", String(kropp.phone)] : ["org_number", String(kropp.org_number ?? "")];
    const varde = sparrvarde(slag as Sparrslag, ratt) ?? ratt.toLowerCase();
    const doman = slag === "email" ? varde.split("@")[1] : null;
    const traffar = SPARRAR.filter((s) => !s.lifted_at && (kanal === "all" || s.channel === "all" || s.channel === kanal) && ((s.kind === slag && s.value === varde) || (s.kind === "domain" && s.value === doman)));
    // Bolag och personer märkta Kontakta inte spärrar också, utan att stå i listan.
    const post = BOLAG.some((b) => !b.deleted_at && b.do_not_contact && (b.org_number === varde || b.phone === varde || (doman != null && b.domain === doman))) || PERSONER.some((p) => !p.deleted_at && p.do_not_contact && (p.email === varde || p.phone === varde || p.mobile === varde));
    const sources = [...(traffar.length ? ["suppression_list"] : []), ...(post ? ["record"] : [])];
    return json({ blocked: sources.length > 0, sources, suppression_ids: traffar.map((s) => s.id) });
  }
  const sparrvag = vag.match(/^\/v1\/suppressions\/([^/]+)$/);
  if (sparrvag && metod === "DELETE") {
    const s = SPARRAR.find((x) => x.id === decodeURIComponent(sparrvag[1]) && !x.lifted_at);
    if (!s) return json({ detail: { code: "suppression_not_found", message: "The suppression does not exist.", meddelande: "Spärren finns inte." } }, 404);
    s.lifted_at = new Date().toISOString();
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

/**
 * Hjälprutans anrop i förhandsvisningen (components/snajp/HjalpRuta.tsx). Ett påhittat ärende som
 * väntar på kunden, så att talet på raden Hjälp och fel syns. En ny felrapport kvitteras med ett
 * nummer. Frågor till agenten svarar att hjälpen inte är påslagen: den prövas i sin egen
 * förhandsvisning (/forhandsvisning/hjalpruta).
 */
async function svaraHjalp(url: URL, init?: RequestInit): Promise<Response> {
  await new Promise((r) => setTimeout(r, 150));
  const metod = (init?.method ?? "GET").toUpperCase();
  if (url.pathname === "/api/snajp-support/hjalp/arenden" && metod === "GET") {
    return json({
      arenden: [
        {
          id: "00000000-0000-4000-8000-000000000046", nummer: "F-0046", status: "redo_att_testa", sida: "/crm/synk",
          gjorde: "Exempel: startade en full synk från HubSpot.", created_at: iso(72), updated_at: iso(1), vantar_pa_kund: true, testversion_url: null,
          handelser: [
            { tid: iso(72), typ: "skapad", status: "mottagen", meddelande: null },
            { tid: iso(1), typ: "status", status: "redo_att_testa", meddelande: "Exempel: rättningen ligger i en testversion. Kör samma synk där." }
          ]
        }
      ]
    });
  }
  if (url.pathname === "/api/snajp-support/hjalp/arenden" && metod === "POST") {
    return json({ id: "00000000-0000-4000-8000-000000000047", nummer: "F-0047", status: "mottagen", created_at: new Date().toISOString() }, 201);
  }
  return json({ kod: "hjalp_av", error: "Hjälpen är inte påslagen i förhandsvisningen." }, 503);
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
    const iForhandsvisning = window.location.pathname.startsWith("/forhandsvisning/");
    if (iForhandsvisning && url.pathname.startsWith("/api/snajp-support/hjalp")) return svaraHjalp(url, init);
    const skalet = iForhandsvisning ? svaraSkalet(url, init) : null;
    if (skalet) return skalet;
    const korningar = iForhandsvisning ? svaraKorningar(url, init) : null;
    if (korningar) return korningar;
    const utkast = iForhandsvisning ? svaraUtkast(url, init) : null;
    if (utkast) return utkast;
    const iris = iForhandsvisning ? svaraIris(url, init) : null;
    if (iris) return iris;
    const galler = iForhandsvisning && url.pathname.startsWith("/api/snajp-support/crm");
    return galler ? svara(url, init) : riktig(in_, init);
  };
}

/** Lägena förhandsvisningen kan visa, ur adressen (se `[[...vy]]/page.tsx`). */
export type Forhandslage = {
  /** `?vy=kund`: kundens nivå (synkens enkla ord, tilläggets besked). */
  kund: boolean;
  /** `?besok=1`: plattformsadmin i kundbesök hos Exempelbolaget AB. */
  besok: boolean;
  /** `?roll=lasare`: en kund med läsroll. */
  lasare: boolean;
  /** `?demo=1`: adminens demovy. `?demo=yta`: en demoarbetsyta. */
  demo: "vy" | "yta" | null;
  /** `?produkter=support`: arbetsytans produkter (kommaseparerade). Standard: leads och support. */
  produkter: string[] | null;
};

/**
 * Vem som tittar. Plattformsadmin som standard (CRM:et släpps bara till admin i
 * dag); lägena ovan ger kundens nivå, kundbesöket, läsrollen och demon.
 * Ett påhittat läge, aldrig en riktig session: ingen identitet att jämföra mot.
 */
function lage(l: Forhandslage): DashboardState {
  const admin = !l.kund && !l.lasare && l.demo !== "yta";
  const produkter = (l.produkter ?? ["leads", "support"]).filter((p): p is "leads" | "support" | "bookkeeping" => p === "leads" || p === "support" || p === "bookkeeping");
  return {
    products: produkter,
    addons: [],
    workspaceName: l.demo === "vy" ? "Demokontot" : "Exempelbolaget AB",
    userEmail: l.besok || l.demo === "vy" ? null : "kim@exempelbolaget.test",
    signedIn: true,
    isDemo: l.demo === "yta",
    isPlatformAdmin: admin || l.besok,
    vy: l.besok ? "kund" : l.demo === "vy" ? "demo" : "admin",
    impersonation: l.besok ? { slug: "exempelbolaget", namn: "Exempelbolaget AB" } : null,
    arLasare: l.lasare,
    initialScope: "both"
  };
}

/**
 * Vyväxeln och utloggningen i förhandsvisningen: ingen server action (den
 * kräver en inloggad plattformsadmin), utan läget byts i adressen, så att
 * banderollen och menyn går att följa. Utloggningen gör ingenting här.
 */
const FORHANDSATGARDER: Partial<Skalatgarder> = {
  async bytVy(varde) {
    const url = new URL(window.location.href);
    for (const p of ["besok", "demo", "vy", "roll"]) url.searchParams.delete(p);
    if (varde === "demo") url.searchParams.set("demo", "1");
    else if (varde.startsWith("kund:")) url.searchParams.set("besok", "1");
    window.location.replace(url.toString());
    return true;
  },
  async loggaUt() {}
};

/** Vyerna förhandsvisningen kan visa. En ny vy läggs till här och i renderingen nedan. */
const KANDA_VYER = ["oversikt", "bolag", "personer", "affarer", "uppgifter", "synk", "sparrar", "utvecklare", "iris/leads", "iris/utkast", "iris/korningar"];

export function CrmForhandsvisning({
  tema,
  vy,
  lagen,
  utanTillagg
}: Readonly<{ tema: Tema; vy: string; lagen: Forhandslage; utanTillagg: boolean }>) {
  tillaggSaknas = utanTillagg;
  fangaAnrop();
  const state = lage(lagen);
  // En väg som ingen vy här visar än faller tillbaka på översikten, som förut.
  // `iris/korningar/<id>`: körningens egen sida (steg 4.4).
  const korning = vy.startsWith("iris/korningar/") ? vy.slice("iris/korningar/".length) : null;
  const visad = korning ? "iris/korning" : KANDA_VYER.includes(vy) ? vy : "oversikt";

  return (
    <DashboardProvider state={state}>
      <CrmRam
        tema={tema}
        bas="/forhandsvisning/crm"
        arbetsyta={state.workspaceName ?? undefined}
        hjalp={!state.isDemo && state.vy !== "demo"}
        notiser={!state.isDemo}
        atgarder={FORHANDSATGARDER}
      >
        {visad === "oversikt" ? <OversiktVy bas="/forhandsvisning/crm" /> : null}
        {visad === "bolag" ? <BolagVy /> : null}
        {visad === "personer" ? <PersonerVy bas="/forhandsvisning/crm" /> : null}
        {visad === "affarer" ? <AffarerVy bas="/forhandsvisning/crm" /> : null}
        {visad === "uppgifter" ? <UppgifterVy bas="/forhandsvisning/crm" /> : null}
        {visad === "synk" ? <SynkVy utvecklarvag="/forhandsvisning/crm/utvecklare" /> : null}
        {visad === "sparrar" ? <SparrarVy /> : null}
        {visad === "utvecklare" ? <UtvecklareVy /> : null}
        {visad === "iris/leads" ? <LeadsVy bas="/forhandsvisning/crm" /> : null}
        {visad === "iris/utkast" ? <UtkastVy bas="/forhandsvisning/crm" /> : null}
        {visad === "iris/korningar" ? <KorningarVy bas="/forhandsvisning/crm" /> : null}
        {visad === "iris/korning" && korning ? <KorningVy id={korning} bas="/forhandsvisning/crm" /> : null}
      </CrmRam>
    </DashboardProvider>
  );
}
