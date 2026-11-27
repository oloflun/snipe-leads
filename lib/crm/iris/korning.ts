/**
 * Iris körningar i CRM:et (steg 4.4): typerna som leads-API:t lämnar för en
 * körning, och orden körningsvyerna visar dem med.
 *
 * Samma ändpunkter som dagens Leads › Körningar (components/leads/IrisKorningar.tsx,
 * LeadsRunForm.tsx, KorningensUtkast.tsx):
 *
 * - `GET  /leads/korningar?limit=` → `{ korningar }` (leads.py:lista_korningar, sammandrag)
 * - `GET  /leads/korningar/{id}` → en körning med tratt och barnjobb (hamta_korning)
 * - `POST /leads/korningar/{id}/pausa|aterupta|avbryt|fortsatt` (styr_korning)
 * - `GET  /leads/korningar/{id}/utkast`, `POST .../utkast/skriv`, `POST .../utkast/skicka-jobb`
 * - `POST /leads/runs/batch` (202, `fase: soker`) och `GET /leads/jobb/{id}`
 *
 * Ingen affärsregel räknas här. Motorn (app/leads/korning.py) avgör när en körning
 * är klar, vilande, under målet eller fallen; vyerna läser fälten och sätter ord
 * på dem. Körningens arbetsminne (kandidater, webbpoolen med län, listspår, utslag)
 * tas bort av API:t innan svaret lämnar servern (leads.py:_ARBETSMINNE, LK-033),
 * och inget här frågar efter det.
 */
import type { Localized } from "@/lib/i18n";
import type { Struktur } from "@/lib/leads/struktur";

/** Ett bolag körningen valde bort, med steget och skälet (svensk servertext). */
export type Tratt = { namn: string; steg: string; skal: string; belagg?: string | null };

/** Ett barnjobb: ett bolag som researchas eller researchats i körningen. */
export type Korningsjobb = { job_id: string; prospect_id?: string; company_name?: string | null };

/** Överskrivningarna körningen startades med (schemas.py:LeadsRunOverrides). */
export type Overskrivningar = {
  industries?: string[];
  exclude_industries?: string[];
  geography?: string[];
  roles?: string[];
  must_have?: string[];
  deal_breakers?: string[];
  anstallda_min?: number;
  anstallda_max?: number;
};

/** Iris-motorns tillstånd (app/leads/korning.py:ny_korning), utan arbetsminnet. */
export type Korning = {
  mal: number;
  levererade: number;
  undersokta: number;
  pagaende: number;
  rundor?: number;
  tak?: number;
  klar: boolean;
  slut_orsak?: string | null;
  flaskhals?: string | null;
  sammanfattning?: string | null;
  scope?: string;
  struktur?: Struktur;
  overrides?: Overskrivningar | null;
  is_test?: boolean;
  /** `lista` för en Skapa utkast-körning ur en lista: den går inte att fortsätta (leads.py:_kan_fortsatta). */
  kalla?: string | null;
  /** Hur många gånger körningen fortsatts efter ett slut under målet. */
  fortsatt?: number;
  tratt?: Tratt[];
  jobs?: Korningsjobb[];
  /** Listan bär antalen i stället för listorna (listvy.korning_sammandrag). */
  tratt_antal?: number;
  jobs_antal?: number;
  styrning?: "paus" | "avbruten" | null;
  /** Under målet med alla påfyllnadssteg tömda: körningen vilar och prövas igen en gång per dygn (CLAUDE.md regel 23). */
  vilande?: { sedan: string; skal: string } | null;
};

/** En rad i liggaren (`leads_job_ledger`): Iris-körningar och listjobb. */
export type KorningsRad = {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  scope: "batch" | "lista";
  is_test: boolean;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  error: string | null;
  korning: Korning | null;
};

// ---------------------------------------------------------------------------
// Körningens utkast (leads.py:_korningens_leads)
// ---------------------------------------------------------------------------

/** Samma härledning som Iris-listan (app/leads/utkaststatus.py). `koad`: köat utan granskning (äldre utkast). */
export type KorningsUtkaststatus = "vantar" | "godkant" | "koad" | "skickat" | "avvisat" | "stoppat" | "saknas";

