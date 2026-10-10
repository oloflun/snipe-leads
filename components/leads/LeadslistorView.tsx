"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { CrmKundlista } from "@/components/leads/CrmKundlista";
import { ImportCsv } from "@/components/leads/ImportCsv";
import { SaljlistaSektion } from "@/components/leads/Saljlista";
import { btnPrimary, btnSecondary, EmptyState, SkeletonRows, chip, chipAktiv, chipInaktiv, chiplista } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { useLocale, type Locale, type Localized } from "@/lib/i18n";
import { LEADS_UPPDATERADE, UTAN_UTKAST, UTKAST_TON, utkastText, type Utkastfalt } from "@/lib/leads/utkast";
import { cn } from "@/lib/utils";

/**
 * Leadslistor — tillägget vid sidan av de riktade körningarna.
 *
 * Kunden beställer en lista med titel och antal; agenten bygger den i
 * bakgrunden (ingen sändning, inga utkast) och raderna landar här som en
 * granskningsbar tabell med kontaktväg, källa och signal per bolag, plus
 * CSV-export. Grinden sitter i WorkspaceSection: den här vyn renderas bara
 * när arbetsytan har tillägget "leadlists".
 *
 * Backendkontraktet (byggs i snajp-support, migration 060):
 *   POST /leads/listor            {titel, antal, is_test?, overrides?} → 202 {list_id, job_id}
 *   GET  /leads/listor            → {lists: [...]}
 *   GET  /leads/listor/{id}       → {list: {...}, items: [...]}
 *   DELETE /leads/listor/{id}     → {id, raderad}  (Ta bort lista, 2026-10-08; 409 medan den byggs)
 *   POST /leads/listor/{id}/omprova {item_ids} → 202 {rader, processering}  (Processa om)
 *   POST /leads/listor/{id}/utkast  {item_ids} → 202 {count, batch_id, processering}  (Skapa utkast)
 *   POST /leads/listor/{id}/items/{item}/prospekt → {prospect, skapad}  (radens lead, för lådan)
 * 409 = listan processas redan. Förloppet står i `list.processering`.
 * 429 betyder budgettak — feltexten kommer i `detail` och visas som den är.
 */

type Lista = {
  id: string;
  titel: string;
  antal: number;
  /** bestalld | byggs | klar | fel — speglar check-villkoret i migration 060. */
  status: string;
  felorsak?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
  item_count?: number | null;
  /** Migration 082/098: 'sok' | 'kombinerad' | 'import' | 'crm', källistornas id och filtret. */
  kalla?: string | null;
  kallistor?: string[] | null;
  kontaktfilter?: string | null;
  /** Processa om / Skapa utkast (migration 110): förloppet, kvar efteråt. */
  processering?: Processering | null;
};

type Processering = {
  typ: "processa" | "utkast";
  status: "pagar" | "klar" | "fallen";
  startad: string;
  senast?: string | null;
  klar_at?: string | null;
  totalt: number;
  klara: number;
  /** Processa om: utfallet per rad. */
  utfall?: { mejl?: number; telefon?: number; utan?: number; avvecklade?: number } | null;
  /** Skapa utkast: levererade utkast, körningen och dess sammanfattning. */
  levererade?: number | null;
  job_id?: string | null;
  sammanfattning?: string | null;
  /** Radernas id i förloppet. */
  rader?: string[] | null;
  fel?: string | null;
};

type ListRad = {
  /** Radens id i lead_list_items. */
  id: string;
  company_name: string;
  website?: string | null;
  ort?: string | null;
  contact_name?: string | null;
  contact_role?: string | null;
  contact_email?: string | null;
  /** Kontaktpersonens telefon (registerkällan, migration 081). */
  contact_phone?: string | null;
  orgnr?: string | null;
  contact_level?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  signal?: string | null;
  signal_detalj?: string | null;
  /** Webbpoolen (migration 108): länets slug och sidbedömningen. Bara
   *  webbyråerna får nivån och revisionen (backenden döljer dem för övriga). */
  lan?: string | null;
  webbniva?: Webbniva | null;
  webbrevision?: { modernitet?: number | null; brister?: string[] | null; platshallare?: string | null } | null;
  /** Radens lead (migration 110): öppnas i samma låda som ett Iris-lead. */
  prospect_id?: string | null;
  /** Källor raden prövats mot ("register", "katalog", "webbplats", "webbuppslag"). */
  kallor?: string[] | null;
  /** När Processa om senast nådde raden. */
  processad_at?: string | null;
  /** Utkaststatusen, samma härledning som Iris-tabellen (app/leads/utkaststatus.py). */
  utkast_status?: Utkastfalt | null;
};

/** Sant från md (768px) och uppåt; null innan fönstret mätts.
 *  Tabellen (md+) och korten (under md) står båda i DOM:en; bolagsknappens
 *  id (lådans fokusretur) sätts bara i den layout som syns. */
function useBredSkarm(): boolean | null {
  const [bred, setBred] = useState<boolean | null>(null);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    const satt = () => setBred(mq.matches);
    satt();
    mq.addEventListener("change", satt);
    return () => mq.removeEventListener("change", satt);
  }, []);
  return bred;
}

/** Backendens statusvärden, som text — samma mönster som Bolagsregistret. */
const STATUS_ETIKETT: Record<string, Localized> = {
  bestalld: { sv: "Beställd", en: "Ordered" },
  byggs: { sv: "Byggs", en: "Building" },
  klar: { sv: "Klar", en: "Done" },
  fel: { sv: "Fel", en: "Failed" }
};

/** Vilken väg raden går att nå: telefon, mejl eller båda. Antons underflik
 *  (2026-10-02) sitter i SAMMA lista, inte som en separat mejllista. */
type Kontaktvag = "telefon" | "mejl" | "bada";
type Kontaktfilter = "alla" | Kontaktvag;
type Sortering = "kontakt" | "bolag" | "niva";

function kontaktvag(rad: ListRad): Kontaktvag | null {
  const tel = Boolean(rad.contact_phone);
  const mejl = Boolean(rad.contact_email);
  if (tel && mejl) return "bada";
  if (tel) return "telefon";
  if (mejl) return "mejl";
  return null;
}

const KONTAKTFILTER: { id: Kontaktfilter; etikett: Localized }[] = [
  { id: "alla", etikett: { sv: "Alla", en: "All" } },
  { id: "telefon", etikett: { sv: "Telefon", en: "Phone" } },
  { id: "mejl", etikett: { sv: "Mejl", en: "Email" } },
  { id: "bada", etikett: { sv: "Båda", en: "Both" } }
];

const KONTAKTVAG_ETIKETT: Record<Kontaktvag, Localized> = {
  telefon: { sv: "Telefon", en: "Phone" },
  mejl: { sv: "Mejl", en: "Email" },
  bada: { sv: "Telefon och mejl", en: "Phone and email" }
};

/** Filtrerad och sorterad vy över listans rader. Sortering på kontaktväg:
 *  båda först, sedan telefon, sedan mejl; inom gruppen bolagsnamn A–Ö. */
type Webbniva = "akut" | "dalig" | "bra" | "mycket_bra";
/** Webbpoolens filter (plan 2026-10-08): webbplats, nivå och län. */
type Webbfilter = { webb: "alla" | "med" | "utan"; niva: "alla" | Webbniva; lan: string };
const INGET_WEBBFILTER: Webbfilter = { webb: "alla", niva: "alla", lan: "alla" };
const NIVAORDNING: Record<Webbniva, number> = { akut: 0, dalig: 1, mycket_bra: 2, bra: 3 };
const NIVAETIKETT: Record<Webbniva, Localized> = {
  akut: { sv: "Akut", en: "Urgent" },
  dalig: { sv: "Dålig", en: "Poor" },
  bra: { sv: "Bra", en: "Good" },
  mycket_bra: { sv: "Inspiration", en: "Inspiration" }
};
const LANNAMN: Record<string, Localized> = {
  "vastra-gotalands-lan": { sv: "Västra Götaland", en: "Västra Götaland" },
  "hallands-lan": { sv: "Halland", en: "Halland" },
  "gavleborgs-lan": { sv: "Gävleborg", en: "Gävleborg" },
  "jamtlands-lan": { sv: "Jämtland", en: "Jämtland" },
  "vasternorrlands-lan": { sv: "Västernorrland", en: "Västernorrland" },
  "vasterbottens-lan": { sv: "Västerbotten", en: "Västerbotten" },
  "norrbottens-lan": { sv: "Norrbotten", en: "Norrbotten" }
};

