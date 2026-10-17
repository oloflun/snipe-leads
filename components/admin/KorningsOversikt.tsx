"use client";

import Link from "next/link";
import { kostnadUsd } from "@/components/admin/AgentAnvandning";
import {
  Aktivitetsgraf,
  Fordelningsstaplar,
  KpiKort,
  Munkdiagram,
  Panelrubrik,
  type Andel,
  type Kpi,
  type Stapel,
  type Vecka
} from "@/components/dashboard/OversiktPaneler";
import { meta, panelKort } from "@/components/ui";
import { KORNINGSTYPNAMN, arIris } from "@/lib/admin/korningstyper";
import { ADMIN, a, antal } from "@/lib/admin/sprak";
import type { RunRow } from "@/lib/data/admin";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Logg › Körningar, överdelen (Sebbes beställning 2026-10-07: översikternas
 * layout). Räknar på exakt de rader sidan hämtat (de senaste 200, filtrerade
 * som tabellen), och säger det: en logg har inget "totalt", bara ett fönster.
 *
 *   nyckeltal: körningar, tokens, svarstid (median), uppskattad kostnad
 *   körningar per dag · per agent och per kund (munkar)
 *   svarstider | tyngsta körningarna
 *
 * Dagarna räknas bakåt från den SENASTE körningen, inte från klockan: samma
 * rader ger då samma graf på servern och i webbläsaren.
 */

const DAGAR = 14;
const DYGN = 86_400_000;

const TYPFARG = [
  "oklch(var(--chart-blue))",
  "oklch(var(--chart-ochre))",
  "oklch(var(--chart-ramp-6))",
  "oklch(var(--chart-ramp-3))",
  "oklch(var(--moss))",
  "oklch(var(--ink-subtle))"
];

const LATENS: { id: string; etikett: Localized; tak: number; farg: string }[] = [
  { id: "1s", etikett: { sv: "Under 1 s", en: "Under 1 s" }, tak: 1_000, farg: "oklch(var(--chart-ramp-6))" },
  { id: "5s", etikett: { sv: "1–5 s", en: "1–5 s" }, tak: 5_000, farg: "oklch(var(--chart-ramp-4))" },
  { id: "15s", etikett: { sv: "5–15 s", en: "5–15 s" }, tak: 15_000, farg: "oklch(var(--chart-ramp-2))" },
  { id: "60s", etikett: { sv: "15–60 s", en: "15–60 s" }, tak: 60_000, farg: "oklch(var(--chart-ochre))" },
  { id: "mer", etikett: { sv: "Över en minut", en: "Over a minute" }, tak: Infinity, farg: "oklch(var(--danger))" }
];

function sekunder(ms: number | null, locale: "sv" | "en"): string {
  if (ms === null) return "–";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", { maximumFractionDigits: 1 }).format(ms / 1000)} s`;
}

function percentil(varden: number[], p: number): number | null {
  if (varden.length === 0) return null;
  const s = [...varden].sort((x, y) => x - y);
  return s[Math.min(s.length - 1, Math.floor((s.length - 1) * p))];
}

function dagnyckel(iso: string): string {
  return iso.slice(0, 10);
}

function typnamn(agentType: string): Localized {
  const nyckel = KORNINGSTYPNAMN.get(agentType);
  return nyckel ? ADMIN[nyckel] : { sv: agentType, en: agentType };
}

