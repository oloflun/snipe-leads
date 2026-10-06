"use client";

import { ChevronDown, Mail, ScanLine } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import {
  Aktivitetsgraf,
  Andelsring,
  KpiKort,
  Munkdiagram,
  forandring,
  type Andel,
  type Kpi,
  type Vecka
} from "@/components/dashboard/OversiktPaneler";
import {
  Flaggrad,
  Granskningsmarke,
  FLAGGETIKETT,
  KUNDFAKTURA,
  MANUELL_HAMTNING,
  PRIORITERAD,
  arIntakt,
  bytRiktning,
  godkannKvitto,
  granskningsordning,
  kronor,
  radbelopp,
  type Kvitto
} from "@/components/kvitton/KvittoYta";
import { btnLiten, btnPrimary, btnSecondary, etikett, meta } from "@/components/ui";
import { DEMO_IDAG, DEMO_MEJLKONTO, demoKvitton } from "@/lib/demo/kvitto-oversikt";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Kvitton › Översikt (Sebbes beställning 2026-10-07): Leads-översiktens
 * layout (components/leads/LeadsOversikt.tsx) anpassad för Kvittohanteraren.
 *
 *   nyckeltal (fakturerat, utlägg, momsnetto, att granska)
 *   in och ut per vecka · munkdiagram för in/ut, kategori och granskning
 *   underlag att granska (expanderbar, godkänn direkt) · moms per sats
 *   senaste underlagen | kunder, leverantörer och obetalda fakturor
 *   avläsningsrutan för Snajp-admin (flaggor, källor, saknade fält)
 *
 * ## Allt räknas ur kvittolistan
 *
 * Ett anrop: `/kvitton` för de senaste tolv veckorna. Veckoserien, perioderna
 * och fördelningarna räknas här i ÖREN (heltal), aldrig i flyttal, så att
 * summorna blir desamma som backendens Decimal-summor. Bara underlag med
 * status "klar" bidrar med belopp — samma regel som `sammanstall` i
 * snajp-support/app/kvitton/sammanfattning.py: ett flaggat underlag står i
 * granskningsräkningen i stället för att bidra med ett osäkert tal.
 *
 * ## Intäkter (sedan 2026-10-07)
 *
 * Kundfakturor (`riktning: "intakt"`, företagets egna fakturor till kunder)
 * räknas för sig och aldrig som utlägg. Deras moms är UTGÅENDE moms; momsnetto
 * är utgående minus ingående. "Över" är in minus ut exklusive moms — ett mått
 * på de inlästa underlagen, inte ett bokslut.
 */

const BAS = "/api/snajp-support/kvitton";
const PERIOD = 4;
const VECKOR = 12;

const T = {
  fakturerat: { sv: "Fakturerat", en: "Invoiced" },
  utlagg: { sv: "Utlägg", en: "Expenses" },
  momsnetto: { sv: "Moms, netto", en: "VAT, net" },
  attBetala: { sv: "att betala in, senaste 4 veckorna", en: "to pay, last 4 weeks" },
  attFa: { sv: "att få tillbaka, senaste 4 veckorna", en: "to reclaim, last 4 weeks" },
  attGranska: { sv: "Att granska", en: "To review" },
  vantarPaDig: { sv: "väntar på ditt ja", en: "waiting for your yes" },
  prioriterad1: { sv: "prioriterad", en: "priority" },
  prioriterade: { sv: "prioriterade", en: "priority" },
  kundfakturor: { sv: "kundfakturor", en: "customer invoices" },
  kvitton: { sv: "kvitton", en: "receipts" },
  aktivitet: { sv: "In och ut per vecka", en: "In and out per week" },
  ingenAktivitet: { sv: "Inga underlag att visa än.", en: "No documents to show yet." },
  over: { sv: "Över, exkl. moms", en: "Surplus, excl. VAT" },
  overText: { sv: "fakturerat minus utlägg", en: "invoiced minus expenses" },
  storsta: { sv: "Största utlägget", en: "Largest expense" },
  utanHjalp: { sv: "Lästa utan anmärkning", en: "Read without remarks" },
  fordelning: { sv: "Fördelning", en: "Breakdown" },
  fordelningText: { sv: "Senaste fyra veckorna.", en: "Last four weeks." },
  inOchUt: { sv: "Pengar in och ut", en: "Money in and out" },
  overMitt: { sv: "kr över", en: "SEK surplus" },
  underMitt: { sv: "kr under", en: "SEK short" },
  perKategori: { sv: "Utlägg per kategori", en: "Expenses by category" },
  granskning: { sv: "Granskning", en: "Review" },
  krMitt: { sv: "kr", en: "SEK" },
  underlagMitt: { sv: "underlag", en: "documents" },
  granskaRubrik: { sv: "Att granska", en: "To review" },
  ingaAttGranska: { sv: "Inget väntar på dig. Allt är avläst.", en: "Nothing is waiting for you. Everything has been read." },
  visaAlla: { sv: "Visa alla", en: "Show all" },
  visaFarre: { sv: "Visa färre", en: "Show fewer" },
  godkann: { sv: "Godkänn", en: "Approve" },
  arKundfaktura: { sv: "Är en kundfaktura", en: "Is a customer invoice" },
  arKvitto: { sv: "Är ett kvitto", en: "Is a receipt" },
  momsRubrik: { sv: "Moms per sats", en: "VAT by rate" },
  momsText: {
    sv: "Utgående moms på fakturorna och ingående på kvittona, senaste fyra veckorna. Underlag till momsdeklarationen, stäm av med din redovisningskonsult.",
    en: "Output VAT on invoices and input VAT on receipts, last four weeks. A basis for your VAT return; check it with your accountant."
  },
  ut: { sv: "ut", en: "out" },
  in: { sv: "in", en: "in" },
  utgaende: { sv: "Utgående moms", en: "Output VAT" },
  ingaende: { sv: "Ingående moms", en: "Input VAT" },
  netto: { sv: "Att betala in", en: "To pay" },
  nettoTillbaka: { sv: "Att få tillbaka", en: "To reclaim" },
  senaste: { sv: "Senaste underlagen", en: "Latest documents" },
  senasteText: { sv: "Kvitton och kundfakturor, med status i samma färger som tabellen.", en: "Receipts and customer invoices, with status in the same colours as the table." },
  allaKvitton: { sv: "Alla underlag", en: "All documents" },
  motparter: { sv: "Kunder och leverantörer", en: "Customers and suppliers" },
  motparterText: { sv: "Var pengarna kommit ifrån och gått till de senaste tolv veckorna.", en: "Where the money came from and went over the last twelve weeks." },
  kunder: { sv: "Kunder", en: "Customers" },
  leverantorer: { sv: "Leverantörer", en: "Suppliers" },
  kundfordringar: { sv: "Obetalda kundfakturor", en: "Unpaid customer invoices" },
  obetalda: { sv: "Obetalda leverantörsfakturor", en: "Unpaid supplier invoices" },
  forfaller: { sv: "förfaller", en: "due" },
  iKorthet: { sv: "I korthet", en: "In short" },
  kopplad: { sv: "Kopplad inkorg:", en: "Connected mailbox:" },
  ingenInkorg: { sv: "Ingen inkorg kopplad.", en: "No mailbox connected." },
  skanna: { sv: "Skanna och ladda upp", en: "Scan and upload" },
  avlasning: { sv: "Avläsning", en: "Reading" },
  avlasningText: {
    sv: "Syns bara för Snajp-admin. Hur ofta agenten läser underlagen utan hjälp, och vad som stoppar den.",
    en: "Visible to Snajp admins only. How often the agent reads documents unaided, and what stops it."
  },
  utanAnmarkning: { sv: "utan anmärkning, tolv veckor", en: "without remarks, twelve weeks" },
  vanligasteFlaggor: { sv: "Vanligaste flaggorna", en: "Most common flags" },
  ingaFlaggor: { sv: "Inga flaggor de senaste tolv veckorna.", en: "No flags in the last twelve weeks." },
  utanKategori: { sv: "Kvitton utan kategori", en: "Receipts, no category" },
  utanMoms: { sv: "Utan momssats", en: "No VAT rate" },
  utanDatum: { sv: "Utan datum", en: "No date" },
  kalla: { sv: "Mejl / uppladdat", en: "Email / uploaded" },
  kvitto: { sv: "Kvitto", en: "Receipt" },
  klar: { sv: "Klar", en: "Done" },
  hamtaSjalv: { sv: "Hämta själv", en: "Fetch it" },
  prioriterad: { sv: "Prioriterad", en: "Priority" },
  granska: { sv: "Granska", en: "Review" }
} satisfies Record<string, Localized>;