export type KorningsLead = {
  prospect_id: string;
  company_name: string | null;
  contact_email: string | null;
  kan_mejlas: boolean;
  status: KorningsUtkaststatus;
  /** Granskningskölens post för ett väntande utkast. */
  queue_item_id?: string | null;
  skal?: string | null;
  skickas_tidigast?: string | null;
  subject: string | null;
  body?: string | null;
  /** Skälet när utkast saknas. */
  notis: string | null;
};

export type KorningsUtkastSvar = {
  leads: KorningsLead[];
  antal: Partial<Record<KorningsUtkaststatus | "kan_skrivas", number>>;
};

export const UTKASTSTATUS: Record<KorningsUtkaststatus, { namn: Localized; badge: "yellow" | "neutral" | "green" | "red" }> = {
  vantar: { namn: { sv: "Utkast väntar", en: "Draft waiting" }, badge: "yellow" },
  godkant: { namn: { sv: "Godkänt, skickas 08 till 16", en: "Approved, sends 08 to 16" }, badge: "neutral" },
  koad: { namn: { sv: "Köat, ej granskat", en: "Queued, not reviewed" }, badge: "yellow" },
  skickat: { namn: { sv: "Skickat", en: "Sent" }, badge: "green" },
  avvisat: { namn: { sv: "Avvisat", en: "Rejected" }, badge: "neutral" },
  stoppat: { namn: { sv: "Stoppat av sändspärr", en: "Stopped by a send guard" }, badge: "red" },
  saknas: { namn: { sv: "Inget utkast", en: "No draft" }, badge: "neutral" }
};

// ---------------------------------------------------------------------------
// Orden för körningen
// ---------------------------------------------------------------------------

/** Pågår? Både liggarens status och motorns `klar`: raden kan stå `completed` från sökjobbet medan motorn fyller på. */
export function pagar(rad: KorningsRad): boolean {
  if (rad.status === "queued" || rad.status === "processing") return true;
  return Boolean(rad.korning && !rad.korning.klar && rad.status !== "failed");
}

/** Arbetar den just nu? En vilande körning väcks en gång per dygn och pollas inte. */
export const arbetar = (rad: KorningsRad) => pagar(rad) && !rad.korning?.vilande;

/** Hur gick det? Klar utan ett enda lead är ett misslyckande för kunden (Sebbe 2026-10-06). */
export type Utfallston = "ok" | "under" | "stannade";

export function utfallston(rad: KorningsRad): Utfallston {
  const k = rad.korning;
  if (rad.status !== "completed" || !k?.klar || !k.mal) return "ok";
  if (k.slut_orsak === "avbruten") return "ok";
  if (k.levererade === 0) return "stannade";
  if (k.levererade < k.mal) return "under";
  return "ok";
}

/** Läget som etikettens nyckel: det styr både ordet och färgen. */
export type Lage = "koad" | "pagar" | "pausad" | "avbryts" | "vilar" | "klar" | "under" | "stannade" | "fel";

export function lage(rad: KorningsRad): Lage {
  if (rad.status === "failed") return "fel";
  if (pagar(rad)) {
    if (rad.korning?.styrning === "paus") return "pausad";
    if (rad.korning?.styrning === "avbruten") return "avbryts";
    if (rad.korning?.vilande) return "vilar";
    return rad.status === "queued" && !rad.korning ? "koad" : "pagar";
  }
  const ton = utfallston(rad);
  return ton === "stannade" ? "stannade" : ton === "under" ? "under" : "klar";
}

/**
 * Lägena i kundens ord (LK-022). "Klar, under målet" finns kvar för äldre körningar:
 * sedan regel 23 (2026-11-24) blir en körning under målet vilande i stället.
 */
