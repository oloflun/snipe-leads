"use client";

import { BolagVy } from "@/components/crm/app/BolagVy";
import { CrmRam, type CrmVy } from "@/components/crm/app/CrmRam";
import { PersonerVy } from "@/components/crm/app/PersonerVy";
import { SynkVy } from "@/components/crm/app/SynkVy";
import { UtvecklareVy } from "@/components/crm/app/UtvecklareVy";
import type { Anslutning, Bolag, Korning, Nyckel, Person, Relation } from "@/lib/crm/api";
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

function bolag(i: number): Bolag {
  const stam = NAMN[i % NAMN.length];
  const namn = i < NAMN.length ? `${stam} AB` : `${stam} ${Math.floor(i / NAMN.length) + 1} AB`;
  const doman = `${stam.toLowerCase().replace(/[^a-z]+/g, "")}${i < NAMN.length ? "" : Math.floor(i / NAMN.length) + 1}.test`;
  const nummer = String(5599000000 + i * 137).slice(0, 10);
  return {
    id: `b${i}`,
    name: namn,
    org_number: nummer,
    vat_number: `SE${nummer}01`,
    legal_form: "AB",
    sni_code: i % 3 === 0 ? "61100" : i % 3 === 1 ? "41200" : "69201",
    website: `https://${doman}`,
    domain: doman,
    email: `info@${doman}`,
    phone: `+4690${String(1000000 + i * 7919).slice(0, 7)}`,
    employees: 4 + ((i * 13) % 180),
    revenue_sek: 2_400_000 + i * 1_730_000,
    relation: RELATIONSFOLJD[i % RELATIONSFOLJD.length],
    customer_since: i % 4 === 3 ? null : `20${18 + (i % 8)}-0${1 + (i % 9)}-15`,
    contract_end: i % 5 === 0 ? "2027-03-31" : null,
    owner: ANSVARIGA[i % ANSVARIGA.length],
    do_not_contact: i % 11 === 10,
    sole_proprietor: false,
    address: { street: `Exempelgatan ${1 + i}`, co: null, postal_code: `9${String(1000 + i * 3).slice(0, 2)} ${String(20 + i).slice(-2)}`, city: ORTER[i % ORTER.length], country: "SE" },
    source: "synk",
    external_ids: [{ connection: i % 6 === 5 ? "fortnox" : "hubspot", id: String(48000 + i * 17), last_seen_at: iso(3) }],
    created_at: iso(24 * 40),
    updated_at: iso(2 + i * 5),
    deleted_at: null
  };
}

const BOLAG: Bolag[] = Array.from({ length: 73 }, (_, i) => bolag(i)).sort((a, b) => (a.name ?? "").localeCompare(b.name ?? "", "sv"));

const PERSONER: Person[] = BOLAG.slice(0, 40).flatMap((b, i) => {
  const en = (fornamn: string, efternamn: string, titel: string): Person => ({
    id: `p${b.id}${fornamn}`,
    first_name: fornamn,
    last_name: efternamn,
    title: titel,
    email: `${fornamn.toLowerCase()}@${b.domain}`,
    phone: null,
    mobile: `+4670${String(1000000 + i * 4391).slice(0, 7)}`,
    company_id: b.id,
    do_not_contact: false,
    source: "synk",
    updated_at: iso(6 + i)
  });
  return i % 3 === 0 ? [en("Per", "Påhitt", "VD"), en("Lo", "Låtsas", "Inköp")] : [en("Sam", "Skiss", "VD")];
});

const ANSLUTNINGAR: Anslutning[] = [
  { id: "a1", name: "hubspot", system: "hubspot", conflict_rule: "source_wins", missing_records: "mark_former_customer", default_relation: "customer", active: true, last_sync_at: iso(3), created_at: iso(24 * 40) },
  { id: "a2", name: "fortnox", system: "fortnox", conflict_rule: "source_wins", missing_records: "keep", default_relation: "customer", active: true, last_sync_at: iso(27), created_at: iso(24 * 12) }
];

const rakning = (o: Partial<Korning["counts"]>): Korning["counts"] => ({ total: 0, created: 0, updated: 0, unchanged: 0, skipped: 0, conflicts: 0, removed: 0, ...o });

const KORNINGAR: Korning[] = [
  { id: "k4", connection_id: "a1", mode: "delta", status: "processing", started_by: "api", counts: rakning({ total: 500, created: 3, updated: 41, unchanged: 452, skipped: 4 }), errors: [], error: null, created_at: iso(0.02), completed_at: null },
  {
    id: "k3", connection_id: "a1", mode: "full", status: "completed", started_by: "api",
    counts: rakning({ total: 73, created: 2, updated: 9, unchanged: 59, skipped: 3, removed: 1 }),
    // Samma form som synken sparar (app/crm/synk.py): koder, inga färdiga meningar.
    errors: [
      { objekt: "bolag", index: 13, externt_id: "48221", faltfel: [{ falt: "orgnr", kod: "orgnr_kontrollsiffra" }] },
      { objekt: "bolag", index: 30, externt_id: "48390", orsak: "saknar_namn" },
      { objekt: "bolag", index: 51, externt_id: "48467", faltfel: [{ falt: "orgnr", kod: "orgnr_ar_personnummer" }] }
    ],
    error: null, created_at: iso(3.1), completed_at: iso(3)
  },
  { id: "k2", connection_id: "a2", mode: "delta", status: "completed", started_by: "api", counts: rakning({ total: 12, updated: 4, unchanged: 8 }), errors: [], error: null, created_at: iso(27.1), completed_at: iso(27) },
  { id: "k1", connection_id: "a1", mode: "full", status: "failed", started_by: "api", counts: rakning({}), errors: [], error: "tom_full_synk", created_at: iso(51), completed_at: iso(51) }
];

