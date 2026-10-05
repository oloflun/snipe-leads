"use client";

/* design · pre-emit critique: P4 H4 E4 S4 R5 V4
 * Tier 0 (DESIGN.md låst), Operate-läge. Lane: linjerad arbetsbänk med en
 * ochre-puls. Referenslås: Upsales produktyta (dominant: tal + förändringspill,
 * en segmenterad fördelningsstapel med teckenförklaring, lätt ytgraf),
 * Twenty för tätheten (DESIGN.md § App surfaces). */

import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import Link from "next/link";
import { useEffect, useId, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, etikett as etikettKlass, meta } from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

// -- Tokens i SVG ------------------------------------------------------------
//
// Recharts skriver färgerna som SVG-attribut, och ett attribut löser inte upp
// var(--x). Färgen läses därför ur de låsta tokens vid körning och läses om när
// temat byts (data-theme på <html>), så att mörkt läge får sina egna steg
// (globals.css) i stället för en automatisk invertering.

type Ton = "chart-blue" | "chart-ochre" | "ink-subtle" | "ink" | "paper" | "moss";

function lasToken(namn: Ton): string {
  if (typeof window === "undefined") return "currentColor";
  const varde = getComputedStyle(document.documentElement).getPropertyValue(`--${namn}`).trim();
  return varde ? `oklch(${varde})` : "currentColor";
}

export function useTokenfarger(): Record<Ton, string> {
  const las = () =>
    Object.fromEntries(
      (["chart-blue", "chart-ochre", "ink-subtle", "ink", "paper", "moss"] as Ton[]).map((t) => [t, lasToken(t)])
    ) as Record<Ton, string>;
  const [farger, setFarger] = useState<Record<Ton, string>>(las);
  useEffect(() => {
    setFarger(las());
    const vakt = new MutationObserver(() => setFarger(las()));
    vakt.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });
    return () => vakt.disconnect();
  }, []);
  return farger;
}

// -- Format ------------------------------------------------------------------

function tal(n: number | null, locale: "sv" | "en"): string {
  if (n === null) return "–";
  return new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE").format(n);
}

/** Förändring mot föregående period i hela procent; null när jämförelsen saknar grund. */
export function forandring(nu: number, forra: number): number | null {
  if (forra === 0) return nu === 0 ? 0 : null;
  return Math.round(((nu - forra) / forra) * 100);
}

// -- Nyckeltalskort ----------------------------------------------------------

export type Kpi = {
  id: string;
  etikett: Localized;
  varde: number | null;
  /** Visas i stället för talet, t.ex. en procentsats. */
  visning?: string;
  forandring?: number | null;
  /** Är en ökning bra (nya leads) eller dålig (eskalerade)? */
  battre?: "upp" | "ner";
  serie?: number[];
  detalj: Localized;
  larm?: boolean;
  href?: string;
};

/**
 * Upsales-kortet i husets språk: etikett, tal i Geist tnum, förändringen som
 * pill (pil + procent, aldrig färg ensam) och en sparkline utan axlar. Ochre
 * bara när något väntar på dig — som linje överst, inte som textfärg (ochre
 * mäter 2,17:1 mot papper).
 */
export function KpiKort({ kpi, perioden }: Readonly<{ kpi: Kpi; perioden: Localized }>) {
  const { locale, text } = useLocale();
  const farger = useTokenfarger();
  const gradient = useId().replace(/:/g, "");
  const f = kpi.forandring;
  const bra = f === null || f === undefined || f === 0 ? null : (f > 0) === ((kpi.battre ?? "upp") === "upp");
  const Pil = !f ? Minus : f > 0 ? ArrowUpRight : ArrowDownRight;
  const innehall = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className={etikettKlass}>{text(kpi.etikett)}</p>
        {f !== undefined ? (
          <Badge tone={bra === null ? "neutral" : bra ? "good" : "danger"}>
            <Pil className="h-3 w-3" aria-hidden />
            <span className="num tabular-nums">{f === null ? text({ sv: "ny", en: "new" }) : `${f > 0 ? "+" : ""}${f} %`}</span>
            <span className="sr-only">{text({ sv: `jämfört med ${perioden.sv}`, en: `compared with ${perioden.en}` })}</span>
          </Badge>
        ) : null}
      </div>
      <p className="num mt-3 text-[2.25rem] font-semibold leading-none tracking-[-0.03em] text-ink tabular-nums">
        {kpi.visning ?? tal(kpi.varde, locale)}
      </p>
      <div className="mt-3 flex items-end justify-between gap-4">
        <p className={cn(meta, "max-w-[22ch]")}>{text(kpi.detalj)}</p>
        {kpi.serie && kpi.serie.length > 1 ? (
          <div className="h-9 w-28 shrink-0" aria-hidden>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={kpi.serie.map((v, i) => ({ i, v }))} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
                <defs>
                  <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={kpi.larm ? farger["chart-ochre"] : farger["chart-blue"]} stopOpacity={0.22} />
                    <stop offset="100%" stopColor={kpi.larm ? farger["chart-ochre"] : farger["chart-blue"]} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={kpi.larm ? farger["chart-ochre"] : farger["chart-blue"]}
                  strokeWidth={2}
                  fill={`url(#${gradient})`}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : null}
      </div>
    </>
  );
  const ram = cn(
    "block rounded-card border bg-paper p-4 transition-colors",
    kpi.larm ? "border-ink/12 shadow-[inset_0_2px_0_0_oklch(var(--ochre))]" : "border-ink/12",
    kpi.href && "focus-ring hover:border-ink/25"
  );
  return kpi.href ? (
    <Link href={kpi.href} className={ram}>
      {innehall}
    </Link>
  ) : (
    <div className={ram}>{innehall}</div>
  );
}

