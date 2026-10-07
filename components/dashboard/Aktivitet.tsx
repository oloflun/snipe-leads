"use client";

import { Loader2, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
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
  IrisKorningar,
  korningsTyp,
  pagar,
  statusText,
  utfallston,
  type KorningsRad
} from "@/components/leads/IrisKorningar";
import { Badge, btnLiten, btnSecondary, etikett, meta } from "@/components/ui";
import { isoVecka } from "@/lib/admin/statistik";
import { TOKENKOSTNAD_MODELL, tokenkostnad } from "@/lib/admin/halsa";
import { demoChattar, demoKorningar, demoUsage } from "@/lib/demo/aktivitet";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Aktivitet — alla agenters körningar på ett ställe (Snajp Suite 2026-10-03),
 * i översikternas layout sedan 2026-10-07 (Sebbes beställning: samma kolumner,
 * grafer och ringar som Leads, Kundtjänst och Kvitton).
 *
 *   nyckeltal (körningar, levererade leads, överlämningar, kostnad)
 *   pågår just nu (Iris körningar med förloppsstapel)
 *   Iris: beställt mot levererat per vecka · hur körningarna slutade och typ
 *   Iris körningar (tabellen, med styrning och detalj)
 *   Kundtjänst: körningar per vecka · dygnsbudget och kostnad
 *   överlämnade samtal | per dag   (split view)
 *
 * Datat är detsamma som de två gamla vyerna läste: Iris jobbliggare
 * (`GET /leads/korningar`, migration 080) och kundtjänstens journal
 * (`GET /usage`, `GET /chattar`). Usage hämtas för 60 dygn så att perioden
 * kan jämföras med perioden före. Kvitton har ingen körningsvy och står inte
 * här. Allt hämtas efter monteringen: relativa tider och demodatans
 * Date.now() får inte skilja mellan server och klient.
 */

// -- Svarets former (spegel av app/api/usage.py och /chattar) ------------------

export type Dagrad = {
  datum: string;
  korningar: number;
  korningar_test: number;
  tokens_in: number;
  tokens_out: number;
};

export type UsageSvar = {
  dagar: Dagrad[];
  budget: { tak: number; forbrukat_24h: number };
};

export type ChattRad = {
  customer_id: string;
  customer_name?: string | null;
  subject?: string | null;
  category?: string | null;
  channel?: string | null;
  overlamnad_at?: string | null;
  orsak_text?: string | null;
  aktiv?: boolean;
  is_test?: boolean;
};

// -- Texter -----------------------------------------------------------------------

const T = {
  korningar: { sv: "Körningar", en: "Runs" },
  korningarDetaljBada: { sv: "Iris och kundtjänsten", en: "Iris and customer service" },
  levererade: { sv: "Leads levererade", en: "Leads delivered" },
  leveransgrad: { sv: "Leveransgrad", en: "Delivery rate" },
  leveransgradDetalj: { sv: "levererade av beställda", en: "delivered of ordered" },
  pagarNu: { sv: "Pågår nu", en: "Running now" },
  overlamnade: { sv: "Till en människa", en: "To a human" },
  kostnad: { sv: "Uppskattad kostnad", en: "Estimated cost" },
  kostnadDetalj: { sv: "kundtjänstens tokens till listpris", en: "customer service tokens at list price" },
  budget: { sv: "Dygnsbudget", en: "Daily budget" },
  irisRubrik: { sv: "Iris, leadsagenten", en: "Iris, the leads agent" },
  supportRubrik: { sv: "Kundtjänsten", en: "Customer service" },
  irisPerVecka: { sv: "Beställt och levererat per vecka", en: "Ordered and delivered per week" },
  bestallt: { sv: "Beställda leads", en: "Leads ordered" },
  levereradeSerie: { sv: "Levererade leads", en: "Leads delivered" },
  ingaIris: { sv: "Inga Iris-körningar de senaste tolv veckorna.", en: "No Iris runs in the last twelve weeks." },
  leadsPerKorning: { sv: "Leads per körning", en: "Leads per run" },
  undersoktaPerLead: { sv: "Undersökta per lead", en: "Researched per lead" },
  fordelning: { sv: "Fördelning", en: "Breakdown" },
  hurSlutade: { sv: "Hur körningarna slutade", en: "How the runs ended" },
  typ: { sv: "Typ av körning", en: "Type of run" },
  korningarMitt: { sv: "körningar", en: "runs" },
  justNu: { sv: "Pågår just nu", en: "Running right now" },
  justNuText: {
    sv: "Körningen fortsätter på servern. Du kan lämna sidan och komma tillbaka.",
    en: "The run continues on the server. You can leave the page and come back."
  },
  leadsAv: { sv: "leads av", en: "leads of" },
  undersokta: { sv: "undersökta", en: "researched" },
  irisTabell: { sv: "Alla Iris-körningar", en: "All Iris runs" },
  irisTabellText: {
    sv: "Klicka på en körning för undersökta och bortvalda bolag. En pågående körning går att pausa och avbryta där.",
    en: "Click a run for researched and dropped companies. A running run can be paused and cancelled there."
  },
  supportPerVecka: { sv: "Körningar per vecka", en: "Runs per week" },
  supportKorningar: { sv: "Körningar", en: "Runs" },
  testkorningar: { sv: "Testkörningar", en: "Test runs" },
  ingaSupport: { sv: "Inga körningar de senaste åtta veckorna.", en: "No runs in the last eight weeks." },
  tokens: { sv: "Tokens", en: "Tokens" },
  perKorning: { sv: "Kostnad per körning", en: "Cost per run" },
  perDygn: { sv: "Körningar per dygn", en: "Runs per day" },
  budgetText: { sv: "tokens senaste dygnet", en: "tokens in the last 24 hours" },
  av: { sv: "av", en: "of" },
  ingetTak: { sv: "Inget dygnstak är satt för er arbetsyta.", en: "No daily cap is set for your workspace." },
  naraTaket: {
    sv: "Nära taket. Vid 100 % pausar agenten tills fönstret rullat vidare.",
    en: "Close to the cap. At 100 % the agent pauses until the window rolls forward."
  },
  listpris: { sv: "Listpris", en: "List price" },
  uppskattning: { sv: "En uppskattning, inte en faktura.", en: "An estimate, not an invoice." },
  overlamnadeRubrik: { sv: "Överlämnade samtal", en: "Handed-over conversations" },
  overlamnadeText: {
    sv: "Samtal agenten lämnat till en människa, senaste först.",
    en: "Conversations the agent handed to a human, latest first."
  },
  ingaOverlamningar: {
    sv: "Inga överlämningar. Agenten har hanterat samtalen själv.",
    en: "No handovers. The agent has handled the conversations on its own."
  },
  vantar: { sv: "Väntar på människa", en: "Waiting for a human" },
  avslutad: { sv: "Avslutad", en: "Closed" },
  samtalMitt: { sv: "samtal", en: "conversations" },
  okandKund: { sv: "Okänd kund", en: "Unknown customer" },
  perDag: { sv: "Per dag", en: "Per day" },
  perDagText: { sv: "Körningar, tokens och uppskattad kostnad.", en: "Runs, tokens and estimated cost." },
  test: { sv: "test", en: "test" },
  visaAlla: { sv: "Visa alla", en: "Show all" },
  visaFarre: { sv: "Visa färre", en: "Show fewer" },
  journalen: { sv: "Journalen", en: "The log" },
  supportFel: { sv: "Kundtjänstens journal gick inte att hämta.", en: "The customer service log could not be loaded." },
  irisFel: { sv: "Iris körningar gick inte att hämta.", en: "The Iris runs could not be loaded." },
  forsok: { sv: "Försök igen", en: "Try again" },
  inget: {
    sv: "Ingen av era agenter har körningar att visa här ännu.",
    en: "None of your agents has runs to show here yet."
  }
} satisfies Record<string, Localized>;

