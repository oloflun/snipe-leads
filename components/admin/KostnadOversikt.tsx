"use client";

import { kostnadUsd } from "@/components/admin/AgentAnvandning";
import {
  KpiKort,
  Munkdiagram,
  Panelrubrik,
  Rangstaplar,
  type Andel,
  type Kpi,
  type Rang
} from "@/components/dashboard/OversiktPaneler";
import { panelKort } from "@/components/ui";
import { ADMIN, a, antal } from "@/lib/admin/sprak";
import type { RunRow } from "@/lib/data/admin";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Logg › Kostnad per agent, överdelen (Sebbes beställning 2026-10-07:
 * översikternas layout). De tre agenternas kostnad bredvid varandra, innan
 * sektionerna per agent går ner på kundnivå.
 *
 * Samma körningar och samma pris som AgentAnvandning (`kostnadUsd`, Vertex
 * listpris), och samma tak: vid taket är talen en undre gräns och säger det.
 */

type Agent = { id: "iris" | "kundtjanst" | "kvitton"; namn: Localized; runs: RunRow[]; vidTaket: boolean; farg: string };

function usd(varde: number): string {
  return `$${varde.toFixed(2)}`;
}

export function KostnadOversikt({
  iris,
  kundtjanst,
  kvitton,
  tak
}: Readonly<{
  iris: { runs: RunRow[]; vidTaket: boolean };
  kundtjanst: { runs: RunRow[]; vidTaket: boolean };
  kvitton: { runs: RunRow[]; vidTaket: boolean };
  tak: number;
}>) {
  const { locale } = useLocale();
  const agenter: Agent[] = [
    { id: "iris", namn: ADMIN.railIris, ...iris, farg: "oklch(var(--chart-ochre))" },
    { id: "kundtjanst", namn: ADMIN.railKundtjanst, ...kundtjanst, farg: "oklch(var(--chart-blue))" },
    { id: "kvitton", namn: ADMIN.railKvitton, ...kvitton, farg: "oklch(var(--moss))" }
  ];
  const summa = (runs: RunRow[]) => ({
    in: runs.reduce((s, r) => s + (r.tokens_in ?? 0), 0),
    ut: runs.reduce((s, r) => s + (r.tokens_out ?? 0), 0)
  });
  const perAgent = agenter.map((ag) => {
    const t = summa(ag.runs);
    return { ...ag, tokens: t.in + t.ut, kostnad: kostnadUsd(t.in, t.ut) };
  });
  const total = perAgent.reduce((s, ag) => s + ag.kostnad, 0);
  const allaRuns = agenter.flatMap((ag) => ag.runs);
  const minst = agenter.some((ag) => ag.vidTaket);
  const plus = (n: number, vid: boolean) => `${antal(n, locale)}${vid ? "+" : ""}`;

  const kpier: Kpi[] = [
    {
      id: "total",
      etikett: ADMIN.aiKostnadUppskattad,
      varde: null,
      visning: usd(total),
      detalj: minst
        ? { sv: `minst; de senaste ${tak} körningarna per agenttyp`, en: `at least; the latest ${tak} runs per agent type` }
        : { sv: `${allaRuns.length} körningar, alla tre agenterna`, en: `${allaRuns.length} runs, all three agents` }
    },
    ...perAgent.map(
      (ag): Kpi => ({
        id: ag.id,
        etikett: ag.namn,
        varde: null,
        visning: usd(ag.kostnad),
        detalj: {
          sv: `${plus(ag.runs.length, ag.vidTaket)} körningar · ${antal(ag.tokens, "sv")} tokens`,
          en: `${plus(ag.runs.length, ag.vidTaket)} runs · ${antal(ag.tokens, "en")} tokens`
        }
      })
    )
  ];

  const tokendelar: Andel[] = perAgent.map((ag) => ({ id: ag.id, etikett: ag.namn, antal: ag.tokens, farg: ag.farg }));
  const korningsdelar: Andel[] = perAgent.map((ag) => ({ id: ag.id, etikett: ag.namn, antal: ag.runs.length, farg: ag.farg }));

  // Dyraste kunderna över alla agenter: samma pris, summerat per kund.
  const perKund = new Map<string, { in: number; ut: number; agenter: Set<string> }>();
  for (const ag of agenter) {
    for (const r of ag.runs) {
      const kund = r.tenant_name || r.tenant_slug || a("okand", locale);
      const post = perKund.get(kund) ?? { in: 0, ut: 0, agenter: new Set<string>() };
      post.in += r.tokens_in ?? 0;
      post.ut += r.tokens_out ?? 0;
      post.agenter.add(ag.namn[locale]);
      perKund.set(kund, post);
    }
  }
  const dyrast: Rang[] = [...perKund.entries()].map(([kund, p]) => ({
    id: kund,
    namn: kund,
    varde: kostnadUsd(p.in, p.ut),
    visning: usd(kostnadUsd(p.in, p.ut)),
    under: `${[...p.agenter].join(", ")} · ${antal(p.in + p.ut, locale)} tokens`
  }));

  return (
    <div className="mt-8 flex min-w-0 flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={{ sv: "", en: "" }} />
        ))}
      </div>
      <div className="grid min-w-0 gap-4 lg:grid-cols-12">
        <section aria-labelledby="kostnad-fordelning" className={cn(panelKort, "min-w-0 lg:col-span-5")}>
          <Panelrubrik id="kostnad-fordelning" titel={{ sv: "Fördelning per agent", en: "Breakdown per agent" }} />
          <div className="grid gap-6">
            <Munkdiagram delar={tokendelar} etikett={ADMIN.kolTokens} mitt={{ sv: "tusen tokens", en: "thousand tokens" }} mittVarde={antal(Math.round(perAgent.reduce((s, ag) => s + ag.tokens, 0) / 1000), locale)} />
            <Munkdiagram delar={korningsdelar} etikett={ADMIN.kolKorningar} mitt={{ sv: "körningar", en: "runs" }} />
          </div>
        </section>
        <section aria-labelledby="kostnad-kunder" className={cn(panelKort, "min-w-0 lg:col-span-7")}>
          <Panelrubrik
            id="kostnad-kunder"
            titel={{ sv: "Dyraste kunderna", en: "Most expensive customers" }}
            under={{ sv: "Uppskattad AI-kostnad per kund, alla agenter tillsammans.", en: "Estimated AI cost per customer, all agents together." }}
          />
          <Rangstaplar
            rader={dyrast.sort((x, y) => y.varde - x.varde).slice(0, 7)}
            tom={{ sv: "Ingen körning loggad ännu.", en: "No run logged yet." }}
            farg="oklch(var(--chart-ochre))"
          />
        </section>
      </div>
    </div>
  );
}
