"use client";

import { ArrowRight, ScanLine } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { PeriodValjare } from "@/components/PeriodValjare";
import { Badge, SkeletonRows, btnLiten, btnPrimary } from "@/components/ui";
import { kronor, procent } from "@/lib/format";
import { useProfil } from "@/lib/profil";
import { useBokforing } from "@/lib/useBokforing";
import { cn } from "@/lib/utils";

/**
 * Första vyn: läget i perioden, i fyra tal, och vägen vidare. Ruled rows i
 * stället för kortmatta — DESIGN.md:s App-familj.
 */

const NYCKELTAL: Array<{ nyckel: string; etikett: string }> = [
  { nyckel: "resultat_fore_skatt", etikett: "Resultat före skatt" },
  { nyckel: "moms_att_betala", etikett: "Moms att betala" },
  { nyckel: "intakter", etikett: "Intäkter" },
  { nyckel: "kostnader", etikett: "Kostnader" }
];

export function OversiktVy() {
  const { underlag, rapport, fel } = useBokforing();
  const { profil } = useProfil();

  const attGranska = (underlag ?? []).filter((rad) => rad.status === "granska_manuellt").length;
  const senaste = (underlag ?? []).slice(0, 5);
  const laddar = underlag === null;

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik={profil.foretagsnamn ? `Bokföringen — ${profil.foretagsnamn}` : "Översikt"}
        beskrivning="Siffrorna nedan är räknade ur periodens avlästa underlag. Ingenting är gissat: det som inte gick att läsa ligger i granskningskön i stället."
        actions={<PeriodValjare />}
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {/* Nyckeltalen. Hårlinjer skiljer kolumnerna, inte kort. */}
      <section aria-label="Periodens nyckeltal">
        <dl className="grid gap-y-6 border-y border-ink/15 py-6 sm:grid-cols-2 lg:grid-cols-4 lg:divide-x lg:divide-ink/12">
          {NYCKELTAL.map(({ nyckel, etikett }, i) => (
            <div key={nyckel} className={cn("min-w-0", i > 0 && "lg:pl-8", i < 3 && "lg:pr-8")}>
              <dt className="text-[0.8125rem] font-medium text-ink/55">{etikett}</dt>
              <dd
                className={cn(
                  "numeral mt-2 truncate text-[1.75rem] lg:text-[2rem]",
                  nyckel === "moms_att_betala" ? "text-ochre" : "text-ink"
                )}
                title={etikett}
              >
                {laddar || !rapport ? "—" : kronor(rapport.summor[nyckel])}
              </dd>
            </div>
          ))}
        </dl>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-[0.875rem] text-ink/60">
          {rapport ? (
            <>
              <span className="num">
                {rapport.antal_underlag} underlag · {rapport.antal_verifikat} verifikat i perioden
              </span>
              {rapport.status === "klar" ? (
                <Badge tone="good">Perioden går ihop</Badge>
              ) : (
                <Badge tone="warn">
                  {rapport.brister.length} sak{rapport.brister.length === 1 ? "" : "er"} att titta på
                </Badge>
              )}
            </>
          ) : laddar ? (
            <span>Hämtar periodens siffror …</span>
          ) : null}
          {attGranska > 0 ? (
            <Link href="/pdf-filer" className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4 hover:text-ink">
              {attGranska} underlag väntar på granskning
            </Link>
          ) : null}
        </div>
      </section>

      {/* Senaste underlagen + vägen in. */}
      <section>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-[1.25rem]">Senaste underlag</h2>
          <Link href="/agenten" className={cn(btnPrimary, btnLiten)}>
            <ScanLine className="h-4 w-4" aria-hidden />
            Ladda upp underlag
          </Link>
        </div>

        {laddar ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : senaste.length === 0 ? (
          <div className="mt-4 border-y border-ink/15 py-10 text-center">
            <p className="font-display text-[1.375rem] text-ink">
              Perioden är tom — börja med ett kvitto.
            </p>
            <p className="mx-auto mt-2 max-w-[52ch] text-[0.9375rem] leading-6 text-ink/60">
              Släpp en PDF eller ett foto hos Bokföringsagenten, så läses den igenom två gånger
              och siffrorna landar här.
            </p>
            <Link href="/agenten" className={cn(btnPrimary, "mt-5")}>
              Till Bokföringsagenten
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        ) : (
          <>
            <div className="mt-4 divide-y divide-ink/12 border-y border-ink/15">
              {senaste.map((rad) => (
                <div key={rad.id} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3">
                  <span className="num w-[6.5rem] shrink-0 text-[0.9375rem] text-ink/62">
                    {rad.datum ?? "—"}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[0.9375rem]">
                    {rad.motpart || rad.filnamn}
                  </span>
                  <span className="text-[0.9375rem] text-ink/62">{procent(rad.momssats)}</span>
                  <span className="num w-[7.5rem] text-right text-[0.9375rem] font-medium">
                    {kronor(rad.brutto)}
                  </span>
                  <Badge tone={rad.status === "granska_manuellt" ? "warn" : "good"}>
                    {rad.status === "granska_manuellt" ? "Granska" : "Klar"}
                  </Badge>
                </div>
              ))}
            </div>
            <Link
              href="/pdf-filer"
              className="focus-ring mt-3 inline-flex items-center gap-1.5 rounded-[4px] text-[0.875rem] text-ink/60 hover:text-ink"
            >
              Alla underlag i perioden
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
          </>
        )}
      </section>
    </div>
  );
}
