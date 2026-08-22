"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { PageShell } from "@/components/AppShell";
import { EmptyState, SkeletonRows, btnPrimary } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Bolagssidan — ETT prospekt, med källorna som motiverade poängen.
 *
 * ## Vad den ersatte
 *
 * `CompanyDetailView` läste `findCompany(id)` ur `lib/mock-data.ts`. Den
 * funktionen faller tillbaka på `companies[0]` när id:t inte finns, alltså
 * Byggkompaniet Syd. Ett klick på ett riktigt prospekt visade därför ett
 * PÅHITTAT bolags researchpromemoria — signaler, källor, storlek, allt — under
 * det riktiga bolagets rubrik. En 404 hade varit ärligare; det här såg
 * komplett ut.
 *
 * ## Poängen redovisas, inte bara siffran
 *
 * `score_breakdown` sparas renderad i databasen (migration 031) av exakt det
 * skäl som gäller här: "84/100" utan motivering går inte att lita på, och
 * poängen kan inte räknas om i efterhand eftersom kundens ICP kan ha ändrats
 * sedan körningen. Därför listas kriterierna som de såg ut DÅ.
 */

type Kriterium = {
  nyckel?: string;
  etikett: string;
  vikt?: number;
  utfall: string;
  motivering: string;
  hart?: boolean;
};

type Prospekt = {
  id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  status: string;
  ort: string | null;
  sni: string | null;
  orgnr: string | null;
  website: string | null;
  anstallda: number | null;
  score_total: number | null;
  icp_fit: number | null;
  qualified: boolean | null;
  disqualifiers: string[] | null;
  score_breakdown: Kriterium[] | null;
  created_at: string | null;
};

type Lage =
  | { fas: "laddar" }
  | { fas: "saknas" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; prospekt: Prospekt; kallor: string[] };

const STATUS_ETIKETT: Record<string, string> = {
  new: "Ny",
  researching: "Research pågår",
  ready: "Redo",
  contacted: "Kontaktad",
  replied: "Svarat",
  meeting: "Möte",
  won: "Vunnen",
  lost: "Förlorad",
  suppressed: "Spärrad"
};

