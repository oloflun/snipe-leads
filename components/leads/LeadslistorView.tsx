"use client";

import { Send } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { CrmKundlista } from "@/components/leads/CrmKundlista";
import { ImportCsv } from "@/components/leads/ImportCsv";
import { SaljlistaSektion } from "@/components/leads/Saljlista";
import { btnPrimary, btnSecondary, EmptyState, SkeletonRows, chip, chipAktiv, chipInaktiv, chiplista } from "@/components/ui";
import { offertForUtkast } from "@/lib/leads/offert";
import type { EmailStudioData } from "@/lib/data/emails";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { sv, useLocale, type Locale, type Localized } from "@/lib/i18n";
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
};

type ListRad = {
  /** Radens id i lead_list_items — behövs för Skriv mejl-bron nedan. */
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
  /** Listutkastet (migration 106, app/leads/listutkast.py): generellt
   *  erbjudande, köas när VD:s adress läggs in. `fel` = skrivningen föll. */
  utkast?: {
    subject?: string;
    body?: string;
    fel?: string;
    anmarkning?: string;
    queue_item_id?: string;
  } | null;
};

/** Raden har ett användbart listutkast (skrivet, inte fallet). */
function harListutkast(rad: ListRad): boolean {
  return Boolean(rad.utkast?.body && !rad.utkast.fel);
}

/** Sant från md (768px) och uppåt; null innan fönstret mätts.
 *  Tabellen (md+) och korten (under md) står båda i DOM:en, och mejlrutan
 *  monterades därför två gånger: för en rad med adress startade varje
 *  instans sitt eget utkastjobb (och köningen av listutkast hade köat två).
 *  Rutan monteras nu bara i den layout som syns. */
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

/** En rad under bolagsnamnet: var listutkastet står. Inget utkast, ingen rad. */
function ListutkastStatus({ rad }: Readonly<{ rad: ListRad }>) {
  const { text } = useLocale();
  if (!rad.utkast) return null;
  if (rad.utkast.fel) {
    return (
      <p className="mt-1 text-[13px] text-danger">
        {text({ sv: "Utkastet kunde inte skrivas", en: "The draft could not be written" })}
      </p>
    );
  }
  if (rad.utkast.queue_item_id) {
    return (
      <p className="mt-1 text-[13px] text-ink-muted">
        {text({ sv: "Utkast köat för granskning", en: "Draft queued for review" })}
      </p>
    );
  }
  return (
    <p className="mt-1 text-[13px] text-moss" title={rad.utkast.subject}>
      {text({ sv: "Utkast klart, väntar på VD:s adress", en: "Draft ready, needs the CEO's address" })}
    </p>
  );
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
type Sortering = "kontakt" | "bolag";

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
function synligaRader(items: ListRad[], filter: Kontaktfilter, sortering: Sortering): ListRad[] {
  const ordning: Record<string, number> = { bada: 0, telefon: 1, mejl: 2 };
  const kvar = filter === "alla" ? items : items.filter((rad) => kontaktvag(rad) === filter);
  return [...kvar].sort((a, b) => {
    if (sortering === "kontakt") {
      const d = (ordning[kontaktvag(a) ?? "z"] ?? 3) - (ordning[kontaktvag(b) ?? "z"] ?? 3);
      if (d !== 0) return d;
    }
    return a.company_name.localeCompare(b.company_name, "sv");
  });
}

const T = {
  flyttar: { sv: "Flyttar…", en: "Moving…" },
  foljKorningen: { sv: "Följ körningen", en: "Follow the run" },
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
  laggerBolaget: { sv: "Lägger bolaget i registret…", en: "Adding the company to the register…" },
  kundeInteLaggas: {
    sv: "Bolaget kunde inte läggas i registret.",
    en: "The company could not be added to the register."
  },
  spararAdressen: { sv: "Sparar adressen på bolaget…", en: "Saving the address on the company…" },
  serEfterUtkast: { sv: "Ser efter om ett utkast redan finns…", en: "Checking if a draft already exists…" },
  agentenSkriverUtkastet: { sv: "Agenten skriver utkastet…", en: "The agent is writing the draft…" },
  utkastKundeInte: { sv: "Utkastet kunde inte skrivas.", en: "The draft could not be written." },
  utkastTogForLang: {
    sv: "Utkastet tog för lång tid. Titta i granskningskön innan du försöker igen.",
    en: "The draft took too long. Check the review queue before you try again."
  },
  utkastInteKlart: { sv: "Utkastet blev inte klart.", en: "The draft was not finished." },
  nyaIRegistret: { sv: "nya i registret", en: "new in the register" },
  fannsRedan: { sv: "fanns redan", en: "already existed" },
  gickInteLaggaIn: { sv: "gick inte att lägga in", en: "could not be added" },
  ingaRaderAttLaggaIn: { sv: "Inga rader att lägga in.", en: "No rows to add." },
  stoppat: { sv: "Stoppat", en: "Stopped" },
  nyttUtkast: { sv: "nytt utkast", en: "new draft" },
  nyaUtkast: { sv: "nya utkast", en: "new drafts" },
  hadeRedanUtkast: { sv: "hade redan ett utkast", en: "already had a draft" },
  gickInteSkriva: { sv: "gick inte att skriva", en: "could not be written" },
  ingaUtkastSkrevs: { sv: "Inga utkast skrevs.", en: "No drafts were written." },
  listanTom: { sv: "Listan är tom.", en: "The list is empty." },
  stangMejlet: { sv: "Stäng mejlet", en: "Close email" },
  skrivMejl: { sv: "Skriv mejl", en: "Write email" },
  allaGenomgangna: { sv: "Alla med adress är genomgångna", en: "All rows with an address are done" },
  skrivUtkastTillAlla: { sv: "Skriv utkast till alla med mejladress", en: "Write drafts for all with an email address" },
  laggerIn: { sv: "Lägger in…", en: "Adding…" },
  laggAllaIRegistret: { sv: "Lägg alla i registret", en: "Add all to register" },
  laddaNerCsv: { sv: "Ladda ner CSV", en: "Download CSV" },
  bekraftaUtkast: { sv: "Bekräfta utkast till hela listan", en: "Confirm drafts for the whole list" },
  agentenSkriver: { sv: "Agenten skriver", en: "The agent writes" },
  ettPerBolag: { sv: ", ett per bolag med mejladress.", en: ", one per company with an email address." },
  raknasMotBudget: { sv: "Varje utkast räknas mot er leadsbudget.", en: "Each draft counts against your leads budget." },
  avbryt: { sv: "Avbryt", en: "Cancel" },
  stopparEfter: { sv: "Stoppar efter det här utkastet…", en: "Stopping after this draft…" },
  stoppaEfter: { sv: "Stoppa efter det här utkastet", en: "Stop after this draft" },
  svepetStoppades: { sv: "Svepet stoppades", en: "The batch stopped" },
  kalla: { sv: "Källa", en: "Source" },
  helMejladress: { sv: "Skriv en hel mejladress.", en: "Enter a full email address." },
  radenSaknarAdress: { sv: "Raden saknar mejladress.", en: "This row has no email address." },
  mejladress: { sv: "Mejladress", en: "Email address" },
  mejladressExempel: { sv: "namn@bolaget.se", en: "name@company.com" },
  sparaOchSkriv: { sv: "Spara adressen och skriv utkast", en: "Save the address and write a draft" },
  andraAdressen: { sv: "Ändra adressen", en: "Change the address" },
  andringarSparasInte: {
    sv: "Ändringar ovan sparas inte. Godkänn skickar det sparade utkastet.",
    en: "Changes above are not saved. Approve sends the saved draft."
  },
  godkant: { sv: "Godkänt. Mejlet ligger nu i sändkön.", en: "Approved. The email is now in the send queue." },
  godkanner: { sv: "Godkänner…", en: "Approving…" },
  godkannOchSkicka: { sv: "Godkänn och skicka", en: "Approve and send" },
  godkannIGranskning: { sv: "Godkänn under Att göra.", en: "Approve under To do." },
  filnamn: { sv: "leadslista", en: "lead-list" }
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
 * Felet bär statuskoden. Snabbmailens svep måste skilja "den här raden gick
 * inte" från "budgeten/AI-kapaciteten är slut" — det senare ska stoppa hela
 * svepet direkt, inte ge 24 likadana fel till.
 */
class AnropsFel extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
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
    throw new AnropsFel(detaljtext ?? k.error ?? avvisat[sprak()], response.status);
  }
  return kropp;
}

