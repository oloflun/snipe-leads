"use client";

import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { PeriodValjare } from "@/components/PeriodValjare";
import { Badge, EmptyState, SkeletonRows } from "@/components/ui";
import type { Underlag } from "@/lib/api";
import { kronor, procent } from "@/lib/format";
import { useBokforing } from "@/lib/useBokforing";

/**
 * Periodens pengar i två riktningar. Summorna kommer ur periodrapporten —
 * inte ur en egen addition här i vyn, så listan och Resultat kan aldrig
 * säga olika saker om samma period.
 *
 * Underlag utan avläst riktning (granskningskön) får en egen sektion i
 * stället för att tyst hamna i någon av kolumnerna.
 */

function Underlagsrad({ rad }: Readonly<{ rad: Underlag }>) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3">
      <span className="num w-[6.5rem] shrink-0 text-[0.9375rem] text-ink/62">
        {rad.datum ?? "—"}
      </span>
      <span className="min-w-0 flex-1 truncate text-[0.9375rem]">{rad.motpart || rad.filnamn}</span>
      {rad.kategori ? (
        <span className="hidden text-[0.875rem] text-ink/50 sm:inline">{rad.kategori}</span>
      ) : null}
      <span className="text-[0.9375rem] text-ink/62">{procent(rad.momssats)}</span>
      <span className="num w-[7.5rem] text-right text-[0.9375rem] font-medium">
        {kronor(rad.brutto)}
      </span>
      {rad.betalstatus === "obetald" ? <Badge tone="warn">Obetald</Badge> : null}
    </div>
  );
}

function Sektion({
  rubrik,
  summa,
  rader,
  tomt
}: Readonly<{ rubrik: string; summa: string | null; rader: Underlag[]; tomt: string }>) {
  return (
    <section>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-display text-[1.25rem]">{rubrik}</h2>
        <span className="num font-display text-[1.125rem]">{summa ? kronor(summa) : "—"}</span>
      </div>
      {rader.length ? (
        <div className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
          {rader.map((rad) => (
            <Underlagsrad key={rad.id} rad={rad} />
          ))}
        </div>
      ) : (
        <p className="mt-3 border-y border-ink/15 py-4 text-[0.9375rem] text-ink/55">{tomt}</p>
      )}
    </section>
  );
}

export function IntakterUtgifterVy() {
  const { underlag, rapport, fel } = useBokforing();
  const laddar = underlag === null && !fel;

  const intakter = (underlag ?? []).filter((rad) => rad.riktning === "intakt");
  const utgifter = (underlag ?? []).filter((rad) => rad.riktning === "kostnad");
  const utanRiktning = (underlag ?? []).filter(
    (rad) => rad.riktning !== "intakt" && rad.riktning !== "kostnad"
  );

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik="Intäkter & utgifter"
        beskrivning="Periodens underlag sorterade på riktning: pengar in och pengar ut. Summorna är periodrapportens — samma tal som under Resultat."
        actions={<PeriodValjare />}
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {laddar ? (
        <SkeletonRows />
      ) : (underlag ?? []).length === 0 ? (
        <EmptyState
          title="Inga underlag i perioden"
          body="Ladda upp kvitton och fakturor hos Bokföringsagenten, så sorteras de in här som intäkter eller utgifter."
        />
      ) : (
        <>
          <Sektion
            rubrik="Intäkter"
            summa={rapport?.summor.intakter ?? null}
            rader={intakter}
            tomt="Inga intäkter i perioden ännu."
          />
          <Sektion
            rubrik="Utgifter"
            summa={rapport?.summor.kostnader ?? null}
            rader={utgifter}
            tomt="Inga utgifter i perioden ännu."
          />
          {utanRiktning.length ? (
            <section>
              <h2 className="font-display text-[1.25rem]">Väntar på granskning</h2>
              <p className="mt-1 max-w-[70ch] text-[0.875rem] text-ink/55">
                Riktningen gick inte att läsa av säkert, så de här räknas inte in någonstans
                förrän de är granskade.{" "}
                <Link href="/pdf-filer" className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4">
                  Se detaljerna under PDF-filer.
                </Link>
              </p>
              <div className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
                {utanRiktning.map((rad) => (
                  <Underlagsrad key={rad.id} rad={rad} />
                ))}
              </div>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