function synligaRader(
  items: ListRad[],
  filter: Kontaktfilter,
  sortering: Sortering,
  webbfilter: Webbfilter = INGET_WEBBFILTER
): ListRad[] {
  const ordning: Record<string, number> = { bada: 0, telefon: 1, mejl: 2 };
  const kvar = items.filter(
    (rad) =>
      (filter === "alla" || kontaktvag(rad) === filter) &&
      (webbfilter.webb === "alla" || Boolean(rad.website) === (webbfilter.webb === "med")) &&
      (webbfilter.niva === "alla" || rad.webbniva === webbfilter.niva) &&
      (webbfilter.lan === "alla" || rad.lan === webbfilter.lan)
  );
  return [...kvar].sort((a, b) => {
    if (sortering === "niva") {
      const d = (a.webbniva ? NIVAORDNING[a.webbniva] : 9) - (b.webbniva ? NIVAORDNING[b.webbniva] : 9);
      if (d !== 0) return d;
      const m = (a.webbrevision?.modernitet ?? 11) - (b.webbrevision?.modernitet ?? 11);
      if (m !== 0) return m;
    }
    if (sortering === "kontakt") {
      const d = (ordning[kontaktvag(a) ?? "z"] ?? 3) - (ordning[kontaktvag(b) ?? "z"] ?? 3);
      if (d !== 0) return d;
    }
    return a.company_name.localeCompare(b.company_name, "sv");
  });
}

const T = {
  kombineraRubrik: { sv: "Kombinera listor", en: "Combine lists" },
  importeraCsv: { sv: "Importera CSV", en: "Import CSV" },
  kallaImport: { sv: "Import", en: "Import" },
  listorSkiljs: {
    sv: "Listorna är bredare och kallare än Iris: bolag med VD:ns telefon eller mejl, för samtal eller ett mer generellt utskick. Ett bolag som redan är ett Iris-lead, står i en annan lista eller är din befintliga kund kommer aldrig med.",
    en: "Lists are broader and colder than Iris: companies with the CEO's phone or email, for calls or a more general outreach. A company that is already an Iris lead, sits in another list or is an existing customer is never included."
  },
  kallaCrm: {
    sv: "CRM-kunder, utesluts från Iris och listor",
    en: "CRM customers, excluded from Iris and lists"
  },
  kombineraHjalp: {
    sv: "Kryssa två eller fler klara listor. Dubbletter tas bort på organisationsnummer, källistorna rörs inte.",
    en: "Tick two or more finished lists. Duplicates are removed by organisation number; the source lists are left untouched."
  },
  kombineraTitel: { sv: "Namn på den nya listan", en: "Name of the new list" },
  kombineraPlaceholder: { sv: "Bygg i Västsverige", en: "Construction in western Sweden" },
  kontaktvag: { sv: "Kontaktväg", en: "Contact channel" },
  filterAlla: { sv: "Alla rader", en: "All rows" },
  filterTelefon: { sv: "Med telefon", en: "With phone" },
  filterMejl: { sv: "Med mejl", en: "With email" },
  filterBada: { sv: "Med både telefon och mejl", en: "With both phone and email" },
  kombinerarKnapp: { sv: "Kombinerar…", en: "Combining…" },
  valjForKombination: { sv: "Välj för kombination", en: "Select for combination" },
  beskrivBolag: { sv: "Beskriv vilka bolag listan ska hitta.", en: "Describe which companies the list should find." },
  antalGranser: { sv: "Antal bolag: minst 1, högst 200.", en: "Number of companies: at least 1, at most 200." },
  listanBestalld: { sv: "Listan är beställd.", en: "The list is ordered." },
  bestallEnLista: { sv: "Beställ en lista", en: "Order a list" },
  vilkaBolag: { sv: "Vilka bolag ska listan hitta?", en: "Which companies should the list find?" },
  vilkaBolagExempel: { sv: "Bransch, ort, storlek", en: "Industry, city, size" },
  antalBolag: { sv: "Antal bolag", en: "Number of companies" },
  bestaller: { sv: "Beställer…", en: "Ordering…" },
  bestallLista: { sv: "Beställ lista", en: "Order list" },
  dinaListor: { sv: "Dina listor", en: "Your lists" },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  ingaListor: { sv: "Inga listor ännu", en: "No lists yet" },
  hamtar: { sv: "Hämtar…", en: "Loading…" },
  doljListan: { sv: "Dölj listan", en: "Hide list" },
  oppnaListan: { sv: "Öppna listan", en: "Open list" },
  listanTom: { sv: "Listan är tom.", en: "The list is empty." },
  laddaNerCsv: { sv: "Ladda ner CSV", en: "Download CSV" },
  kalla: { sv: "Källa", en: "Source" },
  filnamn: { sv: "leadslista", en: "lead-list" },
  oppnar: { sv: "Öppnar…", en: "Opening…" },
  kundeInteOppnas: { sv: "Bolaget kunde inte öppnas.", en: "The company could not be opened." }
} satisfies Record<string, Localized>;

/** Kolumnerna i tabellen, i ordning. */
const TABELLRUBRIKER: Localized[] = [
  { sv: "Bolag", en: "Company" },
  { sv: "Ort", en: "City" },
  { sv: "Kontakt", en: "Contact" },
  { sv: "Kontaktnivå", en: "Contact level" },
  { sv: "Signal", en: "Signal" },
  { sv: "Källa", en: "Source" }
];

/** CSV-filens kolumner, i samma ordning som raderna i byggCsv. */
const CSV_RUBRIKER: Localized[] = [
  { sv: "Bolag", en: "Company" },
  { sv: "Org.nr", en: "Org. no." },
  { sv: "Ort", en: "City" },
  { sv: "Kontakt", en: "Contact" },
  { sv: "Telefon", en: "Phone" },
  { sv: "Kontaktnivå", en: "Contact level" },
  { sv: "Signal", en: "Signal" },
  { sv: "Källa", en: "Source" },
  { sv: "Källänk", en: "Source link" },
  { sv: "Webbplats", en: "Website" },
  { sv: "E-post", en: "Email" }
];

/**
 * Språket för fetch-hjälparen, som anropas utanför komponenterna och inte kan
 * använda useLocale. LocaleProvider (lib/i18n.tsx) håller `<html lang>` i takt
 * med valet, så attributet är samma källa som hooken läser.
 */
function sprak(): Locale {
  return typeof document !== "undefined" && document.documentElement.lang === "en" ? "en" : "sv";
}

/** Status som betyder att agenten fortfarande arbetar — de pollas. */
const PAGAENDE = new Set(["bestalld", "byggs"]);

/** Kontakttrappans nivåer på svenska — speglar LeadsSnabbsok.KONTAKTETIKETT
 *  (samma medvetna spegling som `anropa` och fältklassen ovan). Pixel-
 *  granskningen 2026-09-02 visade råa `ROLE_ADDRESS`-värden i tabellen. */
const KONTAKTNIVA_ETIKETT: Record<string, Localized> = {
  named_role_match: { sv: "Namngiven beslutsfattare", en: "Named decision maker" },
  named_other: { sv: "Namngiven kontakt", en: "Named contact" },
  role_address: { sv: "Rolladress", en: "Role address" },
  contact_form: { sv: "Kontaktformulär", en: "Contact form" }
};

function kontaktniva(rad: ListRad, locale: Locale): string | null {
  if (!rad.contact_level) return null;
  return KONTAKTNIVA_ETIKETT[rad.contact_level]?.[locale] ?? rad.contact_level;
}

// Samma fält- och radmönster som LeadsRunForm. Speglas med flit i stället för
// att delas — samma resonemang som `anropa` nedan och som Bolagssida.tsx: en
// delad hjälpare hade tvingat fram en export ur en fil vars docstring säger
// att den bara har två ytor.
const fältklass =
  "w-full rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] focus-ring";

function Rad({
  etikett,
  hint,
  children
}: Readonly<{ etikett: string; hint?: string; children: React.ReactNode }>) {
  return (
    <label className="block">
      <span className="text-[13px] font-medium text-ink-muted">{etikett}</span>
      {hint ? <span className="ml-2 text-[12px] text-ink-subtle">{hint}</span> : null}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

/**
 * Speglar `anropa()` i LeadsRunForm.tsx med flit i stället för att delas —
 * samma resonemang som Bolagssida.tsx: Pydantics 422 lägger en LISTA i
 * `detail`, en handskriven HTTPException (t.ex. 429-budgettaket) en STRÄNG,
 * och båda ska bli läsbar svenska i stället för "[object Object]".
 */
async function anropa<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/snajp-support${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init
  });
  const kropp =
    (await readJsonBody<T & { error?: string; detail?: unknown }>(response)) ?? ({} as T);
  if (!response.ok) {
    const k = kropp as { error?: string; detail?: unknown };
    const detaljtext = Array.isArray(k.detail)
      ? k.detail
          .map((d) =>
            d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)
          )
          .join("; ")
      : typeof k.detail === "string"
        ? k.detail
        : undefined;
    const avvisat: Localized = {
      sv: `Anropet avvisades (${response.status}).`,
      en: `The request was rejected (${response.status}).`
    };
    throw new Error(detaljtext ?? k.error ?? avvisat[sprak()]);
  }
  return kropp;
}

