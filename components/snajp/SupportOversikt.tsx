"use client";

import { ArrowRight, BookOpen, ChevronDown } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { kostnadUsd } from "@/components/admin/AgentAnvandning";
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
import { btnLiten, btnSecondary, etikett, meta } from "@/components/ui";
import { grundmejl } from "@/lib/demo/support-inbox";
import { demoSupportOversikt } from "@/lib/demo/support-oversikt";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Kundtjänst › Översikt (Sebbes beställning 2026-10-07): Leads-översiktens
 * layout (components/leads/LeadsOversikt.tsx) anpassad för support.
 *
 *   nyckeltal: inkomna, utkast som väntar, besvarat av agenten, svarstid
 *   ärenden per vecka · munkdiagram för hur ärendena besvarades + kategori
 *   utkasten som väntar · svarstidsfördelningen
 *   senaste ärendena | kunskapsbasens träff och luckor   (split view)
 *   driften (körningar, tokens, uppskattad kostnad) för Snajp-admin
 *
 * Talen räknas i backenden (`GET /api/support/oversikt`,
 * snajp-support/app/support_oversikt.py) ur samma mejl som Ärenden visar.
 * Demon (/demo/support) matar samma form ur lib/demo/support-oversikt.ts, så
 * det finns EN rendering. Allt hämtas efter monteringen: relativa tider och
 * demodatans Date.now() får inte skilja mellan server och klient.
 *
 * Utkasten godkänns inte härifrån. Ett mejl till en riktig kund ska skickas
 * där hela ärendet står, så knappen öppnar Ärenden.
 */

// -- Svarets form (spegel av app/support_oversikt.py) --------------------------

type Period = {
  inkomna: number;
  auto: number;
  godkant: number;
  manniska: number;
  vantar: number;
  svarstid_median: number | null;
  inom_timme: number | null;
  kb_traff: number | null;
};

export type OversiktSvar = {
  period_dygn: number;
  veckor: { week: string; start: string; inkomna: number; besvarade: number; eskalerade: number; svarstid_median: number | null }[];
  nu: Period;
  forra: Period;
  kategorier: { id: string; antal: number; eskalerade: number }[];
  svarstider: { id: string; antal: number }[];
  vantande: { antal: number; aldsta: string | null };
  kb_luckor: { antal: number; rader: { id: string; titel: string; created_at: string }[] };
  drift: { korningar: number; tokens_in: number; tokens_out: number; cache: number; modell: string | null; kb_artiklar: number };
};

type Mejl = {
  id: string;
  subject: string | null;
  from_name: string | null;
  from_email: string;
  received_at: string;
  status: string;
  classification?: { category?: string | null } | null;
  draft?: { content?: string | null; confidence?: number | null } | null;
};

// -- Texter ---------------------------------------------------------------------