export const LAGE: Record<Lage, { namn: Localized; badge: "yellow" | "neutral" | "green" | "red"; prick: "ockra" | "mossa" | "mineral" | "fara" }> = {
  koad: { namn: { sv: "Köad", en: "Queued" }, badge: "neutral", prick: "mineral" },
  pagar: { namn: { sv: "Pågår", en: "Running" }, badge: "yellow", prick: "ockra" },
  pausad: { namn: { sv: "Pausad", en: "Paused" }, badge: "neutral", prick: "mineral" },
  avbryts: { namn: { sv: "Avbryts", en: "Cancelling" }, badge: "neutral", prick: "mineral" },
  vilar: { namn: { sv: "Letar vidare", en: "Still looking" }, badge: "neutral", prick: "ockra" },
  klar: { namn: { sv: "Klar", en: "Done" }, badge: "green", prick: "mossa" },
  under: { namn: { sv: "Klar, under målet", en: "Done, under target" }, badge: "yellow", prick: "ockra" },
  stannade: { namn: { sv: "Stannade utan leads", en: "Stalled without leads" }, badge: "red", prick: "fara" },
  fel: { namn: { sv: "Misslyckades", en: "Failed" }, badge: "red", prick: "fara" }
};

/** Körningens typ (LK-021). Strukturen syns, så att det går att följa vilka utkast som skrevs i A och vilka i B. */
export function korningsTyp(rad: KorningsRad): Localized {
  if (rad.scope === "lista") return { sv: "Leadslista", en: "Lead list" };
  if (!rad.korning) return { sv: "Egna bolag", en: "Own companies" };
  if (rad.korning.kalla === "lista") return { sv: "Utkast ur en lista", en: "Drafts from a list" };
  if (rad.korning.scope !== "research_and_draft") return { sv: "Research", en: "Research" };
  return rad.korning.struktur === "b" ? { sv: "Research och utkast, B", en: "Research and drafts, B" } : { sv: "Research och utkast, A", en: "Research and drafts, A" };
}

/** Motorns slutorsaker i kundens ord (LK-024, app/leads/korning.py:avsluta). */
export const SLUT_ETIKETT: Record<string, Localized> = {
  klar: { sv: "Målet nått", en: "Target reached" },
  // Taket förlängs under målet sedan 2026-11-24 och talet har ändrats: inget tal här (Oklarhet 1 i app-04).
  tak: { sv: "Taket för antalet undersökta bolag nåddes", en: "The cap on the number of companies researched was reached" },
  slut_pa_kandidater: { sv: "Inga fler bolag att pröva i målgruppen", en: "No more companies to try in the target group" },
  sokningen_foll: { sv: "Sökningen gick inte att genomföra", en: "The search could not be completed" },
  inga_traffar: {
    sv: "Sökningen hittade inga bolag. Kontrollera orterna eller bredda bransch eller område.",
    en: "The search found no companies. Check the locations or widen the industry or area."
  },
  budget: { sv: "Dagens budget för körningar är slut", en: "Today's budget for runs is used up" },
  kredittak: { sv: "Körningens tak för sidhämtningar är nått", en: "The run's cap on page fetches was reached" },
  ingen_malgrupp: {
    sv: "Ingen målgrupp att söka i. Fyll i målgrupp under Inställningar eller välj bransch i filtret.",
    en: "No target group to search in. Fill in your target group under Settings or choose an industry in the filter."
  },
  avbruten: { sv: "Avbruten", en: "Cancelled" }
};

/** Vad som håller en vilande körning (app/leads/korning.py:vilans_skal). */
const VILA_SKAL: Record<string, Localized> = {
  registret: { sv: "inga fler bolag i målgruppen just nu, Iris prövar igen i morgon", en: "no more companies in the target group right now, Iris tries again tomorrow" },
  kredittak: { sv: "körningens tak för sidhämtningar är nått, Iris fortsätter i morgon", en: "the run's cap on page fetches was reached, Iris continues tomorrow" },
  sokningen_foll: { sv: "sökningen gick inte att genomföra, Iris försöker igen i morgon", en: "the search could not be completed, Iris tries again tomorrow" },
  ingen_malgrupp: { sv: "ingen målgrupp att söka i. Fyll i målgrupp under Inställningar", en: "no target group to search in. Fill in your target group under Settings" },
  inga_traffar: { sv: "sökningen hittade inga bolag. Kontrollera orterna eller bredda bransch eller område", en: "the search found no companies. Check the locations or widen the industry or area" }
};