const UTFALL: { id: string; etikett: Localized; farg: string }[] = [
  { id: "ok", etikett: { sv: "Målet nått", en: "Target reached" }, farg: "oklch(var(--moss))" },
  { id: "under", etikett: { sv: "Klar, under målet", en: "Done, under target" }, farg: "oklch(var(--chart-ochre))" },
  { id: "stannade", etikett: { sv: "Stannade utan leads", en: "Stalled without leads" }, farg: "oklch(var(--danger))" },
  { id: "failed", etikett: { sv: "Misslyckades", en: "Failed" }, farg: "oklch(var(--ink))" },
  { id: "avbruten", etikett: { sv: "Avbruten", en: "Cancelled" }, farg: "oklch(var(--ink-subtle))" },
  { id: "pagar", etikett: { sv: "Pågår", en: "Running" }, farg: "oklch(var(--chart-blue))" },
  { id: "lista", etikett: { sv: "Leadslista klar", en: "Lead list done" }, farg: "oklch(var(--chart-ramp-3))" }
];

const TYPFARG = ["oklch(var(--chart-ramp-6))", "oklch(var(--chart-ramp-4))", "oklch(var(--chart-ramp-2))", "oklch(var(--ink-subtle))"];

const kort = "rounded-card border border-ink/12 bg-paper p-4 sm:p-5";
const rubrik = "text-[1rem] font-semibold";
const lankknapp =
  "focus-ring inline-flex items-center gap-1 text-[0.8125rem] font-medium text-ink-muted underline-offset-4 hover:text-ink hover:underline";

const PERIOD_DYGN = 28;
const DYGN = 86_400_000;

// -- Format -------------------------------------------------------------------------

type Sprak = "sv" | "en";

function talformat(locale: Sprak, decimaler = 0) {
  return new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: decimaler });
}

function kr(varde: number, locale: Sprak): string {
  return `${new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(varde)} kr`;
}

function sedan(iso: string, locale: Sprak): string {
  const minuter = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
  const rtf = new Intl.RelativeTimeFormat(locale === "en" ? "en-GB" : "sv-SE", { numeric: "auto" });
  if (minuter < 60) return rtf.format(-minuter, "minute");
  if (minuter < 1440) return rtf.format(-Math.round(minuter / 60), "hour");
  return rtf.format(-Math.round(minuter / 1440), "day");
}

function kortDatum(iso: string, locale: Sprak): string {
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "sv-SE", { weekday: "short", day: "numeric", month: "short" }).format(d);
}

// -- Veckor ---------------------------------------------------------------------------