const T = {
  inkomna: { sv: "Inkomna ärenden", en: "Incoming cases" },
  vantar: { sv: "Utkast att godkänna", en: "Drafts to approve" },
  vantarPaDig: { sv: "väntar på ditt ja", en: "waiting for your yes" },
  aldsta: { sv: "äldsta", en: "oldest" },
  agentSvar: { sv: "Besvarat av agenten", en: "Answered by the agent" },
  agentSvarDetalj: { sv: "helt utan människa", en: "with no human involved" },
  svarstid: { sv: "Svarstid, median", en: "Response time, median" },
  svarstidDetalj: { sv: "till första svaret", en: "to the first reply" },
  aktivitet: { sv: "Ärenden per vecka", en: "Cases per week" },
  besvarade: { sv: "Besvarade", en: "Answered" },
  ingenAktivitet: { sv: "Inga ärenden de senaste tolv veckorna.", en: "No cases in the last twelve weeks." },
  fordelning: { sv: "Fördelning", en: "Breakdown" },
  hantering: { sv: "Hur ärendena besvarades", en: "How cases were answered" },
  kategori: { sv: "Kategori", en: "Category" },
  arendenMitt: { sv: "ärenden", en: "cases" },
  svarsfrekvens: { sv: "Svarsfrekvens", en: "Response rate" },
  inomTimme: { sv: "Svar inom en timme", en: "Replied within an hour" },
  tillManniska: { sv: "Till en människa", en: "To a human" },
  utkastRubrik: { sv: "Utkast som väntar", en: "Drafts waiting" },
  ingaUtkast: { sv: "Inga utkast väntar på dig.", en: "No drafts are waiting for you." },
  visaAlla: { sv: "Visa alla", en: "Show all" },
  visaFarre: { sv: "Visa färre", en: "Show fewer" },
  oppnaIArenden: { sv: "Öppna i Ärenden", en: "Open in Cases" },
  sakerhet: { sv: "säkerhet", en: "confidence" },
  svarstiderRubrik: { sv: "Svarstider", en: "Response times" },
  svarstiderText: { sv: "Tid till första svaret, per besvarat ärende.", en: "Time to the first reply, per answered case." },
  ingaSvar: { sv: "Inga besvarade ärenden i perioden än.", en: "No answered cases in the period yet." },
  arenden: { sv: "Senaste ärendena", en: "Latest cases" },
  arendenText: { sv: "Med status i samma färger som i Ärenden.", en: "With status in the same colours as in Cases." },
  ingaArenden: { sv: "Inga ärenden än. De dyker upp här när första mejlet kommer in.", en: "No cases yet. They appear here when the first email arrives." },
  allaArenden: { sv: "Alla ärenden", en: "All cases" },
  kbRubrik: { sv: "Kunskapsbasen", en: "The knowledge base" },
  kbTraff: { sv: "Hittade svar i kunskapsbasen", en: "Found an answer in the knowledge base" },
  artiklar: { sv: "artiklar", en: "articles" },
  luckorRubrik: { sv: "Luckor att fylla", en: "Gaps to fill" },
  luckorText: {
    sv: "Frågor agenten inte hittade svar på. Godkänn förslaget så besvaras nästa likadana fråga direkt.",
    en: "Questions the agent found no answer to. Approve the suggestion and the next one like it is answered right away."
  },
  ingaLuckor: { sv: "Inga luckor just nu.", en: "No gaps right now." },
  granska: { sv: "Granska", en: "Review" },
  eskaleringar: { sv: "Till en människa, per kategori", en: "To a human, by category" },
  drift: { sv: "Drift", en: "Operations" },
  driftText: { sv: "Syns bara för Snajp-admin.", en: "Visible to Snajp admins only." },
  korningar: { sv: "Supportkörningar", en: "Support runs" },
  perArende: { sv: "Körningar per ärende", en: "Runs per case" },
  kostnad: { sv: "Uppskattad kostnad", en: "Estimated cost" },
  kostnadPerArende: { sv: "per ärende", en: "per case" },
  cache: { sv: "Svar ur cachen", en: "Answers from cache" },
  modell: { sv: "Modell", en: "Model" },
  fel: { sv: "Översikten gick inte att hämta just nu.", en: "The overview could not be loaded right now." },
  forsok: { sv: "Försök igen", en: "Try again" }
} satisfies Record<string, Localized>;

const KATEGORI: Record<string, Localized> = {
  teknisk_support: { sv: "Teknisk support", en: "Technical support" },
  garanti: { sv: "Garanti", en: "Warranty" },
  leverans: { sv: "Leverans och frakt", en: "Delivery and shipping" },
  utbildning: { sv: "Användarstöd", en: "User help" },
  retur_reklamation: { sv: "Reklamation och retur", en: "Complaints and returns" },
  betalning: { sv: "Betalning och faktura", en: "Payment and invoice" },
  orderstatus: { sv: "Orderstatus", en: "Order status" },
  ovrigt: { sv: "Övrigt", en: "Other" },
  okand: { sv: "Ej klassad", en: "Not classified" }
};

function kategoriEtikett(id: string): Localized {
  if (KATEGORI[id]) return KATEGORI[id];
  // Kundens egna kategorier (regler i inställningarna) har inget översatt
  // namn; id:t är kundens eget ord och visas likadant på båda språken.
  const namn = id.replace(/_/g, " ");
  const versal = namn.charAt(0).toUpperCase() + namn.slice(1);
  return { sv: versal, en: versal };
}

