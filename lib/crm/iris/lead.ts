/**
 * Iris-leads i CRM:et: typerna för prospektet som leads-API:t lämnar det, och
 * de små regler listan och panelen delar. Etiketterna och utkastets härledda
 * status bor där dagens Leads har dem (lib/prospekt.ts, lib/leads/utkast.ts)
 * och importeras, så att samma lead heter samma sak i båda gränssnitten.
 *
 * Ingen affärsregel räknas här: statusen "Research pågår", utkastets status
 * och vad som får synas avgör backenden (app/leads/listvy.py, utkaststatus.py).
 */
import type { Localized } from "@/lib/i18n";
import type { UtkastStatus, Utkastfalt } from "@/lib/leads/utkast";

export { STATUS_ETIKETT, LEAD_TYP_ETIKETT, kriterier, leadTyp, nivaEtikett, utfallEtikett, type Kriterium, type LeadTyp } from "@/lib/prospekt";
export { UTKAST_ETIKETT, kanSkickas, sandtid, utkastText, UTAN_UTKAST, type UtkastStatus } from "@/lib/leads/utkast";

/** Webbplatsens bedömning som listläget bär den (listvy.listrad): betyget och första bristen. Bara hos kunder som får se den. */
export type Webbrevision = {
  modernitet?: number | null;
  brister?: string[] | null;
  platshallare?: string | null;
  svarar_inte?: boolean | null;
  layout_era?: string | null;
  uppskattat_byggar?: number | null;
  pagespeed?: { mobil?: { prestanda?: number | null; lcp_s?: number | null } | null } | null;
};

/** En rad i Iris-listan (`GET /leads/prospects?lista=1`, listvy.LISTKOLUMNER plus utkastets status). Fält utan värde saknas. */
export type Lead = {
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
  senaste_handelse_at?: string | null;
  website?: string | null;
  ort?: string | null;
  motivering?: string | null;
  disqualifiers?: string[] | null;
  arkiverad_at?: string | null;
  pafylld?: boolean | null;
  pafylld_skal?: string | null;
  /** Bara när kunden får se webbplatsbedömningen (lib/crm/iris/webb.ts). */
  webbrevision?: Webbrevision | null;
  webbniva?: string | null;
} & Utkastfalt;

/** Jevs förbedömning och klassning (app/leads/jev.py). */
export type Jev = {
  triage?: { lage?: string; fit?: number | null; skulle_falla?: boolean; fall_skal?: string[]; stodrad?: string | null } | null;
  klassning?: { lage?: string; sannolikhet?: number | null; trafikniva?: string | null; insats?: string | null } | null;
};

/** Hela prospektet (`GET /leads/prospects/{id}`): det lådan läser. */
export type LeadPost = Lead & {
  contact_role?: string | null;
  sni?: string | null;
  orgnr?: string | null;
  anstallda?: number | null;
  qualified?: boolean | null;
  score_breakdown?: unknown;
  jev?: Jev | null;
  lagesbeskrivning?: string | null;
  signaler?: unknown;
  rollkoppling_oklar?: boolean | null;
};

export type LeadSvar = { prospect: LeadPost; sources: string[] };

/** Utkastet som `GET /leads/prospects/{id}/utkast` lämnar det. */
export type Utkastsvar = {
  utkast: { id: string | null; subject: string | null; body: string; brodtext: string | null; svans: string | null } | null;
  thread_id?: string | null;
  signatur?: { text?: string | null; logotyp_url?: string | null } | null;
} & Utkastfalt;

/** En händelse på leadets tidslinje (`GET /leads/prospects/{id}/tidslinje`). */
export type Leadhandelse = {
  typ: "skapad" | "status" | "mejl_ut" | "mejl_in" | "anteckning" | "uppgift" | "samtal";
  nar: string;
  rubrik: string;
  text: string | null;
  id: string | null;
  klar: boolean | null;
};

/** En öppen uppgift (`GET /leads/uppgifter?oppna=1`). */
export type Leaduppgift = { id: string; prospect_id: string; titel: string; forfaller: string | null; klar: boolean };

/** En sparad vy (`GET /leads/vyer`): status, nivå, typ och sök. Per kund. */
export type Vyfilter = { status?: string; niva?: string; typ?: string; sok?: string };
export type Sparadvy = { id: string; namn: string; filter: Vyfilter; created_at?: string | null };

/** Leads före utskick: det Att bearbeta visar (LR-033). Kontaktade bor under Skickat. */
export const FORE_UTSKICK = ["researching", "new", "ready"] as const;

/** Statusar kunden kan välja i raden (LR-039). Research pågår och Spärrad sätter systemet. */
export const VALBARA = ["new", "ready", "contacted", "replied", "meeting", "won", "lost"] as const;
export const SYSTEMSTATUS = new Set(["researching", "suppressed"]);

/** Statusens prick: vunnen grön, svarat och möte blå, kontaktad ockra, förlorad röd (LR-039). */
export const STATUSTON: Record<string, "mossa" | "bla" | "ockra" | "fara" | null> = {
  won: "mossa",
  replied: "bla",
  meeting: "bla",
  contacted: "ockra",
  lost: "fara"
};