/** Måndagarna för de `antal` senaste veckorna, äldst först, som lokal midnatt. */
function mandagar(antal: number): Date[] {
  const idag = new Date();
  const mandag = new Date(idag.getFullYear(), idag.getMonth(), idag.getDate() - ((idag.getDay() + 6) % 7));
  return Array.from({ length: antal }, (_, i) => new Date(mandag.getFullYear(), mandag.getMonth(), mandag.getDate() - (antal - 1 - i) * 7));
}

function veckoindex(start: Date[], tid: number): number {
  for (let i = start.length - 1; i >= 0; i--) {
    if (tid >= start[i].getTime()) return tid < start[i].getTime() + 7 * DYGN ? i : -1;
  }
  return -1;
}

function iPeriod(iso: string | null | undefined, fran: number, till: number): boolean {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  return t >= fran && t < till;
}

// -- Data -------------------------------------------------------------------------------

type Laddat = {
  korningar: KorningsRad[] | null;
  usage: UsageSvar | null;
  chattar: ChattRad[] | null;
  irisFel: boolean;
  supportFel: boolean;
  ejAktiverad: boolean;
};

function useAktivitet(demo: boolean, iris: boolean, support: boolean): Laddat & { ladda: () => void } {
  const [data, setData] = useState<Laddat>({
    korningar: null,
    usage: null,
    chattar: null,
    irisFel: false,
    supportFel: false,
    ejAktiverad: false
  });

  const ladda = useCallback(async () => {
    if (demo) {
      setData({
        korningar: iris ? demoKorningar() : [],
        usage: support ? demoUsage() : null,
        chattar: support ? demoChattar() : [],
        irisFel: false,
        supportFel: false,
        ejAktiverad: false
      });
      return;
    }
    const hamta = async <R,>(path: string): Promise<{ data: R | null; ejAktiverad: boolean }> => {
      try {
        const response = await fetch(`/api/snajp-support${path}`, { cache: "no-store" });
        const kropp = await readJsonBody<R & { offline?: boolean }>(response);
        if (!response.ok || kropp?.offline) return { data: null, ejAktiverad: arEjAktiverad(response.status, kropp) };
        return { data: kropp, ejAktiverad: false };
      } catch {
        return { data: null, ejAktiverad: false };
      }
    };
    const [k, u, c] = await Promise.all([
      iris ? hamta<{ korningar?: KorningsRad[] }>("/leads/korningar?limit=100") : Promise.resolve(null),
      support ? hamta<UsageSvar>("/usage?days=60") : Promise.resolve(null),
      support ? hamta<{ chattar?: ChattRad[] }>("/chattar") : Promise.resolve(null)
    ]);
    setData({
      korningar: k?.data ? (k.data.korningar ?? []) : iris ? null : [],
      usage: u?.data ?? null,
      chattar: c?.data ? (c.data.chattar ?? []) : support ? null : [],
      irisFel: Boolean(iris && !k?.data),
      supportFel: Boolean(support && (!u?.data || !c?.data) && !u?.ejAktiverad),
      ejAktiverad: Boolean(u?.ejAktiverad || c?.ejAktiverad)
    });
  }, [demo, iris, support]);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  // Körformuläret och tabellen sänder samma händelser när en körning rör sig.
  useEffect(() => {
    if (demo || !iris) return;
    const lyssnare = () => void ladda();
    window.addEventListener("snipra:leads-korning-klar", lyssnare);
    return () => window.removeEventListener("snipra:leads-korning-klar", lyssnare);
  }, [demo, iris, ladda]);

  return { ...data, ladda: () => void ladda() };
}

// -- Uträkningar ----------------------------------------------------------------------

type IrisTal = {
  nu: { korningar: number; levererade: number; bestallt: number; undersokta: number };
  forra: { korningar: number; levererade: number; bestallt: number };
  veckor: Vecka[];
  utfall: Andel[];
  typer: Andel[];
  pagaende: KorningsRad[];
};