const HINK: Record<string, Localized> = {
  "15m": { sv: "Under 15 min", en: "Under 15 min" },
  "1h": { sv: "15–60 min", en: "15–60 min" },
  "4h": { sv: "1–4 timmar", en: "1–4 hours" },
  "24h": { sv: "4–24 timmar", en: "4–24 hours" },
  mer: { sv: "Mer än ett dygn", en: "More than a day" }
};
const HINKFARG: Record<string, string> = {
  "15m": "oklch(var(--chart-ramp-6))",
  "1h": "oklch(var(--chart-ramp-4))",
  "4h": "oklch(var(--chart-ramp-2))",
  "24h": "oklch(var(--chart-ochre))",
  mer: "oklch(var(--danger))"
};

const ARENDESTATUS: Record<string, { etikett: Localized; prick: string; text: string }> = {
  new: { etikett: { sv: "Tas emot", en: "Arriving" }, prick: "bg-ink-subtle", text: "text-ink-muted" },
  processing: { etikett: { sv: "Agenten arbetar", en: "Agent working" }, prick: "bg-ink-subtle", text: "text-ink-muted" },
  awaiting_approval: { etikett: { sv: "Väntar på ditt ja", en: "Awaiting your yes" }, prick: "bg-ochre", text: "text-warning" },
  escalated: { etikett: { sv: "Eskalerat", en: "Escalated" }, prick: "bg-danger", text: "text-danger" },
  failed: { etikett: { sv: "Misslyckades", en: "Failed" }, prick: "bg-danger", text: "text-danger" },
  taken_over: { etikett: { sv: "Övertaget", en: "Taken over" }, prick: "bg-chart-blue", text: "text-ink-muted" },
  rejected: { etikett: { sv: "Utkast avvisat", en: "Draft rejected" }, prick: "bg-ink-subtle", text: "text-ink-muted" },
  auto_sent: { etikett: { sv: "Besvarat automatiskt", en: "Answered automatically" }, prick: "bg-moss", text: "text-ink-muted" },
  sent: { etikett: { sv: "Besvarat", en: "Answered" }, prick: "bg-moss", text: "text-ink-muted" }
};

const kort = "rounded-card border border-ink/12 bg-paper p-4 sm:p-5";
const rubrik = "text-[1rem] font-semibold";
const lankknapp =
  "focus-ring inline-flex items-center gap-1 text-[0.8125rem] font-medium text-ink-muted underline-offset-4 hover:text-ink hover:underline";

// -- Format ---------------------------------------------------------------------

type Sprak = "sv" | "en";

function procent(n: number | null, locale: Sprak): string {
  if (n === null) return "–";
  return `${new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: 0 }).format(n * 100)} %`;
}

function andel(del: number, helhet: number): number | null {
  return helhet > 0 ? del / helhet : null;
}

function varaktighet(minuter: number | null, locale: Sprak): string {
  if (minuter === null) return "–";
  const tal = new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: 1 });
  if (minuter < 60) return `${Math.round(minuter)} min`;
  if (minuter < 1440) return `${tal.format(minuter / 60)} ${locale === "en" ? "h" : "tim"}`;
  return `${tal.format(minuter / 1440)} ${locale === "en" ? "d" : "dygn"}`;
}

function sedan(iso: string, locale: Sprak): string {
  const minuter = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
  const rtf = new Intl.RelativeTimeFormat(locale === "en" ? "en-GB" : "sv-SE", { numeric: "auto" });
  if (minuter < 60) return rtf.format(-minuter, "minute");
  if (minuter < 1440) return rtf.format(-Math.round(minuter / 60), "hour");
  return rtf.format(-Math.round(minuter / 1440), "day");
}

/** Förändring i procentenheter för andelar; ingen pill när en period saknar grund. */
function enheter(nu: number | null, forra: number | null): number | undefined {
  if (nu === null || forra === null) return undefined;
  return Math.round((nu - forra) * 100);
}

// -- Data -------------------------------------------------------------------------

type Laddat = { svar: OversiktSvar | null; arenden: Mejl[] | null; utkast: Mejl[] | null; fel: boolean };