// -- Aktivitetsgrafen ---------------------------------------------------------

export type Vecka = { week: string; new_leads?: number; replies?: number; sent?: number; tickets?: number; resolved?: number; escalated?: number };

type Serie = { nyckel: keyof Vecka; etikett: Localized; ton: "chart-ochre" | "chart-blue" };

/**
 * Två serier, en axel. Teckenförklaring alltid (två serier) och värdet direkt
 * vid seriens slut, så att identiteten aldrig bärs av färg ensam och ochrens
 * låga kontrast mot papper har en synlig etikett (dataviz-validatorns krav).
 * Hårkors och tooltip vid hovring.
 */
export function Aktivitetsgraf({ veckor, serier }: Readonly<{ veckor: Vecka[]; serier: Serie[] }>) {
  const { locale, text } = useLocale();
  const farger = useTokenfarger();
  const id = useId().replace(/:/g, "");
  const data = veckor.map((v) => ({ ...v }));
  const sista = data[data.length - 1];
  return (
    <figure className="m-0">
      <figcaption className="mb-3 flex flex-wrap gap-x-5 gap-y-1.5">
        {serier.map((s) => (
          <span key={String(s.nyckel)} className="inline-flex items-center gap-2 text-[0.8125rem] text-ink-muted">
            <span className={cn("h-2 w-4 rounded-full", s.ton === "chart-ochre" ? "bg-chart-ochre" : "bg-chart-blue")} aria-hidden />
            {text(s.etikett)}
            <span className="num font-medium text-ink tabular-nums">{tal(Number(sista?.[s.nyckel] ?? 0), locale)}</span>
            <span className="sr-only">{text({ sv: "senaste veckan", en: "last week" })}</span>
          </span>
        ))}
      </figcaption>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
            <defs>
              {serier.map((s) => (
                <linearGradient key={String(s.nyckel)} id={`${id}-${String(s.nyckel)}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={farger[s.ton]} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={farger[s.ton]} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid vertical={false} stroke={farger["ink-subtle"]} strokeOpacity={0.18} />
            <XAxis
              dataKey="week"
              tickLine={false}
              axisLine={false}
              tick={{ fill: farger["ink-subtle"], fontSize: 12 }}
              interval="preserveStartEnd"
              minTickGap={24}
            />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: farger["ink-subtle"], fontSize: 12 }} width={44} />
            <Tooltip
              cursor={{ stroke: farger["ink-subtle"], strokeOpacity: 0.5, strokeWidth: 1 }}
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <div className="rounded-input border border-ink/12 bg-paper px-3 py-2 text-[0.8125rem] shadow-sm">
                    <p className="font-medium text-ink">{label}</p>
                    {serier.map((s) => {
                      const rad = payload.find((p) => p.dataKey === s.nyckel);
                      return (
                        <p key={String(s.nyckel)} className="mt-1 flex items-center gap-2 text-ink-muted">
                          <span className={cn("h-2 w-2 rounded-full", s.ton === "chart-ochre" ? "bg-chart-ochre" : "bg-chart-blue")} aria-hidden />
                          {text(s.etikett)}
                          <span className="num ml-auto pl-3 font-medium text-ink tabular-nums">{tal(Number(rad?.value ?? 0), locale)}</span>
                        </p>
                      );
                    })}
                  </div>
                ) : null
              }
            />
            {serier.map((s) => (
              <Area
                key={String(s.nyckel)}
                type="monotone"
                dataKey={String(s.nyckel)}
                stroke={farger[s.ton]}
                strokeWidth={2}
                fill={`url(#${id}-${String(s.nyckel)})`}
                activeDot={{ r: 4, stroke: farger.paper, strokeWidth: 2 }}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {/* Tabellvyn: samma tal för skärmläsare och för den som vill läsa exakt. */}
      <table className="sr-only">
        <caption>{text({ sv: "Aktivitet per vecka", en: "Activity per week" })}</caption>
        <thead>
          <tr>
            <th scope="col">{text({ sv: "Vecka", en: "Week" })}</th>
            {serier.map((s) => (
              <th key={String(s.nyckel)} scope="col">
                {text(s.etikett)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((v) => (
            <tr key={v.week}>
              <th scope="row">{v.week}</th>
              {serier.map((s) => (
                <td key={String(s.nyckel)}>{Number(v[s.nyckel] ?? 0)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

// -- Pipelinen ---------------------------------------------------------------

export type Steg = { status: string; etikett: Localized; antal: number };

/** Sekventiell rampa i en nyans (blått), ljust till mörkt: stegen har en ordning. */
const RAMPA = [1, 2, 3, 4, 5, 6].map((n) => `oklch(var(--chart-ramp-${n}))`);

/**
 * Upsales fördelningsstapel: EN stapel med segment och 2px yta mellan dem, och
 * en teckenförklaring under med punkt, etikett, antal och konverteringen från
 * föregående steg. Varje post leder till Leads.
 */
export function PipelineStapel({ steg, href }: Readonly<{ steg: Steg[]; href: string }>) {
  const { locale, text } = useLocale();
  const total = steg.reduce((s, x) => s + x.antal, 0);
  if (total === 0) {
    return (
      <p className="rounded-card border border-ink/12 bg-paper2/50 px-4 py-3 text-[0.9375rem] text-ink-muted">
        {text({ sv: "Inga leads än. Kör Iris för att fylla pipelinen.", en: "No leads yet. Run Iris to fill the pipeline." })}
      </p>
    );
  }
  return (
    <div>
      <div className="flex h-3 w-full gap-[2px] overflow-hidden rounded-full" role="img" aria-label={text({ sv: "Fördelning per steg", en: "Distribution per stage" })}>
        {steg.map((s, i) =>
          s.antal > 0 ? (
            <span
              key={s.status}
              className="h-full first:rounded-l-full last:rounded-r-full"
              style={{ width: `${(s.antal / total) * 100}%`, background: RAMPA[Math.min(i, RAMPA.length - 1)] }}
              title={`${text(s.etikett)}: ${s.antal}`}
            />
          ) : null
        )}
      </div>
      <ul className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4 lg:grid-cols-7">
        {steg.map((s, i) => {
          const forra = i > 0 ? steg.slice(i).reduce((a, x) => a + x.antal, 0) : null;
          const fore = i > 0 ? steg.slice(i - 1).reduce((a, x) => a + x.antal, 0) : null;
          const konv = forra !== null && fore ? Math.round((forra / fore) * 100) : null;
          return (
            <li key={s.status}>
              <Link href={href} className="focus-ring -m-1 block rounded-input p-1 hover:bg-paper2/60">
                <span className="flex items-center gap-2 text-[0.8125rem] text-ink-muted">
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: RAMPA[Math.min(i, RAMPA.length - 1)] }} aria-hidden />
                  {text(s.etikett)}
                </span>
                <span className="num mt-1 block text-[1.25rem] font-semibold tabular-nums text-ink">{tal(s.antal, locale)}</span>
                {i === 0 ? (
                  <span className={meta}>{text({ sv: "ingång", en: "entry" })}</span>
                ) : konv !== null ? (
                  <span className={meta}>{text({ sv: `${konv} % gick vidare hit`, en: `${konv} % moved on to here` })}</span>
                ) : (
                  <span className={meta}>{text({ sv: "ingen har nått hit", en: "none reached this yet" })}</span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// -- Självlösningsgraden ------------------------------------------------------

/** En ring, inte en paj: en andel av en helhet, med talet i mitten. */
export function Andelsring({ andel, etikett }: Readonly<{ andel: number | null; etikett: string }>) {
  const r = 34;
  const omkrets = 2 * Math.PI * r;
  const fylld = andel === null ? 0 : Math.max(0, Math.min(1, andel)) * omkrets;
  return (
    <div className="relative h-24 w-24 shrink-0">
      <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90" role="img" aria-label={etikett}>
        <circle cx="40" cy="40" r={r} fill="none" strokeWidth="8" className="stroke-ink/10" />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${fylld} ${omkrets}`}
          className="stroke-moss"
        />
      </svg>
      <span className="num absolute inset-0 grid place-items-center text-[1.25rem] font-semibold tabular-nums text-ink">
        {andel === null ? "–" : `${Math.round(andel * 100)} %`}
      </span>
    </div>
  );
}