/** "8 av 10, letar vidare: <skäl>" för en vilande körning, annars null. */
export function vilaText(k: Korning | null | undefined, text: (l: Localized) => string): string | null {
  if (!k?.vilande) return null;
  const skal = text(VILA_SKAL[k.vilande.skal] ?? VILA_SKAL.registret);
  return text({ sv: `${k.levererade} av ${k.mal}, letar vidare: ${skal}`, en: `${k.levererade} of ${k.mal}, still looking: ${skal}` });
}

/** Utfallet i en mening (LK-023): felet, vilan, sammanfattningen eller vad den gör nu. */
export function utfallText(rad: KorningsRad, text: (l: Localized) => string): string {
  const k = rad.korning;
  if (rad.error) return rad.error;
  const vila = vilaText(k, text);
  if (vila) return vila;
  if (k?.klar) return k.sammanfattning ?? (SLUT_ETIKETT[k.slut_orsak ?? ""] ? text(SLUT_ETIKETT[k.slut_orsak ?? ""]) : text({ sv: "Klar", en: "Done" }));
  if (k) {
    if (k.styrning === "paus") return text({ sv: "Pausad. De som redan researchas blir klara.", en: "Paused. Those already in research finish." });
    if (k.styrning === "avbruten") return text({ sv: "Avbryts när bolagen som researchas är klara.", en: "Cancels once the companies in research are done." });
    return k.pagaende ? text({ sv: "Researchar nästa bolag", en: "Researching the next company" }) : text({ sv: "Letar fler bolag", en: "Looking for more companies" });
  }
  if (rad.scope === "lista") return text({ sv: "Raderna finns under Listor.", en: "The rows are under Lists." });
  return pagar(rad) ? text({ sv: "Letar bolag som matchar målgruppen", en: "Looking for companies that match the target group" }) : "";
}

/**
 * Går körningen att fortsätta (LK-030)? Samma villkor som leads.py:_kan_fortsatta,
 * också `kalla=lista`, som servern vägrar (Oklarhet 2 i app-04): knappen visas inte för dem.
 */
export function kanFortsatta(rad: KorningsRad): boolean {
  const k = rad.korning;
  return (
    rad.scope === "batch" &&
    (rad.status === "completed" || rad.status === "failed") &&
    Boolean(k?.mal) &&
    (k?.levererade ?? 0) < (k?.mal ?? 0) &&
    k?.slut_orsak !== "avbruten" &&
    k?.kalla !== "lista" &&
    !k?.vilande
  );
}

/** Går den att styra (pausa, återuppta, avbryta)? Bara en pågående Iris-körning som inte redan avbryts. */
export const kanStyras = (rad: KorningsRad) => rad.scope === "batch" && pagar(rad) && Boolean(rad.korning) && rad.korning?.styrning !== "avbruten";

/**
 * Går den att pausa? Inte när den vilar: en vilande körning arbetar inte, och servern
 * (leads.py:styr_korning) väcker motorn direkt vid Återuppta, utanför vilans takt på en
 * gång per dygn. Avbryt står kvar för en vilande körning (sluta leta), och en redan
 * pausad vilande körning kan återupptas.
 */
export const kanPausas = (rad: KorningsRad) => kanStyras(rad) && !rad.korning?.vilande && rad.korning?.styrning !== "paus";

export const antalBortvalda = (k: Korning | null | undefined) => k?.tratt?.length ?? k?.tratt_antal ?? 0;
export const antalJobb = (k: Korning | null | undefined) => k?.jobs?.length ?? k?.jobs_antal ?? 0;

/** Trattens steg i kundens ord (LK-031, LK-042). Okända steg visas som de står. */
export const STEG: Record<string, Localized> = {
  register: { sv: "Registret", en: "Register" },
  jev: { sv: "Jev", en: "Jev" },
  "förfilter": { sv: "Förfiltret", en: "Pre-filter" },
  existens: { sv: "Existenskontrollen", en: "Existence check" },
  research: { sv: "Researchen", en: "Research" },
  "listspår": { sv: "Listspåret", en: "List track" },
  dubblett: { sv: "Dubblett", en: "Duplicate" }
};