export function Bolagssida({ id, demo = false }: Readonly<{ id: string; demo?: boolean }>) {
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });
  const vag = useArbetsvag();

  const hamta = useCallback(async () => {
    setLage({ fas: "laddar" });

    if (demo) {
      // Demon har ingen egen bolagssida-endpoint; prospektet plockas ur samma
      // lista som registret visar. Hittas det inte är det ett riktigt "saknas"
      // och inte ett tyst första-bolag — det var hela buggen.
      const svar = demoOversiktSvar("/leads/prospects") as { prospects?: Prospekt[] } | undefined;
      const träff = svar?.prospects?.find((p) => p.id === id);
      setLage(träff ? { fas: "klar", prospekt: träff, kallor: [] } : { fas: "saknas" });
      return;
    }

    try {
      const response = await fetch(
        `/api/snajp-support/leads/prospects/${encodeURIComponent(id)}`,
        { cache: "no-store" }
      );
      if (response.status === 404) {
        setLage({ fas: "saknas" });
        return;
      }
      if (!response.ok) {
        setLage({
          fas: "fel",
          meddelande:
            response.status >= 500
              ? "Tjänsten svarar inte just nu. Den vaknar ur viloläge och kan ta upp till en minut."
              : `Kunde inte hämta bolaget (status ${response.status}).`
        });
        return;
      }
      const kropp = await readJsonBody<{
        prospect?: Prospekt;
        sources?: string[];
        offline?: boolean;
      }>(response);
      if (!kropp?.prospect || kropp.offline) {
        setLage({ fas: "fel", meddelande: "Backenden svarade utan innehåll." });
        return;
      }
      setLage({ fas: "klar", prospekt: kropp.prospect, kallor: kropp.sources ?? [] });
    } catch (error) {
      setLage({
        fas: "fel",
        meddelande: error instanceof Error ? error.message : "Kunde inte nå servern."
      });
    }
  }, [id, demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  if (lage.fas === "laddar") {
    return (
      <PageShell title="Hämtar bolaget…">
        <SkeletonRows />
      </PageShell>
    );
  }

  if (lage.fas === "saknas") {
    return (
      <PageShell kicker="Företag" title="Bolaget finns inte">
        <EmptyState
          title="Hittade inget sådant bolag"
          body="Prospektet finns inte i din arbetsyta. Det kan ha tagits bort, eller så pekar länken fel."
        />
        <Link href={vag("/dashboard/companies")} className={cn(btnPrimary, "mt-6")}>
          Till bolagen
        </Link>
      </PageShell>
    );
  }

  if (lage.fas === "fel") {
    return (
      <PageShell kicker="Företag" title="Bolaget kunde inte hämtas">
        <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ochre" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm text-ink/70">{lage.meddelande}</p>
            <button
              type="button"
              onClick={() => void hamta()}
              className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
            >
              Försök igen
            </button>
          </div>
        </div>
      </PageShell>
    );
  }

  const { prospekt: p, kallor } = lage;
  const poang =
    typeof p.score_total === "number"
      ? `${p.score_total}/100`
      : typeof p.icp_fit === "number"
        ? `${Math.round(p.icp_fit * 100)}/100`
        : "—";

  return (
    <PageShell
      kicker={[p.sni, p.ort].filter(Boolean).join(" · ") || "Företag"}
      title={p.company_name}
      description={p.website ?? undefined}
      action={
        <Link href={vag("/dashboard/emails")} className={btnPrimary}>
          Skriv mejl <span aria-hidden>↗</span>
        </Link>
      }
    >
      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <dl className="col-span-12 grid grid-cols-12 gap-x-8 gap-y-8">
          <Matt label="Score" value={poang} detail={p.qualified === false ? "diskvalificerad" : "kvalificerad"} />
          <Matt
            label="Anställda"
            value={p.anstallda == null ? "—" : String(p.anstallda)}
            detail={p.orgnr ? `org.nr ${p.orgnr}` : "org.nr saknas"}
          />
          <Matt label="Källor" value={String(kallor.length)} detail="provenienskällor" />
          <Matt label="Status" value={STATUS_ETIKETT[p.status] ?? p.status} detail="nuvarande läge" />
        </dl>

        <section className="col-span-12 md:col-span-7">
          <h2 className="kicker text-mineral">Så räknades poängen</h2>
          {p.score_breakdown?.length ? (
            <ul className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
              {p.score_breakdown.map((k, i) => (
                <li key={`${k.nyckel ?? k.etikett}-${i}`} className="py-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <p className="text-[15px] font-medium">{k.etikett}</p>
                    <span
                      className={cn(
                        "kicker",
                        k.hart && k.utfall === "miss" ? "text-danger" : "text-mineral"
                      )}
                    >
                      {k.utfall}
                      {typeof k.vikt === "number" ? ` · vikt ${k.vikt}` : ""}
                    </span>
                  </div>
                  {k.motivering ? (
                    <p className="mt-1.5 max-w-[65ch] text-[15px] leading-6 text-ink/70">
                      {k.motivering}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 border-y border-ink/15 py-4 text-[15px] text-ink/60">
              Ingen poängmotivering sparad för det här bolaget. Den skrivs vid körningen — ett
              prospekt som lagts till för hand har ingen.
            </p>
          )}

          {p.disqualifiers?.length ? (
            <div className="mt-8">
              <h2 className="kicker text-mineral">Diskvalificerare</h2>
              <ul className="mt-4 space-y-2">
                {p.disqualifiers.map((skäl) => (
                  <li key={skäl} className="border-l-2 border-danger pl-3 text-[15px] text-ink/75">
                    {skäl}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        <section className="col-span-12 md:col-span-5">
          <h2 className="kicker text-mineral">Kontakt</h2>
          <div className="mt-4 border-y border-ink/15 py-4">
            <p className="text-[15px]">{p.contact_name ?? "Ingen kontaktperson hittad"}</p>
            {p.contact_email ? (
              <p className="mt-1 break-all text-sm text-ink/60">{p.contact_email}</p>
            ) : null}
          </div>

          <h2 className="kicker mt-8 text-mineral">Källor</h2>
          {kallor.length ? (
            <ul className="mt-4 space-y-2">
              {kallor.map((url) => (
                <li key={url}>
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="focus-ring break-all text-sm text-ink/70 underline decoration-ink/25 underline-offset-4"
                  >
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-[15px] text-ink/60">
              Inga källor sparade. Utan minst en källa får agenten inte skriva ett utkast — se
              provenienskravet i leads-agentens regler.
            </p>
          )}
        </section>
      </div>
    </PageShell>
  );
}

function Matt({
  label,
  value,
  detail
}: Readonly<{ label: string; value: string; detail: string }>) {
  return (
    <div className="col-span-6 border-t border-ink/15 pt-4 md:col-span-3">
      <dt className="kicker text-mineral">{label}</dt>
      <dd className="num mt-3 text-[1.75rem] font-semibold tabular-nums tracking-[-0.02em]">
        {value}
      </dd>
      <p className="mt-2 text-[14px] leading-6 text-ink/65">{detail}</p>
    </div>
  );
}
