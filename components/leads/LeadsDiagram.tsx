"use client";

import { useCallback, useEffect, useState } from "react";
import { Aktivitetsgraf, Munkdiagram, type Andel, type Vecka } from "@/components/dashboard/OversiktPaneler";
import { meta } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { kontaktvagAv, type SuiteProspekt } from "@/lib/leads/suite";
import { STATUS_ETIKETT } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Leadsens diagram: nya leads och svar per vecka, och fördelningen på status
 * och kontaktväg. Flyttade från Leads-översikten till Aktivitet 2026-10-07
 * (impeccable-kritiken, Sebbes val): Leads är arbetsytan och öppnar med
 * listan, Aktivitet är där statistiken bor — under Iris egen rubrik, så att
 * det syns vilken agent diagrammen gäller.
 */

const T = {
  perVecka: { sv: "Nya leads och svar per vecka", en: "New leads and replies per week" },
  nyaLeads: { sv: "Nya leads", en: "New leads" },
  svar: { sv: "Svar från leads", en: "Replies from leads" },
  ingenAktivitet: { sv: "Ingen leadsaktivitet att visa än.", en: "No leads activity to show yet." },
  fordelning: { sv: "Leadsen i listan", en: "The leads in the list" },
  status: { sv: "Status", en: "Status" },
  kontaktvag: { sv: "Kontaktväg", en: "Contact path" },
  leadsMitt: { sv: "leads", en: "leads" },
  nyaLeadsForklaring: {
    sv: "Nya leads räknar varje bolag Iris lagt till, även de som sedan valdes bort.",
    en: "New leads counts every company Iris added, including those later dropped."
  }
} satisfies Record<string, Localized>;

const KONTAKT: { id: ReturnType<typeof kontaktvagAv>; etikett: Localized; farg: string }[] = [
  { id: "bada", etikett: { sv: "Tel och mejl", en: "Phone and email" }, farg: "oklch(var(--moss))" },
  { id: "telefon", etikett: { sv: "Tel", en: "Phone" }, farg: "oklch(var(--chart-blue))" },
  { id: "mejl", etikett: { sv: "Mejl", en: "Email" }, farg: "oklch(var(--chart-ochre))" },
  { id: "saknas", etikett: { sv: "Saknas", en: "Missing" }, farg: "oklch(var(--danger))" }
];

/** Pipelinens steg i ordning: blå rampa ljust till mörkt, förlorad i grått. */
const STATUSFARG: Record<string, string> = {
  new: "oklch(var(--chart-ramp-1))",
  researching: "oklch(var(--chart-ramp-2))",
  ready: "oklch(var(--chart-ramp-3))",
  contacted: "oklch(var(--chart-ramp-4))",
  replied: "oklch(var(--chart-ramp-5))",
  meeting: "oklch(var(--chart-ramp-6))",
  won: "oklch(var(--moss))",
  lost: "oklch(var(--ink-subtle))"
};

const kort = "rounded-card border border-ink/12 bg-paper p-4 sm:p-5";
const rubrik = "text-[1rem] font-semibold";

/** Ett fel blir null, och rutan visar tankstreck. */
export function useLeadsdata(demo: boolean) {
  const [prospekt, setProspekt] = useState<SuiteProspekt[] | null>(null);
  const [veckor, setVeckor] = useState<Vecka[] | null>(null);

  const hamta = useCallback(
    async <R,>(path: string): Promise<R | null> => {
      if (demo) return (demoOversiktSvar(path) as R | undefined) ?? null;
      try {
        const response = await fetch(`/api/snajp-support${path}`, { cache: "no-store" });
        if (!response.ok) return null;
        return await readJsonBody<R>(response);
      } catch {
        return null;
      }
    },
    [demo]
  );

  const ladda = useCallback(async () => {
    const [p, w] = await Promise.all([
      hamta<{ prospects?: SuiteProspekt[] }>("/leads/prospects?limit=500"),
      hamta<{ weeks?: Vecka[] }>("/analytics/weekly?weeks=24")
    ]);
    setProspekt(p ? (p.prospects ?? []) : []);
    setVeckor(w ? (w.weeks ?? []) : []);
  }, [hamta]);

  useEffect(() => {
    void ladda();
    // En körning eller ett skickat utkast flyttar talen medan man tittar.
    const uppdatera = () => void ladda();
    window.addEventListener("snipra:leads-korning-klar", uppdatera);
    return () => window.removeEventListener("snipra:leads-korning-klar", uppdatera);
  }, [ladda]);

  return { prospekt, veckor };
}

export function LeadsDiagram({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  const { prospekt, veckor } = useLeadsdata(demo);
  const v = veckor ?? [];
  const rader = prospekt ?? [];

  const statusdelar: Andel[] = Object.keys(STATUSFARG).map((s) => ({
    id: s,
    etikett: STATUS_ETIKETT[s],
    antal: rader.filter((p) => (p.status ?? "new") === s).length,
    farg: STATUSFARG[s]
  }));
  const kontaktdelar: Andel[] = KONTAKT.map((k) => ({
    id: k.id,
    etikett: k.etikett,
    farg: k.farg,
    antal: rader.filter((p) => kontaktvagAv(p) === k.id).length
  }));

  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-12">
      <section aria-labelledby="aktivitet-leads-vecka" className={cn(kort, "min-w-0 lg:col-span-7")}>
        <h3 id="aktivitet-leads-vecka" className={cn(rubrik, "mb-4")}>
          {text(T.perVecka)}
        </h3>
        {v.length > 0 ? (
          <>
            <Aktivitetsgraf
              veckor={v.slice(-12)}
              serier={[
                { nyckel: "new_leads", etikett: T.nyaLeads, ton: "chart-ochre" },
                { nyckel: "replies", etikett: T.svar, ton: "chart-blue" }
              ]}
            />
            <p className={cn(meta, "mt-3")}>{text(T.nyaLeadsForklaring)}</p>
          </>
        ) : (
          <p className={meta}>{veckor === null ? "…" : text(T.ingenAktivitet)}</p>
        )}
      </section>
      <section aria-labelledby="aktivitet-leads-fordelning" className={cn(kort, "min-w-0 lg:col-span-5")}>
        <h3 id="aktivitet-leads-fordelning" className={cn(rubrik, "mb-4")}>
          {text(T.fordelning)}
        </h3>
        {prospekt === null ? (
          <p className={meta}>…</p>
        ) : (
          <div className="grid gap-6">
            <Munkdiagram delar={statusdelar} etikett={T.status} mitt={T.leadsMitt} />
            <Munkdiagram delar={kontaktdelar} etikett={T.kontaktvag} mitt={T.leadsMitt} />
          </div>
        )}
      </section>
    </div>
  );
}