export function KorningsOversikt({ runs, filter }: Readonly<{ runs: RunRow[]; filter: string }>) {
  const { locale, text } = useLocale();
  if (runs.length === 0) return null;

  const tokensIn = runs.reduce((s, r) => s + (r.tokens_in ?? 0), 0);
  const tokensUt = runs.reduce((s, r) => s + (r.tokens_out ?? 0), 0);
  const latenser = runs.map((r) => r.latency_ms).filter((x): x is number => typeof x === "number");
  const median = percentil(latenser, 0.5);
  const p90 = percentil(latenser, 0.9);
  const tider = runs.map((r) => r.created_at).sort();
  const forsta = tider[0];
  const sista = tider[tider.length - 1];
  const datumformat = new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "sv-SE", { day: "numeric", month: "short" });
  const span = `${datumformat.format(new Date(forsta))}–${datumformat.format(new Date(sista))}`;

  const kpier: Kpi[] = [
    {
      id: "antal",
      etikett: ADMIN.kolKorningar,
      varde: runs.length,
      detalj: { sv: `de senaste i loggen, ${span}`, en: `the latest in the log, ${span}` }
    },
    {
      id: "tokens",
      etikett: ADMIN.kolTokens,
      varde: tokensIn + tokensUt,
      detalj: {
        sv: `${antal(tokensIn, "sv")} in, ${antal(tokensUt, "sv")} ut`,
        en: `${antal(tokensIn, "en")} in, ${antal(tokensUt, "en")} out`
      }
    },
    {
      id: "latens",
      etikett: { sv: "Svarstid, median", en: "Latency, median" },
      varde: null,
      visning: sekunder(median, locale),
      detalj: { sv: `9 av 10 under ${sekunder(p90, "sv")}`, en: `9 in 10 under ${sekunder(p90, "en")}` }
    },
    {
      id: "kostnad",
      etikett: ADMIN.aiKostnadUppskattad,
      varde: null,
      visning: `$${kostnadUsd(tokensIn, tokensUt).toFixed(2)}`,
      detalj: { sv: "listpris, inte en faktura", en: "list price, not an invoice" }
    }
  ];

  // Per dag, bakåt från den senaste körningen.
  const slut = new Date(`${dagnyckel(sista)}T12:00:00Z`).getTime();
  const dagar = Array.from({ length: DAGAR }, (_, i) => new Date(slut - (DAGAR - 1 - i) * DYGN).toISOString().slice(0, 10));
  const index = new Map(dagar.map((d, i) => [d, i]));
  const graf: Vecka[] = dagar.map((d) => ({
    week: datumformat.format(new Date(`${d}T12:00:00Z`)),
    kundtjanst: 0,
    iris: 0,
    korningar: 0
  }));
  for (const r of runs) {
    const i = index.get(dagnyckel(r.created_at));
    if (i === undefined) continue;
    graf[i].korningar = (graf[i].korningar ?? 0) + 1;
    if (r.agent_type === "support") graf[i].kundtjanst = (graf[i].kundtjanst ?? 0) + 1;
    if (arIris(r.agent_type)) graf[i].iris = (graf[i].iris ?? 0) + 1;
  }

  const perTyp = new Map<string, number>();
  const perKund = new Map<string, number>();
  for (const r of runs) {
    perTyp.set(r.agent_type, (perTyp.get(r.agent_type) ?? 0) + 1);
    const kund = r.tenant_name || r.tenant_slug || a("okand", locale);
    perKund.set(kund, (perKund.get(kund) ?? 0) + 1);
  }
  const typdelar: Andel[] = [...perTyp.entries()]
    .sort((x, y) => y[1] - x[1])
    .map(([typ, n], i) => ({ id: typ, etikett: typnamn(typ), antal: n, farg: TYPFARG[Math.min(i, TYPFARG.length - 1)] }));
  // Fem största kunderna, resten samlade: en munk med tjugo smala segment går inte att läsa.
  const kundlista = [...perKund.entries()].sort((x, y) => y[1] - x[1]);
  const ovriga = kundlista.slice(5).reduce((s, [, n]) => s + n, 0);
  const kunddelar: Andel[] = [
    ...kundlista.slice(0, 5).map(([namn, n], i) => ({
      id: namn,
      etikett: { sv: namn, en: namn },
      antal: n,
      farg: `oklch(var(--chart-ramp-${6 - i}))`
    })),
    ...(ovriga > 0 ? [{ id: "ovriga", etikett: { sv: "Övriga", en: "Others" }, antal: ovriga, farg: "oklch(var(--ink-subtle))" }] : [])
  ];

  const staplar: Stapel[] = LATENS.map((h, i) => ({
    id: h.id,
    etikett: h.etikett,
    farg: h.farg,
    antal: latenser.filter((ms) => ms < h.tak && (i === 0 || ms >= LATENS[i - 1].tak)).length
  }));

  const tyngsta = [...runs]
    .sort((x, y) => (y.tokens_in ?? 0) + (y.tokens_out ?? 0) - ((x.tokens_in ?? 0) + (x.tokens_out ?? 0)))
    .slice(0, 5);
  const storst = Math.max(1, ...tyngsta.map((r) => (r.tokens_in ?? 0) + (r.tokens_out ?? 0)));

  const serier: { nyckel: keyof Vecka; etikett: Localized; ton: "chart-blue" | "chart-ochre" }[] = filter
    ? [{ nyckel: "korningar", etikett: typnamn(filter), ton: "chart-blue" }]
    : [
        { nyckel: "kundtjanst", etikett: ADMIN.railKundtjanst, ton: "chart-blue" },
        { nyckel: "iris", etikett: ADMIN.railIris, ton: "chart-ochre" }
      ];

  return (
    <div className="mt-6 flex min-w-0 flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={{ sv: "", en: "" }} />
        ))}
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-12">
        <section aria-labelledby="logg-perdag" className={cn(panelKort, "min-w-0 lg:col-span-7")}>
          <Panelrubrik
            id="logg-perdag"
            titel={{ sv: "Körningar per dag", en: "Runs per day" }}
            under={{ sv: `De ${DAGAR} dagarna fram till den senaste körningen.`, en: `The ${DAGAR} days up to the latest run.` }}
          />
          <Aktivitetsgraf typ="staplar" veckor={graf} serier={serier} />
        </section>
        <section aria-labelledby="logg-fordelning" className={cn(panelKort, "min-w-0 lg:col-span-5")}>
          <Panelrubrik id="logg-fordelning" titel={{ sv: "Fördelning", en: "Breakdown" }} />
          <div className="grid gap-6">
            <Munkdiagram delar={typdelar} etikett={{ sv: "Per agent", en: "Per agent" }} mitt={{ sv: "körningar", en: "runs" }} />
            <Munkdiagram delar={kunddelar} etikett={{ sv: "Per kund", en: "Per customer" }} mitt={{ sv: "körningar", en: "runs" }} />
          </div>
        </section>
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <section aria-labelledby="logg-latens" className={cn(panelKort, "min-w-0")}>
          <Panelrubrik
            id="logg-latens"
            titel={{ sv: "Svarstider", en: "Latency" }}
            under={{ sv: "Hur lång tid körningarna tog, från start till svar.", en: "How long the runs took, from start to answer." }}
          />
          {latenser.length === 0 ? (
            <p className={meta}>{text({ sv: "Inga svarstider loggade.", en: "No latency logged." })}</p>
          ) : (
            <Fordelningsstaplar staplar={staplar} />
          )}
        </section>
        <section aria-labelledby="logg-tyngsta" className={cn(panelKort, "min-w-0")}>
          <Panelrubrik
            id="logg-tyngsta"
            titel={{ sv: "Tyngsta körningarna", en: "Heaviest runs" }}
            under={{ sv: "Flest tokens. Klicka för spåret steg för steg.", en: "Most tokens. Click for the step-by-step trace." }}
          />
          <ul className="divide-y divide-ink/10">
            {tyngsta.map((r) => {
              const tokens = (r.tokens_in ?? 0) + (r.tokens_out ?? 0);
              return (
                <li key={r.id} className="py-2.5">
                  <div className="flex items-baseline justify-between gap-3">
                    <Link
                      href={`/admin/korningar/${r.id}`}
                      className="focus-ring min-w-0 truncate rounded-input text-[0.9375rem] font-medium underline decoration-ink/20 underline-offset-4 hover:text-ochre"
                    >
                      {r.tenant_name || r.tenant_slug || a("okand", locale)}
                    </Link>
                    <span className="num shrink-0 text-[0.875rem] font-medium tabular-nums">{antal(tokens, locale)}</span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-ink/[0.06]">
                    <span className="block h-full rounded-full bg-chart-ochre" style={{ width: `${(tokens / storst) * 100}%` }} />
                  </div>
                  <p className={cn(meta, "mt-1 truncate")}>
                    {text(typnamn(r.agent_type))} · {r.created_at.slice(0, 16).replace("T", " ")} · {sekunder(r.latency_ms, locale)}
                  </p>
                </li>
              );
            })}
          </ul>
        </section>
      </div>
    </div>
  );
}
