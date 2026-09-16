"use client";

import { ArrowRight, ScanLine } from "lucide-react";
import Link from "next/link";
import { Integritetsnotis } from "@/components/Integritetsnotis";
import { PageHeader } from "@/components/PageHeader";
import { PeriodValjare } from "@/components/PeriodValjare";
import { Badge, SkeletonRows, btnLiten, btnPrimary } from "@/components/ui";
import { kronor } from "@/lib/format";
import { useProfil } from "@/lib/profil";
import { useKvitton } from "@/lib/kvitton";
import { cn } from "@/lib/utils";

/**
 * Första vyn: periodens kvitton i fyra tal, kategorierna, sammanfattningen i
 * klartext och vägen vidare. Ruled rows i stället för kortmatta —
 * DESIGN.md:s App-familj, samma form som den gamla översikten hade.
 */
export function OversiktVy() {
  const { kvitton, samman, fel } = useKvitton();
  const { profil } = useProfil();

  const laddar = kvitton === null;
  const senaste = (kvitton ?? []).slice(-5).reverse();

  const nyckeltal: Array<{ etikett: string; varde: string; ochre?: boolean }> = samman
    ? [
        { etikett: "Summa utlägg", varde: kronor(samman.totalt) },
        { etikett: "Ingående moms", varde: kronor(samman.moms), ochre: true },
        { etikett: "Kvitton i perioden", varde: String(samman.antal) },
        { etikett: "Väntar på granskning", varde: String(samman.antal_granska) }
      ]
    : [];

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik={profil.foretagsnamn ? `Kvittona — ${profil.foretagsnamn}` : "Översikt"}
        beskrivning="Siffrorna nedan är räknade ur periodens avlästa kvitton. Ingenting är gissat: det som inte gick att läsa väntar i granskningskön i stället."
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
          {(nyckeltal.length
            ? nyckeltal
            : [
                { etikett: "Summa utlägg", varde: "—" },
                { etikett: "Ingående moms", varde: "—" },
                { etikett: "Kvitton i perioden", varde: "—" },
                { etikett: "Väntar på granskning", varde: "—" }
              ]
          ).map((tal, i) => (
            <div key={tal.etikett} className={cn("min-w-0", i > 0 && "lg:pl-8", i < 3 && "lg:pr-8")}>
              <dt className="text-[0.8125rem] font-medium text-ink/55">{tal.etikett}</dt>
              <dd
                className={cn(
                  "numeral mt-2 truncate text-[1.75rem] lg:text-[2rem]",
                  "ochre" in tal && tal.ochre ? "text-ochre" : "text-ink"
                )}
                title={tal.etikett}
              >
                {tal.varde}
              </dd>
            </div>
          ))}
        </dl>
        {samman?.text ? (
          <p className="mt-4 max-w-[78ch] text-[0.9375rem] leading-7 text-ink/70">{samman.text}</p>
        ) : laddar ? (
          <p className="mt-3 text-[0.875rem] text-ink/60">Hämtar periodens siffror …</p>
        ) : null}
      </section>

      {/* Kategorierna. */}
      {samman && samman.per_kategori.length ? (
        <section>
          <h2 className="font-display text-[1.25rem]">Per kategori</h2>
          <dl className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
            {samman.per_kategori.map((rad) => (
              <div key={rad.kategori} className="flex items-baseline justify-between gap-4 py-3">
                <dt className="min-w-0 truncate text-[0.9375rem] text-ink/75">
                  {rad.etikett}
                  <span className="ml-2 text-[0.8125rem] text-mineral">×{rad.antal}</span>
                </dt>
                <dd className="num text-[0.9375rem] font-medium">{kronor(rad.summa)}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}

      {/* Senaste kvittona + vägen in. */}
      <section>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-[1.25rem]">Senaste kvitton</h2>
          <Link href="/inkorgen" className={cn(btnPrimary, btnLiten)}>
            <ScanLine className="h-4 w-4" aria-hidden />
            Skanna inkorgen
          </Link>
        </div>

        {laddar ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : senaste.length === 0 ? (
          <div className="mt-4 border-y border-ink/15 py-10 text-center">
            <p className="font-display text-[1.375rem] text-ink">
              Perioden är tom — låt inkorgen fylla den.
            </p>
            <p className="mx-auto mt-2 max-w-[52ch] text-[0.9375rem] leading-6 text-ink/60">
              Kör en skanning av den kopplade inkorgen, eller ladda upp ett kvitto
              under Kvitton, så landar siffrorna här.
            </p>
            <Link href="/inkorgen" className={cn(btnPrimary, "mt-5")}>
              Till Inkorgen
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
                    {rad.motpart || rad.mejl_amne || rad.filnamn}
                  </span>
                  <span className="text-[0.875rem] text-ink/62">{rad.kategorietikett}</span>
                  <span className="num w-[7.5rem] text-right text-[0.9375rem] font-medium">
                    {rad.brutto !== null ? kronor(rad.brutto) : (rad.belopp_original ?? "—")}
                  </span>
                  <Badge tone={rad.status === "granska_manuellt" ? "warn" : "good"}>
                    {rad.status === "granska_manuellt" ? "Granska" : "Klar"}
                  </Badge>
                </div>
              ))}
            </div>
            <Link
              href="/kvitton"
              className="focus-ring mt-3 inline-flex items-center gap-1.5 rounded-[4px] text-[0.875rem] text-ink/60 hover:text-ink"
            >
              Alla kvitton i perioden
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
          </>
        )}
      </section>

      <Integritetsnotis />
    </div>
  );
}