/** Vad varje steg gör, för förklaringen under tratten. */
export const STEG_VAD: Record<string, Localized> = {
  register: { sv: "Föll i registrets filter på bransch, ort eller storlek.", en: "Dropped by the register's filter on industry, location or size." },
  jev: { sv: "Jev bedömde att bolaget inte passar er målgrupp.", en: "Jev judged that the company does not fit your target group." },
  "förfilter": { sv: "Föll på storlek, bransch, område eller en utesluten domän.", en: "Dropped on size, industry, area or an excluded domain." },
  existens: { sv: "Bolagets egen sajt kunde inte styrka att bolaget finns.", en: "The company's own site could not confirm that it exists." },
  research: { sv: "Researchen fann att bolaget inte blev ett leverbart lead.", en: "The research found that the company did not become a deliverable lead." },
  "listspår": { sv: "Gick till ringlistan eller listan över ej kvalificerade.", en: "Went to the call list or the list of not qualified companies." },
  dubblett: { sv: "Fanns redan som lead, i en lista eller i en annan körning.", en: "Already existed as a lead, in a list or in another run." }
};

/** Ordningen stegen står i, som motorn går dem. */
export const STEGORDNING = ["register", "förfilter", "existens", "jev", "research", "listspår", "dubblett"];

/** Lägesfraserna i Just nu (LK-027): det sakliga först, sedan vad körningen gör, var tionde sekund. */
export const RESEARCH_FRASER: Localized[] = [
  { sv: "Researchar", en: "Researching" },
  { sv: "Hittar dina nästa kunder", en: "Finding your next customers" },
  { sv: "Gräver i registren", en: "Digging through the registers" },
  { sv: "Läser bolagens sajter", en: "Reading the companies' sites" },
  { sv: "Väger bolagen mot din målgrupp", en: "Weighing companies against your target group" },
  { sv: "Letar rätt kontaktväg", en: "Finding the right way in" },
  { sv: "Sållar fram guldkornen", en: "Sifting out the gold" }
];
export const LETAR_FRASER: Localized[] = [
  { sv: "Letar", en: "Searching" },
  { sv: "Gräver i registren", en: "Digging through the registers" },
  { sv: "Hittar dina nästa kunder", en: "Finding your next customers" },
  { sv: "Ringar in nästa område", en: "Circling the next area" }
];

// ---------------------------------------------------------------------------
// Starten (POST /leads/runs/batch)
// ---------------------------------------------------------------------------

export type Startsvar = {
  jobs?: { job_id: string; prospect_id?: string }[];
  count?: number;
  scope?: string;
  is_test?: boolean;
  fase?: string;
  overrides?: Overskrivningar | null;
  struktur?: Struktur;
};

/** Ett jobb som `GET /leads/jobb/{id}` svarar för (api/chat.py:get_job). */
export type Jobbsvar = {
  status?: string;
  error?: string | null;
  result?: { jobs?: { job_id: string; prospect_id?: string }[]; korning?: Korning | null } | null;
};

/** Körningen som startades härifrån och ännu söker: följs igen efter en omladdning (LK-012). */
export type Startad = {
  jobbId: string;
  /** Beställt antal, eller antalet egna bolag. */
  antal: number;
  /** Egna bolag: körningen går den gamla vägen, ett researchjobb per bolag (LK-005, LK-014). */
  egna: boolean;
  scope: "research_and_draft" | "research";
  struktur: Struktur;
  /** Barnjobben när sökningen gav dem (egna bolag): de följs ett och ett. */
  barn?: string[];
};

/** Ett komma-separerat fält som lista. Tomt blir `undefined`: null betyder "använd den sparade målgruppen". */
export function lista(varde: string): string[] | undefined {
  const delar = varde
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean);
  return delar.length ? delar : undefined;
}

/** Egna bolag: ett per rad eller med semikolon. */
export function rader(varde: string): string[] {
  return varde
    .split(/[\n;]/)
    .map((d) => d.trim())
    .filter(Boolean);
}