/** Kontoplanens nycklar på båda språken. Okänd nyckel: backendens etikett. */
const KATEGORI: Record<string, Localized> = {
  drivmedel: { sv: "Drivmedel", en: "Fuel" },
  biljett: { sv: "Resor & transport", en: "Travel & transport" },
  kost_och_logi: { sv: "Logi", en: "Accommodation" },
  representation: { sv: "Representation", en: "Entertainment" },
  kontorsmateriel: { sv: "Kontorsmateriel", en: "Office supplies" },
  programvara: { sv: "Prenumerationer & programvara", en: "Subscriptions & software" },
  it_tjanst: { sv: "IT-tjänster", en: "IT services" },
  forbrukningsinventarier: { sv: "Verktyg & förbrukning", en: "Tools & consumables" },
  varuinkop: { sv: "Varuinköp", en: "Goods purchased" },
  mobiltelefon: { sv: "Telefoni", en: "Phone" },
  datakommunikation: { sv: "Datakommunikation", en: "Data communication" },
  forsakring: { sv: "Försäkringar", en: "Insurance" },
  bankkostnad: { sv: "Bankkostnader", en: "Bank charges" },
  annonsering: { sv: "Annonsering", en: "Advertising" },
  lokalhyra: { sv: "Lokalhyra", en: "Premises rent" },
  ovrig_extern_kostnad: { sv: "Övrigt", en: "Other" }
};
const OKATEGORISERAT: Localized = { sv: "Okategoriserat", en: "Uncategorised" };
const OVRIGA: Localized = { sv: "Övriga kategorier", en: "Other categories" };

function kategoriAv(rad: Kvitto): Localized {
  if (arIntakt(rad)) return KUNDFAKTURA;
  if (!rad.kategori) return OKATEGORISERAT;
  return KATEGORI[rad.kategori] ?? { sv: rad.kategorietikett || rad.kategori, en: rad.kategorietikett || rad.kategori };
}

const KATEGORIFARG = [
  "oklch(var(--chart-blue))",
  "oklch(var(--chart-ochre))",
  "oklch(var(--moss))",
  "oklch(var(--chart-ramp-3))",
  "oklch(var(--chart-ramp-5))"
];

const SATSER: { sats: string; etikett: string }[] = [
  { sats: "0.25", etikett: "25 %" },
  { sats: "0.12", etikett: "12 %" },
  { sats: "0.06", etikett: "6 %" },
  { sats: "0", etikett: "0 %" }
];

const kort = "rounded-card border border-ink/12 bg-paper p-4 sm:p-5";

// -- Belopp i ören -------------------------------------------------------------

/** "623.50" → 62350. Strängen tolkas siffra för siffra, aldrig som flyttal. */
function ore(varde: string | null): number | null {
  if (varde === null) return null;
  const negativt = varde.startsWith("-");
  const [heltal, decimaler = ""] = varde.replace("-", "").split(".");
  const n = Number(heltal) * 100 + Number((decimaler + "00").slice(0, 2));
  return Number.isFinite(n) ? (negativt ? -n : n) : null;
}

function normaliseradSats(sats: string | null): string | null {
  if (sats === null) return null;
  const s = sats.includes(".") ? sats.replace(/0+$/, "").replace(/\.$/, "") : sats;
  return s === "0.25" || s === "0.12" || s === "0.06" || s === "0" ? s : null;
}

/** Momsen ur bruttot, öresavrundad: brutto × sats ÷ (1 + sats). */
function momsOre(rad: Kvitto): number {
  const b = ore(rad.brutto);
  const s = normaliseradSats(rad.momssats);
  if (b === null || s === null || s === "0") return 0;
  const procent = Math.round(Number(s) * 100);
  return Math.round((b * procent) / (100 + procent));
}

function bruttoOre(rad: Kvitto): number {
  return ore(rad.brutto) ?? 0;
}