/** Kontaktvägen som EN sträng: namn/roll om de finns, annars adressen. */
function kontakt(rad: ListRad): string {
  const namnRoll = [rad.contact_name, rad.contact_role].filter(Boolean).join(", ");
  return namnRoll || rad.contact_email || "—";
}

function signaltext(rad: ListRad, text?: (s: Localized) => string): string {
  // Webbpoolens rader (plan 2026-10-08): nivån och betyget byggs här på
  // användarens språk; bristen är bildmodellens fritext och står som den är.
  if (text && rad.webbniva) {
    const m = rad.webbrevision?.modernitet;
    const detalj = rad.webbrevision?.platshallare ?? rad.webbrevision?.brister?.[0];
    return [
      text(NIVAETIKETT[rad.webbniva]),
      typeof m === "number" ? text({ sv: `modernitet ${m}/10`, en: `modernity ${m}/10` }) : null,
      detalj
    ]
      .filter(Boolean)
      .join(" · ");
  }
  return [rad.signal, rad.signal_detalj].filter(Boolean).join(" — ") || "—";
}

/** RFC 4180-citering. Semikolon som avgränsare och BOM först: svensk Excel
 *  öppnar annars hela filen i en kolumn och läser å/ä/ö som mojibake. */
function csvFalt(värde: string | null | undefined): string {
  const text = värde ?? "";
  return /[";\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function byggCsv(items: ListRad[], locale: Locale): string {
  const rader = [
    CSV_RUBRIKER.map((rubrik) => rubrik[locale]),
    ...items.map((rad) => [
      rad.company_name,
      rad.orgnr ?? "",
      rad.ort ?? "",
      kontakt(rad),
      rad.contact_phone ?? "",
      kontaktniva(rad, locale) ?? "",
      signaltext(rad),
      rad.source_name ?? "",
      rad.source_url ?? "",
      rad.website ?? "",
      rad.contact_email ?? ""
    ])
  ];
  return "\uFEFF" + rader.map((rad) => rad.map(csvFalt).join(";")).join("\r\n");
}

function laddaNerCsv(titel: string, items: ListRad[], locale: Locale) {
  const blob = new Blob([byggCsv(items, locale)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  // Ur titeln, inte ett id: filen ska gå att hitta i en nedladdningsmapp.
  a.download = `${titel.replace(/[^\p{L}\p{N} _-]/gu, "").trim() || T.filnamn[locale]}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function datum(varde: string | null | undefined): string | null {
  if (!varde) return null;
  const d = new Date(varde);
  return Number.isNaN(d.getTime()) ? null : d.toISOString().slice(0, 10);
}

export function LeadslistorView({
  demo = false,
  crmOppen = false,
  onValjLead
}: Readonly<{
  demo?: boolean;
  crmOppen?: boolean;
  /** Öppnar lådan för ett lead (LeadsSida sätter `?lead=`). Utan den är
   *  listraderna inte klickbara (förhandsvisningarna). */
  onValjLead?: (prospektId: string) => void;
}> = {}) {
  const { isDemo, vy } = useDashboard();
  const { locale, text } = useLocale();

  const [titel, setTitel] = useState("");
  const [antal, setAntal] = useState("25");
  const [bestaller, setBestaller] = useState(false);
  const [bestallFel, setBestallFel] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const [listor, setListor] = useState<Lista[] | null>(null);
  const [listFel, setListFel] = useState<string | null>(null);

  const [vald, setVald] = useState<{ lista: Lista; items: ListRad[] } | null>(null);
  const [oppnar, setOppnar] = useState<string | null>(null);
  const [detaljFel, setDetaljFel] = useState<string | null>(null);
  // Kombinera (migration 082): kryssa flera klara listor, bygg en ny ur dem.
  const [valdaListor, setValdaListor] = useState<Set<string>>(new Set());
  const [kombTitel, setKombTitel] = useState("");
  const [kombFilter, setKombFilter] = useState<"alla" | "telefon" | "mejl" | "bada">("alla");
  const [kombinerar, setKombinerar] = useState(false);
  const [kombFel, setKombFel] = useState<string | null>(null);
  const [kombKvitto, setKombKvitto] = useState<Localized | null>(null);
  // CSV-import (Fas 10): bredvid Kombinera, listan hämtas om när importen är klar.
  const [importOppen, setImportOppen] = useState(false);

  function vaxlaVald(id: string) {
    setValdaListor((fore) => {
      const nasta = new Set(fore);
      if (nasta.has(id)) nasta.delete(id);
      else nasta.add(id);
      return nasta;
    });
  }

  async function kombinera() {
    setKombinerar(true);
    setKombFel(null);
    setKombKvitto(null);
    try {
      const ut = await anropa<{ list: Lista; items: ListRad[]; dubbletter_bort: number }>("/leads/listor/kombinera", {
        method: "POST",
        body: JSON.stringify({ titel: kombTitel.trim(), list_ids: [...valdaListor], kontaktfilter: kombFilter })
      });
      setKombKvitto({
        sv: `${ut.list.titel}: ${ut.items.length} rader, ${ut.dubbletter_bort} dubbletter borttagna.`,
        en: `${ut.list.titel}: ${ut.items.length} rows, ${ut.dubbletter_bort} duplicates removed.`
      });
      setValdaListor(new Set());
      setKombTitel("");
      await hamtaListor();
    } catch (cause) {
      setKombFel(felmeddelande(cause));
    } finally {
      setKombinerar(false);
    }
  }

  const hamtaListor = useCallback(async (tyst = false) => {
    if (!tyst) setListFel(null);
    // Demon har inget konto: inget anrop, ingen "Du måste vara inloggad" (a11y-audit 2026-10-02).
    if (demo || isDemo || vy === "demo") {
      setListor([]);
      return;
    }
    try {
      const svar = await anropa<{ lists?: Lista[] }>("/leads/listor");
      setListor(svar.lists ?? []);
      setListFel(null);
    } catch (fel) {
      // Vid tyst pollning skrivs listan inte över av ett fel — nästa varv
      // kan lyckas, och en lista som blinkar bort är värre än en gammal.
      if (!tyst || listor === null) setListFel(felmeddelande(fel));
    }
  }, [listor, demo, isDemo, vy]);

  useEffect(() => {
    void hamtaListor();
    // Bara vid montering — pollningen nedan äger uppdateringarna.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Pollning: så länge någon lista är beställd eller byggs hämtas läget om
  // var 5:e sekund — samma tålmodiga mönster som LeadsRunForm mot jobben,
  // men mot listresursen: timern re-armas av varje nytt svar och dör av sig
  // själv när inget längre är pågående.
  useEffect(() => {
    if (!listor?.some((l) => PAGAENDE.has(l.status))) return;
    const timer = window.setTimeout(() => void hamtaListor(true), 5000);
    return () => window.clearTimeout(timer);
  }, [listor, hamtaListor]);

  async function bestall() {
    const antalTal = Number(antal);
    if (!titel.trim()) {
      setBestallFel(text(T.beskrivBolag));
      return;
    }
    if (!Number.isInteger(antalTal) || antalTal < 1 || antalTal > 200) {
      setBestallFel(text(T.antalGranser));
      return;
    }

    setBestaller(true);
    setBestallFel(null);
    setStatus(null);
    try {
      // 429 = budgettak, 422 = inget sökbart underlag (varken sparad målgrupp
      // eller titel). `anropa` plockar redan ut feltexten ur `detail`, så den
      // visas som den är i felraden nedan.
      await anropa<{ list_id?: string; job_id?: string }>("/leads/listor", {
        method: "POST",
        body: JSON.stringify({
          titel: titel.trim(),
          antal: antalTal,
          // Titeln STYR sökningen. Utan overrides byggde listjobbet bara på
          // den sparade målgruppen, och "Bygg i Norrland" gav samma bolag som
          // "Tandläkare i Skåne" — testaren skrev en titel som såg ut som en
          // sökning och fick något annat. Samma form som LeadsSnabbsok.
          overrides: { must_have: [titel.trim()] },
          // Demovyn räknas som test, precis som i Discovery: den ska aldrig
          // synas som kundvolym.
          is_test: isDemo || vy === "demo"
        })
      });
      setTitel("");
      setStatus(text(T.listanBestalld));
      await hamtaListor(true);
    } catch (fel) {
      setBestallFel(felmeddelande(fel));
    } finally {
      setBestaller(false);
    }
  }

  /** Hämtar den öppna listans rader igen utan att fälla ihop den — medan
   *  Processa om eller Skapa utkast pågår dyker fynden upp rad för rad. */
  async function uppdatera(listaId: string) {
    try {
      const svar = await anropa<{ list?: Lista; items?: ListRad[] }>(`/leads/listor/${encodeURIComponent(listaId)}`);
      setVald((nu) => (nu && nu.lista.id === listaId ? { lista: svar.list ?? nu.lista, items: svar.items ?? nu.items } : nu));
    } catch {
      // En missad uppdatering rättar nästa; listan står kvar som den var.
    }
  }

  async function oppna(lista: Lista) {
    if (lista.status !== "klar") return;
    if (vald?.lista.id === lista.id) {
      setVald(null);
      return;
    }
    setOppnar(lista.id);
    setDetaljFel(null);
    try {
      const svar = await anropa<{ list?: Lista; items?: ListRad[] }>(
        `/leads/listor/${encodeURIComponent(lista.id)}`
      );
      setVald({ lista: svar.list ?? lista, items: svar.items ?? [] });
    } catch (fel) {
      setDetaljFel(felmeddelande(fel));
    } finally {
      setOppnar(null);
    }
  }

  return (
    <div className="flex min-w-0 flex-col gap-12">
      {/* ------------------------------ SÄLJLISTAN (100, 103) */}
      <SaljlistaSektion demo={demo} />

      {/* ------------------------------------- CRM-KUNDLISTAN (098) */}
      <CrmKundlista
        demo={demo || isDemo || vy === "demo"}
        startOppen={crmOppen}
        onKlar={() => void hamtaListor(true)}
      />

      {/* ------------------------------------------- BESTÄLLNING */}
      <section aria-labelledby="bestall-lista">
        <h2 id="bestall-lista" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
          {text(T.bestallEnLista)}
        </h2>
        <p className="mt-1 max-w-[64ch] text-[14px] leading-6 text-ink-subtle">{text(T.listorSkiljs)}</p>

        <div className="mt-6 grid max-w-[760px] gap-5 sm:grid-cols-2">
          <Rad etikett={text(T.vilkaBolag)}>
            <input
              value={titel}
              onChange={(e) => setTitel(e.target.value)}
              placeholder={text(T.vilkaBolagExempel)}
              className={fältklass}
            />
          </Rad>
          <Rad etikett={text(T.antalBolag)} hint="1–200">
            <input
              type="number"
              min={1}
              max={200}
              value={antal}
              onChange={(e) => setAntal(e.target.value)}
              className={fältklass}
            />
          </Rad>
        </div>

        <button
          type="button"
          onClick={() => void bestall()}
          disabled={bestaller}
          className={cn(btnSecondary, "mt-5")}
        >
          {bestaller ? text(T.bestaller) : text(T.bestallLista)}
        </button>

        {status ? <p className="mt-3 text-[13px] text-ink-subtle">{status}</p> : null}
        {bestallFel ? (
          <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
            {bestallFel}
          </p>
        ) : null}
      </section>

      {/* ---------------------------------------------- LISTORNA */}
      <section aria-labelledby="dina-listor" className="border-t border-ink/15 pt-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="dina-listor" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
            {text(T.dinaListor)}
          </h2>
          <button
            type="button"
            aria-expanded={importOppen}
            onClick={() => setImportOppen((v) => !v)}
            className={btnSecondary}
          >
            {text(T.importeraCsv)}
          </button>
        </div>

        {importOppen ? (
          <div className="mt-4 rounded-card border border-ink/12 bg-paper2/40 p-4">
            <ImportCsv demo={demo || isDemo || vy === "demo"} onKlar={() => void hamtaListor(true)} />
          </div>
        ) : null}

        {listFel ? (
          <div className="mt-4">
            <p role="alert" className="max-w-[70ch] break-words text-[15px] text-danger">
              {listFel}
            </p>
            <button
              type="button"
              onClick={() => void hamtaListor()}
              className={cn(btnSecondary, "mt-4")}
            >
              {text(T.forsokIgen)}
            </button>
          </div>
        ) : listor === null ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : listor.length === 0 ? (
          <div className="mt-4">
            <EmptyState title={text(T.ingaListor)} />
          </div>
        ) : (
          <>
          {listor.filter((l) => l.status === "klar" && l.kalla !== "crm" && l.kalla !== "saljlista").length >= 2 ? (
            <div className="mt-4 rounded-card border border-ink/12 bg-paper2/40 p-4">
              <p className="text-[15px] font-semibold">{text(T.kombineraRubrik)}</p>
              <p className="mt-1 text-[13px] text-ink-subtle">{text(T.kombineraHjalp)}</p>
              <div className="mt-3 flex flex-wrap items-end gap-3">
                <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-[13px] text-ink-muted">
                  {text(T.kombineraTitel)}
                  <input
                    value={kombTitel}
                    onChange={(e) => setKombTitel(e.target.value)}
                    placeholder={text(T.kombineraPlaceholder)}
                    className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[15px]"
                  />
                </label>
                <label className="flex flex-col gap-1 text-[13px] text-ink-muted">
                  {text(T.kontaktvag)}
                  <select
                    value={kombFilter}
                    onChange={(e) => setKombFilter(e.target.value as typeof kombFilter)}
                    className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-2 text-[15px] text-ink"
                  >
                    <option value="alla">{text(T.filterAlla)}</option>
                    <option value="telefon">{text(T.filterTelefon)}</option>
                    <option value="mejl">{text(T.filterMejl)}</option>
                    <option value="bada">{text(T.filterBada)}</option>
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => void kombinera()}
                  disabled={kombinerar || valdaListor.size < 2 || !kombTitel.trim()}
                  className={cn(btnPrimary, "disabled:opacity-60")}
                >
                  {kombinerar
                    ? text(T.kombinerarKnapp)
                    : text({ sv: `Kombinera ${valdaListor.size} valda`, en: `Combine ${valdaListor.size} selected` })}
                </button>
              </div>
              {kombFel ? (
                <p role="alert" className="mt-3 text-[15px] text-danger">
                  {kombFel}
                </p>
              ) : null}
              {kombKvitto ? (
                <p role="status" className="mt-3 text-[15px] text-moss">
                  {text(kombKvitto)}
                </p>
              ) : null}
            </div>
          ) : null}
          <ul className="mt-4 divide-y divide-ink/15 border-y border-ink/15">
            {listor
              // En säljlistebeställning (105) är ingen lista att öppna:
              // raderna ligger i säljlistan ovanför, resten är uteslutning.
              .filter((lista) => lista.kalla !== "saljlista")
              .map((lista) => {
              const oppen = vald?.lista.id === lista.id;
              const klar = lista.status === "klar";
              return (
                <li key={lista.id} className="py-4">
                  {klar && lista.kalla !== "crm" ? (
                    <label className="mb-2 flex items-center gap-2 text-[13px] text-ink-muted">
                      <input
                        type="checkbox"
                        checked={valdaListor.has(lista.id)}
                        onChange={() => vaxlaVald(lista.id)}
                        className="h-4 w-4 accent-ink"
                      />
                      {text(T.valjForKombination)}
                    </label>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => void oppna(lista)}
                    disabled={!klar}
                    aria-expanded={klar ? oppen : undefined}
                    className={cn(
                      "focus-ring block w-full rounded-input text-left",
                      !klar && "cursor-default"
                    )}
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                      <div className="min-w-0">
                        <p className="text-[15px] font-semibold tracking-[-0.01em]">
                          {lista.titel}
                        </p>
                        <p className="mt-1 text-[13px] text-ink-subtle">
                          {[
                            lista.kalla === "kombinerad"
                              ? text({
                                  sv: `Kombinerad av ${lista.kallistor?.length ?? 0} listor`,
                                  en: `Combined from ${lista.kallistor?.length ?? 0} lists`
                                })
                              : lista.kalla === "crm"
                                ? text(T.kallaCrm)
                                : lista.kalla === "import"
                                ? text(T.kallaImport)
                                : lista.kalla === "webbpool"
                                ? text({ sv: "Webbpoolen, bedömda sajter", en: "Website pool, assessed sites" })
                                : text({ sv: `${lista.antal} beställda`, en: `${lista.antal} ordered` }),
                            typeof lista.item_count === "number"
                              ? text({ sv: `${lista.item_count} träffar`, en: `${lista.item_count} matches` })
                              : null,
                            datum(lista.completed_at ?? lista.created_at)
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                      </div>
                      {/* Ochre bara på det som pågår — klart är utgångsläget,
                          fel bär danger. Samma logik som StatusOrd i registret. */}
                      <span
                        className={cn(
                          "kicker shrink-0",
                          lista.status === "fel"
                            ? "text-danger"
                            : PAGAENDE.has(lista.status)
                              ? "text-warning"
                              : "text-mineral"
                        )}
                      >
                        {STATUS_ETIKETT[lista.status]?.[locale] ?? lista.status}
                      </span>
                    </div>
                    {lista.status === "fel" && lista.felorsak ? (
                      <p className="mt-2 max-w-[70ch] text-[14px] leading-6 text-danger">
                        {lista.felorsak}
                      </p>
                    ) : null}
                    {klar ? (
                      <p className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-warning">
                        {oppnar === lista.id
                          ? text(T.hamtar)
                          : oppen
                            ? text(T.doljListan)
                            : text(T.oppnaListan)}
                        <span aria-hidden>{oppen ? "↑" : "→"}</span>
                      </p>
                    ) : null}
                  </button>

                  <ListaAtgarder
                    lista={lista}
                    onBorttagen={() => {
                      if (vald?.lista.id === lista.id) setVald(null);
                      setValdaListor((fore) => {
                        const nasta = new Set(fore);
                        nasta.delete(lista.id);
                        return nasta;
                      });
                      void hamtaListor(true);
                    }}
                  />

                  {oppen && vald ? (
                    <Listtabell
                      lista={vald.lista}
                      items={vald.items}
                      onUppdatera={() => uppdatera(vald.lista.id)}
                      onValjLead={onValjLead}
                    />
                  ) : null}
                </li>
              );
            })}
          </ul>
          </>
        )}

        {detaljFel ? (
          <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
            {detaljFel}
          </p>
        ) : null}
      </section>
    </div>
  );
}

/** Samma tak som backendens `_PROCESSERING_MAX_S`: en Processa om som inte
 *  rört sig på så länge dog med processen (en deploy mitt i). */
const STILLA_MS = 45 * 60_000;

/** Pågår förloppet? Processa om skriver `senast` per rad och räknas som dött
 *  när det stått still; Skapa utkast läses ur körningen och avgörs av den. */
function pagar(p: Processering | null | undefined): boolean {
  if (p?.status !== "pagar") return false;
  if (p.typ !== "processa") return true;
  const senast = Date.parse(p.senast ?? p.startad);
  return Number.isNaN(senast) || Date.now() - senast < STILLA_MS;
}

function klockslag(iso: string | null | undefined, locale: Locale): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/Stockholm"
      });
}

/**
 * Förloppet i listan (Antons regel 2026-10-10: varje funktion har ett sätt att
 * följa flödet). Läses ur `lead_lists.processering`: medan det pågår räknare
 * och stapel, efteråt en bestående resultatrad med tiden.
 */
function Forlopp({ p, korningHref }: Readonly<{ p: Processering; korningHref: string | null }>) {
  const { locale, text } = useLocale();
  const igang = pagar(p);
  const stannat = p.status === "pagar" && !igang;
  const u = p.utfall ?? {};
  const mejl = u.mejl ?? 0;
  const tel = u.telefon ?? 0;
  const utan = u.utan ?? 0;
  const avv = u.avvecklade ?? 0;
  const lev = p.levererade ?? 0;
  const tid = klockslag(p.klar_at ?? p.senast, locale);
  const procent = p.totalt > 0 ? Math.min(100, Math.round((p.klara / p.totalt) * 100)) : 0;

  let rad: string;
  if (p.typ === "processa") {
    const delar = (skilje: string) =>
      text({
        sv: [`${mejl} mejladress`, `${tel} telefon`, `${utan} utan kontakt`, avv ? `${avv} avvecklas` : null].filter(Boolean).join(skilje),
        en: [`${mejl} email address`, `${tel} phone`, `${utan} without contact`, avv ? `${avv} winding up` : null].filter(Boolean).join(skilje)
      });
    rad = igang
      ? text({
          sv: `Processar om ${p.klara} av ${p.totalt} · ${delar(" · ")}`,
          en: `Reprocessing ${p.klara} of ${p.totalt} · ${delar(" · ")}`
        })
      : stannat
        ? text({
            sv: `Processa om stannade efter ${p.klara} av ${p.totalt}. Starta igen för resten.`,
            en: `Reprocessing stopped after ${p.klara} of ${p.totalt}. Start again for the rest.`
          })
        : p.status === "fallen"
          ? text({ sv: "Processa om avbröts", en: "Reprocessing failed" })
          : text({ sv: `Processa om klar ${tid}: ${delar(", ")}.`, en: `Reprocessing done ${tid}: ${delar(", ")}.` });
  } else {
    rad = igang
      ? text({
          sv: `Skapar utkast ${p.klara} av ${p.totalt} · ${lev} utkast klara`,
          en: `Creating drafts ${p.klara} of ${p.totalt} · ${lev} drafts ready`
        })
      : p.status === "fallen"
        ? text({ sv: "Skapa utkast avbröts", en: "Creating drafts failed" })
        : text({
            sv: `Skapa utkast klar ${tid}: ${lev} utkast av ${p.totalt} bolag. Utkasten väntar på ditt ja innan något skickas.`,
            en: `Creating drafts done ${tid}: ${lev} drafts for ${p.totalt} companies. The drafts wait for your yes before anything is sent.`
          });
  }

  const fel = p.status === "fallen" || stannat;
  return (
    <div
      className="mt-4 rounded-card border border-ink/12 bg-paper2/40 p-4"
      // Räknaren byts var fjärde sekund; bara utfallet läses upp.
      aria-live={igang ? "off" : "polite"}
    >
      <p className={cn("max-w-[75ch] text-[15px] leading-6", fel ? "text-danger" : "text-ink")}>
        <span className="num tabular-nums">{rad}</span>
        {p.status === "fallen" && p.fel ? `: ${p.fel}` : null}
      </p>
      {igang ? (
        <div
          role="progressbar"
          aria-label={p.typ === "processa" ? text({ sv: "Processa om", en: "Reprocess" }) : text({ sv: "Skapa utkast", en: "Create drafts" })}
          aria-valuemin={0}
          aria-valuemax={p.totalt}
          aria-valuenow={p.klara}
          className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink/10"
        >
          <div className="h-full rounded-full bg-ochre transition-[width] duration-500" style={{ width: `${procent}%` }} />
        </div>
      ) : null}
      {p.typ === "utkast" && p.sammanfattning && !igang ? (
        <p className="mt-2 max-w-[75ch] text-[14px] leading-6 text-ink-muted">{p.sammanfattning}</p>
      ) : null}
      {p.typ === "utkast" && korningHref ? (
        <Link href={korningHref} className="focus-ring mt-2 inline-block text-[13px] font-medium text-warning underline underline-offset-4 hover:text-ink">
          {igang ? text({ sv: "Följ körningen", en: "Follow the run" }) : text({ sv: "Se körningen", en: "See the run" })}
        </Link>
      ) : null}
    </div>
  );
}

/** Radens läge under bolagsnamnet: "Söks…" medan Processa om når raden,
 *  "Iris skriver utkast…" under Skapa utkast, annars utkastets status med
 *  samma etikett som Iris-tabellen (lib/leads/utkast.ts). */
function RadLage({ rad, p }: Readonly<{ rad: ListRad; p: Processering | null | undefined }>) {
  const { locale, text } = useLocale();
  const status = rad.utkast_status?.utkast_status ?? "saknas";
  if (p && pagar(p) && p.rader?.includes(rad.id)) {
    const processad = rad.processad_at ? Date.parse(rad.processad_at) : Number.NaN;
    if (p.typ === "processa" && !(processad >= Date.parse(p.startad))) {
      return <p className="mt-1 text-[13px] text-warning">{text({ sv: "Söks…", en: "Searching…" })}</p>;
    }
    if (p.typ === "utkast" && UTAN_UTKAST.has(status)) {
      return <p className="mt-1 text-[13px] text-warning">{text({ sv: "Iris skriver utkast…", en: "Iris is writing a draft…" })}</p>;
    }
  }
  if (!rad.utkast_status || status === "saknas") return null;
  return (
    <p className={cn("mt-1 text-[13px]", UTKAST_TON[status])} title={rad.utkast_status.utkast_skal ?? undefined}>
      {utkastText(rad.utkast_status, locale, text)}
    </p>
  );
}

/**
 * Raderna i EN klar lista. Samma form som Bolagsregistret: tabell från md och
 * upp, kort under — sex kolumner krympta till 375px blir oläsliga.
 *
 * Raderna stannar i listan (Antons beslut 2026-10-10): ett klick på bolaget
 * öppnar samma låda som ett Iris-lead (radens bakgrundsprospekt, migration
 * 110), Skapa utkast gör samma research och utkast som Iris per bolag, och
 * Processa om söker kontaktuppgifterna på nytt. Båda gäller de markerade
 * raderna, annars de som syns, och följs i förloppet ovanför tabellen.
 */
function Listtabell({
  lista,
  items,
  onUppdatera,
  onValjLead
}: Readonly<{
  lista: Lista;
  items: ListRad[];
  onUppdatera: () => Promise<void>;
  onValjLead?: (prospektId: string) => void;
}>) {
  // I demon finns ingen riktig kedja att köra mot — åtgärderna döljs, CSV:n
  // står kvar.
  const { isDemo, vy } = useDashboard();
  const { locale, text } = useLocale();
  // En CRM-kundlista (migration 098) är kundens befintliga kunder: den är en
  // uteslutningsmängd och prospekteras inte — inga utkast, ingen låda.
  const atgarder = !isDemo && vy !== "demo" && lista.kalla !== "crm";
  const bred = useBredSkarm();
  const pathname = usePathname() ?? "/dashboard/leads";
  // Ytans rot (/dashboard eller /admin): körningen följs i Leads › Körningar.
  const bas = pathname.replace(/\/(leads|iris)(\/.*)?$/, "");

  const [valda, setValda] = useState<Set<string>>(new Set());
  const [startar, setStartar] = useState<"processa" | "utkast" | null>(null);
  const [atgardFel, setAtgardFel] = useState<string | null>(null);
  const [oppnar, setOppnar] = useState<string | null>(null);
  const [radFel, setRadFel] = useState<string | null>(null);
  const [kontaktfilter, setKontaktfilter] = useState<Kontaktfilter>("alla");
  const harNiva = items.some((rad) => rad.webbniva);
  const [sortering, setSortering] = useState<Sortering>(harNiva ? "niva" : "kontakt");
  const [webbfilter, setWebbfilter] = useState<Webbfilter>(INGET_WEBBFILTER);
  const visade = synligaRader(items, kontaktfilter, sortering, webbfilter);
  // Markerat som inte syns räknas inte: det som syns är det som berörs.
  const valt = visade.filter((rad) => valda.has(rad.id));
  const mal = valt.length ? valt : visade;
  const allaValda = visade.length > 0 && valt.length === visade.length;
  const lanIListan = [...new Set(items.map((rad) => rad.lan).filter((l): l is string => Boolean(l)))].sort();
  const nivaerIListan = (Object.keys(NIVAORDNING) as Webbniva[]).filter((n) => items.some((rad) => rad.webbniva === n));
  const antalPer = (f: Kontaktfilter) => (f === "alla" ? items.length : items.filter((rad) => kontaktvag(rad) === f).length);
  const medAdress = items.filter((rad) => rad.contact_email).length;

  const p = lista.processering ?? null;
  const igang = pagar(p);
  const korningHref = p?.job_id ? `${bas}/leads?vy=korningar&id=${encodeURIComponent(p.job_id)}` : null;

  // Listan hämtas om var fjärde sekund medan förloppet pågår (pausat när
  // fliken inte syns), och när lådan eller en massåtgärd ändrat ett utkast.
  const uppdateraRef = useRef(onUppdatera);
  useEffect(() => {
    uppdateraRef.current = onUppdatera;
  });
  useEffect(() => {
    if (!igang) return;
    const timer = window.setInterval(() => {
      if (!document.hidden) void uppdateraRef.current();
    }, 4000);
    return () => window.clearInterval(timer);
  }, [igang]);
  useEffect(() => {
    const uppdatera = () => void uppdateraRef.current();
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    return () => window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
  }, []);

  function vaxlaVald(id: string) {
    setValda((nu) => {
      const nasta = new Set(nu);
      if (nasta.has(id)) nasta.delete(id);
      else nasta.add(id);
      return nasta;
    });
  }

  /** Startar förloppet för `mal`, alltid med uttryckliga rad-id:n: förut
   *  skickades null utan kontaktfilter, och webbfiltren följde inte med. */
  async function starta(typ: "processa" | "utkast") {
    const item_ids = mal.map((rad) => rad.id);
    if (!item_ids.length || startar || igang) return;
    if (
      typ === "utkast" &&
      !window.confirm(
        text({
          sv: `Skapa utkast för ${item_ids.length} bolag? Varje bolag får samma research och utkast som ett Iris-lead och räknas mot er leadsbudget. Bolag som redan har ett utkast hoppas över.`,
          en: `Create drafts for ${item_ids.length} companies? Each company gets the same research and draft as an Iris lead and counts against your leads budget. Companies that already have a draft are skipped.`
        })
      )
    ) {
      return;
    }
    setStartar(typ);
    setAtgardFel(null);
    try {
      const body = JSON.stringify({ item_ids });
      if (typ === "utkast") {
        await anropa<{ count: number }>(`/leads/listor/${encodeURIComponent(lista.id)}/utkast`, { method: "POST", body });
      } else {
        await anropa<{ rader: number }>(`/leads/listor/${encodeURIComponent(lista.id)}/omprova`, { method: "POST", body });
      }
      setValda(new Set());
      await onUppdatera();
    } catch (orsak) {
      setAtgardFel(felmeddelande(orsak));
    } finally {
      setStartar(null);
    }
  }

  /** Öppnar radens lead i lådan. Saknar raden ett prospekt kopplas ett först
   *  (idempotent); raden stannar i listan. */
  async function oppnaRad(rad: ListRad) {
    if (!onValjLead) return;
    if (rad.prospect_id) {
      onValjLead(rad.prospect_id);
      return;
    }
    setOppnar(rad.id);
    setRadFel(null);
    try {
      const svar = await anropa<{ prospect?: { id: string } }>(
        `/leads/listor/${encodeURIComponent(lista.id)}/items/${encodeURIComponent(rad.id)}/prospekt`,
        { method: "POST" }
      );
      if (!svar.prospect?.id) throw new Error(text(T.kundeInteOppnas));
      onValjLead(svar.prospect.id);
      void onUppdatera();
    } catch (orsak) {
      setRadFel(felmeddelande(orsak));
    } finally {
      setOppnar(null);
    }
  }

  if (!items.length) {
    return (
      <p className="mt-4 border-t border-ink/10 pt-4 text-[15px] text-ink-muted">
        {text(T.listanTom)}
      </p>
    );
  }

  const klickbar = atgarder && Boolean(onValjLead);
  /** Bolagsnamnet: en knapp som öppnar lådan, annars text. `id` bara i den
   *  layout som syns, så att lådan lämnar tillbaka fokus till rätt knapp. */
  const bolagsnamn = (rad: ListRad, synlig: boolean, extra?: string) =>
    klickbar ? (
      <button
        type="button"
        id={synlig && rad.prospect_id ? `iris-rad-${rad.prospect_id}` : undefined}
        onClick={() => void oppnaRad(rad)}
        disabled={oppnar !== null}
        aria-label={text({ sv: `Öppna ${rad.company_name}`, en: `Open ${rad.company_name}` })}
        className={cn(
          "focus-ring -mx-1 rounded-input px-1 text-left text-[15px] font-semibold tracking-[-0.01em] decoration-ink/40 underline-offset-4 hover:underline disabled:cursor-wait",
          extra
        )}
      >
        {rad.company_name}
        {oppnar === rad.id ? <span className="ml-2 text-[13px] font-normal text-ink-subtle">{text(T.oppnar)}</span> : null}
      </button>
    ) : (
      <span className={cn("text-[15px] font-semibold tracking-[-0.01em]", extra)}>{rad.company_name}</span>
    );

  const kryss = (rad: ListRad, extra?: string) => (
    <label className={cn("-m-2 inline-flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center", extra)}>
      <input
        type="checkbox"
        checked={valda.has(rad.id)}
        onChange={() => vaxlaVald(rad.id)}
        aria-label={text({ sv: `Markera ${rad.company_name}`, en: `Select ${rad.company_name}` })}
        className="h-4 w-4 accent-ink"
      />
    </label>
  );

  return (
    <div className="mt-4 rounded-card border border-ink/10 bg-paper p-4 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <p className="text-[13px] text-ink-subtle">
          {text({
            sv: `${items.length} bolag i listan · ${antalPer("telefon") + antalPer("bada")} med telefon · ${medAdress} med mejladress`,
            en: `${items.length} companies in the list · ${antalPer("telefon") + antalPer("bada")} with a phone number · ${medAdress} with an email address`
          })}
        </p>
        {/* CSV:n byggs helt på klientsidan av raderna som redan är hämtade —
            ingen ny endpoint, och det som laddas ner är exakt det som syns. */}
        <button type="button" onClick={() => laddaNerCsv(lista.titel, items, locale)} className={cn(btnSecondary)}>
          {text(T.laddaNerCsv)}
        </button>
      </div>

      {atgarder ? (
        <>
          <p className="mt-3 max-w-[75ch] text-[14px] leading-6 text-ink-muted">
            {text({
              sv: "Klicka på ett bolag för att öppna det som ett Iris-lead. Skapa utkast gör samma research och utkast som för Iris-leads, och Processa om söker kontaktuppgifterna på nytt. Båda gäller de markerade bolagen, eller alla som syns om inget är markerat. Bolagen stannar i listan.",
              en: "Click a company to open it as an Iris lead. Create drafts runs the same research and drafts as for Iris leads, and Reprocess searches for contact details again. Both apply to the selected companies, or to everything visible if nothing is selected. The companies stay in the list."
            })}
          </p>
          <div
            className={cn(
              "mt-3 flex flex-wrap items-center gap-x-3 gap-y-2",
              valt.length > 0 && "sticky top-14 z-20 -mx-1 border-b border-ink/12 bg-paper px-1 py-2 lg:top-0"
            )}
          >
            <button
              type="button"
              onClick={() => setValda(allaValda ? new Set() : new Set(visade.map((rad) => rad.id)))}
              disabled={visade.length === 0}
              className={cn(btnSecondary, "disabled:opacity-60")}
            >
              {allaValda
                ? text({ sv: "Avmarkera alla", en: "Clear all" })
                : text({ sv: `Markera alla som syns (${visade.length})`, en: `Select all visible (${visade.length})` })}
            </button>
            {valt.length > 0 ? (
              <span className="num text-[0.875rem] font-medium">
                {text({ sv: `${valt.length} markerade`, en: `${valt.length} selected` })}
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => void starta("utkast")}
              disabled={startar !== null || igang || mal.length === 0}
              className={cn(btnPrimary, "disabled:opacity-60")}
            >
              {startar === "utkast"
                ? text({ sv: "Startar…", en: "Starting…" })
                : text({ sv: `Skapa utkast (${mal.length})`, en: `Create drafts (${mal.length})` })}
            </button>
            <button
              type="button"
              onClick={() => void starta("processa")}
              disabled={startar !== null || igang || mal.length === 0}
              className={cn(btnSecondary, "disabled:opacity-60")}
            >
              {startar === "processa"
                ? text({ sv: "Startar…", en: "Starting…" })
                : text({ sv: `Processa om (${mal.length})`, en: `Reprocess (${mal.length})` })}
            </button>
          </div>
          {atgardFel ? (
            <p role="alert" className="mt-3 max-w-[70ch] break-words text-[15px] text-danger">
              {atgardFel}
            </p>
          ) : null}
          {p ? <Forlopp p={p} korningHref={korningHref} /> : null}
        </>
      ) : null}

      {radFel ? (
        <p role="alert" className="mt-3 max-w-[70ch] break-words text-[14px] text-danger">
          {radFel}
        </p>
      ) : null}

      {/* Underfliken: samma lista, filtrerad på kontaktväg. Sortering: båda →
          telefon → mejl, eller bolagsnamn. */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        {/* Tryckknappar, inte role=tab: ett filter över samma tabell har ingen
            tabpanel, och tab-rollen lovar pilnavigering som inte finns (4.1.2). */}
        <div className={chiplista} role="group" aria-label={text({ sv: "Kontaktväg", en: "Contact channel" })}>
          {KONTAKTFILTER.map((f) => (
            <button
              key={f.id}
              type="button"
              aria-pressed={kontaktfilter === f.id}
              onClick={() => setKontaktfilter(f.id)}
              className={cn(chip, kontaktfilter === f.id ? chipAktiv : chipInaktiv)}
            >
              {text(f.etikett)} <span className="num tabular-nums">{antalPer(f.id)}</span>
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-[13px] text-ink-subtle">
          {text({ sv: "Sortera", en: "Sort" })}
          <select
            value={sortering}
            onChange={(e) => setSortering(e.target.value as Sortering)}
            className="focus-ring min-h-9 rounded-input border border-ink/15 bg-paper px-2 text-[13px] text-ink"
          >
            {harNiva ? <option value="niva">{text({ sv: "Webbnivå, akut först", en: "Website level, urgent first" })}</option> : null}
            <option value="kontakt">{text({ sv: "Kontaktväg", en: "Contact channel" })}</option>
            <option value="bolag">{text({ sv: "Bolag A–Ö", en: "Company A–Z" })}</option>
          </select>
        </label>
      </div>

      {/* Webbpoolens filter (plan 2026-10-08). Nivå och län visas bara när
          listan bär dem, alltså hos webbyråerna (bedömningen är hemlig). */}
      <div className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className={chiplista} role="group" aria-label={text({ sv: "Webbplats", en: "Website" })}>
          {(
            [
              ["alla", { sv: "Med och utan webbplats", en: "With and without website" }],
              ["med", { sv: "Med webbplats", en: "With website" }],
              ["utan", { sv: "Utan webbplats", en: "Without website" }]
            ] as const
          ).map(([id, etikett]) => (
            <button
              key={id}
              type="button"
              aria-pressed={webbfilter.webb === id}
              onClick={() => setWebbfilter({ ...webbfilter, webb: id })}
              className={cn(chip, webbfilter.webb === id ? chipAktiv : chipInaktiv)}
            >
              {text(etikett)}{" "}
              <span className="num tabular-nums">
                {id === "alla" ? items.length : items.filter((rad) => Boolean(rad.website) === (id === "med")).length}
              </span>
            </button>
          ))}
        </div>
        {nivaerIListan.length ? (
          <label className="flex items-center gap-2 text-[13px] text-ink-subtle">
            {text({ sv: "Webbnivå", en: "Website level" })}
            <select
              value={webbfilter.niva}
              onChange={(e) => setWebbfilter({ ...webbfilter, niva: e.target.value as Webbfilter["niva"] })}
              className="focus-ring min-h-9 rounded-input border border-ink/15 bg-paper px-2 text-[13px] text-ink"
            >
              <option value="alla">{text({ sv: "Alla nivåer", en: "All levels" })}</option>
              {nivaerIListan.map((n) => (
                <option key={n} value={n}>
                  {text(NIVAETIKETT[n])} ({items.filter((rad) => rad.webbniva === n).length})
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {lanIListan.length > 1 ? (
          <label className="flex items-center gap-2 text-[13px] text-ink-subtle">
            {text({ sv: "Län", en: "County" })}
            <select
              value={webbfilter.lan}
              onChange={(e) => setWebbfilter({ ...webbfilter, lan: e.target.value })}
              className="focus-ring min-h-9 rounded-input border border-ink/15 bg-paper px-2 text-[13px] text-ink"
            >
              <option value="alla">{text({ sv: "Alla län", en: "All counties" })}</option>
              {lanIListan.map((l) => (
                <option key={l} value={l}>
                  {LANNAMN[l] ? text(LANNAMN[l]) : l}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {/* Fast layout (table-fixed + colgroup): bredderna deklareras och
          summerar till tabellen — se Tabell i components/ui.tsx. Kryssrutans
          kolumn finns bara när åtgärderna gör det, så colgroup och huvudet
          följer samma villkor som cellerna. */}
      <div className="mt-4 hidden overflow-x-auto border-y border-ink/15 md:block">
        <table className="w-full min-w-[960px] table-fixed border-collapse text-[15px]">
          <colgroup>
            {atgarder ? <col style={{ width: "44px" }} /> : null}
            <col style={{ width: "22%" }} />
            <col style={{ width: "10%" }} />
            <col style={{ width: "18%" }} />
            <col style={{ width: "12%" }} />
            <col style={{ width: "24%" }} />
            <col style={{ width: "14%" }} />
          </colgroup>
          <thead>
            <tr className="border-b border-ink/15 text-left">
              {atgarder ? (
                <th scope="col" className="py-4">
                  <span className="sr-only">{text({ sv: "Markera", en: "Select" })}</span>
                </th>
              ) : null}
              {TABELLRUBRIKER.map((rubrik, i) => (
                <th
                  key={rubrik.sv}
                  scope="col"
                  className={cn("kicker py-4 font-medium text-mineral", i < TABELLRUBRIKER.length - 1 ? "pr-6" : "")}
                >
                  {text(rubrik)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink/15">
            {visade.map((rad) => (
              <tr key={rad.id} className={cn("transition hover:bg-paper2/60", valda.has(rad.id) && "bg-paper2/40")}>
                {atgarder ? <td className="py-4 pl-1 align-top">{kryss(rad, "mt-0.5")}</td> : null}
                <th scope="row" className="py-4 pr-6 text-left align-top font-normal">
                  {bolagsnamn(rad, bred === true)}
                  {rad.website ? <p className="mt-1 break-all text-sm text-ink-subtle">{rad.website}</p> : null}
                  <RadLage rad={rad} p={p} />
                </th>
                <td className="kicker py-4 pr-6 align-top text-mineral">{rad.ort ?? "—"}</td>
                <td className="py-4 pr-6 align-top">
                  <p className="text-[15px]">{kontakt(rad)}</p>
                  {kontaktvag(rad) ? (
                    <p className="mt-1 text-[12px] text-ink-subtle">{text(KONTAKTVAG_ETIKETT[kontaktvag(rad)!])}</p>
                  ) : null}
                  {rad.contact_phone ? (
                    <a href={`tel:${rad.contact_phone.replace(/[^\d+]/g, "")}`} className="num mt-1 block text-sm text-ink-muted underline-offset-4 hover:underline">
                      {rad.contact_phone}
                    </a>
                  ) : null}
                  {rad.contact_email && (rad.contact_name || rad.contact_role) ? (
                    <p className="mt-1 break-all text-sm text-ink-subtle">{rad.contact_email}</p>
                  ) : null}
                </td>
                <td className="py-4 pr-6 align-top text-[14px] text-ink-muted">{kontaktniva(rad, locale) ?? "—"}</td>
                <td className="py-4 pr-6 align-top text-[15px] leading-6 text-ink-muted">{signaltext(rad, text)}</td>
                <td className="py-4 align-top">
                  {rad.source_url ? (
                    <a
                      href={rad.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="focus-ring text-[14px] underline underline-offset-4 transition hover:text-ochre"
                    >
                      {rad.source_name || text(T.kalla)}
                    </a>
                  ) : (
                    <span className="text-[14px] text-ink-subtle">{rad.source_name ?? "—"}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="mt-4 space-y-2 md:hidden">
        {visade.map((rad) => (
          <li key={rad.id} className="rounded-input border border-ink/15 px-4 py-3">
            <div className="flex items-start gap-3">
              {atgarder ? kryss(rad, "mt-0.5") : null}
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-3">
                  {bolagsnamn(rad, bred === false, "min-w-0")}
                  {kontaktniva(rad, locale) ? (
                    <span className="shrink-0 text-[12px] text-ink-subtle">{kontaktniva(rad, locale)}</span>
                  ) : null}
                </div>
                <p className="kicker mt-1 text-mineral">{[rad.ort, rad.website].filter(Boolean).join(" · ") || "—"}</p>
                <RadLage rad={rad} p={p} />
                <p className="mt-2 text-sm leading-6 text-ink-muted">{signaltext(rad, text)}</p>
                <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <span className="min-w-0 break-all text-sm text-ink-muted">
                    {kontakt(rad)}
                    {rad.contact_phone ? (
                      <>
                        {" · "}
                        <a href={`tel:${rad.contact_phone.replace(/[^\d+]/g, "")}`} className="num underline-offset-4 hover:underline">
                          {rad.contact_phone}
                        </a>
                      </>
                    ) : null}
                  </span>
                  {rad.source_url ? (
                    <a
                      href={rad.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="focus-ring text-[13px] underline underline-offset-4"
                    >
                      {rad.source_name || text(T.kalla)}
                    </a>
                  ) : null}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Ta bort lista (kunden och adminen) och, för plattformsadmin, Kopiera eller
 * Flytta till en annan kund (Antons beställning 2026-10-08). Raderna följer
 * med när listan tas bort, och bolagen blir lediga för nästa körning. En
 * lista som byggs går inte att ta bort (backenden svarar 409). Kopian och
 * flytten går genom en serveraction med masternyckeln (lib/actions/listor.ts);
 * kunderna att välja bland är desamma som Byt kund erbjuder (/api/admin/kunder).
 */
function ListaAtgarder({ lista, onBorttagen }: Readonly<{ lista: Lista; onBorttagen: () => void }>) {
  const { isPlatformAdmin, isDemo, vy, arLasare } = useDashboard();
  const { text } = useLocale();
  const [tarBort, setTarBort] = useState(false);
  const [kundval, setKundval] = useState(false);
  const [kunder, setKunder] = useState<{ slug: string; name: string }[] | null>(null);
  const [vald, setVald] = useState("");
  const [skickar, setSkickar] = useState<"kopiera" | "flytta" | null>(null);
  const [besked, setBesked] = useState<{ text: string; fel: boolean } | null>(null);

  useEffect(() => {
    if (!kundval || kunder) return;
    let avbruten = false;
    void (async () => {
      try {
        const response = await fetch("/api/admin/kunder", { cache: "no-store" });
        const kropp = await readJsonBody<{ tenants?: { slug?: string | null; name?: string | null }[] }>(response);
        if (avbruten) return;
        if (!response.ok || !kropp?.tenants) {
          setBesked({ text: text({ sv: "Kundlistan gick inte att hämta.", en: "The customer list could not be loaded." }), fel: true });
          return;
        }
        setKunder(
          kropp.tenants
            .filter((t): t is { slug: string; name: string } => Boolean(t.slug && t.name))
            .map((t) => ({ slug: t.slug, name: t.name }))
            .sort((a, b) => a.name.localeCompare(b.name, "sv"))
        );
      } catch {
        if (!avbruten) {
          setBesked({ text: text({ sv: "Kundlistan gick inte att hämta.", en: "The customer list could not be loaded." }), fel: true });
        }
      }
    })();
    return () => {
      avbruten = true;
    };
  }, [kundval, kunder, text]);

  if (isDemo || vy === "demo" || arLasare || PAGAENDE.has(lista.status)) return null;

  async function taBort() {
    const rader = typeof lista.item_count === "number" ? lista.item_count : null;
    const fraga = text({
      sv: `Ta bort listan ”${lista.titel}”${rader !== null ? ` med ${rader} rader` : ""}? Det går inte att ångra.`,
      en: `Delete the list “${lista.titel}”${rader !== null ? ` with ${rader} rows` : ""}? This cannot be undone.`
    });
    if (!window.confirm(fraga)) return;
    setTarBort(true);
    setBesked(null);
    try {
      await anropa(`/leads/listor/${encodeURIComponent(lista.id)}`, { method: "DELETE" });
      onBorttagen();
    } catch (fel) {
      setBesked({ text: felmeddelande(fel), fel: true });
      setTarBort(false);
    }
  }

  async function tillKund(flytta: boolean) {
    const kund = kunder?.find((k) => k.slug === vald);
    if (!kund) return;
    if (
      flytta &&
      !window.confirm(
        text({
          sv: `Flytta listan ”${lista.titel}” till ${kund.name}? Den tas bort här när den kopierats.`,
          en: `Move the list “${lista.titel}” to ${kund.name}? It is removed here once copied.`
        })
      )
    ) {
      return;
    }
    setSkickar(flytta ? "flytta" : "kopiera");
    setBesked(null);
    try {
      const { listaTillKund } = await import("@/lib/actions/listor");
      const svar = await listaTillKund(lista.id, kund.slug, flytta);
      if (svar.error) {
        const kand: Record<string, Localized> = {
          admin: { sv: "Kräver plattformsadmin.", en: "Requires platform admin." },
          nyckel: { sv: "Masternyckeln saknas i den här miljön.", en: "The master key is missing in this environment." },
          indata: { sv: "Ogiltig lista eller kund.", en: "Invalid list or customer." },
          kund: { sv: "Kunden gick inte att läsa.", en: "The customer could not be read." }
        };
        setBesked({ text: svar.felkod ? text(kand[svar.felkod]) : svar.error, fel: true });
        return;
      }
      const upptagna = svar.upptagna ?? 0;
      setBesked({
        text: text({
          sv: `${svar.kopierade ?? 0} rader ${svar.flyttad ? "flyttade" : "kopierade"} till ${kund.name}.${upptagna ? ` ${upptagna} bolag fanns redan hos kunden och hoppades över.` : ""}`,
          en: `${svar.kopierade ?? 0} rows ${svar.flyttad ? "moved" : "copied"} to ${kund.name}.${upptagna ? ` ${upptagna} companies were already at the customer and were skipped.` : ""}`
        }),
        fel: false
      });
      if (svar.flyttad) onBorttagen();
    } catch (fel) {
      setBesked({ text: felmeddelande(fel), fel: true });
    } finally {
      setSkickar(null);
    }
  }

  const lank = "focus-ring text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink disabled:opacity-60";

  return (
    <div className="mt-2">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <button type="button" disabled={tarBort} onClick={() => void taBort()} className={lank}>
          {tarBort ? text({ sv: "Tar bort…", en: "Deleting…" }) : text({ sv: "Ta bort lista", en: "Delete list" })}
        </button>
        {isPlatformAdmin && lista.status === "klar" ? (
          <button type="button" aria-expanded={kundval} onClick={() => setKundval((v) => !v)} className={lank}>
            {text({ sv: "Kopiera eller flytta till kund", en: "Copy or move to customer" })}
          </button>
        ) : null}
      </div>
      {kundval && isPlatformAdmin ? (
        <div className="mt-3 flex flex-wrap items-end gap-3 rounded-card border border-ink/12 bg-paper2/40 p-3">
          <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-[13px] text-ink-muted">
            {text({ sv: "Till kund", en: "To customer" })}
            <select
              value={vald}
              onChange={(e) => setVald(e.target.value)}
              disabled={kunder === null}
              className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-2 text-[15px] text-ink"
            >
              <option value="">
                {kunder === null ? text({ sv: "Hämtar kunder…", en: "Loading customers…" }) : text({ sv: "Välj kund", en: "Choose customer" })}
              </option>
              {(kunder ?? []).map((k) => (
                <option key={k.slug} value={k.slug}>
                  {k.name} ({k.slug})
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={!vald || skickar !== null}
            onClick={() => void tillKund(false)}
            className={cn(btnSecondary, "disabled:opacity-60")}
          >
            {skickar === "kopiera" ? text({ sv: "Kopierar…", en: "Copying…" }) : text({ sv: "Kopiera till kund", en: "Copy to customer" })}
          </button>
          <button
            type="button"
            disabled={!vald || skickar !== null}
            onClick={() => void tillKund(true)}
            className={cn(btnSecondary, "disabled:opacity-60")}
          >
            {skickar === "flytta" ? text({ sv: "Flyttar…", en: "Moving…" }) : text({ sv: "Flytta till kund", en: "Move to customer" })}
          </button>
        </div>
      ) : null}
      {besked ? (
        <p role={besked.fel ? "alert" : "status"} className={cn("mt-2 text-[14px]", besked.fel ? "text-danger" : "text-moss")}>
          {besked.text}
        </p>
      ) : null}
    </div>
  );
}