function irisTal(rader: KorningsRad[]): IrisTal {
  const nu = Date.now();
  const fran = nu - PERIOD_DYGN * DYGN;
  const fore = fran - PERIOD_DYGN * DYGN;
  const summa = (lista: KorningsRad[]) => ({
    korningar: lista.length,
    levererade: lista.reduce((s, r) => s + (r.korning?.levererade ?? 0), 0),
    bestallt: lista.reduce((s, r) => s + (r.korning?.mal ?? 0), 0),
    undersokta: lista.reduce((s, r) => s + (r.korning?.undersokta ?? 0), 0)
  });
  const iNu = rader.filter((r) => iPeriod(r.created_at, fran, nu + DYGN));
  const iForra = rader.filter((r) => iPeriod(r.created_at, fore, fran));

  const start = mandagar(12);
  const veckor: Vecka[] = start.map((m) => ({ week: `v${isoVecka(new Date(Date.UTC(m.getFullYear(), m.getMonth(), m.getDate())))}`, bestallt: 0, levererade: 0, korningar: 0 }));
  for (const r of rader) {
    if (!r.created_at) continue;
    if (!r.korning) {
      const j = veckoindex(start, new Date(r.created_at).getTime());
      if (j >= 0) veckor[j].korningar = (veckor[j].korningar ?? 0) + 1;
      continue;
    }
    const i = veckoindex(start, new Date(r.created_at).getTime());
    if (i < 0) continue;
    veckor[i].korningar = (veckor[i].korningar ?? 0) + 1;
    veckor[i].bestallt = (veckor[i].bestallt ?? 0) + (r.korning.mal ?? 0);
    veckor[i].levererade = (veckor[i].levererade ?? 0) + (r.korning.levererade ?? 0);
  }

  const utfallAntal: Record<string, number> = {};
  for (const r of iNu) {
    const id =
      r.status === "failed"
        ? "failed"
        : pagar(r)
          ? "pagar"
          : r.scope === "lista"
            ? "lista"
            : r.korning?.slut_orsak === "avbruten"
              ? "avbruten"
              : utfallston(r);
    utfallAntal[id] = (utfallAntal[id] ?? 0) + 1;
  }
  const typAntal = new Map<string, { etikett: Localized; antal: number }>();
  for (const r of iNu) {
    const typ = korningsTyp(r);
    const post = typAntal.get(typ.sv) ?? { etikett: typ, antal: 0 };
    post.antal += 1;
    typAntal.set(typ.sv, post);
  }

  return {
    nu: summa(iNu),
    forra: summa(iForra),
    veckor,
    utfall: UTFALL.map((u) => ({ ...u, antal: utfallAntal[u.id] ?? 0 })),
    typer: [...typAntal.values()]
      .sort((a, b) => b.antal - a.antal)
      .map((t, i) => ({ id: t.etikett.sv, etikett: t.etikett, antal: t.antal, farg: TYPFARG[Math.min(i, TYPFARG.length - 1)] })),
    pagaende: rader.filter(pagar)
  };
}

type SupportTal = {
  nu: { korningar: number; test: number; tokensIn: number; tokensUt: number };
  forra: { korningar: number; tokensIn: number; tokensUt: number };
  veckor: Vecka[];
  /** Uppskattad kostnad per vecka i kronor, samma veckor som `veckor`. */
  kostnad: number[];
  dagar: Dagrad[];
};

function supportTal(usage: UsageSvar): SupportTal {
  const nu = Date.now();
  const fran = nu - PERIOD_DYGN * DYGN;
  const fore = fran - PERIOD_DYGN * DYGN;
  const tid = (d: Dagrad) => new Date(`${d.datum}T12:00:00`).getTime();
  const summa = (lista: Dagrad[]) => ({
    korningar: lista.reduce((s, d) => s + d.korningar, 0),
    test: lista.reduce((s, d) => s + d.korningar_test, 0),
    tokensIn: lista.reduce((s, d) => s + d.tokens_in, 0),
    tokensUt: lista.reduce((s, d) => s + d.tokens_out, 0)
  });
  const start = mandagar(8);
  const veckor: Vecka[] = start.map((m) => ({ week: `v${isoVecka(new Date(Date.UTC(m.getFullYear(), m.getMonth(), m.getDate())))}`, korningar: 0, korningar_test: 0 }));
  const kostnad = start.map(() => 0);
  for (const d of usage.dagar) {
    const i = veckoindex(start, tid(d));
    if (i < 0) continue;
    kostnad[i] += tokenkostnad(d.tokens_in, d.tokens_out);
    veckor[i].korningar = (veckor[i].korningar ?? 0) + d.korningar;
    veckor[i].korningar_test = (veckor[i].korningar_test ?? 0) + d.korningar_test;
  }
  return {
    nu: summa(usage.dagar.filter((d) => tid(d) >= fran)),
    forra: summa(usage.dagar.filter((d) => tid(d) >= fore && tid(d) < fran)),
    veckor,
    kostnad,
    dagar: [...usage.dagar].sort((a, b) => b.datum.localeCompare(a.datum)).filter((d) => tid(d) >= nu - 30 * DYGN)
  };
}

// -- Delar ----------------------------------------------------------------------------------

function Laddar({ hojd = "h-24" }: Readonly<{ hojd?: string }>) {
  return <div className={cn("animate-pulse rounded-input bg-ink/[0.05]", hojd)} aria-hidden />;
}

function Felruta({ besked, onForsok }: Readonly<{ besked: Localized; onForsok: () => void }>) {
  const { text } = useLocale();
  return (
    <div className={cn(kort, "flex flex-wrap items-center justify-between gap-4")}>
      <p className="text-[0.9375rem] text-ink-muted">{text(besked)}</p>
      <button type="button" onClick={onForsok} className={cn(btnSecondary, btnLiten)}>
        {text(T.forsok)}
      </button>
    </div>
  );
}

function Avsnitt({ id, titel, children }: Readonly<{ id: string; titel: Localized; children: React.ReactNode }>) {
  const { text } = useLocale();
  return (
    <section aria-labelledby={id} className="flex min-w-0 flex-col gap-4">
      <h2 id={id} className="mt-2 text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">
        {text(titel)}
      </h2>
      {children}
    </section>
  );
}