function oreTillStrang(n: number): string {
  const tecken = n < 0 ? "-" : "";
  const a = Math.abs(n);
  return `${tecken}${Math.floor(a / 100)}.${String(a % 100).padStart(2, "0")}`;
}

function helaKronor(n: number, locale: "sv" | "en"): string {
  const avrundat = Math.round(n / 100);
  return `${avrundat < 0 ? "−" : ""}${new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: 0 }).format(Math.abs(avrundat))} kr`;
}

function procent(n: number, locale: "sv" | "en"): string {
  return `${new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: 0 }).format(n * 100)} %`;
}

// -- Datum ---------------------------------------------------------------------

function utc(iso: string): Date {
  const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(a, m - 1, d));
}

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function mandagFor(datum: string): string {
  const d = utc(datum);
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return iso(d);
}

function isoVecka(datum: string): number {
  const d = utc(datum);
  d.setUTCDate(d.getUTCDate() + 3 - ((d.getUTCDay() + 6) % 7));
  const forsta = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  return 1 + Math.round(((d.getTime() - forsta.getTime()) / 86_400_000 - 3 + ((forsta.getUTCDay() + 6) % 7)) / 7);
}

function idagLokalt(): string {
  const nu = new Date();
  return `${nu.getFullYear()}-${String(nu.getMonth() + 1).padStart(2, "0")}-${String(nu.getDate()).padStart(2, "0")}`;
}

/** Måndagarna för de tolv veckorna som slutar med veckan för `idag`, äldst först. */
function mandagar(idag: string): string[] {
  const sista = utc(mandagFor(idag));
  return Array.from({ length: VECKOR }, (_, i) => {
    const d = new Date(sista);
    d.setUTCDate(d.getUTCDate() - 7 * (VECKOR - 1 - i));
    return iso(d);
  });
}

function datumKort(datum: string | null, locale: "sv" | "en"): string {
  if (!datum) return "–";
  return new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "sv-SE", { day: "numeric", month: "short", timeZone: "UTC" }).format(utc(datum));
}

// -- Data ----------------------------------------------------------------------

type Mejlkonto = { kopplad: boolean; leverantor?: string; adress?: string };

function useKvittodata(demo: boolean) {
  const [idag] = useState(() => (demo ? DEMO_IDAG : idagLokalt()));
  const [kvitton, setKvitton] = useState<Kvitto[] | null>(() => (demo ? demoKvitton() : null));
  const [konto, setKonto] = useState<Mejlkonto | null>(() => (demo ? DEMO_MEJLKONTO : null));
  const [fel, setFel] = useState(false);
  const fran = mandagar(idag)[0];

  const ladda = useCallback(async () => {
    if (demo) return;
    try {
      const [lista, k] = await Promise.all([
        fetch(`${BAS}?fran=${fran}&till=${idag}`, { cache: "no-store" }),
        fetch(`${BAS}/mejlkonto`, { cache: "no-store" })
      ]);
      if (!lista.ok) throw new Error(String(lista.status));
      const svar = await readJsonBody<{ kvitton?: Kvitto[] }>(lista);
      setKvitton(svar?.kvitton ?? []);
      setFel(false);
      if (k.ok) setKonto(await readJsonBody<Mejlkonto>(k));
    } catch {
      setFel(true);
      setKvitton((nu) => nu ?? []);
    }
  }, [demo, fran, idag]);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  return { idag, kvitton, setKvitton, konto, fel, ladda };
}

/** Summor för en uppsättning klara underlag, i ören. */
type Summor = { in: number; ut: number; utgaende: number; ingaende: number };

function summor(rader: Kvitto[]): Summor {
  const s: Summor = { in: 0, ut: 0, utgaende: 0, ingaende: 0 };
  for (const k of rader) {
    if (k.status !== "klar") continue;
    if (arIntakt(k)) {
      s.in += bruttoOre(k);
      s.utgaende += momsOre(k);
    } else {
      s.ut += bruttoOre(k);
      s.ingaende += momsOre(k);
    }
  }
  return s;
}

type Statistik = {
  veckor: Vecka[];
  /** Momsnetto per vecka i hela kronor (utgående − ingående), för sparklinen. */
  momsnetto: number[];
  klara: Kvitto[];
  granska: Kvitto[];
  period: Kvitto[];
  nu: Summor;
  forra: Summor;
  antalNu: { kvitton: number; fakturor: number };
};

function berakna(kvitton: Kvitto[], idag: string): Statistik {
  const man = mandagar(idag);
  const index = new Map(man.map((m, i) => [m, i]));
  const per = man.map(() => [] as Kvitto[]);
  const veckaAv = (k: Kvitto) => (k.datum ? index.get(mandagFor(k.datum)) : undefined);
  for (const k of kvitton) {
    const i = veckaAv(k);
    if (i !== undefined) per[i].push(k);
  }
  const veckor: Vecka[] = man.map((m, i) => {
    const s = summor(per[i]);
    return {
      week: `v${isoVecka(m)}`,
      utlagg: Math.round(s.ut / 100),
      intakter: Math.round(s.in / 100),
      moms: Math.round(s.ingaende / 100),
      kvitton: per[i].filter((k) => !arIntakt(k)).length
    };
  });
  const momsnetto = man.map((_, i) => {
    const s = summor(per[i]);
    return Math.round((s.utgaende - s.ingaende) / 100);
  });
  const start = VECKOR - PERIOD;
  const period = per.slice(start).flat();
  const forra = per.slice(start - PERIOD, start).flat();
  return {
    veckor,
    momsnetto,
    klara: kvitton.filter((k) => k.status === "klar"),
    granska: kvitton.filter((k) => k.status !== "klar"),
    period,
    nu: summor(period),
    forra: summor(forra),
    // Godkända underlag, samma tal som beloppen bredvid räknas på.
    antalNu: {
      kvitton: period.filter((k) => k.status === "klar" && !arIntakt(k)).length,
      fakturor: period.filter((k) => k.status === "klar" && arIntakt(k)).length
    }
  };
}

/** In minus ut exklusive moms, i ören. */
function over(s: Summor): number {
  return s.in - s.utgaende - (s.ut - s.ingaende);
}

// -- Delarna -------------------------------------------------------------------

