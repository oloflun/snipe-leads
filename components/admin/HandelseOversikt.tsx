"use client";

import {
  Aktivitetsgraf,
  KpiKort,
  Munkdiagram,
  Panelrubrik,
  type Andel,
  type Kpi,
  type Vecka
} from "@/components/dashboard/OversiktPaneler";
import { panelKort } from "@/components/ui";
import { kallnamn, tolkaHandelse } from "@/lib/admin/handelsetext";
import { ADMIN } from "@/lib/admin/sprak";
import type { EventRow } from "@/lib/data/admin";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Logg › Händelser, överdelen (Sebbes beställning 2026-10-07: översikternas
 * layout). Räknar på de händelser sidan hämtat, med samma nivåfilter som
 * listan, och säger att det är ett fönster.
 *
 *   nyckeltal: fel, varningar, info, unika problem
 *   händelser per dag · per källa och per kund (munkar)
 *
 * "Unika problem" är samma gruppering som listan under (källa + meddelande):
 * hundra rader av samma trasiga källa är ETT problem. Dagarna räknas bakåt från
 * den senaste händelsen, inte från klockan, så att servern och webbläsaren
 * ritar samma graf.
 */

const DAGAR = 14;
const DYGN = 86_400_000;

export function HandelseOversikt({ events, niva }: Readonly<{ events: EventRow[]; niva: string }>) {
  const { locale } = useLocale();
  if (events.length === 0) return null;

  const fel = events.filter((e) => e.level === "error");
  const varningar = events.filter((e) => e.level === "warning");
  const info = events.filter((e) => e.level === "info");
  const grupper = new Map<string, EventRow[]>();
  for (const e of events) {
    const nyckel = `${e.source}::${e.message}`;
    grupper.set(nyckel, [...(grupper.get(nyckel) ?? []), e]);
  }
  const vanligast = [...grupper.values()].sort((x, y) => y.length - x.length)[0];

  const tider = events.map((e) => e.created_at).sort();
  const datumformat = new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "sv-SE", { day: "numeric", month: "short" });
  const span = `${datumformat.format(new Date(tider[0]))}–${datumformat.format(new Date(tider[tider.length - 1]))}`;
  const fonster: Localized = { sv: `${events.length} händelser, ${span}`, en: `${events.length} events, ${span}` };

  const kpier: Kpi[] = [
    { id: "fel", etikett: ADMIN.filterFel, varde: fel.length, larm: fel.length > 0, battre: "ner", detalj: fonster, href: niva === "error" ? undefined : "/admin/handelser?level=error" },
    { id: "varningar", etikett: ADMIN.filterVarningar, varde: varningar.length, battre: "ner", detalj: fonster, href: niva === "warning" ? undefined : "/admin/handelser?level=warning" },
    { id: "info", etikett: ADMIN.filterInfo, varde: info.length, detalj: fonster, href: niva === "info" ? undefined : "/admin/handelser?level=info" },
    {
      id: "unika",
      etikett: { sv: "Unika problem", en: "Distinct problems" },
      varde: grupper.size,
      detalj: vanligast
        ? {
            sv: `vanligast: ${tolkaHandelse(vanligast[0].message).rubrik.sv} (${vanligast.length})`,
            en: `most common: ${tolkaHandelse(vanligast[0].message).rubrik.en} (${vanligast.length})`
          }
        : { sv: "grupperade på källa och orsak", en: "grouped by source and cause" }
    }
  ];

  const slut = new Date(`${tider[tider.length - 1].slice(0, 10)}T12:00:00Z`).getTime();
  const dagar = Array.from({ length: DAGAR }, (_, i) => new Date(slut - (DAGAR - 1 - i) * DYGN).toISOString().slice(0, 10));
  const index = new Map(dagar.map((d, i) => [d, i]));
  const graf: Vecka[] = dagar.map((d) => ({ week: datumformat.format(new Date(`${d}T12:00:00Z`)), fel: 0, varningar: 0, korningar: 0 }));
  for (const e of events) {
    const i = index.get(e.created_at.slice(0, 10));
    if (i === undefined) continue;
    if (e.level === "error") graf[i].fel = (graf[i].fel ?? 0) + 1;
    else if (e.level === "warning") graf[i].varningar = (graf[i].varningar ?? 0) + 1;
    else graf[i].korningar = (graf[i].korningar ?? 0) + 1;
  }
  const serier: { nyckel: keyof Vecka; etikett: Localized; ton: "chart-blue" | "chart-ochre" }[] =
    niva === "info"
      ? [{ nyckel: "korningar", etikett: ADMIN.filterInfo, ton: "chart-blue" }]
      : niva === "warning"
        ? [{ nyckel: "varningar", etikett: ADMIN.filterVarningar, ton: "chart-blue" }]
        : niva === "error"
          ? [{ nyckel: "fel", etikett: ADMIN.filterFel, ton: "chart-ochre" }]
          : [
              { nyckel: "fel", etikett: ADMIN.filterFel, ton: "chart-ochre" },
              { nyckel: "varningar", etikett: ADMIN.filterVarningar, ton: "chart-blue" }
            ];

  const topp = (nyckel: (e: EventRow) => string, namn: (k: string) => Localized): Andel[] => {
    const raknat = new Map<string, number>();
    for (const e of events) raknat.set(nyckel(e), (raknat.get(nyckel(e)) ?? 0) + 1);
    const lista = [...raknat.entries()].sort((x, y) => y[1] - x[1]);
    const ovriga = lista.slice(5).reduce((s, [, n]) => s + n, 0);
    return [
      ...lista.slice(0, 5).map(([k, n], i) => ({ id: k, etikett: namn(k), antal: n, farg: `oklch(var(--chart-ramp-${6 - i}))` })),
      ...(ovriga > 0 ? [{ id: "ovriga", etikett: { sv: "Övriga", en: "Others" }, antal: ovriga, farg: "oklch(var(--ink-subtle))" }] : [])
    ];
  };
  const kalldelar = topp((e) => e.source, kallnamn);
  const kunddelar = topp(
    (e) => e.tenant_slug ?? "",
    (k) => (k ? { sv: k, en: k } : { sv: "Plattformsnivå", en: "Platform level" })
  );

  return (
    <div className="mt-6 flex min-w-0 flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={{ sv: "", en: "" }} />
        ))}
      </div>
      <div className="grid min-w-0 gap-4 lg:grid-cols-12">
        <section aria-labelledby="handelser-perdag" className={cn(panelKort, "min-w-0 lg:col-span-7")}>
          <Panelrubrik
            id="handelser-perdag"
            titel={{ sv: "Händelser per dag", en: "Events per day" }}
            under={{ sv: `De ${DAGAR} dagarna fram till den senaste händelsen.`, en: `The ${DAGAR} days up to the latest event.` }}
          />
          <Aktivitetsgraf typ="staplar" veckor={graf} serier={serier} />
        </section>
        <section aria-labelledby="handelser-fordelning" className={cn(panelKort, "min-w-0 lg:col-span-5")}>
          <Panelrubrik id="handelser-fordelning" titel={{ sv: "Varifrån de kommer", en: "Where they come from" }} />
          <div className="grid gap-6">
            <Munkdiagram delar={kalldelar} etikett={{ sv: "Per källa", en: "Per source" }} mitt={{ sv: "händelser", en: "events" }} />
            <Munkdiagram delar={kunddelar} etikett={{ sv: "Per kund", en: "Per customer" }} mitt={{ sv: "händelser", en: "events" }} />
          </div>
        </section>
      </div>
    </div>
  );
}