function useSupportOversikt(demo: boolean): Laddat & { ladda: () => void } {
  const [data, setData] = useState<Laddat>({ svar: null, arenden: null, utkast: null, fel: false });

  const ladda = useCallback(async () => {
    if (demo) {
      const mejl = grundmejl() as unknown as Mejl[];
      setData({
        svar: demoSupportOversikt(),
        arenden: mejl,
        utkast: mejl.filter((m) => m.status === "awaiting_approval"),
        fel: false
      });
      return;
    }
    const hamta = async <T,>(path: string): Promise<T | null> => {
      try {
        const response = await fetch(`/api/snajp-support${path}`, { cache: "no-store" });
        if (!response.ok) return null;
        return await readJsonBody<T>(response);
      } catch {
        return null;
      }
    };
    const [svar, arenden, utkast] = await Promise.all([
      hamta<OversiktSvar>("/support/oversikt"),
      hamta<{ emails?: Mejl[] }>("/inbox?limit=8"),
      hamta<{ emails?: Mejl[] }>("/inbox?status=awaiting_approval&limit=30")
    ]);
    setData({
      svar,
      arenden: arenden ? (arenden.emails ?? []) : [],
      utkast: utkast ? (utkast.emails ?? []) : [],
      fel: svar === null
    });
  }, [demo]);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  return { ...data, ladda: () => void ladda() };
}

// -- Delar ------------------------------------------------------------------------

function Laddar({ hojd = "h-24" }: Readonly<{ hojd?: string }>) {
  return <div className={cn("animate-pulse rounded-input bg-ink/[0.05]", hojd)} aria-hidden />;
}