const NYCKLAR: Nyckel[] = [
  { id: "n1", namn: "HubSpot-synken", prefix: "snajp_crm_4f2a", omfang: ["crm:las", "crm:synk"], created_at: iso(24 * 40), last_used_at: iso(3), revoked_at: null },
  { id: "n2", namn: "Fortnox", prefix: "snajp_crm_91c0", omfang: ["crm:synk"], created_at: iso(24 * 12), last_used_at: iso(27), revoked_at: null },
  { id: "n3", namn: "Provnyckel", prefix: "snajp_crm_07be", omfang: ["crm:las"], created_at: iso(24 * 70), last_used_at: null, revoked_at: iso(24 * 60) }
];

const DBNAMN: Record<Relation, string> = { customer: "kund", former_customer: "tidigare_kund", prospect: "prospekt", partner: "partner", supplier: "leverantor", other: "ovrigt" };

function json(kropp: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } });
}

async function svara(url: URL, init?: RequestInit): Promise<Response> {
  await new Promise((r) => setTimeout(r, 180));
  const vag = url.pathname.replace("/api/snajp-support/crm", "");
  const metod = (init?.method ?? "GET").toUpperCase();
  const kropp = typeof init?.body === "string" ? (JSON.parse(init.body) as Record<string, unknown>) : {};

  if (vag === "/oversikt") {
    const antal: Record<string, number> = { alla: BOLAG.length };
    for (const b of BOLAG) antal[DBNAMN[b.relation]] = (antal[DBNAMN[b.relation]] ?? 0) + 1;
    return json({ bolag: antal, personer: PERSONER.length, anslutningar: ANSLUTNINGAR.length, korningar: KORNINGAR });
  }
  if (vag === "/v1/companies" && metod === "GET") {
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const rel = url.searchParams.get("relation");
    const start = Number(url.searchParams.get("cursor") ?? 0);
    const traffar = BOLAG.filter(
      (b) => (!rel || b.relation === rel) && (!q || [b.name, b.org_number, b.address.city, b.owner].some((v) => (v ?? "").toLowerCase().includes(q)))
    );
    return json({ data: traffar.slice(start, start + 50), next_cursor: start + 50 < traffar.length ? String(start + 50) : null });
  }
  if (vag === "/v1/companies" && metod === "POST") {
    const orgnr = String(kropp.org_number ?? "").replace(/\D/g, "");
    if (kropp.org_number && orgnr.length !== 10) {
      return json({ detail: { code: "invalid_fields", message: "org_number must have ten digits.", meddelande: "Organisationsnumret ska ha tio siffror." } }, 422);
    }
    const nytt: Bolag = { ...bolag(900 + BOLAG.length), id: `b${900 + BOLAG.length}`, name: String(kropp.name), org_number: orgnr || null, relation: (kropp.relation as Relation) ?? "customer", source: "app", external_ids: [], updated_at: new Date().toISOString() };
    BOLAG.unshift(nytt);
    return json(nytt, 201);
  }
  if (vag === "/v1/people") {
    const bolagId = url.searchParams.get("company_id");
    return json({ data: PERSONER.filter((p) => !bolagId || p.company_id === bolagId).slice(0, 50), next_cursor: null });
  }
  if (vag === "/v1/connections" && metod === "GET") return json({ data: ANSLUTNINGAR });
  if (vag === "/v1/connections" && metod === "POST") {
    const ny: Anslutning = { id: `a${ANSLUTNINGAR.length + 1}`, name: String(kropp.name), system: String(kropp.system ?? "generisk"), conflict_rule: (kropp.conflict_rule as Anslutning["conflict_rule"]) ?? "source_wins", missing_records: "keep", default_relation: "customer", active: true, last_sync_at: null, created_at: new Date().toISOString() };
    if (ANSLUTNINGAR.some((a) => a.name === ny.name)) {
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
  return json({ detail: "Förhandsvisningen har inget svar för den här vägen." }, 404);
}

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

export function CrmForhandsvisning({ tema, vy }: Readonly<{ tema: Tema; vy: CrmVy }>) {
  fangaAnrop();

  return (
    <CrmRam tema={tema} bas="/forhandsvisning/crm" arbetsyta="Exempelbolaget AB">
      {vy === "bolag" ? <BolagVy /> : null}
      {vy === "personer" ? <PersonerVy /> : null}
      {vy === "synk" ? <SynkVy utvecklarvag="/forhandsvisning/crm/utvecklare" /> : null}
      {vy === "utvecklare" ? <UtvecklareVy /> : null}
    </CrmRam>
  );
}
