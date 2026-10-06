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
  MANUELL_HAMTNING,
  PRIORITERAD,
  godkannKvitto,
  granskningsordning,
  kronor,
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
 *   nyckeltal (utlägg, att granska, ingående moms, inlästa kvitton)
 *   utlägg och moms per vecka · munkdiagram för kategori och granskning
 *   kvitton att granska (expanderbar, godkänn direkt) · moms per sats
 *   senaste kvittona | leverantörer och obetalda fakturor   (split view)
 *   avläsningsrutan för Snajp-admin (flaggor, källor, saknade fält)
 *
 * ## Allt räknas ur kvittolistan
 *
 * Ett anrop: `/kvitton` för de senaste tolv veckorna. Veckoserien, perioderna
 * och fördelningarna räknas här i ÖREN (heltal), aldrig i flyttal, så att
 * summorna blir desamma som backendens Decimal-summor. Bara kvitton med
 * status "klar" bidrar med belopp — samma regel som `sammanstall` i
 * snajp-support/app/kvitton/sammanfattning.py: ett flaggat kvitto står i
 * granskningsräkningen i stället för att bidra med ett osäkert tal.
 *
 * ## Inga intäkter
 *
 * Kvittohanteraren tar bara emot utlägg (`bara_utlagg` i backenden filtrerar
 * bort kundfakturor), så översikten visar vart pengarna går, inte resultatet.
 */

const BAS = "/api/snajp-support/kvitton";
const PERIOD = 4;
const VECKOR = 12;