function UtkastRuta({ utkast, onOppna }: Readonly<{ utkast: Mejl[] | null; onOppna?: () => void }>) {
  const { text, locale } = useLocale();
  const [alla, setAlla] = useState(false);
  const [oppen, setOppen] = useState<string | null>(null);
  const lista = utkast ?? [];
  const visade = alla ? lista : lista.slice(0, 3);

  return (
    <section aria-labelledby="support-utkast" className={cn(kort, "min-w-0")}>
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <h2 id="support-utkast" className={rubrik}>
          {text(T.utkastRubrik)}
          {lista.length ? <span className="num ml-2 font-normal tabular-nums text-ink-subtle">{lista.length}</span> : null}
        </h2>
        {lista.length > 3 ? (
          <button type="button" onClick={() => setAlla((a) => !a)} className={lankknapp}>
            {text(alla ? T.visaFarre : T.visaAlla)}
          </button>
        ) : null}
      </div>
      {utkast === null ? (
        <Laddar />
      ) : visade.length === 0 ? (
        <p className={meta}>{text(T.ingaUtkast)}</p>
      ) : (
        <ul className="divide-y divide-ink/10">
          {visade.map((m) => {
            const ar = oppen === m.id;
            return (
              <li key={m.id} className="py-2.5">
                <button
                  type="button"
                  onClick={() => setOppen(ar ? null : m.id)}
                  aria-expanded={ar}
                  className="focus-ring -mx-1.5 flex w-[calc(100%+0.75rem)] items-center gap-3 rounded-input px-1.5 py-1 text-left hover:bg-paper2/60"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[0.9375rem] font-medium">{m.subject || "–"}</span>
                    <span className={cn(meta, "block truncate")}>
                      {m.from_name || m.from_email} · {sedan(m.received_at, locale)}
                    </span>
                  </span>
                  {typeof m.draft?.confidence === "number" ? (
                    <span className="num shrink-0 text-[0.8125rem] tabular-nums text-ink-subtle" title={text(T.sakerhet)}>
                      {procent(m.draft.confidence, locale)}
                    </span>
                  ) : null}
                  <ChevronDown className={cn("h-4 w-4 shrink-0 text-ink-subtle transition-transform", ar && "rotate-180")} aria-hidden />
                </button>
                {ar ? (
                  <div className="mt-2.5">
                    {m.draft?.content ? (
                      <p className="thin-scrollbar max-h-48 overflow-y-auto whitespace-pre-wrap rounded-input border border-ink/12 bg-paper2/40 px-3 py-2.5 text-[0.875rem] leading-6 text-ink-muted">
                        {m.draft.content}
                      </p>
                    ) : null}
                    {onOppna ? (
                      <button type="button" onClick={onOppna} className={cn(btnSecondary, btnLiten, "mt-2.5")}>
                        {text(T.oppnaIArenden)}
                        <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    ) : null}
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

function Svarstider({ svar }: Readonly<{ svar: OversiktSvar | null }>) {
  const { text, locale } = useLocale();
  const hinkar = svar?.svarstider ?? [];
  const total = hinkar.reduce((s, h) => s + h.antal, 0);
  const storst = Math.max(1, ...hinkar.map((h) => h.antal));
  return (
    <section aria-labelledby="support-svarstider" className={cn(kort, "min-w-0")}>
      <h2 id="support-svarstider" className={rubrik}>
        {text(T.svarstiderRubrik)}
      </h2>
      <p className={cn(meta, "mb-4 mt-1")}>{text(T.svarstiderText)}</p>
      {svar === null ? (
        <Laddar hojd="h-32" />
      ) : total === 0 ? (
        <p className={meta}>{text(T.ingaSvar)}</p>
      ) : (
        <ul className="space-y-3">
          {hinkar.map((h) => (
            <li key={h.id} className="grid grid-cols-[6.5rem_1fr_4.75rem] items-center gap-3 text-[0.8125rem] sm:grid-cols-[7.5rem_1fr_5rem]">
              <span className="truncate text-ink-muted">{text(HINK[h.id] ?? { sv: h.id, en: h.id })}</span>
              <span className="h-2 overflow-hidden rounded-full bg-ink/[0.06]">
                <span
                  className="block h-full rounded-full"
                  style={{ width: h.antal ? `max(0.5rem, ${(h.antal / storst) * 100}%)` : 0, background: HINKFARG[h.id] }}
                />
              </span>
              <span className="num text-right tabular-nums">
                <span className="font-medium text-ink">{h.antal}</span>
                <span className="ml-1.5 inline-block w-9 text-ink-subtle">{procent(h.antal / total, locale)}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Arendelista({ arenden, onOppna }: Readonly<{ arenden: Mejl[] | null; onOppna?: () => void }>) {
  const { text, locale } = useLocale();
  if (arenden === null) return <Laddar hojd="h-48" />;
  if (arenden.length === 0) return <p className={meta}>{text(T.ingaArenden)}</p>;
  return (
    <>
      <ul className="divide-y divide-ink/10">
        {arenden.slice(0, 8).map((m) => {
          const s = ARENDESTATUS[m.status] ?? ARENDESTATUS.new;
          const kat = m.classification?.category ? kategoriEtikett(m.classification.category) : null;
          return (
            <li key={m.id} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[0.9375rem] font-medium">{m.subject || "–"}</span>
                <span className={cn(meta, "block truncate")}>
                  {m.from_name || m.from_email}
                  {kat ? ` · ${text(kat)}` : ""} · {sedan(m.received_at, locale)}
                </span>
              </span>
              <span className={cn("inline-flex shrink-0 items-center gap-1.5 text-[0.8125rem]", s.text)}>
                <span aria-hidden className={cn("h-1.5 w-1.5 rounded-full", s.prick)} />
                {text(s.etikett)}
              </span>
            </li>
          );
        })}
      </ul>
      {onOppna ? (
        <button type="button" onClick={onOppna} className={cn(lankknapp, "mt-3")}>
          {text(T.allaArenden)}
          <ArrowRight className="h-3.5 w-3.5" aria-hidden />
        </button>
      ) : null}
    </>
  );
}

function Kunskapsbas({ svar, demo }: Readonly<{ svar: OversiktSvar | null; demo: boolean }>) {
  const { text, locale } = useLocale();
  const vag = useArbetsvag();
  if (svar === null) return <Laddar hojd="h-48" />;
  const eskalerade = svar.kategorier.filter((k) => k.eskalerade > 0).sort((a, b) => b.eskalerade - a.eskalerade);
  const eskTotal = eskalerade.reduce((s, k) => s + k.eskalerade, 0);
  const datum = new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "sv-SE", { day: "numeric", month: "short" });

  return (
    <div className="grid gap-6">
      <div className="flex items-center gap-4">
        <Andelsring andel={svar.nu.kb_traff} etikett={text(T.kbTraff)} />
        <div className="min-w-0">
          <p className="text-[0.9375rem] font-medium">{text(T.kbTraff)}</p>
          <p className={cn(meta, "num tabular-nums")}>
            {svar.drift.kb_artiklar} {text(T.artiklar)}
          </p>
        </div>
      </div>

      <div>
        <p className={etikett}>
          {text(T.luckorRubrik)}
          {svar.kb_luckor.antal ? <span className="num ml-1.5 tabular-nums text-ink-subtle">{svar.kb_luckor.antal}</span> : null}
        </p>
        <p className={cn(meta, "mt-1 max-w-[60ch]")}>{text(T.luckorText)}</p>
        {svar.kb_luckor.rader.length === 0 ? (
          <p className={cn(meta, "mt-3")}>{text(T.ingaLuckor)}</p>
        ) : (
          <ul className="mt-2 divide-y divide-ink/10">
            {svar.kb_luckor.rader.map((l) => (
              <li key={l.id} className="flex items-center justify-between gap-4 py-2.5">
                <span className="flex min-w-0 items-center gap-2.5">
                  <BookOpen className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
                  <span className="min-w-0">
                    <span className="line-clamp-2 block text-[0.9375rem] font-medium">{l.titel || "–"}</span>
                    {l.created_at && !Number.isNaN(Date.parse(l.created_at)) ? (
                      <span className={meta}>{datum.format(new Date(l.created_at))}</span>
                    ) : null}
                  </span>
                </span>
                {demo ? null : (
                  <Link href={vag("/dashboard/larande")} className={cn(btnSecondary, btnLiten, "shrink-0")}>
                    {text(T.granska)}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {eskTotal > 0 ? (
        <div>
          <p className={etikett}>{text(T.eskaleringar)}</p>
          <ul className="mt-2 space-y-1.5">
            {eskalerade.slice(0, 5).map((k) => (
              <li key={k.id} className="flex items-center gap-2 text-[0.8125rem] text-ink-muted">
                <span className="h-2 w-2 shrink-0 rounded-full bg-chart-ochre" aria-hidden />
                <span className="min-w-0 flex-1 truncate">{text(kategoriEtikett(k.id))}</span>
                <span className="num font-medium tabular-nums text-ink">{k.eskalerade}</span>
                <span className="num w-10 text-right tabular-nums text-ink-subtle">{Math.round((k.eskalerade / eskTotal) * 100)} %</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function Driftruta({ svar }: Readonly<{ svar: OversiktSvar }>) {
  const { text, locale } = useLocale();
  const d = svar.drift;
  const tal = new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: 1 });
  const usd = kostnadUsd(d.tokens_in, d.tokens_out);
  const perArende = svar.nu.inkomna > 0 ? d.korningar / svar.nu.inkomna : null;
  const rader: { id: string; etikett: Localized; varde: string; under?: string; mono?: boolean }[] = [
    { id: "korningar", etikett: T.korningar, varde: tal.format(d.korningar) },
    { id: "per", etikett: T.perArende, varde: perArende === null ? "–" : tal.format(perArende) },
    {
      id: "kostnad",
      etikett: T.kostnad,
      varde: `$${usd.toFixed(2)}`,
      under: svar.nu.inkomna > 0 ? `$${(usd / svar.nu.inkomna).toFixed(3)} ${text(T.kostnadPerArende)}` : undefined
    },
    { id: "cache", etikett: T.cache, varde: procent(andel(d.cache, d.korningar), locale) },
    { id: "modell", etikett: T.modell, varde: (d.modell ?? "–").replace(/^[a-z]+:/, ""), mono: true }
  ];
  return (
    <section aria-labelledby="support-drift" className={cn(kort, "border-dashed")}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id="support-drift" className={rubrik}>
          {text(T.drift)}
        </h2>
        <p className={meta}>
          {text(T.driftText)} {text({ sv: `Senaste ${svar.period_dygn} dygnen.`, en: `Last ${svar.period_dygn} days.` })}
        </p>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
        {rader.map((r) => (
          <div key={r.id} className="min-w-0">
            <dt className={etikett}>{text(r.etikett)}</dt>
            <dd
              className={cn(
                "mt-1 font-semibold text-ink",
                r.mono ? "break-all font-mono text-[0.875rem] leading-6" : "num truncate text-[1.25rem] tabular-nums"
              )}
              title={r.varde}
            >
              {r.varde}
            </dd>
            {r.under ? <dd className={cn(meta, "num tabular-nums")}>{r.under}</dd> : null}
          </div>
        ))}
      </dl>
    </section>
  );
}

// -- Vyn --------------------------------------------------------------------------

export function SupportOversikt({
  demo = false,
  visaDrift = false,
  onOppnaArenden
}: Readonly<{ demo?: boolean; visaDrift?: boolean; onOppnaArenden?: () => void }>) {
  const { isPlatformAdmin } = useDashboard();
  const { text, locale } = useLocale();
  const { svar, arenden, utkast, fel, ladda } = useSupportOversikt(demo);

  if (fel) {
    return (
      <div className={cn(kort, "flex flex-wrap items-center justify-between gap-4")}>
        <p className="text-[0.9375rem] text-ink-muted">{text(T.fel)}</p>
        <button type="button" onClick={ladda} className={cn(btnSecondary, btnLiten)}>
          {text(T.forsok)}
        </button>
      </div>
    );
  }

  const nu = svar?.nu;
  const forra = svar?.forra;
  const veckor = svar?.veckor ?? [];
  const dygn = svar?.period_dygn ?? 28;
  const perioden: Localized = { sv: `de ${dygn} dygnen före`, en: `the ${dygn} days before` };
  const detalj = (bas: Localized): Localized => ({ sv: `${bas.sv}, ${dygn} dygn`, en: `${bas.en}, ${dygn} days` });

  const autoNu = nu ? andel(nu.auto, nu.inkomna) : null;
  const autoForra = forra ? andel(forra.auto, forra.inkomna) : null;
  const tider = veckor.map((v) => v.svarstid_median).filter((x): x is number => x !== null).slice(-8);
  const vantande = svar?.vantande;

  const kpier: Kpi[] = [
    {
      id: "inkomna",
      etikett: T.inkomna,
      varde: nu ? nu.inkomna : null,
      forandring: nu && forra ? forandring(nu.inkomna, forra.inkomna) : undefined,
      serie: veckor.slice(-8).map((v) => v.inkomna),
      detalj: { sv: `senaste ${dygn} dygnen`, en: `last ${dygn} days` }
    },
    {
      id: "vantar",
      etikett: T.vantar,
      varde: vantande ? vantande.antal : null,
      larm: (vantande?.antal ?? 0) > 0,
      detalj:
        vantande?.aldsta && vantande.antal > 0
          ? {
              sv: `${T.vantarPaDig.sv} · ${T.aldsta.sv} ${sedan(vantande.aldsta, "sv")}`,
              en: `${T.vantarPaDig.en} · ${T.aldsta.en} ${sedan(vantande.aldsta, "en")}`
            }
          : T.vantarPaDig
    },
    {
      id: "auto",
      etikett: T.agentSvar,
      varde: null,
      visning: nu ? procent(autoNu, locale) : undefined,
      forandring: enheter(autoNu, autoForra),
      detalj: detalj(T.agentSvarDetalj)
    },
    {
      id: "svarstid",
      etikett: T.svarstid,
      varde: null,
      visning: nu ? varaktighet(nu.svarstid_median, locale) : undefined,
      forandring:
        nu?.svarstid_median != null && forra?.svarstid_median != null
          ? forandring(nu.svarstid_median, forra.svarstid_median)
          : undefined,
      battre: "ner",
      serie: tider,
      detalj: detalj(T.svarstidDetalj)
    }
  ];

  const hanteringsdelar: Andel[] = nu
    ? [
        { id: "auto", etikett: { sv: "Svarat automatiskt", en: "Answered automatically" }, antal: nu.auto, farg: "oklch(var(--moss))" },
        { id: "godkant", etikett: { sv: "Svar efter ditt ja", en: "Answered after your yes" }, antal: nu.godkant, farg: "oklch(var(--chart-blue))" },
        { id: "manniska", etikett: { sv: "Till en människa", en: "To a human" }, antal: nu.manniska, farg: "oklch(var(--chart-ochre))" },
        { id: "vantar", etikett: { sv: "Väntar på svar", en: "Awaiting a reply" }, antal: nu.vantar, farg: "oklch(var(--danger))" }
      ]
    : [];

  // Sex största kategorierna, resten samlas i Övrigt: en munk med tolv
  // smala segment går inte att läsa.
  const kat = svar?.kategorier ?? [];
  const toppen = kat.filter((k) => k.id !== "ovrigt").slice(0, 6);
  const resten = kat.filter((k) => !toppen.includes(k)).reduce((s, k) => s + k.antal, 0);
  const kategoridelar: Andel[] = [
    ...toppen.map((k, i) => ({
      id: k.id,
      etikett: kategoriEtikett(k.id),
      antal: k.antal,
      farg: k.id === "okand" ? "oklch(var(--ink-subtle))" : `oklch(var(--chart-ramp-${6 - Math.min(i, 5)}))`
    })),
    ...(resten > 0 ? [{ id: "ovrigt", etikett: KATEGORI.ovrigt, antal: resten, farg: "oklch(var(--ink-subtle))" }] : [])
  ];

  const nyckeltal: { id: string; etikett: Localized; varde: string }[] = [
    { id: "frekvens", etikett: T.svarsfrekvens, varde: nu ? procent(andel(nu.auto + nu.godkant, nu.inkomna), locale) : "–" },
    { id: "timme", etikett: T.inomTimme, varde: nu ? procent(nu.inom_timme, locale) : "–" },
    { id: "manniska", etikett: T.tillManniska, varde: nu ? procent(andel(nu.manniska, nu.inkomna), locale) : "–" }
  ];

  const graf: Vecka[] = veckor.map((v) => ({ week: v.week, tickets: v.inkomna, resolved: v.besvarade }));
  const harTrafik = veckor.some((v) => v.inkomna > 0);
  const kolumn = cn(kort, "relative min-w-0 thin-scrollbar xl:max-h-[44rem] xl:overflow-y-auto");

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={perioden} />
        ))}
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-12">
        <section aria-labelledby="support-aktivitet" className={cn(kort, "min-w-0 lg:col-span-7")}>
          <h2 id="support-aktivitet" className={cn(rubrik, "mb-4")}>
            {text(T.aktivitet)}
          </h2>
          {svar === null ? (
            <Laddar hojd="h-64" />
          ) : harTrafik ? (
            <Aktivitetsgraf
              veckor={graf}
              serier={[
                { nyckel: "tickets", etikett: T.inkomna, ton: "chart-ochre" },
                { nyckel: "resolved", etikett: T.besvarade, ton: "chart-blue" }
              ]}
            />
          ) : (
            <p className={meta}>{text(T.ingenAktivitet)}</p>
          )}
          <dl className="mt-5 grid grid-cols-1 gap-3 border-t border-ink/10 pt-4 sm:grid-cols-3 sm:gap-4">
            {nyckeltal.map((x) => (
              <div key={x.id} className="flex items-baseline justify-between gap-3 sm:block">
                <dt className={etikett}>{text(x.etikett)}</dt>
                <dd className="num text-[1.25rem] font-semibold tabular-nums text-ink sm:mt-1">{x.varde}</dd>
              </div>
            ))}
          </dl>
        </section>
        <section aria-labelledby="support-fordelning" className={cn(kort, "min-w-0 lg:col-span-5")}>
          <h2 id="support-fordelning" className={cn(rubrik, "mb-4")}>
            {text(T.fordelning)}
          </h2>
          {svar === null ? (
            <Laddar hojd="h-64" />
          ) : (
            <div className="grid gap-6">
              <Munkdiagram delar={hanteringsdelar} etikett={T.hantering} mitt={T.arendenMitt} />
              <Munkdiagram delar={kategoridelar} etikett={T.kategori} mitt={T.arendenMitt} />
            </div>
          )}
        </section>
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <UtkastRuta utkast={utkast} onOppna={onOppnaArenden} />
        <Svarstider svar={svar} />
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <section aria-labelledby="support-arenden" className={kolumn}>
          <h2 id="support-arenden" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
            {text(T.arenden)}
          </h2>
          <p className={cn(meta, "mb-2 mt-1")}>{text(T.arendenText)}</p>
          <Arendelista arenden={arenden} onOppna={onOppnaArenden} />
        </section>
        <section aria-labelledby="support-kb" className={kolumn}>
          <h2 id="support-kb" className="mb-4 text-[1.0625rem] font-semibold tracking-[-0.01em]">
            {text(T.kbRubrik)}
          </h2>
          <Kunskapsbas svar={svar} demo={demo} />
        </section>
      </div>

      {svar && (visaDrift || isPlatformAdmin) ? <Driftruta svar={svar} /> : null}
    </div>
  );
}