/** Utkastets ton: väntar och köat i varningsfärg, skickat grönt, stoppat rött, övriga dämpade (LR-056). */
export const UTKASTTON: Record<UtkastStatus, "varning" | "mossa" | "fara" | "dampad"> = {
  saknas: "dampad",
  skrivs: "dampad",
  vantar: "varning",
  godkant: "dampad",
  koad: "varning",
  skickat: "mossa",
  avvisat: "dampad",
  stoppat: "fara"
};

export type Kontaktvag = "bada" | "telefon" | "mejl" | "saknas";

export const KONTAKTVAG: Record<Kontaktvag, Localized> = {
  bada: { sv: "Tel och mejl", en: "Phone and email" },
  telefon: { sv: "Tel", en: "Phone" },
  mejl: { sv: "Mejl", en: "Email" },
  saknas: { sv: "Saknas", en: "Missing" }
};

export function kontaktvag(p: Lead): Kontaktvag {
  const tel = Boolean(p.contact_phone?.trim());
  const mejl = Boolean(p.contact_email?.trim());
  return tel && mejl ? "bada" : tel ? "telefon" : mejl ? "mejl" : "saknas";
}

/** Poängen: `score_total`, annars `icp_fit` × 100. Null när leadet inte är bedömt. */
export function poang(p: Lead): number | null {
  if (typeof p.score_total === "number") return p.score_total;
  if (typeof p.icp_fit === "number") return Math.round(p.icp_fit * 100);
  return null;
}

/** Backenden säger att researchen är köad eller pågår (status härledd ur jobbliggaren). */
export const iResearch = (p: Lead) => p.origin !== "example" && p.status === "researching";

/** Raden finns men är inte bedömd än: poängen visas som ett streck (LR-036). */
export const obedomd = (p: Lead) => p.origin !== "example" && (p.status === "researching" || (!p.niva && p.score_total == null && p.icp_fit == null));

/** Motiveringens första mening, annars underkännandets första skäl. */
export function forstaMening(p: Lead): string | null {
  const text = p.motivering ?? p.disqualifiers?.[0] ?? null;
  if (!text) return null;
  const slut = text.search(/[.!?](\s|$)/);
  return slut > 0 ? text.slice(0, slut + 1) : text;
}

const senast = (p: Lead) => p.senaste_handelse_at ?? p.created_at ?? "";
const NIVA_RANG: Record<string, number> = { A: 0, B: 1 };

/** Nyaste överst (LR-032): under research först, sedan senaste händelse, poäng och nivå. */
export function sortera(rader: Lead[]): Lead[] {
  return [...rader].sort((a, b) => {
    const g = Number(!iResearch(a)) - Number(!iResearch(b));
    if (g) return g;
    const x = senast(a);
    const y = senast(b);
    if (x !== y) return x < y ? 1 : -1;
    const k = (poang(b) ?? -1) - (poang(a) ?? -1);
    if (k) return k;
    return (NIVA_RANG[a.niva ?? ""] ?? 2) - (NIVA_RANG[b.niva ?? ""] ?? 2);
  });
}

/** Nyast först, för Bortvalda och Arkiverade (LR-050, LR-051). */
export const nyastForst = (rader: Lead[]) => [...rader].sort((a, b) => (senast(a) < senast(b) ? 1 : senast(a) > senast(b) ? -1 : 0));

/** Fritextsökningen i listan (LR-034): bolag, kontaktnamn och kontaktmejl, skiftlägesokänsligt. */
export function matcharSok(p: Lead, sok: string): boolean {
  const s = sok.trim().toLowerCase();
  if (!s) return true;
  return [p.company_name, p.contact_name, p.contact_email].some((v) => v?.toLowerCase().includes(s));
}

/** "exempel.test" ur en webbadress. */
export function domanAv(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Har leadet fått ett mejl (Skapa uppföljning gäller bara dem, LR-044). */
export const harFattMejl = (p: Lead) => Boolean(p.skickat_at) || p.utkast_status === "skickat";

/** Skälen Skapa uppföljning hoppar över ett lead (Uppfoljningar.tsx i dagens Leads, `hoppade`). */
export const UPPFOLJNING_HOPPAD: Record<string, Localized> = {
  inget_skickat: { sv: "har inte fått något mejl än", en: "have not been emailed yet" },
  avslutad: { sv: "har svarat eller är avslutade", en: "have replied or are closed" },
  sekvensen_klar: { sv: "har fått alla uppföljningar", en: "have had every follow-up" },
  skrivs_redan: { sv: "får redan en uppföljning skriven", en: "already have one being written" },
  har_utkast: { sv: "har redan en uppföljning som väntar", en: "already have one waiting" }
};

/** Samtalens utfall på tidslinjen (app/leads/samtal.py). */
export const SAMTALSUTFALL: Record<string, Localized> = {
  ej_svar: { sv: "Ej svar", en: "No answer" },
  aterkom: { sv: "Återkom", en: "Call back" },
  ej_intresserad: { sv: "Ej intresserad", en: "Not interested" },
  kontakta_inte: { sv: "Kontakta inte", en: "Do not contact" },
  mote: { sv: "Möte bokat", en: "Meeting booked" }
};