/** Kontaktvägen som EN sträng: namn/roll om de finns, annars adressen. */
function kontakt(rad: ListRad): string {
  const namnRoll = [rad.contact_name, rad.contact_role].filter(Boolean).join(", ");
  return namnRoll || rad.contact_email || "—";
}

function signaltext(rad: ListRad): string {
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
  crmOppen = false
}: Readonly<{ demo?: boolean; crmOppen?: boolean }> = {}) {
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

  /** Hämtar den öppna listans rader igen utan att fälla ihop den — när
   *  listutkasten skrivs i bakgrunden dyker de upp rad för rad. */
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
                    <Listtabell lista={vald.lista} items={vald.items} onUppdatera={() => uppdatera(vald.lista.id)} />
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

/**
 * Hur många utkast ETT klick på "Skriv utkast till alla med mejladress" får
 * starta. Varje utkast är ett riktigt LLM-jobb mot leadsbudgeten; en lista på
 * 200 bolag ska inte kunna tömma budgeten i ett enda klick som ingen hann
 * ångra. Nästa klick tar nästa omgång.
 */
const SVEP_TAK = 25;

/**
 * Leverantörens och backendens formuleringar för slut kapacitet. Speglar
 * `_KREDITMARKORER` och kundtexterna i snajp-support/app/kvotfel.py — en
 * misslyckad utkastjobbstext bär bara meningen, inte statuskoden, så svepet
 * måste känna igen texten för att veta att det ska sluta.
 */
const KAPACITETSMARKORER = [
  "prepayment credits",
  "credits are depleted",
  "billing#prepay",
  // Backendens svenska meningar, matchade ordagrant: data, inte copy, och
  // översätts aldrig. Markören inte-copy håller INV-COPY-001 borta från raderna.
  "ai-kapaciteten är slut", // inte-copy
  "kvot är slut", // inte-copy
  "kvoten är slut" // inte-copy
];

/** Saknad erbjudandetext gäller varje rad lika — därför stoppar den svepet. */
const OFFERT_SAKNAS: Localized = {
  sv: "Fyll i ”Vad ni säljer” under Inställningar först.",
  en: "Fill in What you sell under Settings first."
};

/** Ska svepet stanna helt? 429 = budgettak, 503 = ingen skarp LLM, eller en
 *  kredit-/kvottext ur ett misslyckat jobb. Allt annat gäller bara raden. */
function stopparSvepet(fel: unknown): boolean {
  if (fel instanceof AnropsFel && (fel.status === 429 || fel.status === 503)) return true;
  if (fel instanceof Error && (fel.message === OFFERT_SAKNAS.sv || fel.message === OFFERT_SAKNAS.en)) return true;
  const text = (fel instanceof Error ? fel.message : String(fel)).toLocaleLowerCase("sv");
  return KAPACITETSMARKORER.some((markor) => text.includes(markor));
}

type Utkast = {
  prospectId: string;
  subject: string | null | undefined;
  body: string;
  queueItemId: string | null;
  offert: string | null;
  /** Ett utkast fanns redan för bolaget — inget nytt jobb startades. */
  fanns: boolean;
};

/**
 * Utkastkedjan för EN listrad. Delas av mejlrutan och snabbmailens svep, så
 * att de två aldrig kan skriva utkast på olika sätt.
 *
 * (1) Raden lyfts in i prospektregistret — LLM-fritt och idempotent, en
 * befintlig rad återanvänds. (2) Saknade raden adress sparas den som
 * användaren angav på prospektet. (3) Finns ett utkast redan visas det i
 * stället för att ett nytt skrivs. (4) Annars skrivs utkastet av samma kedja
 * som bolagssidans (/leads/outreach/draft) och pollas tills jobbet är klart.
 *
 * `adress` krävs. Backenden bygger avregistreringsfoten som lagen kräver ur
 * mottagaradressen NÄR UTKASTET KÖAS (leads_tools._med_lagstadgad_fot) — ett
 * utkast utan adress hade legat i kön utan fot och blivit oskickbart på
 * lagligt vis även sedan en adress lagts till.
 */
async function skrivUtkastForRad(
  lista: Lista,
  rad: ListRad,
  adress: string,
  locale: Locale,
  steg: (text: Localized) => void = () => {}
): Promise<Utkast> {
  // Listutkastet (generellt erbjudande, redan skrivet) köas direkt till
  // adressen: befordran, adress, signatur och fot sköts av backenden i ett
  // anrop. Ingen ny skrivning, ingen research (regel 8).
  if (harListutkast(rad)) {
    steg(T.laggerBolaget);
    const koat = await anropa<{
      prospect_id: string;
      queue_item_id: string;
      subject?: string | null;
      body?: string | null;
    }>(`/leads/listor/${encodeURIComponent(lista.id)}/items/${encodeURIComponent(rad.id)}/koa`, {
      method: "POST",
      body: JSON.stringify({ email: adress })
    });
    return {
      prospectId: koat.prospect_id,
      subject: koat.subject ?? rad.utkast?.subject,
      body: koat.body ?? rad.utkast?.body ?? "",
      queueItemId: koat.queue_item_id,
      offert: null,
      fanns: false
    };
  }

  steg(T.laggerBolaget);
  const befordran = await anropa<{ prospect?: { id: string } }>(
    `/leads/listor/${encodeURIComponent(lista.id)}/items/${encodeURIComponent(rad.id)}/prospekt`,
    { method: "POST" }
  );
  const prospectId = befordran.prospect?.id;
  if (!prospectId) throw new Error(T.kundeInteLaggas[locale]);

  if (!rad.contact_email) {
    // Adressen hör hemma på prospektet, inte bara i det här anropet: tråden
    // och sändkön läser mottagaren ur prospects.contact_email.
    steg(T.spararAdressen);
    await anropa(`/leads/prospects/${encodeURIComponent(prospectId)}`, {
      method: "PATCH",
      body: JSON.stringify({ contact_email: adress })
    });
  }

  // Finns ett utkast redan (rutan öppnad förut, eller en körning har hunnit
  // skriva ett)? Då används det — ett andra utkastjobb för samma bolag är
  // dubbel kostnad för samma fråga.
  steg(T.serEfterUtkast);
  try {
    const befintligt = await anropa<{
      utkast?: { subject?: string | null; body?: string | null } | null;
      queue_item_id?: string | null;
    }>(`/leads/prospects/${encodeURIComponent(prospectId)}/utkast`);
    if (befintligt.utkast?.body) {
      return {
        prospectId,
        subject: befintligt.utkast.subject,
        body: befintligt.utkast.body,
        queueItemId: befintligt.queue_item_id ?? null,
        offert: null,
        fanns: true
      };
    }
  } catch {
    // Ett fel här ska inte hindra ett nytt utkast från att skrivas.
  }

  steg(T.agentenSkriverUtkastet);
  // Utan erbjudandetext svarar /leads/outreach/draft 422 (offer_summary har
  // min_length=1) — att skicka `undefined` gav bara ett obegripligare fel ett
  // steg senare. Felet skrivs om här i stället för att föras vidare: en server
  // action maskerar sitt meddelande i produktionsbygget, och de två sätt den
  // kan kasta på (utloggad, tom affärskontext) har samma åtgärd för kunden.
  let offert: string;
  try {
    offert = await offertForUtkast();
  } catch {
    throw new Error(OFFERT_SAKNAS[locale]);
  }

  type Utkastsvar = {
    job_id?: string;
    fase?: string;
    subject?: string;
    body?: string;
    escalated?: boolean;
    escalation_reason?: string | null;
    queue_item_id?: string | null;
  };
  const koat = await anropa<Utkastsvar>("/leads/outreach/draft", {
    method: "POST",
    body: JSON.stringify({
      prospect_id: prospectId,
      prospect_email: adress,
      company_name: rad.company_name,
      offer_summary: offert ?? undefined,
      // Agentens instruktion och underlag, inte copy: alltid svenska, så att
      // mejlet till det svenska bolaget blir svenskt oavsett gränssnittets språk.
      brief: sv({
        sv: `Skriv ett kort, personligt första mejl till kontaktvägen på ${rad.company_name}. Utgå från signalen i underlaget och håll dig till det som är känt. Ingen hype, inga superlativ, ren text. Utkastet ska köas för granskning, inte skickas.`,
        en: `Write a short, personal first email to the contact channel at ${rad.company_name}. Start from the signal in the research and stick to what is known. No hype, no superlatives, plain text. The draft is queued for review, not sent.`
      }),
      research_summary: [
        rad.ort ? `Ort: ${rad.ort}` : null,
        rad.signal ? `Signal: ${signaltext(rad)}` : null,
        rad.source_name ? sv({ sv: `Källa: ${rad.source_name}`, en: `Source: ${rad.source_name}` }) : null,
        rad.contact_name || rad.contact_role
          ? `Kontakt: ${[rad.contact_name, rad.contact_role].filter(Boolean).join(", ")}`
          : null,
        rad.orgnr ? `Org.nr: ${rad.orgnr}` : null
      ]
        .filter(Boolean)
        .join("\n"),
      research_evidence: rad.source_url ? [rad.source_url] : []
    })
  });

  let svar: Utkastsvar = koat;
  if (koat.job_id && (koat.fase === "skriver" || !koat.body)) {
    let klart = false;
    for (let forsok = 0; forsok < 90; forsok += 1) {
      await new Promise((r) => setTimeout(r, forsok < 5 ? 800 : 2000));
      const jobb = await anropa<{ status?: string; error?: string; result?: Utkastsvar }>(
        `/leads/jobb/${encodeURIComponent(koat.job_id)}`
      );
      if (jobb.status === "completed" && jobb.result) {
        svar = jobb.result;
        klart = true;
        break;
      }
      if (jobb.status === "failed") {
        throw new Error(jobb.error || T.utkastKundeInte[locale]);
      }
    }
    // Utan den här raden föll en utgången väntan igenom till eskalerings-
    // texten nedan, och "agenten lämnade över till en människa" är inte vad
    // som hände — jobbet kan fortfarande bli klart.
    if (!klart) {
      throw new Error(T.utkastTogForLang[locale]);
    }
  }

  if (svar.escalated || !svar.body) {
    throw new Error(svar.escalation_reason || T.utkastInteKlart[locale]);
  }

  return {
    prospectId,
    subject: svar.subject,
    body: svar.body,
    queueItemId: svar.queue_item_id ?? null,
    offert,
    fanns: false
  };
}

type Svep =
  | { fas: "bekraftar" }
  | { fas: "kor"; klara: number; totalt: number; bolag: string };

/**
 * Raderna i EN klar lista. Samma form som Bolagsregistret: tabell från md och
 * upp, kort under — sex kolumner krympta till 375px blir oläsliga.
 */
function Listtabell({
  lista,
  items,
  onUppdatera
}: Readonly<{ lista: Lista; items: ListRad[]; onUppdatera: () => Promise<void> }>) {
  // I demon finns ingen riktig utkastkedja att köra mot — mejlrutan döljs,
  // CSV:n står kvar.
  const { isDemo, vy } = useDashboard();
  const { locale, text } = useLocale();
  // En CRM-kundlista (migration 098) är kundens befintliga kunder: den är en
  // uteslutningsmängd och prospekteras inte — ingen flytt till Iris, inga utkast.
  const mejlbro = !isDemo && vy !== "demo" && lista.kalla !== "crm";

  // Skriv mejl: rutan med Email studio öppnas UNDER raden. Ett öppet rad-id i
  // taget: två samtidiga utkastjobb från samma lista är dubbel kostnad för
  // samma klick.
  const [oppenRad, setOppenRad] = useState<string | null>(null);
  const [laggerAlla, setLaggerAlla] = useState(false);
  const [allaResultat, setAllaResultat] = useState<Localized | null>(null);
  const [radFel, setRadFel] = useState<string | null>(null);
  const bred = useBredSkarm();

  // Listutkast (Sebbe 2026-10-07): ett utkast med det generella erbjudandet
  // per bolag, skrivet i bakgrunden. Listan hämtas om var fjärde sekund tills
  // varje rad som saknade utkast har fått ett (eller ett fel).
  const utanUtkast = items.filter((rad) => !harListutkast(rad));
  const medUtkast = items.length - utanUtkast.length;
  const [skriverUtkast, setSkriverUtkast] = useState(false);
  const [utkastBesked, setUtkastBesked] = useState<Localized | null>(null);
  const [utkastFel, setUtkastFel] = useState<string | null>(null);
  const pollUtkast = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (pollUtkast.current) clearTimeout(pollUtkast.current);
    },
    []
  );
  // Polling slutar när ingen rad väntar längre (utkast eller fel på alla).
  const vantarPaUtkast = items.some((rad) => !rad.utkast);
  useEffect(() => {
    if (!skriverUtkast) return;
    if (!vantarPaUtkast) {
      setSkriverUtkast(false);
      return;
    }
    let forsok = 0;
    const tick = () => {
      forsok += 1;
      void onUppdatera().finally(() => {
        if (forsok < 90) pollUtkast.current = setTimeout(tick, 4000);
        else setSkriverUtkast(false);
      });
    };
    pollUtkast.current = setTimeout(tick, 4000);
    return () => {
      if (pollUtkast.current) clearTimeout(pollUtkast.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skriverUtkast, vantarPaUtkast]);

  async function skrivAllaListutkast() {
    setUtkastFel(null);
    setUtkastBesked(null);
    try {
      const svar = await anropa<{ count?: number }>(`/leads/listor/${encodeURIComponent(lista.id)}/utkast`, {
        method: "POST"
      });
      const antal = svar.count ?? 0;
      setUtkastBesked(
        antal
          ? {
              sv: `Iris skriver ${antal} utkast med ert generella erbjudande. De dyker upp på raderna allteftersom.`,
              en: `Iris is writing ${antal} drafts with your general offer. They appear on the rows as they finish.`
            }
          : { sv: "Alla bolag i listan har redan ett utkast.", en: "Every company in the list already has a draft." }
      );
      if (antal) {
        await onUppdatera();
        setSkriverUtkast(true);
      }
    } catch (orsak) {
      setUtkastFel(felmeddelande(orsak));
    }
  }

  // Snabbmail: utkast till alla rader med adress, i omgångar om SVEP_TAK.
  // `hanterade` minns vilka rader svepet redan tagit (lyckade som felade), så
  // att nästa klick tar NÄSTA omgång i stället för att köra om de första 25.
  const [svep, setSvep] = useState<Svep | null>(null);
  const [svepResultat, setSvepResultat] = useState<Localized | null>(null);
  const [svepStopp, setSvepStopp] = useState<string | null>(null);
  const [hanterade, setHanterade] = useState<Set<string>>(new Set());
  const avbryt = useRef(false);
  const korRef = useRef(false);
  const [stopparBegart, setStopparBegart] = useState(false);
  // Stängs listan mitt i svepet ska loopen inte fortsätta beställa jobb åt en
  // vy ingen längre tittar på — det pågående utkastet blir klart, inget mer.
  useEffect(
    () => () => {
      avbryt.current = true;
    },
    []
  );

  const medAdress = items.filter((rad) => rad.contact_email);
  const kandidater = medAdress.filter((rad) => !hanterade.has(rad.id));
  // Flytta till Iris (2026-10-02): raderna blir prospekt och en riktig körning
  // köas med research per bolag. Ersätter svepet "utkast till alla med
  // mejladress", som skrev utkast ur radens metadata utan research.
  const pathname = usePathname() ?? "/dashboard/leads";
  // Ytans rot (/dashboard eller /admin): körningen följs i Leads › Körningar.
  const bas = pathname.replace(/\/(leads|iris)(\/.*)?$/, "");
  const [flyttar, setFlyttar] = useState(false);
  const [flyttKvitto, setFlyttKvitto] = useState<{ batchId: string; antal: number; nya: number } | null>(null);
  const [flyttFel, setFlyttFel] = useState<string | null>(null);
  const [kontaktfilter, setKontaktfilter] = useState<Kontaktfilter>("alla");
  const [sortering, setSortering] = useState<Sortering>("kontakt");
  const visade = synligaRader(items, kontaktfilter, sortering);
  const antalPer = (f: Kontaktfilter) => (f === "alla" ? items.length : items.filter((rad) => kontaktvag(rad) === f).length);
  const omgang = kandidater.slice(0, SVEP_TAK);
  const svepKor = svep?.fas === "kor";

  // Processa om (Antons beställning 2026-10-08): registret och sajten hämtas
  // på nytt och den nya kontaktsökningen körs i bakgrunden. Mejl, telefon och
  // kontaktperson skrivs på raderna; inget flyttas. Sedan Flytta till Iris
  // eller Skriv utkast till alla med mejladress.
  const [provar, setProvar] = useState(false);
  const [provBesked, setProvBesked] = useState<number | null>(null);
  async function provaMotIris() {
    setProvar(true);
    setFlyttFel(null);
    setProvBesked(null);
    try {
      const ut = await anropa<{ rader: number }>(`/leads/listor/${encodeURIComponent(lista.id)}/omprova`, {
        method: "POST",
        // De rader som syns, som Flytta till Iris: filtret avgör vad som processas.
        body: JSON.stringify({ item_ids: kontaktfilter === "alla" ? null : visade.map((rad) => rad.id) })
      });
      setProvBesked(ut.rader);
    } catch (cause) {
      setFlyttFel(felmeddelande(cause));
    } finally {
      setProvar(false);
    }
  }

  async function flyttaTillIris() {
    setFlyttar(true);
    setFlyttFel(null);
    setFlyttKvitto(null);
    try {
      const ut = await anropa<{ batch_id: string; prospekt: number; nya: number }>(
        `/leads/listor/${encodeURIComponent(lista.id)}/till-iris`,
        {
          method: "POST",
          body: JSON.stringify({
            // En väg (Antons beställning 2026-10-08): research och utkast.
            scope: "research_and_draft",
            // De rader som syns: filtret på kontaktväg avgör vad som flyttas.
            item_ids: kontaktfilter === "alla" ? null : visade.map((rad) => rad.id)
          })
        }
      );
      setFlyttKvitto({ batchId: ut.batch_id, antal: ut.prospekt, nya: ut.nya });
      window.dispatchEvent(new Event("snipra:leads-korning-steg"));
    } catch (cause) {
      setFlyttFel(felmeddelande(cause));
    } finally {
      setFlyttar(false);
    }
  }

  const laggAllaIRegistret = useCallback(async () => {
    setLaggerAlla(true);
    setRadFel(null);
    setAllaResultat(null);
    let nya = 0;
    let fanns = 0;
    let fel = 0;
    // Sekventiellt med flit: befordran är billig, och en parallell skur mot
    // dedupe-kontrollen hade kunnat skapa just de dubbletter den finns för
    // att stoppa.
    for (const rad of items) {
      try {
        const svar = await anropa<{ skapad?: boolean }>(
          `/leads/listor/${encodeURIComponent(lista.id)}/items/${encodeURIComponent(rad.id)}/prospekt`,
          { method: "POST" }
        );
        if (svar.skapad) nya += 1;
        else fanns += 1;
      } catch {
        fel += 1;
      }
    }
    const resultat = (l: Locale) =>
      [
        nya ? `${nya} ${T.nyaIRegistret[l]}` : null,
        fanns ? `${fanns} ${T.fannsRedan[l]}` : null,
        fel ? `${fel} ${T.gickInteLaggaIn[l]}` : null
      ]
        .filter(Boolean)
        .join(" · ") || T.ingaRaderAttLaggaIn[l];
    setAllaResultat({ sv: resultat("sv"), en: resultat("en") });
    setLaggerAlla(false);
  }, [items, lista.id]);

  const skrivAllaUtkast = useCallback(async () => {
    const rader = omgang;
    // Ref och inte state: ett dubbelklick på bekräftelsen hinner avfyras två
    // gånger innan dialogen renderats bort, och två svep hade dubblat jobben.
    if (!rader.length || korRef.current) return;
    korRef.current = true;
    setStopparBegart(false);
    // Mejlrutan stängs: den och svepet hade annars kunnat starta två jobb för
    // samma bolag samtidigt.
    setOppenRad(null);
    setSvepResultat(null);
    setSvepStopp(null);
    avbryt.current = false;

    let nya = 0;
    let fanns = 0;
    let fel = 0;
    let klara = 0;
    const tagna = new Set(hanterade);

    // Sekventiellt, inte parallellt: budgetgrinden räknar per jobb, och 25
    // samtidiga jobb hade passerat grinden innan det första hunnit räknas.
    for (const rad of rader) {
      if (avbryt.current) break;
      setSvep({ fas: "kor", klara, totalt: rader.length, bolag: rad.company_name });
      try {
        const utkast = await skrivUtkastForRad(lista, rad, rad.contact_email as string, locale);
        if (utkast.fanns) fanns += 1;
        else nya += 1;
        tagna.add(rad.id);
      } catch (orsak) {
        if (stopparSvepet(orsak)) {
          // Backendens egen mening visas, inte en omskrivning: den säger om
          // det är budgettaket eller kapaciteten, och vad som gäller härnäst.
          // Raden räknas INTE som hanterad — den ska med i nästa försök.
          setSvepStopp(felmeddelande(orsak));
          break;
        }
        fel += 1;
        tagna.add(rad.id);
      }
      klara += 1;
      setHanterade(new Set(tagna));
    }

    korRef.current = false;
    const stoppadAvDig = avbryt.current;
    setStopparBegart(false);
    setSvep(null);
    const resultat = (l: Locale) =>
      [
        stoppadAvDig ? T.stoppat[l] : null,
        nya ? `${nya} ${nya === 1 ? T.nyttUtkast[l] : T.nyaUtkast[l]}` : null,
        fanns ? `${fanns} ${T.hadeRedanUtkast[l]}` : null,
        fel ? `${fel} ${T.gickInteSkriva[l]}` : null
      ]
        .filter(Boolean)
        .join(" · ") || T.ingaUtkastSkrevs[l];
    setSvepResultat({ sv: resultat("sv"), en: resultat("en") });
  }, [hanterade, lista, omgang, locale]);

  if (!items.length) {
    return (
      <p className="mt-4 border-t border-ink/10 pt-4 text-[15px] text-ink-muted">
        {text(T.listanTom)}
      </p>
    );
  }

  function skrivMejlKnapp(rad: ListRad, extra?: string) {
    return (
      <button
        type="button"
        onClick={() => setOppenRad(oppenRad === rad.id ? null : rad.id)}
        aria-expanded={oppenRad === rad.id}
        disabled={svepKor}
        className={cn(btnSecondary, "whitespace-nowrap disabled:opacity-60", extra)}
      >
        {oppenRad === rad.id ? text(T.stangMejlet) : text(T.skrivMejl)}
      </button>
    );
  }

  return (
    <div className="mt-4 rounded-card border border-ink/10 bg-paper p-4 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <p className="text-[13px] text-ink-subtle">
          {text({
            sv: `${items.length} bolag i listan · ${antalPer("telefon") + antalPer("bada")} med telefon · ${medAdress.length} med mejladress`,
            en: `${items.length} companies in the list · ${antalPer("telefon") + antalPer("bada")} with a phone number · ${medAdress.length} with an email address`
          })}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {/* Flytta till Iris: prospekt + riktig körning med research per bolag.
              Svepet "utkast till alla med mejladress" och "Lägg alla i registret"
              ersattes 2026-10-02: utkast ska utgå från bolagets läge, inte en
              mall ur radens metadata. (ponytail: svepets kod står kvar
              oanropad tills /simplify tar den.) */}
          {mejlbro && utanUtkast.length > 0 ? (
            <button
              type="button"
              onClick={() => void skrivAllaListutkast()}
              disabled={skriverUtkast}
              className={cn(btnPrimary, "disabled:opacity-60")}
            >
              {skriverUtkast
                ? text({
                    sv: `Skriver utkast, ${medUtkast} av ${items.length} klara`,
                    en: `Writing drafts, ${medUtkast} of ${items.length} done`
                  })
                : text({
                    sv: `Skriv utkast till ${utanUtkast.length} bolag`,
                    en: `Write drafts for ${utanUtkast.length} companies`
                  })}
            </button>
          ) : null}
          {mejlbro ? (
            <>
              <button
                type="button"
                onClick={() => void flyttaTillIris()}
                disabled={flyttar || visade.length === 0}
                className={cn(btnPrimary, "disabled:opacity-60")}
              >
                {flyttar
                  ? text(T.flyttar)
                  : text({ sv: `Flytta ${visade.length} till Iris`, en: `Move ${visade.length} to Iris` })}
              </button>
              <button
                type="button"
                onClick={() => void provaMotIris()}
                disabled={provar || items.length === 0}
                className={cn(btnSecondary, "disabled:opacity-60")}
              >
                {provar ? text({ sv: "Startar…", en: "Starting…" }) : text({ sv: "Processa om", en: "Reprocess" })}
              </button>
            </>
          ) : null}
          {/* CSV:n byggs helt på klientsidan av raderna som redan är hämtade —
              ingen ny endpoint, och det som laddas ner är exakt det som syns. */}
          <button
            type="button"
            onClick={() => laddaNerCsv(lista.titel, items, locale)}
            className={cn(btnSecondary)}
          >
            {text(T.laddaNerCsv)}
          </button>
        </div>
      </div>

      {flyttFel ? (
        <p role="alert" className="mt-3 text-[15px] text-danger">
          {flyttFel}
        </p>
      ) : null}
      <div aria-live="polite">
        {utkastBesked ? <p className="mt-3 max-w-[70ch] text-[15px] text-moss">{text(utkastBesked)}</p> : null}
        {utkastFel ? (
          <p role="alert" className="mt-3 max-w-[70ch] text-[15px] text-danger">
            {utkastFel}
          </p>
        ) : null}
        {medUtkast > 0 && mejlbro ? (
          <p className="mt-3 max-w-[70ch] text-[14px] leading-6 text-ink-muted">
            {text({
              sv: "Öppna Skriv mejl på en rad och lägg in VD:s mejladress, så köas utkastet med signatur och syns under Utkast att godkänna.",
              en: "Open Write email on a row and add the CEO's email address; the draft is queued with your signature and shows under Drafts to approve."
            })}
          </p>
        ) : null}
      </div>
      {provBesked !== null ? (
        <p role="status" className="mt-3 max-w-[70ch] text-[15px] text-moss">
          {text({
            sv: `${provBesked} bolag processas om i bakgrunden: registret och webbplatsen läses på nytt, och mejl, telefon och kontaktperson fylls i på raderna. Ladda om om en stund, och flytta sedan till Iris eller skriv utkast till dem med mejladress.`,
            en: `${provBesked} companies are being reprocessed in the background: the register and website are read again, and email, phone and contact are filled in on the rows. Reload in a while, then move them to Iris or write drafts for those with an email address.`
          })}
        </p>
      ) : null}
      {flyttKvitto ? (
        <p role="status" className="mt-3 text-[15px] text-moss">
          {text({
            sv: `${flyttKvitto.antal} bolag i Iris (${flyttKvitto.nya} nya). Research pågår per bolag.`,
            en: `${flyttKvitto.antal} companies in Iris (${flyttKvitto.nya} new). Research is running per company.`
          })}{" "}
          <Link href={`${bas}/leads?vy=korningar&id=${encodeURIComponent(flyttKvitto.batchId)}`} className="underline underline-offset-4 hover:text-ink">
            {text(T.foljKorningen)}
          </Link>
        </p>
      ) : null}

      {svep?.fas === "bekraftar" ? (
        <div
          role="alertdialog"
          aria-label={text(T.bekraftaUtkast)}
          className="mt-4 rounded-card border border-warning/40 bg-warning/10 p-4"
        >
          <p className="max-w-[70ch] text-[0.875rem] leading-6 text-ink">
            {text(T.agentenSkriver)}{" "}
            <strong className="font-semibold">
              {text({
                sv: `${omgang.length} utkast`,
                en: `${omgang.length} ${omgang.length === 1 ? "draft" : "drafts"}`
              })}
            </strong>
            {kandidater.length > omgang.length
              ? text({ sv: ` av ${kandidater.length} med adress.`, en: ` of ${kandidater.length} with an address.` })
              : text(T.ettPerBolag)}{" "}
            {text(T.raknasMotBudget)}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void skrivAllaUtkast()}
              // Bekräftelsen dyker upp på knapptryck; fokus följer med så att
              // tangentbordet landar på beslutet i stället för bakom det.
              autoFocus
              className="focus-ring rounded-input bg-ink px-4 py-2 text-[0.8125rem] font-semibold text-paper hover:bg-ink2"
            >
              {text({
                sv: `Skriv ${omgang.length} utkast`,
                en: `Write ${omgang.length} ${omgang.length === 1 ? "draft" : "drafts"}`
              })}
            </button>
            <button
              type="button"
              onClick={() => setSvep(null)}
              className="focus-ring rounded-input bg-paper2 px-4 py-2 text-[0.8125rem] text-ink hover:bg-paper2/70"
            >
              {text(T.avbryt)}
            </button>
          </div>
        </div>
      ) : null}

      {svep?.fas === "kor" ? (
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
          <p role="status" className="text-[13px] text-ink-muted">
            {text({
              sv: `Skriver utkast ${svep.klara + 1} av ${svep.totalt}: ${svep.bolag}`,
              en: `Writing draft ${svep.klara + 1} of ${svep.totalt}: ${svep.bolag}`
            })}
          </p>
          <button
            type="button"
            onClick={() => {
              avbryt.current = true;
              setStopparBegart(true);
            }}
            disabled={stopparBegart}
            className="focus-ring text-[13px] underline underline-offset-4 hover:text-ochre disabled:text-ink-subtle disabled:no-underline"
          >
            {stopparBegart ? text(T.stopparEfter) : text(T.stoppaEfter)}
          </button>
        </div>
      ) : null}
      {svepStopp ? (
        <p role="alert" className="mt-3 max-w-[70ch] break-words text-[14px] text-danger">
          {text(T.svepetStoppades)}: {svepStopp}
        </p>
      ) : null}
      {svepResultat ? (
        <p className="mt-3 text-[13px] text-ink-subtle">{text(svepResultat)}</p>
      ) : null}

      {allaResultat ? (
        <p className="mt-3 text-[13px] text-ink-subtle">{text(allaResultat)}</p>
      ) : null}
      {radFel ? (
        <p role="alert" className="mt-3 max-w-[70ch] break-words text-[14px] text-danger">
          {radFel}
        </p>
      ) : null}

      {/* Fast layout (table-fixed + colgroup): bredderna deklareras i procent
          och summerar till 100 — se Tabell i components/ui.tsx. Knappkolumnen
          finns bara när mejlbron är på, så colgroup och expanderradens colSpan
          måste följa samma villkor som cellerna. */}
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
            <option value="kontakt">{text({ sv: "Kontaktväg", en: "Contact channel" })}</option>
            <option value="bolag">{text({ sv: "Bolag A–Ö", en: "Company A–Z" })}</option>
          </select>
        </label>
      </div>

      <div className="mt-4 hidden overflow-x-auto border-y border-ink/15 md:block">
        <table className="w-full min-w-[960px] table-fixed border-collapse text-[15px]">
          <colgroup>
            <col style={{ width: "22%" }} />
            <col style={{ width: "10%" }} />
            <col style={{ width: "18%" }} />
            <col style={{ width: "12%" }} />
            <col style={{ width: "24%" }} />
            <col style={{ width: "14%" }} />
            {mejlbro ? <col style={{ width: "130px" }} /> : null}
          </colgroup>
          <thead>
            <tr className="border-b border-ink/15 text-left">
              {[...TABELLRUBRIKER.map((rubrik) => text(rubrik)), ...(mejlbro ? [""] : [])].map(
                (rubrik, i, alla) => (
                  <th
                    key={rubrik}
                    scope="col"
                    className={cn(
                      "kicker py-4 font-medium text-mineral",
                      i < alla.length - 1 ? "pr-6" : ""
                    )}
                  >
                    {rubrik}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink/15">
            {visade.map((rad, index) => [
              <tr key={`${rad.company_name}-${index}`} className="transition hover:bg-paper2/60">
                <th scope="row" className="py-4 pr-6 text-left font-normal">
                  <p className="text-[15px] font-semibold tracking-[-0.01em]">
                    {rad.company_name}
                  </p>
                  {rad.website ? (
                    <p className="mt-1 break-all text-sm text-ink-subtle">{rad.website}</p>
                  ) : null}
                  <ListutkastStatus rad={rad} />
                </th>
                <td className="kicker py-4 pr-6 text-mineral">{rad.ort ?? "—"}</td>
                <td className="py-4 pr-6">
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
                <td className="py-4 pr-6 text-[14px] text-ink-muted">{kontaktniva(rad, locale) ?? "—"}</td>
                <td className="py-4 pr-6 text-[15px] leading-6 text-ink-muted">{signaltext(rad)}</td>
                <td className="py-4 pr-6">
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
                {/* Knappen står på VARJE rad. Förut syntes den bara där en
                    adress fanns, och i en lista utan adresser fanns ingen
                    väg till Email studio alls. Saknas adressen frågar rutan
                    efter den i stället. */}
                {mejlbro ? <td className="py-4 text-right">{skrivMejlKnapp(rad)}</td> : null}
              </tr>,
              bred === true && oppenRad === rad.id ? (
                <tr key={`${rad.id}-mejl`}>
                  {/* Samma villkor som colgroup och huvudet: sex kolumner utan
                      mejlbro, sju med. */}
                  <td colSpan={mejlbro ? 7 : 6} className="pb-6 pt-1">
                    <MejlRuta lista={lista} rad={rad} onKoat={() => void onUppdatera()} />
                  </td>
                </tr>
              ) : null
            ])}
          </tbody>
        </table>
      </div>

      <ul className="mt-4 space-y-2 md:hidden">
        {visade.map((rad, index) => (
          <li
            key={`${rad.company_name}-${index}`}
            className="rounded-input border border-ink/15 px-4 py-3"
          >
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 text-[15px] font-semibold tracking-[-0.01em]">
                {rad.company_name}
              </span>
              {kontaktniva(rad, locale) ? (
                <span className="shrink-0 text-[12px] text-ink-subtle">{kontaktniva(rad, locale)}</span>
              ) : null}
            </div>
            <p className="kicker mt-1 text-mineral">
              {[rad.ort, rad.website].filter(Boolean).join(" · ") || "—"}
            </p>
            <ListutkastStatus rad={rad} />
            <p className="mt-2 text-sm leading-6 text-ink-muted">{signaltext(rad)}</p>
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
            {mejlbro ? skrivMejlKnapp(rad, "mt-3 w-full") : null}
            {mejlbro && bred === false && oppenRad === rad.id ? (
              <div className="mt-3">
                <MejlRuta lista={lista} rad={rad} onKoat={() => void onUppdatera()} />
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Tillräckligt för att fånga ett felskrivet fält, inte en RFC 5322-validering —
 *  backenden och sändvägen är domarna. */
const ADRESS_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Mejlrutan under en listrad: Email studio, på plats.
 *
 * Kedjan är `skrivUtkastForRad` ovan. Utkastet landar i granskningskön och
 * visas här i Email studio-editorn, med Förbättra/Personalisera-knapparna och
 * "Godkänn och skicka".
 *
 * Saknar raden adress frågar rutan efter den FÖRST. Ett utkast utan mottagare
 * går inte att skicka lagligt (avregistreringsfoten byggs på adressen när
 * utkastet köas), så ett utkast före adressen hade varit ett löfte rutan inte
 * kan hålla.
 *
 * Ingenting skickas från den här rutan — godkännandet släpper utkastet till
 * samma sändkö som alla andra prospekt (INV-SEC-004 består: listjobbet har
 * inget sändverktyg, det har bara människan efter granskning).
 */
function MejlRuta({
  lista,
  rad,
  onKoat
}: Readonly<{ lista: Lista; rad: ListRad; onKoat?: () => void }>) {
  const { locale, text } = useLocale();
  const [fas, setFas] = useState<"adress" | "skapar" | "klar" | "fel">(
    rad.contact_email ? "skapar" : "adress"
  );
  const [steg, setSteg] = useState<Localized>(T.laggerBolaget);
  const [fel, setFel] = useState<string | null>(null);
  const [data, setData] = useState<EmailStudioData | null>(null);
  const [queueItemId, setQueueItemId] = useState<string | null>(null);
  const [godkant, setGodkant] = useState(false);
  const [godkannBusy, setGodkannBusy] = useState(false);
  const [godkannFel, setGodkannFel] = useState<string | null>(null);
  const [adressfalt, setAdressfalt] = useState("");
  const [adressFel, setAdressFel] = useState<string | null>(null);
  const [adress, setAdress] = useState<string | null>(rad.contact_email ?? null);

  const skapa = useCallback(
    async (mottagare: string) => {
      setFas("skapar");
      setFel(null);
      try {
        const utkast = await skrivUtkastForRad(lista, rad, mottagare, locale, setSteg);
        setData(byggStudioData(rad, utkast.prospectId, utkast.subject, utkast.body, utkast.offert));
        setQueueItemId(utkast.queueItemId);
        // Radens status ("Utkast köat") läses ur listan; hämta den igen.
        if (harListutkast(rad)) onKoat?.();
        setFas("klar");
      } catch (orsak) {
        setFel(felmeddelande(orsak));
        setFas("fel");
      }
    },
    [lista, rad, locale, onKoat]
  );

  useEffect(() => {
    if (rad.contact_email) void skapa(rad.contact_email);
    // Kör en gång när rutan öppnas för raden — skapa() är stabil per rad.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rad.id]);

  function sparaAdress() {
    const varde = adressfalt.trim();
    if (!ADRESS_RE.test(varde)) {
      setAdressFel(text(T.helMejladress));
      return;
    }
    setAdressFel(null);
    setAdress(varde);
    void skapa(varde);
  }

  const godkann = useCallback(async () => {
    if (!queueItemId) return;
    setGodkannBusy(true);
    setGodkannFel(null);
    try {
      await anropa(`/leads/queue/${encodeURIComponent(queueItemId)}/approve`, { method: "POST" });
      setGodkant(true);
    } catch (orsak) {
      setGodkannFel(felmeddelande(orsak));
    } finally {
      setGodkannBusy(false);
    }
  }, [queueItemId]);

  return (
    <div className="rounded-card border border-ink/15 bg-paper2/50 p-4 md:p-5">
      <p className="kicker text-mineral">
        {text({ sv: `Mejl till ${adress ?? rad.company_name}`, en: `Email to ${adress ?? rad.company_name}` })}
      </p>

      {fas === "adress" ? (
        <form
          className="mt-3"
          // Egen svensk validering nedan; webbläsarens bubbla hade hunnit före.
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            sparaAdress();
          }}
        >
          {harListutkast(rad) ? (
            // Listutkastet läses innan adressen läggs in: det är det som köas.
            <div className="max-w-[72ch] rounded-input border border-ink/12 bg-paper px-4 py-3">
              <p className="text-[13px] font-medium text-ink-subtle">{text({ sv: "Utkast", en: "Draft" })}</p>
              <p className="mt-1 text-[15px] font-semibold">{rad.utkast?.subject}</p>
              <p className="mt-2 whitespace-pre-wrap text-[15px] leading-7 text-ink">{rad.utkast?.body}</p>
              <p className="mt-2 text-[13px] text-ink-subtle">
                {text({
                  sv: "Signatur med logga och avregistreringsrad läggs till när utkastet köas.",
                  en: "Signature with logo and the unsubscribe line are added when the draft is queued."
                })}
              </p>
            </div>
          ) : null}
          <p className="mt-3 text-[14px] leading-6 text-ink-muted">
            {harListutkast(rad)
              ? text({
                  sv: "Lägg in VD:s mejladress. En adress som inte kan knytas till VD hör inte hemma här.",
                  en: "Add the CEO's email address. An address that cannot be tied to the CEO does not belong here."
                })
              : text(T.radenSaknarAdress)}
          </p>
          <label className="mt-3 block max-w-[420px]">
            <span className="text-[13px] font-medium text-ink-muted">
              {harListutkast(rad) ? text({ sv: "VD:s mejladress", en: "CEO's email address" }) : text(T.mejladress)}
            </span>
            <input
              type="email"
              value={adressfalt}
              onChange={(e) => setAdressfalt(e.target.value)}
              placeholder={text(T.mejladressExempel)}
              autoComplete="off"
              aria-invalid={adressFel ? true : undefined}
              aria-describedby={adressFel ? `adressfel-${rad.id}` : undefined}
              className={cn(fältklass, "mt-1.5")}
            />
          </label>
          {adressFel ? (
            <p id={`adressfel-${rad.id}`} role="alert" className="mt-2 text-[14px] text-danger">
              {adressFel}
            </p>
          ) : null}
          <button type="submit" className={cn(btnPrimary, "mt-3")}>
            {harListutkast(rad) ? text({ sv: "Köa utkastet för granskning", en: "Queue the draft for review" }) : text(T.sparaOchSkriv)}
          </button>
        </form>
      ) : null}

      {fas === "skapar" ? (
        <p className="mt-3 text-[14px] text-ink-subtle" role="status">
          {text(steg)}
        </p>
      ) : null}

      {fas === "fel" ? (
        <div className="mt-3">
          <p role="alert" className="max-w-[70ch] text-[14px] leading-6 text-danger">
            {fel}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => (adress ? void skapa(adress) : setFas("adress"))}
              className={cn(btnSecondary)}
            >
              {text(T.forsokIgen)}
            </button>
            {!rad.contact_email ? (
              <button
                type="button"
                onClick={() => {
                  setAdressfalt(adress ?? "");
                  setFas("adress");
                }}
                className={cn(btnSecondary)}
              >
                {text(T.andraAdressen)}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {fas === "klar" && data ? (
        <div className="mt-4">
          <EmailStudioEditor data={data} compact />
          <p className="mt-4 max-w-[65ch] text-[13px] leading-6 text-ink-subtle">
            {text(T.andringarSparasInte)}
          </p>
          <div className="mt-4 border-t border-ink/15 pt-4">
            {godkant ? (
              <p role="status" className="text-[15px] text-moss">
                {text(T.godkant)}
              </p>
            ) : (
              <>
                <button
                  type="button"
                  disabled={godkannBusy || !queueItemId}
                  onClick={() => void godkann()}
                  className={cn(btnPrimary, "disabled:cursor-wait disabled:opacity-60")}
                >
                  <Send className="h-4 w-4" aria-hidden />
                  {godkannBusy ? text(T.godkanner) : text(T.godkannOchSkicka)}
                </button>
                {!queueItemId ? (
                  <p className="mt-3 text-[13px] leading-6 text-ink-subtle">
                    {text(T.godkannIGranskning)}
                  </p>
                ) : null}
                {godkannFel ? (
                  <p role="alert" className="mt-3 max-w-[65ch] text-[14px] text-danger">
                    {godkannFel}
                  </p>
                ) : null}
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** Radens fält som Email studio-kontext: signalen och kontakten följer med
 *  till Förbättra/Personalisera-knapparna, så omskrivningar behåller bolaget
 *  och sammanhanget i stället för att bli generisk text. */
function byggStudioData(
  rad: ListRad,
  prospectId: string,
  subject: string | null | undefined,
  body: string,
  offert: string | null
): EmailStudioData {
  return {
    source: "database",
    businessContext: null,
    email: {
      id: prospectId,
      subject: subject || `Till ${rad.company_name}`,
      body,
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: prospectId,
      contactId: null,
      companyName: rad.company_name,
      signal: signaltext(rad) === "—" ? null : signaltext(rad),
      offer: offert,
      cta: null,
      contactName: rad.contact_name ?? null
    }
  };
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