const STATUSPRICK: Record<string, { prick: string; text: string; etikett: Localized }> = {
  klar: { prick: "bg-moss", text: "text-ink-muted", etikett: T.klar },
  granska: { prick: "bg-ochre", text: "text-warning", etikett: T.granska },
  hamta: { prick: "bg-chart-blue", text: "text-ink-muted", etikett: T.hamtaSjalv },
  prioriterad: { prick: "bg-danger", text: "text-danger", etikett: T.prioriterad }
};

function statusAv(rad: Kvitto): keyof typeof STATUSPRICK {
  if (rad.status === "klar") return "klar";
  if (rad.granskningsstatus === PRIORITERAD) return "prioriterad";
  if (rad.granskningsstatus === MANUELL_HAMTNING) return "hamta";
  return "granska";
}

function namnAv(rad: Kvitto, text: (v: Localized) => string): string {
  return rad.motpart || rad.mejl_amne || rad.filnamn || text(arIntakt(rad) ? KUNDFAKTURA : T.kvitto);
}

/** Granskningsrutan: tre mest angelägna, fäll ut till alla, godkänn på raden. */
function GranskaRuta({
  rader,
  onGodkann,
  onByt
}: Readonly<{ rader: Kvitto[]; onGodkann: (rad: Kvitto) => Promise<void>; onByt: (rad: Kvitto) => Promise<void> }>) {
  const { text, locale } = useLocale();
  const [alla, setAlla] = useState(false);
  const [oppen, setOppen] = useState<string | null>(null);
  const [arbetar, setArbetar] = useState<string | null>(null);
  const sorterade = [...rader].sort(
    (a, b) => granskningsordning(a) - granskningsordning(b) || (b.datum ?? "").localeCompare(a.datum ?? "")
  );
  const visade = alla ? sorterade : sorterade.slice(0, 3);

  async function medArbete(rad: Kvitto, f: (rad: Kvitto) => Promise<void>) {
    setArbetar(rad.id);
    try {
      await f(rad);
    } finally {
      setArbetar(null);
    }
  }

  return (
    <section aria-labelledby="kvitto-granska" className={cn(kort, "min-w-0")}>
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <h2 id="kvitto-granska" className="text-[1rem] font-semibold">
          {text(T.granskaRubrik)}
          {rader.length ? <span className="num ml-2 font-normal tabular-nums text-ink-subtle">{rader.length}</span> : null}
        </h2>
        {rader.length > 3 ? (
          <button
            type="button"
            onClick={() => setAlla((a) => !a)}
            className="focus-ring text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
          >
            {text(alla ? T.visaFarre : T.visaAlla)}
          </button>
        ) : null}
      </div>
      {visade.length === 0 ? (
        <p className={meta}>{text(T.ingaAttGranska)}</p>
      ) : (
        <ul className="divide-y divide-ink/10">
          {visade.map((rad) => {
            const ar = oppen === rad.id;
            return (
              <li key={rad.id} className="py-2.5">
                <button
                  type="button"
                  onClick={() => setOppen(ar ? null : rad.id)}
                  aria-expanded={ar}
                  className="focus-ring -mx-1 flex w-[calc(100%+0.5rem)] items-center gap-3 rounded-input px-1 py-0.5 text-left hover:bg-paper2/60"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[0.9375rem] font-medium">{namnAv(rad, text)}</span>
                    <span className={cn(meta, "block truncate")}>
                      {[datumKort(rad.datum, locale), text(kategoriAv(rad))].join(" · ")}
                      <span className="num tabular-nums sm:hidden"> · {radbelopp(rad)}</span>
                    </span>
                  </span>
                  <span
                    className={cn(
                      "num hidden shrink-0 text-[0.8125rem] tabular-nums sm:inline",
                      arIntakt(rad) ? "text-moss" : "text-ink-muted"
                    )}
                  >
                    {radbelopp(rad)}
                  </span>
                  <span className="shrink-0">
                    <Granskningsmarke rad={rad} />
                  </span>
                  <ChevronDown className={cn("h-4 w-4 shrink-0 text-ink-subtle transition-transform", ar && "rotate-180")} aria-hidden />
                </button>
                {ar ? (
                  <div className="mt-2.5 rounded-input border border-ink/12 bg-paper2/40 px-3 py-2.5">
                    {rad.anmarkning ? <p className="text-[0.875rem] leading-6 text-ink-muted">{rad.anmarkning}</p> : null}
                    <Flaggrad flaggor={rad.flaggor} />
                    {rad.forfallodatum ? (
                      <p className={cn(meta, "mt-1.5")}>
                        {text(T.forfaller)} {datumKort(rad.forfallodatum, locale)}
                      </p>
                    ) : null}
                    <div className="mt-2.5 flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        disabled={arbetar === rad.id}
                        onClick={() => void medArbete(rad, onGodkann)}
                        className={cn(btnPrimary, btnLiten)}
                      >
                        {text(T.godkann)}
                      </button>
                      <button
                        type="button"
                        disabled={arbetar === rad.id}
                        onClick={() => void medArbete(rad, onByt)}
                        className="focus-ring rounded-input text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
                      >
                        {text(arIntakt(rad) ? T.arKvitto : T.arKundfaktura)}
                      </button>
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/** Moms per sats: utgående (fakturorna) och ingående (kvittona), och nettot. */
function MomsRuta({ period }: Readonly<{ period: Kvitto[] }>) {
  const { text, locale } = useLocale();
  const klara = period.filter((k) => k.status === "klar");
  const rader = SATSER.map((s) => {
    const deras = klara.filter((k) => normaliseradSats(k.momssats) === s.sats);
    return {
      ...s,
      ut: deras.filter(arIntakt).reduce((a, k) => a + momsOre(k), 0),
      in: deras.filter((k) => !arIntakt(k)).reduce((a, k) => a + momsOre(k), 0)
    };
  });
  const storst = Math.max(1, ...rader.flatMap((r) => [r.ut, r.in]));
  const utgaende = rader.reduce((a, r) => a + r.ut, 0);
  const ingaende = rader.reduce((a, r) => a + r.in, 0);
  const netto = utgaende - ingaende;
  return (
    <section aria-labelledby="kvitto-moms" className={cn(kort, "min-w-0")}>
      <h2 id="kvitto-moms" className="text-[1rem] font-semibold">
        {text(T.momsRubrik)}
      </h2>
      <p className={cn(meta, "mb-4 mt-1")}>{text(T.momsText)}</p>
      <div className="mb-2 flex gap-4 text-[0.75rem] text-ink-muted">
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden className="h-2 w-3 rounded-full bg-chart-blue" />
          {text(T.utgaende)}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden className="h-2 w-3 rounded-full bg-chart-ochre" />
          {text(T.ingaende)}
        </span>
      </div>
      <ul className="space-y-3">
        {rader.map((r) => (
          <li key={r.sats} className="grid grid-cols-[3rem_1fr_auto] items-center gap-x-3 gap-y-1 text-[0.8125rem]">
            <span className="num row-span-2 tabular-nums text-ink-muted">{r.etikett}</span>
            <span className="h-2 overflow-hidden rounded-full bg-ink/[0.06]">
              <span className="block h-full rounded-full bg-chart-blue" style={{ width: `${(r.ut / storst) * 100}%` }} />
            </span>
            <span className="num text-right tabular-nums text-ink">
              <span className="sr-only">{text(T.utgaende)} </span>
              {helaKronor(r.ut, locale)}
            </span>
            <span className="h-2 overflow-hidden rounded-full bg-ink/[0.06]">
              <span className="block h-full rounded-full bg-chart-ochre" style={{ width: `${(r.in / storst) * 100}%` }} />
            </span>
            <span className="num text-right tabular-nums text-ink-muted">
              <span className="sr-only">{text(T.ingaende)} </span>
              {helaKronor(r.in, locale)}
            </span>
          </li>
        ))}
      </ul>
      <dl className="mt-4 space-y-1 border-t border-ink/10 pt-3 text-[0.875rem]">
        <div className="flex items-baseline justify-between gap-4">
          <dt className="text-ink-muted">{text(T.utgaende)}</dt>
          <dd className="num tabular-nums text-ink">{kronor(oreTillStrang(utgaende))}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-4">
          <dt className="text-ink-muted">{text(T.ingaende)}</dt>
          <dd className="num tabular-nums text-ink">−{kronor(oreTillStrang(ingaende))}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-4 font-semibold">
          <dt>{text(netto >= 0 ? T.netto : T.nettoTillbaka)}</dt>
          <dd className="num tabular-nums text-ink">{kronor(oreTillStrang(Math.abs(netto)))}</dd>
        </div>
      </dl>
    </section>
  );
}

function Kvittolista({ rader }: Readonly<{ rader: Kvitto[] }>) {
  const { text, locale } = useLocale();
  return (
    <ul className="divide-y divide-ink/10">
      {rader.map((rad) => {
        const s = STATUSPRICK[statusAv(rad)];
        return (
          <li key={rad.id} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[0.9375rem] font-medium">{namnAv(rad, text)}</span>
              <span className={cn(meta, "block truncate")}>
                {text(kategoriAv(rad))} · {datumKort(rad.datum, locale)} ·{" "}
                {rad.kalla === "mejl" ? text({ sv: "Mejl", en: "Email" }) : text({ sv: "Uppladdad", en: "Uploaded" })}
              </span>
            </span>
            <span className="flex shrink-0 items-center gap-4">
              <span className={cn("num text-[0.875rem] font-medium tabular-nums", arIntakt(rad) && "text-moss")}>
                {radbelopp(rad)}
              </span>
              <span className={cn("inline-flex w-28 items-center gap-1.5 text-[0.8125rem]", s.text)}>
                <span aria-hidden className={cn("h-1.5 w-1.5 shrink-0 rounded-full", s.prick)} />
                {text(s.etikett)}
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** Motparterna summerade, största först, med en stapel för andelen. */
function Topplista({ rader, farg, tak }: Readonly<{ rader: Kvitto[]; farg: string; tak: number }>) {
  const { locale } = useLocale();
  const per = new Map<string, { namn: string; antal: number; summa: number }>();
  for (const k of rader) {
    const namn = k.motpart || k.filnamn || "–";
    const post = per.get(namn) ?? { namn, antal: 0, summa: 0 };
    post.antal += 1;
    post.summa += bruttoOre(k);
    per.set(namn, post);
  }
  const lista = [...per.values()].sort((a, b) => b.summa - a.summa).slice(0, tak);
  const total = rader.reduce((s, k) => s + bruttoOre(k), 0) || 1;
  return (
    <ul className="space-y-3">
      {lista.map((l) => (
        <li key={l.namn}>
          <div className="flex items-baseline justify-between gap-4 text-[0.875rem]">
            <span className="min-w-0 truncate font-medium text-ink">
              {l.namn}
              <span className="ml-1.5 text-[0.75rem] font-normal text-ink-subtle">×{l.antal}</span>
            </span>
            <span className="num shrink-0 tabular-nums text-ink">{helaKronor(l.summa, locale)}</span>
          </div>
          <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-ink/[0.06]">
            <span className={cn("block h-full rounded-full", farg)} style={{ width: `${(l.summa / total) * 100}%` }} />
          </span>
        </li>
      ))}
    </ul>
  );
}

function Forfallolista({ rubrik, rader }: Readonly<{ rubrik: Localized; rader: Kvitto[] }>) {
  const { text, locale } = useLocale();
  if (rader.length === 0) return null;
  return (
    <div>
      <p className={etikett}>{text(rubrik)}</p>
      <ul className="mt-2 divide-y divide-ink/10">
        {rader.map((k) => (
          <li key={k.id} className="flex items-baseline justify-between gap-4 py-2 text-[0.8125rem]">
            <span className="min-w-0 truncate text-ink-muted">{k.motpart || k.filnamn}</span>
            <span className="num shrink-0 tabular-nums text-ink-subtle">
              {text(T.forfaller)} {datumKort(k.forfallodatum ?? null, locale)}
            </span>
            <span className="num w-24 shrink-0 text-right font-medium tabular-nums text-ink">{kronor(k.brutto)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Motparter({ klara, obetalda }: Readonly<{ klara: Kvitto[]; obetalda: Kvitto[] }>) {
  const { text } = useLocale();
  const fakturor = klara.filter(arIntakt);
  const kvitton = klara.filter((k) => !arIntakt(k));
  return (
    <div className="grid gap-6">
      {fakturor.length ? (
        <div>
          <p className={cn(etikett, "mb-2")}>{text(T.kunder)}</p>
          <Topplista rader={fakturor} farg="bg-moss" tak={5} />
        </div>
      ) : null}
      {kvitton.length ? (
        <div>
          <p className={cn(etikett, "mb-2")}>{text(T.leverantorer)}</p>
          <Topplista rader={kvitton} farg="bg-chart-blue" tak={8} />
        </div>
      ) : null}
      <Forfallolista rubrik={T.kundfordringar} rader={obetalda.filter(arIntakt)} />
      <Forfallolista rubrik={T.obetalda} rader={obetalda.filter((k) => !arIntakt(k))} />
    </div>
  );
}

/** Bara för Snajp-admin: hur avläsningen går, ur samma lista. */
function Avlasningsruta({ kvitton }: Readonly<{ kvitton: Kvitto[] }>) {
  const { text, locale } = useLocale();
  const medGranskning = kvitton.filter((k) => k.granskningsstatus);
  const rena = medGranskning.filter((k) => k.status === "klar" && (k.flaggor ?? []).length === 0).length;
  const andel = medGranskning.length ? rena / medGranskning.length : null;
  const flaggor = new Map<string, number>();
  for (const k of kvitton) for (const f of k.flaggor ?? []) flaggor.set(f, (flaggor.get(f) ?? 0) + 1);
  const topp = [...flaggor.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  const mejl = kvitton.filter((k) => k.kalla === "mejl").length;
  const rader: { etikett: Localized; varde: string }[] = [
    { etikett: T.kalla, varde: `${mejl} / ${kvitton.length - mejl}` },
    { etikett: T.utanKategori, varde: String(kvitton.filter((k) => !arIntakt(k) && !k.kategori).length) },
    { etikett: T.utanMoms, varde: String(kvitton.filter((k) => k.momssats === null).length) },
    { etikett: T.utanDatum, varde: String(kvitton.filter((k) => !k.datum).length) }
  ];
  return (
    <section aria-labelledby="kvitto-avlasning" className={cn(kort, "border-dashed")}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id="kvitto-avlasning" className="text-[1rem] font-semibold">
          {text(T.avlasning)}
        </h2>
        <p className={meta}>{text(T.avlasningText)}</p>
      </div>
      <div className="mt-4 flex flex-wrap items-start gap-x-10 gap-y-5">
        <div className="flex items-center gap-4">
          <Andelsring andel={andel} etikett={text(T.utanHjalp)} />
          <div>
            <p className={etikett}>{text(T.utanHjalp)}</p>
            <p className={cn(meta, "num tabular-nums")}>
              {rena} / {medGranskning.length} {text(T.utanAnmarkning)}
            </p>
          </div>
        </div>
        <dl className="grid min-w-[16rem] flex-1 grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
          {rader.map((r) => (
            <div key={r.etikett.sv}>
              <dt className={etikett}>{text(r.etikett)}</dt>
              <dd className="num mt-1 text-[1.25rem] font-semibold tabular-nums text-ink">{r.varde}</dd>
            </div>
          ))}
        </dl>
        <div className="min-w-[14rem] flex-1">
          <p className={etikett}>{text(T.vanligasteFlaggor)}</p>
          {topp.length === 0 ? (
            <p className={cn(meta, "mt-2")}>{text(T.ingaFlaggor)}</p>
          ) : (
            <ul className="mt-2 space-y-1.5">
              {topp.map(([f, n]) => (
                <li key={f} className="flex items-center gap-2 text-[0.8125rem] text-ink-muted">
                  <span className="min-w-0 flex-1 truncate">{FLAGGETIKETT[f] ? text(FLAGGETIKETT[f]) : f}</span>
                  <span className="num font-medium tabular-nums text-ink">{n}</span>
                  <span className="num w-10 text-right tabular-nums text-ink-subtle">{procent(n / Math.max(1, kvitton.length), locale)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

// -- Översikten ------------------------------------------------------------------

export function KvittoOversikt({
  demo = false,
  visaDrift = false,
  onOppnaKvitton
}: Readonly<{ demo?: boolean; visaDrift?: boolean; onOppnaKvitton?: () => void }>) {
  const { isPlatformAdmin, isDemo, vy } = useDashboard();
  const { text, locale } = useLocale();
  const arDemo = demo || isDemo || vy === "demo";
  const { idag, kvitton, setKvitton, konto, fel, ladda } = useKvittodata(arDemo);
  const [atgardsfel, setAtgardsfel] = useState<Localized | null>(null);

  const s = useMemo(() => (kvitton ? berakna(kvitton, idag) : null), [kvitton, idag]);

  async function godkann(rad: Kvitto) {
    setAtgardsfel(null);
    if (arDemo) {
      // Demon har ingen backend: godkännandet flyttar bara raden lokalt.
      setKvitton((nu) => (nu ?? []).map((k) => (k.id === rad.id ? { ...k, status: "klar", flaggor: [] } : k)));
      return;
    }
    const utfall = await godkannKvitto(rad, text);
    if (utfall === "avbrutet") return;
    if (utfall) setAtgardsfel(utfall);
    await ladda();
  }

  async function byt(rad: Kvitto) {
    setAtgardsfel(null);
    const ny = arIntakt(rad) ? "kostnad" : "intakt";
    if (arDemo) {
      setKvitton((nu) => (nu ?? []).map((k) => (k.id === rad.id ? { ...k, riktning: ny } : k)));
      return;
    }
    const utfall = await bytRiktning(rad, ny);
    if (utfall) setAtgardsfel(utfall);
    await ladda();
  }

  const perioden: Localized = { sv: `de ${PERIOD} veckorna före`, en: `the ${PERIOD} weeks before` };
  const serie = (k: keyof Vecka) => (s ? s.veckor.slice(-8).map((v) => Number(v[k] ?? 0)) : undefined);
  const prioriterade = s ? s.granska.filter((k) => k.granskningsstatus === PRIORITERAD).length : 0;
  const momsnetto = s ? s.nu.utgaende - s.nu.ingaende : 0;

  const kpier: Kpi[] = [
    {
      id: "in",
      etikett: T.fakturerat,
      varde: null,
      visning: s ? helaKronor(s.nu.in, locale) : "–",
      forandring: s ? forandring(s.nu.in, s.forra.in) : undefined,
      serie: serie("intakter"),
      detalj: s
        ? { sv: `${s.antalNu.fakturor} ${T.kundfakturor.sv}, 4 veckor`, en: `${s.antalNu.fakturor} ${T.kundfakturor.en}, 4 weeks` }
        : T.fordelningText
    },
    {
      id: "ut",
      etikett: T.utlagg,
      varde: null,
      visning: s ? helaKronor(s.nu.ut, locale) : "–",
      forandring: s ? forandring(s.nu.ut, s.forra.ut) : undefined,
      battre: "ner",
      serie: serie("utlagg"),
      detalj: s ? { sv: `${s.antalNu.kvitton} ${T.kvitton.sv}, 4 veckor`, en: `${s.antalNu.kvitton} ${T.kvitton.en}, 4 weeks` } : T.fordelningText
    },
    {
      id: "moms",
      etikett: T.momsnetto,
      varde: null,
      visning: s ? helaKronor(Math.abs(momsnetto), locale) : "–",
      serie: s ? s.momsnetto.slice(-8) : undefined,
      detalj: momsnetto >= 0 ? T.attBetala : T.attFa
    },
    {
      id: "granska",
      etikett: T.attGranska,
      varde: s ? s.granska.length : null,
      larm: (s?.granska.length ?? 0) > 0,
      detalj: prioriterade
        ? {
            sv: `${T.vantarPaDig.sv} · ${prioriterade} ${prioriterade === 1 ? T.prioriterad1.sv : T.prioriterade.sv}`,
            en: `${T.vantarPaDig.en} · ${prioriterade} ${T.prioriterade.en}`
          }
        : T.vantarPaDig
    }
  ];

  // Fördelningarna, periodens klara underlag.
  const periodKlara = s ? s.period.filter((k) => k.status === "klar") : [];
  const periodKvitton = periodKlara.filter((k) => !arIntakt(k));
  const perKategori = new Map<string, { etikett: Localized; ore: number }>();
  for (const k of periodKvitton) {
    const nyckel = k.kategori ?? "";
    const post = perKategori.get(nyckel) ?? { etikett: kategoriAv(k), ore: 0 };
    post.ore += bruttoOre(k);
    perKategori.set(nyckel, post);
  }
  const kategorier = [...perKategori.entries()].sort((a, b) => b[1].ore - a[1].ore);
  const kategoridelar: Andel[] = kategorier.slice(0, 5).map(([id, p], i) => ({
    id: id || "okategoriserat",
    etikett: p.etikett,
    antal: Math.round(p.ore / 100),
    farg: KATEGORIFARG[i]
  }));
  if (kategorier.length > 5) {
    kategoridelar.push({
      id: "ovriga",
      etikett: OVRIGA,
      antal: Math.round(kategorier.slice(5).reduce((a, [, p]) => a + p.ore, 0) / 100),
      farg: "oklch(var(--ink-subtle))"
    });
  }
  const inUtDelar: Andel[] = [
    { id: "in", etikett: T.fakturerat, antal: s ? Math.round(s.nu.in / 100) : 0, farg: "oklch(var(--moss))" },
    { id: "ut", etikett: T.utlagg, antal: s ? Math.round(s.nu.ut / 100) : 0, farg: "oklch(var(--chart-ochre))" }
  ];
  const overNu = s ? over(s.nu) : 0;
  const statusdelar: Andel[] = [
    { id: "klar", etikett: T.klar, farg: "oklch(var(--moss))" },
    { id: "granska", etikett: T.granska, farg: "oklch(var(--chart-ochre))" },
    { id: "hamta", etikett: T.hamtaSjalv, farg: "oklch(var(--chart-blue))" },
    { id: "prioriterad", etikett: T.prioriterad, farg: "oklch(var(--danger))" }
  ].map((d) => ({ ...d, antal: s ? s.period.filter((k) => statusAv(k) === d.id).length : 0 }));

  const storsta = periodKvitton.reduce<Kvitto | null>((a, k) => (!a || bruttoOre(k) > bruttoOre(a) ? k : a), null);
  const medGranskning = s ? s.period.filter((k) => k.granskningsstatus) : [];
  const nyckeltal: { etikett: Localized; varde: string; under?: string }[] = [
    { etikett: T.over, varde: s ? helaKronor(overNu, locale) : "–", under: text(T.overText) },
    { etikett: T.storsta, varde: storsta ? helaKronor(bruttoOre(storsta), locale) : "–", under: storsta?.motpart ?? undefined },
    {
      etikett: T.utanHjalp,
      varde: medGranskning.length
        ? procent(medGranskning.filter((k) => k.status === "klar" && (k.flaggor ?? []).length === 0).length / medGranskning.length, locale)
        : "–"
    }
  ];

  // I korthet: meningar ur talen ovan, på båda språken. Ingen modell.
  const toppKategori = kategorier[0];
  const fakturorKlara = periodKlara.filter(arIntakt).length;
  const korthetsdelar: Localized[] = s
    ? [
        ...(fakturorKlara
          ? [
              {
                sv: `${fakturorKlara} kundfakturor på ${helaKronor(s.nu.in, "sv")} de senaste fyra veckorna, med ${helaKronor(s.nu.utgaende, "sv")} i utgående moms.`,
                en: `${fakturorKlara} customer invoices for ${helaKronor(s.nu.in, "en")} over the last four weeks, with ${helaKronor(s.nu.utgaende, "en")} in output VAT.`
              }
            ]
          : []),
        ...(periodKvitton.length
          ? [
              {
                sv: `${periodKvitton.length} avlästa kvitton på ${helaKronor(s.nu.ut, "sv")}, varav ${helaKronor(s.nu.ingaende, "sv")} ingående moms.`,
                en: `${periodKvitton.length} receipts read for ${helaKronor(s.nu.ut, "en")}, including ${helaKronor(s.nu.ingaende, "en")} input VAT.`
              }
            ]
          : []),
        ...(toppKategori
          ? [
              {
                sv: `Mest gick till ${toppKategori[1].etikett.sv.toLowerCase()} (${helaKronor(toppKategori[1].ore, "sv")}).`,
                en: `Most went to ${toppKategori[1].etikett.en.toLowerCase()} (${helaKronor(toppKategori[1].ore, "en")}).`
              }
            ]
          : []),
        ...(s.granska.length
          ? [
              {
                sv: `${s.granska.length} underlag väntar på granskning och räknas inte in förrän du godkänt dem.`,
                en: `${s.granska.length} documents are waiting for review and are not counted until you approve them.`
              }
            ]
          : [])
      ]
    : [];
  const korthet: Localized | null = korthetsdelar.length
    ? { sv: korthetsdelar.map((d) => d.sv).join(" "), en: korthetsdelar.map((d) => d.en).join(" ") }
    : null;

  const senaste = kvitton ? [...kvitton].sort((a, b) => (b.datum ?? "").localeCompare(a.datum ?? "")).slice(0, 15) : [];
  const obetalda = kvitton
    ? kvitton
        .filter((k) => k.status === "klar" && k.betalstatus === "obetald" && k.forfallodatum)
        .sort((a, b) => (a.forfallodatum ?? "").localeCompare(b.forfallodatum ?? ""))
    : [];
  const harVeckor = s !== null && s.veckor.some((v) => (v.kvitton ?? 0) > 0 || (v.intakter ?? 0) > 0);
  const kolumn = cn(kort, "relative min-w-0 thin-scrollbar xl:max-h-[40rem] xl:overflow-y-auto");

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <p className="flex flex-wrap items-center gap-2 text-[0.875rem] text-ink-muted">
          <Mail className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
          {konto === null ? (
            "…"
          ) : konto.kopplad ? (
            <>
              {text(T.kopplad)} <span className="font-medium text-ink">{konto.adress}</span>
            </>
          ) : (
            text(T.ingenInkorg)
          )}
        </p>
        {onOppnaKvitton ? (
          <button type="button" onClick={onOppnaKvitton} className={cn(btnSecondary, btnLiten)}>
            <ScanLine className="h-4 w-4" aria-hidden />
            {text(T.skanna)}
          </button>
        ) : null}
      </div>

      {fel ? (
        <p role="alert" className="text-[0.875rem] text-danger">
          {text({ sv: "Underlagen gick inte att hämta just nu.", en: "The documents could not be loaded right now." })}
        </p>
      ) : null}
      {atgardsfel ? (
        <p role="alert" className="text-[0.875rem] text-danger">
          {text(atgardsfel)}
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={perioden} />
        ))}
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-12">
        <section aria-labelledby="kvitto-aktivitet" className={cn(kort, "min-w-0 lg:col-span-7")}>
          <h2 id="kvitto-aktivitet" className="mb-4 text-[1rem] font-semibold">
            {text(T.aktivitet)}
          </h2>
          {harVeckor && s ? (
            <>
              <Aktivitetsgraf
                veckor={s.veckor}
                axelbredd={60}
                serier={[
                  { nyckel: "intakter", etikett: { sv: "Fakturerat, kr", en: "Invoiced, SEK" }, ton: "chart-blue" },
                  { nyckel: "utlagg", etikett: { sv: "Utlägg, kr", en: "Expenses, SEK" }, ton: "chart-ochre" }
                ]}
              />
              <dl className="mt-5 grid grid-cols-1 gap-3 border-t border-ink/10 pt-4 sm:grid-cols-3 sm:gap-4">
                {nyckeltal.map((x) => (
                  <div key={x.etikett.sv} className="flex items-baseline justify-between gap-3 sm:block">
                    <dt className={etikett}>{text(x.etikett)}</dt>
                    <dd className="text-right sm:mt-1 sm:text-left">
                      <span className="num block text-[1.25rem] font-semibold tabular-nums text-ink">{x.varde}</span>
                      {x.under ? <span className={cn(meta, "block truncate")}>{x.under}</span> : null}
                    </dd>
                  </div>
                ))}
              </dl>
            </>
          ) : (
            <p className={meta}>{kvitton === null ? "…" : text(T.ingenAktivitet)}</p>
          )}
        </section>
        <section aria-labelledby="kvitto-fordelning" className={cn(kort, "min-w-0 lg:col-span-5")}>
          <div className="mb-4 flex items-baseline justify-between gap-4">
            <h2 id="kvitto-fordelning" className="text-[1rem] font-semibold">
              {text(T.fordelning)}
            </h2>
            <p className={meta}>{text(T.fordelningText)}</p>
          </div>
          {kvitton === null ? (
            <p className={meta}>…</p>
          ) : (
            <div className="grid gap-6">
              <Munkdiagram
                delar={inUtDelar}
                etikett={T.inOchUt}
                mitt={overNu >= 0 ? T.overMitt : T.underMitt}
                mittVarde={new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: 0 }).format(
                  Math.abs(Math.round(overNu / 100))
                )}
              />
              <Munkdiagram delar={kategoridelar} etikett={T.perKategori} mitt={T.krMitt} />
              <Munkdiagram delar={statusdelar} etikett={T.granskning} mitt={T.underlagMitt} />
            </div>
          )}
        </section>
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <GranskaRuta rader={s?.granska ?? []} onGodkann={godkann} onByt={byt} />
        <MomsRuta period={s?.period ?? []} />
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <section aria-labelledby="kvitto-senaste" className={kolumn}>
          <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
            <h2 id="kvitto-senaste" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
              {text(T.senaste)}
            </h2>
            {onOppnaKvitton ? (
              <button
                type="button"
                onClick={onOppnaKvitton}
                className="focus-ring text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
              >
                {text(T.allaKvitton)}
              </button>
            ) : null}
          </div>
          <p className={cn(meta, "mb-2 mt-1 max-w-[70ch]")}>{text(T.senasteText)}</p>
          {kvitton === null ? <p className={meta}>…</p> : senaste.length ? <Kvittolista rader={senaste} /> : <p className={meta}>{text(T.ingenAktivitet)}</p>}
        </section>
        <section aria-labelledby="kvitto-motparter" className={kolumn}>
          <h2 id="kvitto-motparter" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
            {text(T.motparter)}
          </h2>
          <p className={cn(meta, "mb-4 mt-1 max-w-[70ch]")}>{text(T.motparterText)}</p>
          {korthet ? (
            <div className="mb-5 rounded-input bg-paper2/50 px-3 py-2.5">
              <p className={etikett}>{text(T.iKorthet)}</p>
              <p className="mt-1 text-[0.875rem] leading-6 text-ink-muted">{text(korthet)}</p>
            </div>
          ) : null}
          {s ? <Motparter klara={s.klara} obetalda={obetalda} /> : <p className={meta}>…</p>}
        </section>
      </div>

      {(visaDrift || isPlatformAdmin) && kvitton ? <Avlasningsruta kvitton={kvitton} /> : null}
    </div>
  );
}