/** Förloppet för de körningar som pågår: levererade av beställda, som en fylld stapel. */
function PagarJustNu({ rader }: Readonly<{ rader: KorningsRad[] }>) {
  const { text, locale } = useLocale();
  return (
    <section aria-labelledby="aktivitet-pagar" className={cn(kort, "shadow-[inset_0_2px_0_0_oklch(var(--ochre))]")}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id="aktivitet-pagar" className={cn(rubrik, "inline-flex items-center gap-2")}>
          <Loader2 className="h-4 w-4 animate-spin text-ink-subtle" aria-hidden />
          {text(T.justNu)}
        </h2>
        <p className={meta}>{text(T.justNuText)}</p>
      </div>
      <ul className="mt-4 grid gap-4 md:grid-cols-2">
        {rader.map((r) => {
          const k = r.korning;
          const andel = k?.mal ? Math.min(1, k.levererade / k.mal) : 0;
          return (
            <li key={r.job_id} className="min-w-0" role="status" aria-live="polite">
              <div className="flex items-baseline justify-between gap-3">
                <span className="truncate text-[0.9375rem] font-medium">{text(korningsTyp(r))}</span>
                <span className="shrink-0 text-[0.8125rem] text-warning">{text(statusText(r))}</span>
              </div>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full bg-ink/[0.06]"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={k?.mal ?? 0}
                aria-valuenow={k?.levererade ?? 0}
                aria-label={text(T.levererade)}
              >
                <span className="block h-full rounded-full bg-chart-blue transition-[width]" style={{ width: `${Math.round(andel * 100)}%` }} />
              </div>
              <p className={cn(meta, "num mt-1.5 tabular-nums")}>
                {k
                  ? `${k.levererade} ${text(T.leadsAv)} ${k.mal} · ${k.undersokta} ${text(T.undersokta)}`
                  : "–"}
                {r.created_at ? ` · ${sedan(r.created_at, locale)}` : ""}
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function PerDag({ dagar }: Readonly<{ dagar: Dagrad[] }>) {
  const { text, locale } = useLocale();
  const [alla, setAlla] = useState(false);
  const fmt = talformat(locale);
  const storst = Math.max(1, ...dagar.map((d) => d.korningar + d.korningar_test));
  const visade = alla ? dagar : dagar.slice(0, 10);
  if (dagar.length === 0) return <p className={meta}>{text(T.ingaSupport)}</p>;
  return (
    <>
      <ul className="divide-y divide-ink/10">
        {visade.map((d) => (
          <li key={d.datum} className="grid grid-cols-[6.5rem_1fr_auto] items-center gap-3 py-2 text-[0.8125rem] sm:grid-cols-[7.5rem_1fr_5.5rem_5.5rem]">
            <span className="truncate text-ink-muted">{kortDatum(d.datum, locale)}</span>
            <span className="flex min-w-0 items-center gap-2">
              <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-ink/[0.06]">
                <span className="block h-full rounded-full bg-chart-blue" style={{ width: `${((d.korningar + d.korningar_test) / storst) * 100}%` }} />
              </span>
              <span className="num w-14 shrink-0 text-right font-medium tabular-nums text-ink">
                {fmt.format(d.korningar)}
                {d.korningar_test ? <span className="font-normal text-ink-subtle"> +{d.korningar_test}</span> : null}
              </span>
            </span>
            <span className="num hidden text-right tabular-nums text-ink-subtle sm:block">{fmt.format(d.tokens_in + d.tokens_out)}</span>
            <span className="num text-right tabular-nums text-ink-muted">{kr(tokenkostnad(d.tokens_in, d.tokens_out), locale)}</span>
          </li>
        ))}
      </ul>
      {dagar.length > 10 ? (
        <button type="button" onClick={() => setAlla((a) => !a)} aria-expanded={alla} className={cn(lankknapp, "mt-3")}>
          {alla ? text(T.visaFarre) : `${text(T.visaAlla)} (${dagar.length})`}
        </button>
      ) : null}
    </>
  );
}

// -- Vyn ----------------------------------------------------------------------------------------

export function Aktivitet({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { products } = useDashboard();
  const { text, locale } = useLocale();
  const iris = products.includes("leads");
  const support = products.includes("support");
  const { korningar, usage, chattar, irisFel, supportFel, ejAktiverad, ladda } = useAktivitet(demo, iris, support);

  if (!iris && !support) {
    return <p className="text-[0.9375rem] text-ink-muted">{text(T.inget)}</p>;
  }

  const it = korningar ? irisTal(korningar) : null;
  const st = usage ? supportTal(usage) : null;
  const fmt = talformat(locale);
  const perioden: Localized = { sv: `de ${PERIOD_DYGN} dygnen före`, en: `the ${PERIOD_DYGN} days before` };
  const senaste: Localized = { sv: `senaste ${PERIOD_DYGN} dygnen`, en: `last ${PERIOD_DYGN} days` };
  const med = (bas: Localized): Localized => ({ sv: `${bas.sv}, ${senaste.sv}`, en: `${bas.en}, ${senaste.en}` });

  // -- Nyckeltalen följer vilka agenter arbetsytan har ----------------------------
  const irisLaddad = !iris || it !== null || irisFel;
  const supportLaddad = !support || st !== null || supportFel || ejAktiverad;
  const allaKorningar = (it?.nu.korningar ?? 0) + (st?.nu.korningar ?? 0);
  const allaForra = (it?.forra.korningar ?? 0) + (st?.forra.korningar ?? 0);
  // Körningar per vecka, de åtta senaste: kundtjänstens och Iris summerade.
  const korningsserie =
    it || st
      ? Array.from({ length: 8 }, (_, i) => (st?.veckor[i]?.korningar ?? 0) + (it?.veckor[it.veckor.length - 8 + i]?.korningar ?? 0))
      : undefined;
  const aktivaSamtal = (chattar ?? []).filter((c) => c.aktiv).length;
  const overlamnadeNu = (chattar ?? []).filter((c) => iPeriod(c.overlamnad_at, Date.now() - PERIOD_DYGN * DYGN, Date.now() + DYGN)).length;
  const kostnadNu = st ? tokenkostnad(st.nu.tokensIn, st.nu.tokensUt) : null;
  const kostnadForra = st ? tokenkostnad(st.forra.tokensIn, st.forra.tokensUt) : null;
  const gradNu = it && it.nu.bestallt ? it.nu.levererade / it.nu.bestallt : null;
  const gradForra = it && it.forra.bestallt ? it.forra.levererade / it.forra.bestallt : null;

  const kpiKorningar: Kpi = {
    id: "korningar",
    etikett: T.korningar,
    varde: irisLaddad && supportLaddad ? allaKorningar : null,
    forandring: irisLaddad && supportLaddad ? forandring(allaKorningar, allaForra) : undefined,
    serie: korningsserie,
    detalj: iris && support ? med(T.korningarDetaljBada) : senaste
  };
  const kpiLevererade: Kpi = {
    id: "levererade",
    etikett: T.levererade,
    varde: it ? it.nu.levererade : null,
    forandring: it ? forandring(it.nu.levererade, it.forra.levererade) : undefined,
    serie: it?.veckor.slice(-8).map((v) => v.levererade ?? 0),
    detalj: it
      ? { sv: `av ${it.nu.bestallt} beställda, ${senaste.sv}`, en: `of ${it.nu.bestallt} ordered, ${senaste.en}` }
      : senaste
  };
  const kpiGrad: Kpi = {
    id: "grad",
    etikett: T.leveransgrad,
    varde: null,
    visning: it ? (gradNu === null ? "–" : `${Math.round(gradNu * 100)} %`) : undefined,
    forandring: gradNu !== null && gradForra !== null ? Math.round((gradNu - gradForra) * 100) : undefined,
    forandringEnhet: "pe",
    detalj: med(T.leveransgradDetalj)
  };
  const kpiPagar: Kpi = {
    id: "pagar",
    etikett: T.pagarNu,
    varde: it ? it.pagaende.length : null,
    detalj: it?.pagaende.length
      ? { sv: "Iris arbetar, följ förloppet nedan", en: "Iris is working, follow the progress below" }
      : { sv: "ingen körning är igång", en: "no run is going" }
  };
  const kpiOverlamnade: Kpi = {
    id: "overlamnade",
    etikett: T.overlamnade,
    varde: chattar ? overlamnadeNu : null,
    larm: aktivaSamtal > 0,
    battre: "ner",
    detalj: aktivaSamtal
      ? { sv: `${aktivaSamtal} väntar på en människa nu`, en: `${aktivaSamtal} waiting for a human now` }
      : med({ sv: "överlämnade samtal", en: "handed-over conversations" })
  };
  const kpiKostnad: Kpi = {
    id: "kostnad",
    etikett: T.kostnad,
    varde: null,
    visning: kostnadNu === null ? undefined : kr(kostnadNu, locale),
    forandring: kostnadNu !== null && kostnadForra !== null ? forandring(kostnadNu, kostnadForra) : undefined,
    battre: "ner",
    serie: st?.kostnad,
    detalj: med(T.kostnadDetalj)
  };
  const budgetAndel = usage && usage.budget.tak > 0 ? usage.budget.forbrukat_24h / usage.budget.tak : null;
  const kpiBudget: Kpi = {
    id: "budget",
    etikett: T.budget,
    varde: null,
    visning: usage ? (budgetAndel === null ? "–" : `${Math.round(budgetAndel * 100)} %`) : undefined,
    larm: (budgetAndel ?? 0) >= 0.8,
    detalj: budgetAndel === null ? T.ingetTak : { sv: "av taket, senaste dygnet", en: "of the cap, last 24 hours" }
  };

  const kpier: Kpi[] =
    iris && support
      ? [kpiKorningar, kpiLevererade, kpiOverlamnade, kpiKostnad]
      : iris
        ? [kpiKorningar, kpiLevererade, kpiGrad, kpiPagar]
        : [kpiKorningar, kpiOverlamnade, kpiKostnad, kpiBudget];

  const irisNyckeltal: { id: string; etikett: Localized; varde: string }[] = [
    { id: "grad", etikett: T.leveransgrad, varde: gradNu === null ? "–" : `${Math.round(gradNu * 100)} %` },
    {
      id: "perKorning",
      etikett: T.leadsPerKorning,
      varde: it && it.nu.korningar ? talformat(locale, 1).format(it.nu.levererade / it.nu.korningar) : "–"
    },
    {
      id: "undersokta",
      etikett: T.undersoktaPerLead,
      varde: it && it.nu.levererade ? talformat(locale, 1).format(it.nu.undersokta / it.nu.levererade) : "–"
    }
  ];

  const supportNyckeltal: { id: string; etikett: Localized; varde: string }[] = st
    ? [
        { id: "tokens", etikett: T.tokens, varde: fmt.format(st.nu.tokensIn + st.nu.tokensUt) },
        {
          id: "perKorning",
          etikett: T.perKorning,
          varde: st.nu.korningar ? kr(tokenkostnad(st.nu.tokensIn, st.nu.tokensUt) / st.nu.korningar, locale) : "–"
        },
        { id: "perDygn", etikett: T.perDygn, varde: talformat(locale, 1).format(st.nu.korningar / PERIOD_DYGN) }
      ]
    : [];

  const harIris = Boolean(it && it.veckor.some((v) => (v.bestallt ?? 0) > 0));
  const harSupport = Boolean(st && st.veckor.some((v) => (v.korningar ?? 0) + (v.korningar_test ?? 0) > 0));
  const kolumn = cn(kort, "relative min-w-0 thin-scrollbar xl:max-h-[40rem] xl:overflow-y-auto");

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={perioden} />
        ))}
      </div>

      {it && it.pagaende.length > 0 ? <PagarJustNu rader={it.pagaende} /> : null}

      {iris ? (
        <Avsnitt id="aktivitet-iris" titel={T.irisRubrik}>
          {irisFel ? (
            <Felruta besked={T.irisFel} onForsok={ladda} />
          ) : (
            <>
              <div className="grid min-w-0 gap-4 lg:grid-cols-12">
                <section aria-labelledby="aktivitet-iris-vecka" className={cn(kort, "min-w-0 lg:col-span-7")}>
                  <h3 id="aktivitet-iris-vecka" className={cn(rubrik, "mb-4")}>
                    {text(T.irisPerVecka)}
                  </h3>
                  {it === null ? (
                    <Laddar hojd="h-64" />
                  ) : harIris ? (
                    <Aktivitetsgraf
                      veckor={it.veckor}
                      serier={[
                        { nyckel: "bestallt", etikett: T.bestallt, ton: "chart-ochre" },
                        { nyckel: "levererade", etikett: T.levereradeSerie, ton: "chart-blue" }
                      ]}
                    />
                  ) : (
                    <p className={meta}>{text(T.ingaIris)}</p>
                  )}
                  <dl className="mt-5 grid grid-cols-1 gap-3 border-t border-ink/10 pt-4 sm:grid-cols-3 sm:gap-4">
                    {irisNyckeltal.map((x) => (
                      <div key={x.id} className="flex items-baseline justify-between gap-3 sm:block">
                        <dt className={etikett}>{text(x.etikett)}</dt>
                        <dd className="num text-[1.25rem] font-semibold tabular-nums text-ink sm:mt-1">{x.varde}</dd>
                      </div>
                    ))}
                  </dl>
                  <p className={cn(meta, "mt-3")}>{text(senaste)}</p>
                </section>
                <section aria-labelledby="aktivitet-iris-fordelning" className={cn(kort, "min-w-0 lg:col-span-5")}>
                  <h3 id="aktivitet-iris-fordelning" className={cn(rubrik, "mb-4")}>
                    {text(T.fordelning)}
                    <span className={cn(meta, "ml-2 font-normal")}>{text(senaste)}</span>
                  </h3>
                  {it === null ? (
                    <Laddar hojd="h-64" />
                  ) : (
                    <div className="grid gap-6">
                      <Munkdiagram delar={it.utfall} etikett={T.hurSlutade} mitt={T.korningarMitt} />
                      <Munkdiagram delar={it.typer} etikett={T.typ} mitt={T.korningarMitt} />
                    </div>
                  )}
                </section>
              </div>

              <section aria-labelledby="aktivitet-iris-tabell" className={cn(kort, "min-w-0")}>
                <h3 id="aktivitet-iris-tabell" className={rubrik}>
                  {text(T.irisTabell)}
                </h3>
                <p className={cn(meta, "mb-3 mt-1 max-w-[70ch]")}>{text(T.irisTabellText)}</p>
                {demo ? korningar ? <IrisKorningar demoRader={korningar} tak={8} /> : <Laddar hojd="h-48" /> : <IrisKorningar tak={8} />}
              </section>
            </>
          )}
        </Avsnitt>
      ) : null}

      {support ? (
        <Avsnitt id="aktivitet-kundtjanst" titel={T.supportRubrik}>
          {ejAktiverad ? (
            <EjAktiverad yta={text(T.journalen)} />
          ) : supportFel ? (
            <Felruta besked={T.supportFel} onForsok={ladda} />
          ) : (
            <>
              <div className="grid min-w-0 gap-4 lg:grid-cols-12">
                <section aria-labelledby="aktivitet-support-vecka" className={cn(kort, "min-w-0 lg:col-span-7")}>
                  <h3 id="aktivitet-support-vecka" className={cn(rubrik, "mb-4")}>
                    {text(T.supportPerVecka)}
                  </h3>
                  {st === null ? (
                    <Laddar hojd="h-64" />
                  ) : harSupport ? (
                    <Aktivitetsgraf
                      veckor={st.veckor}
                      axelbredd={52}
                      serier={[
                        { nyckel: "korningar", etikett: T.supportKorningar, ton: "chart-blue" },
                        { nyckel: "korningar_test", etikett: T.testkorningar, ton: "chart-ochre" }
                      ]}
                    />
                  ) : (
                    <p className={meta}>{text(T.ingaSupport)}</p>
                  )}
                  {st ? (
                    <>
                      <dl className="mt-5 grid grid-cols-1 gap-3 border-t border-ink/10 pt-4 sm:grid-cols-3 sm:gap-4">
                        {supportNyckeltal.map((x) => (
                          <div key={x.id} className="flex items-baseline justify-between gap-3 sm:block">
                            <dt className={etikett}>{text(x.etikett)}</dt>
                            <dd className="num text-[1.25rem] font-semibold tabular-nums text-ink sm:mt-1">{x.varde}</dd>
                          </div>
                        ))}
                      </dl>
                      <p className={cn(meta, "mt-3")}>
                        {text(senaste)}. {text(T.listpris)} {TOKENKOSTNAD_MODELL}. {text(T.uppskattning)}
                      </p>
                    </>
                  ) : null}
                </section>

                <section aria-labelledby="aktivitet-budget" className={cn(kort, "min-w-0 lg:col-span-5")}>
                  <h3 id="aktivitet-budget" className={cn(rubrik, "mb-4")}>
                    {text(T.budget)}
                  </h3>
                  {usage === null ? (
                    <Laddar hojd="h-32" />
                  ) : budgetAndel === null ? (
                    <p className={meta}>{text(T.ingetTak)}</p>
                  ) : (
                    <div className="flex items-center gap-4">
                      <Andelsring andel={Math.min(1, budgetAndel)} etikett={text(T.budget)} />
                      <div className="min-w-0">
                        <p className="num text-[0.9375rem] font-medium tabular-nums">
                          {fmt.format(usage.budget.forbrukat_24h)} {text(T.av)} {fmt.format(usage.budget.tak)}
                        </p>
                        <p className={meta}>{text(T.budgetText)}</p>
                        {budgetAndel >= 0.8 ? <p className="mt-2 text-[0.8125rem] leading-5 text-danger">{text(T.naraTaket)}</p> : null}
                      </div>
                    </div>
                  )}
                  <div className="mt-6 border-t border-ink/10 pt-4">
                    {chattar === null ? <Laddar hojd="h-28" /> : (
                      <Munkdiagram
                        delar={[
                          { id: "vantar", etikett: T.vantar, antal: aktivaSamtal, farg: "oklch(var(--chart-ochre))" },
                          { id: "avslutad", etikett: T.avslutad, antal: chattar.length - aktivaSamtal, farg: "oklch(var(--moss))" }
                        ]}
                        etikett={T.overlamnadeRubrik}
                        mitt={T.samtalMitt}
                      />
                    )}
                  </div>
                </section>
              </div>

              <div className="grid min-w-0 gap-4 xl:grid-cols-2">
                <section aria-labelledby="aktivitet-overlamnade" className={kolumn}>
                  <h3 id="aktivitet-overlamnade" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
                    {text(T.overlamnadeRubrik)}
                    {chattar?.length ? <span className="num ml-2 font-normal tabular-nums text-ink-subtle">{chattar.length}</span> : null}
                  </h3>
                  <p className={cn(meta, "mb-2 mt-1")}>{text(T.overlamnadeText)}</p>
                  {chattar === null ? <Laddar hojd="h-48" /> : <OverlamningsLista chattar={chattar} />}
                </section>
                <section aria-labelledby="aktivitet-perdag" className={kolumn}>
                  <h3 id="aktivitet-perdag" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
                    {text(T.perDag)}
                  </h3>
                  <p className={cn(meta, "mb-2 mt-1")}>{text(T.perDagText)}</p>
                  {st === null ? <Laddar hojd="h-48" /> : <PerDag dagar={st.dagar} />}
                </section>
              </div>
            </>
          )}
        </Avsnitt>
      ) : null}
    </div>
  );
}

/** Listan utan munken: munken står redan i budgetrutan ovanför. */
function OverlamningsLista({ chattar }: Readonly<{ chattar: ChattRad[] }>) {
  const { text, locale } = useLocale();
  const [alla, setAlla] = useState(false);
  const visade = alla ? chattar : chattar.slice(0, 8);
  if (chattar.length === 0) return <p className={meta}>{text(T.ingaOverlamningar)}</p>;
  return (
    <>
      <ul className="divide-y divide-ink/10">
        {visade.map((c) => (
          <li key={c.customer_id} className="flex items-center gap-3 py-2.5">
            <ShieldAlert className={cn("h-4 w-4 shrink-0", c.aktiv ? "text-warning" : "text-ink-subtle")} aria-hidden />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[0.9375rem] font-medium">
                {c.customer_name || c.subject || text(T.okandKund)}
                {c.is_test ? <span className={cn(meta, "ml-2 font-normal")}>{text(T.test)}</span> : null}
              </span>
              <span className={cn(meta, "block truncate")}>
                {[c.subject && c.customer_name ? c.subject : null, c.orsak_text, c.overlamnad_at ? sedan(c.overlamnad_at, locale) : null]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </span>
            <Badge tone={c.aktiv ? "warn" : "good"}>{text(c.aktiv ? T.vantar : T.avslutad)}</Badge>
          </li>
        ))}
      </ul>
      {chattar.length > 8 ? (
        <button type="button" onClick={() => setAlla((a) => !a)} aria-expanded={alla} className={cn(lankknapp, "mt-3")}>
          {alla ? text(T.visaFarre) : `${text(T.visaAlla)} (${chattar.length})`}
        </button>
      ) : null}
    </>
  );
}