const T = {
  utlagg: { sv: "Utlägg", en: "Expenses" },
  attGranska: { sv: "Att granska", en: "To review" },
  vantarPaDig: { sv: "väntar på ditt ja", en: "waiting for your yes" },
  prioriterad1: { sv: "prioriterad", en: "priority" },
  prioriterade: { sv: "prioriterade", en: "priority" },
  moms: { sv: "Ingående moms", en: "Input VAT" },
  kvitton: { sv: "Inlästa kvitton", en: "Receipts read" },
  franMejl: { sv: "från mejlen", en: "from email" },
  uppladdade: { sv: "uppladdade", en: "uploaded" },
  aktivitet: { sv: "Utlägg per vecka", en: "Expenses per week" },
  ingenAktivitet: { sv: "Inga kvitton att visa än.", en: "No receipts to show yet." },
  snitt: { sv: "Snittkvitto", en: "Average receipt" },
  storsta: { sv: "Största utlägget", en: "Largest expense" },
  utanHjalp: { sv: "Lästa utan anmärkning", en: "Read without remarks" },
  fordelning: { sv: "Fördelning", en: "Breakdown" },
  fordelningText: { sv: "Senaste fyra veckorna.", en: "Last four weeks." },
  perKategori: { sv: "Utlägg per kategori", en: "Expenses by category" },
  granskning: { sv: "Granskning", en: "Review" },
  krMitt: { sv: "kr", en: "SEK" },
  kvittonMitt: { sv: "kvitton", en: "receipts" },
  granskaRubrik: { sv: "Kvitton att granska", en: "Receipts to review" },
  ingaAttGranska: { sv: "Inget väntar på dig. Alla kvitton är avlästa.", en: "Nothing is waiting for you. Every receipt has been read." },
  visaAlla: { sv: "Visa alla", en: "Show all" },
  visaFarre: { sv: "Visa färre", en: "Show fewer" },
  godkann: { sv: "Godkänn", en: "Approve" },
  momsRubrik: { sv: "Ingående moms per sats", en: "Input VAT by rate" },
  momsText: {
    sv: "Underlaget till momsdeklarationen, senaste fyra veckorna. Stäm av med din redovisningskonsult.",
    en: "The basis for your VAT return, last four weeks. Check it with your accountant."
  },
  brutto: { sv: "brutto", en: "gross" },
  summa: { sv: "Summa", en: "Total" },
  senaste: { sv: "Senaste kvittona", en: "Latest receipts" },
  senasteText: { sv: "Med status i samma färger som kvittotabellen.", en: "With status in the same colours as the receipt table." },
  allaKvitton: { sv: "Alla kvitton", en: "All receipts" },
  leverantorer: { sv: "Leverantörer", en: "Suppliers" },
  leverantorerText: { sv: "Vart pengarna gått de senaste tolv veckorna.", en: "Where the money went over the last twelve weeks." },
  obetalda: { sv: "Obetalda fakturor", en: "Unpaid invoices" },
  forfaller: { sv: "förfaller", en: "due" },
  iKorthet: { sv: "I korthet", en: "In short" },
  kopplad: { sv: "Kopplad inkorg:", en: "Connected mailbox:" },
  ingenInkorg: { sv: "Ingen inkorg kopplad.", en: "No mailbox connected." },
  skanna: { sv: "Skanna och ladda upp", en: "Scan and upload" },
  avlasning: { sv: "Avläsning", en: "Reading" },
  avlasningText: {
    sv: "Syns bara för Snajp-admin. Hur ofta agenten läser kvittona utan hjälp, och vad som stoppar den.",
    en: "Visible to Snajp admins only. How often the agent reads receipts unaided, and what stops it."
  },
  utanAnmarkning: { sv: "utan anmärkning, tolv veckor", en: "without remarks, twelve weeks" },
  vanligasteFlaggor: { sv: "Vanligaste flaggorna", en: "Most common flags" },
  ingaFlaggor: { sv: "Inga flaggor de senaste tolv veckorna.", en: "No flags in the last twelve weeks." },
  utanKategori: { sv: "Utan kategori", en: "No category" },
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

function oreTillStrang(n: number): string {
  const tecken = n < 0 ? "-" : "";
  const a = Math.abs(n);
  return `${tecken}${Math.floor(a / 100)}.${String(a % 100).padStart(2, "0")}`;
}

function helaKronor(n: number, locale: "sv" | "en"): string {
  return `${new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: 0 }).format(Math.round(n / 100))} kr`;
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

type Statistik = {
  veckor: Vecka[];
  klara: Kvitto[];
  granska: Kvitto[];
  period: Kvitto[];
  forra: Kvitto[];
  utlaggNu: number;
  utlaggForra: number;
  momsNu: number;
  momsForra: number;
};

function berakna(kvitton: Kvitto[], idag: string): Statistik {
  const man = mandagar(idag);
  const index = new Map(man.map((m, i) => [m, i]));
  const veckor: Vecka[] = man.map((m) => ({ week: `v${isoVecka(m)}`, utlagg: 0, moms: 0, kvitton: 0 }));
  const utlaggOre = Array<number>(VECKOR).fill(0);
  const momsOreV = Array<number>(VECKOR).fill(0);
  const klara = kvitton.filter((k) => k.status === "klar");
  const granska = kvitton.filter((k) => k.status !== "klar");
  const veckaAv = (k: Kvitto) => (k.datum ? index.get(mandagFor(k.datum)) : undefined);

  for (const k of kvitton) {
    const i = veckaAv(k);
    if (i === undefined) continue;
    veckor[i].kvitton = (veckor[i].kvitton ?? 0) + 1;
    if (k.status !== "klar") continue;
    utlaggOre[i] += ore(k.brutto) ?? 0;
    momsOreV[i] += momsOre(k);
  }
  veckor.forEach((v, i) => {
    v.utlagg = Math.round(utlaggOre[i] / 100);
    v.moms = Math.round(momsOreV[i] / 100);
  });

  const start = VECKOR - PERIOD;
  const iPerioden = (k: Kvitto, fran: number, till: number) => {
    const i = veckaAv(k);
    return i !== undefined && i >= fran && i < till;
  };
  const period = kvitton.filter((k) => iPerioden(k, start, VECKOR));
  const forra = kvitton.filter((k) => iPerioden(k, start - PERIOD, start));
  const sum = (rader: Kvitto[], f: (k: Kvitto) => number) => rader.filter((k) => k.status === "klar").reduce((s, k) => s + f(k), 0);

  return {
    veckor,
    klara,
    granska,
    period,
    forra,
    utlaggNu: sum(period, (k) => ore(k.brutto) ?? 0),
    utlaggForra: sum(forra, (k) => ore(k.brutto) ?? 0),
    momsNu: sum(period, momsOre),
    momsForra: sum(forra, momsOre)
  };
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

function belopp(rad: Kvitto): string {
  return rad.brutto !== null ? kronor(rad.brutto) : (rad.belopp_original ?? "–");
}

/** Granskningsrutan: tre mest angelägna, fäll ut till alla, godkänn på raden. */
function GranskaRuta({
  rader,
  onGodkann
}: Readonly<{ rader: Kvitto[]; onGodkann: (rad: Kvitto) => Promise<void> }>) {
  const { text, locale } = useLocale();
  const [alla, setAlla] = useState(false);
  const [oppen, setOppen] = useState<string | null>(null);
  const [arbetar, setArbetar] = useState<string | null>(null);
  const sorterade = [...rader].sort(
    (a, b) => granskningsordning(a) - granskningsordning(b) || (b.datum ?? "").localeCompare(a.datum ?? "")
  );
  const visade = alla ? sorterade : sorterade.slice(0, 3);

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
                    <span className="block truncate text-[0.9375rem] font-medium">
                      {rad.motpart || rad.mejl_amne || rad.filnamn || text(T.kvitto)}
                    </span>
                    <span className={cn(meta, "block truncate")}>
                      {[datumKort(rad.datum, locale), text(kategoriAv(rad))].join(" · ")}
                      <span className="num tabular-nums sm:hidden"> · {belopp(rad)}</span>
                    </span>
                  </span>
                  <span className="num hidden shrink-0 text-[0.8125rem] tabular-nums text-ink-muted sm:inline">{belopp(rad)}</span>
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
                    <button
                      type="button"
                      disabled={arbetar === rad.id}
                      onClick={async () => {
                        setArbetar(rad.id);
                        try {
                          await onGodkann(rad);
                        } finally {
                          setArbetar(null);
                        }
                      }}
                      className={cn(btnPrimary, btnLiten, "mt-2.5")}
                    >
                      {text(T.godkann)}
                    </button>
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

/** Horisontella staplar per momssats. Talet står alltid vid stapeln. */
function MomsRuta({ period }: Readonly<{ period: Kvitto[] }>) {
  const { text, locale } = useLocale();
  const klara = period.filter((k) => k.status === "klar");
  const rader = SATSER.map((s) => {
    const deras = klara.filter((k) => normaliseradSats(k.momssats) === s.sats);
    return {
      ...s,
      moms: deras.reduce((a, k) => a + momsOre(k), 0),
      brutto: deras.reduce((a, k) => a + (ore(k.brutto) ?? 0), 0),
      antal: deras.length
    };
  });
  const storst = Math.max(1, ...rader.map((r) => r.brutto));
  const totalMoms = rader.reduce((a, r) => a + r.moms, 0);
  return (
    <section aria-labelledby="kvitto-moms" className={cn(kort, "min-w-0")}>
      <h2 id="kvitto-moms" className="text-[1rem] font-semibold">
        {text(T.momsRubrik)}
      </h2>
      <p className={cn(meta, "mb-4 mt-1")}>{text(T.momsText)}</p>
      <ul className="space-y-2.5">
        {rader.map((r, i) => (
          <li key={r.sats} className="grid grid-cols-[3rem_1fr_auto] items-center gap-3 text-[0.8125rem]">
            <span className="num tabular-nums text-ink-muted">{r.etikett}</span>
            <span className="h-2.5 overflow-hidden rounded-full bg-ink/[0.06]">
              <span
                className="block h-full rounded-full"
                style={{ width: `${(r.brutto / storst) * 100}%`, background: `oklch(var(--chart-ramp-${6 - i}))` }}
              />
            </span>
            <span className="num text-right tabular-nums">
              <span className="font-medium text-ink">{helaKronor(r.moms, locale)}</span>
              <span className="ml-1.5 text-ink-subtle">
                {helaKronor(r.brutto, locale)} {text(T.brutto)}
              </span>
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-4 flex items-baseline justify-between gap-4 border-t border-ink/10 pt-3 text-[0.875rem]">
        <span className="text-ink-muted">{text(T.summa)}</span>
        <span className="num font-semibold tabular-nums text-ink">{kronor(oreTillStrang(totalMoms))}</span>
      </p>
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
              <span className="block truncate text-[0.9375rem] font-medium">
                {rad.motpart || rad.mejl_amne || rad.filnamn || text(T.kvitto)}
              </span>
              <span className={cn(meta, "block truncate")}>
                {text(kategoriAv(rad))} · {datumKort(rad.datum, locale)} ·{" "}
                {rad.kalla === "mejl" ? text({ sv: "Mejl", en: "Email" }) : text({ sv: "Uppladdad", en: "Uploaded" })}
              </span>
            </span>
            <span className="flex shrink-0 items-center gap-4">
              <span className="num text-[0.875rem] font-medium tabular-nums">{belopp(rad)}</span>
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

function Leverantorer({ klara, obetalda }: Readonly<{ klara: Kvitto[]; obetalda: Kvitto[] }>) {
  const { text, locale } = useLocale();
  const per = new Map<string, { namn: string; antal: number; summa: number }>();
  for (const k of klara) {
    const namn = k.motpart || k.filnamn || "–";
    const post = per.get(namn) ?? { namn, antal: 0, summa: 0 };
    post.antal += 1;
    post.summa += ore(k.brutto) ?? 0;
    per.set(namn, post);
  }
  const lista = [...per.values()].sort((a, b) => b.summa - a.summa).slice(0, 8);
  const total = klara.reduce((s, k) => s + (ore(k.brutto) ?? 0), 0) || 1;
  return (
    <div className="grid gap-6">
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
              <span className="block h-full rounded-full bg-chart-blue" style={{ width: `${(l.summa / total) * 100}%` }} />
            </span>
          </li>
        ))}
      </ul>
      {obetalda.length ? (
        <div>
          <p className={etikett}>{text(T.obetalda)}</p>
          <ul className="mt-2 divide-y divide-ink/10">
            {obetalda.map((k) => (
              <li key={k.id} className="flex items-baseline justify-between gap-4 py-2 text-[0.8125rem]">
                <span className="min-w-0 truncate text-ink-muted">{k.motpart || k.filnamn}</span>
                <span className="num shrink-0 tabular-nums text-ink-subtle">
                  {text(T.forfaller)} {datumKort(k.forfallodatum ?? null, locale)}
                </span>
                <span className="num w-24 shrink-0 text-right font-medium tabular-nums text-ink">{belopp(k)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
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
    { etikett: T.utanKategori, varde: String(kvitton.filter((k) => !k.kategori).length) },
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
  const [godkannFel, setGodkannFel] = useState<Localized | null>(null);

  const s = useMemo(() => (kvitton ? berakna(kvitton, idag) : null), [kvitton, idag]);

  async function godkann(rad: Kvitto) {
    setGodkannFel(null);
    if (arDemo) {
      // Demon har ingen backend: godkännandet flyttar bara raden lokalt.
      setKvitton((nu) => (nu ?? []).map((k) => (k.id === rad.id ? { ...k, status: "klar", flaggor: [] } : k)));
      return;
    }
    const utfall = await godkannKvitto(rad, text);
    if (utfall === "avbrutet") return;
    if (utfall) setGodkannFel(utfall);
    await ladda();
  }

  const perioden: Localized = { sv: `de ${PERIOD} veckorna före`, en: `the ${PERIOD} weeks before` };
  const detalj: Localized = { sv: `senaste ${PERIOD} veckorna`, en: `last ${PERIOD} weeks` };
  const serie = (k: keyof Vecka) => (s ? s.veckor.slice(-8).map((v) => Number(v[k] ?? 0)) : undefined);

  const prioriterade = s ? s.granska.filter((k) => k.granskningsstatus === PRIORITERAD).length : 0;
  const franMejl = s ? s.period.filter((k) => k.kalla === "mejl").length : 0;

  const kpier: Kpi[] = [
    {
      id: "utlagg",
      etikett: T.utlagg,
      varde: null,
      visning: s ? helaKronor(s.utlaggNu, locale) : "–",
      forandring: s ? forandring(s.utlaggNu, s.utlaggForra) : undefined,
      battre: "ner",
      serie: serie("utlagg"),
      detalj
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
    },
    {
      id: "moms",
      etikett: T.moms,
      varde: null,
      visning: s ? helaKronor(s.momsNu, locale) : "–",
      forandring: s ? forandring(s.momsNu, s.momsForra) : undefined,
      battre: "ner",
      serie: serie("moms"),
      detalj
    },
    {
      id: "kvitton",
      etikett: T.kvitton,
      varde: s ? s.period.length : null,
      forandring: s ? forandring(s.period.length, s.forra.length) : undefined,
      serie: serie("kvitton"),
      detalj: s
        ? {
            sv: `${franMejl} ${T.franMejl.sv} · ${s.period.length - franMejl} ${T.uppladdade.sv}`,
            en: `${franMejl} ${T.franMejl.en} · ${s.period.length - franMejl} ${T.uppladdade.en}`
          }
        : detalj
    }
  ];

  // Fördelningarna: periodens klara kvitton per kategori (kronor), och
  // periodens kvitton per granskningsläge (antal).
  const periodKlara = s ? s.period.filter((k) => k.status === "klar") : [];
  const perKategori = new Map<string, { etikett: Localized; ore: number }>();
  for (const k of periodKlara) {
    const nyckel = k.kategori ?? "";
    const post = perKategori.get(nyckel) ?? { etikett: kategoriAv(k), ore: 0 };
    post.ore += ore(k.brutto) ?? 0;
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
  const statusdelar: Andel[] = [
    { id: "klar", etikett: T.klar, farg: "oklch(var(--moss))" },
    { id: "granska", etikett: T.granska, farg: "oklch(var(--chart-ochre))" },
    { id: "hamta", etikett: T.hamtaSjalv, farg: "oklch(var(--chart-blue))" },
    { id: "prioriterad", etikett: T.prioriterad, farg: "oklch(var(--danger))" }
  ].map((d) => ({ ...d, antal: s ? s.period.filter((k) => statusAv(k) === d.id).length : 0 }));

  const storsta = periodKlara.reduce<Kvitto | null>((a, k) => (!a || (ore(k.brutto) ?? 0) > (ore(a.brutto) ?? 0) ? k : a), null);
  const medGranskning = s ? s.period.filter((k) => k.granskningsstatus) : [];
  const nyckeltal: { etikett: Localized; varde: string; under?: string }[] = [
    { etikett: T.snitt, varde: periodKlara.length && s ? helaKronor(s.utlaggNu / periodKlara.length, locale) : "–" },
    {
      etikett: T.storsta,
      varde: storsta ? helaKronor(ore(storsta.brutto) ?? 0, locale) : "–",
      under: storsta?.motpart ?? undefined
    },
    {
      etikett: T.utanHjalp,
      varde: medGranskning.length
        ? procent(medGranskning.filter((k) => k.status === "klar" && (k.flaggor ?? []).length === 0).length / medGranskning.length, locale)
        : "–"
    }
  ];

  // I korthet: en mening ur talen ovan, på båda språken. Ingen modell.
  const toppKategori = kategorier[0];
  const korthetsdelar: Localized[] =
    s && periodKlara.length
      ? [
          {
            sv: `${periodKlara.length} avlästa kvitton på ${helaKronor(s.utlaggNu, "sv")} de senaste fyra veckorna, varav ${helaKronor(s.momsNu, "sv")} ingående moms.`,
            en: `${periodKlara.length} receipts read for ${helaKronor(s.utlaggNu, "en")} over the last four weeks, including ${helaKronor(s.momsNu, "en")} input VAT.`
          },
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
                  sv: `${s.granska.length} kvitton väntar på granskning och räknas inte in förrän du godkänt dem.`,
                  en: `${s.granska.length} receipts are waiting for review and are not counted until you approve them.`
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
        .filter((k) => k.betalstatus === "obetald" && k.forfallodatum)
        .sort((a, b) => (a.forfallodatum ?? "").localeCompare(b.forfallodatum ?? ""))
    : [];
  const harVeckor = s !== null && s.veckor.some((v) => (v.kvitton ?? 0) > 0);
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
          {text({ sv: "Kvittona gick inte att hämta just nu.", en: "The receipts could not be loaded right now." })}
        </p>
      ) : null}
      {godkannFel ? (
        <p role="alert" className="text-[0.875rem] text-danger">
          {text(godkannFel)}
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
                axelbredd={56}
                serier={[
                  { nyckel: "utlagg", etikett: { sv: "Utlägg, kr", en: "Expenses, SEK" }, ton: "chart-ochre" },
                  { nyckel: "moms", etikett: { sv: "Ingående moms, kr", en: "Input VAT, SEK" }, ton: "chart-blue" }
                ]}
              />
              <dl className="mt-5 grid grid-cols-1 gap-3 border-t border-ink/10 pt-4 sm:grid-cols-3 sm:gap-4">
                {nyckeltal.map((x) => (
                  <div key={x.etikett.sv} className="flex items-baseline justify-between gap-3 sm:block">
                    <dt className={etikett}>{text(x.etikett)}</dt>
                    <dd className="sm:mt-1">
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
              <Munkdiagram delar={kategoridelar} etikett={T.perKategori} mitt={T.krMitt} />
              <Munkdiagram delar={statusdelar} etikett={T.granskning} mitt={T.kvittonMitt} />
            </div>
          )}
        </section>
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <GranskaRuta rader={s?.granska ?? []} onGodkann={godkann} />
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
        <section aria-labelledby="kvitto-leverantorer" className={kolumn}>
          <h2 id="kvitto-leverantorer" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
            {text(T.leverantorer)}
          </h2>
          <p className={cn(meta, "mb-4 mt-1 max-w-[70ch]")}>{text(T.leverantorerText)}</p>
          {korthet ? (
            <div className="mb-5 rounded-input bg-paper2/50 px-3 py-2.5">
              <p className={etikett}>{text(T.iKorthet)}</p>
              <p className="mt-1 text-[0.875rem] leading-6 text-ink-muted">{text(korthet)}</p>
            </div>
          ) : null}
          {s ? <Leverantorer klara={s.klara} obetalda={obetalda} /> : <p className={meta}>…</p>}
        </section>
      </div>

      {(visaDrift || isPlatformAdmin) && kvitton ? <Avlasningsruta kvitton={kvitton} /> : null}
    </div>
  );
}
