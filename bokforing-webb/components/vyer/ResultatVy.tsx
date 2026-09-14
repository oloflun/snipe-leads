"use client";

import { AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PeriodValjare } from "@/components/PeriodValjare";
import { SkeletonRows } from "@/components/ui";
import { kronor, preliminarBolagsskatt, somTal } from "@/lib/format";
import { useBokforing } from "@/lib/useBokforing";

/**
 * Resultaträkningen för perioden — samma summor som backendens periodrapport,
 * rad för rad, plus två saker som är UPPSKATTNINGAR och märks som det:
 * proportionsstaplarna (visualisering, inte bokföring) och den preliminära
 * bolagsskatten (20,6 %, satsen sedan 2021, räknad i ören — se lib/format.ts).
 */

const RESULTATRADER: Array<{ nyckel: string; etikett: string }> = [
  { nyckel: "intakter", etikett: "Intäkter" },
  { nyckel: "kostnader", etikett: "Kostnader" },
  { nyckel: "resultat_fore_skatt", etikett: "Resultat före skatt" }
];

const MOMSRADER: Array<{ nyckel: string; etikett: string }> = [
  { nyckel: "utgaende_moms", etikett: "Utgående moms (på försäljning)" },
  { nyckel: "ingaende_moms", etikett: "Ingående moms (på inköp)" },
  { nyckel: "moms_att_betala", etikett: "Moms att betala" }
];

export function ResultatVy() {
  const { underlag, rapport, fel } = useBokforing();
  const laddar = underlag === null && !fel;

  const skatt = rapport ? preliminarBolagsskatt(rapport.summor.resultat_fore_skatt) : null;

  const intakter = rapport ? somTal(rapport.summor.intakter) : 0;
  const kostnader = rapport ? somTal(rapport.summor.kostnader) : 0;
  const storst = Math.max(intakter, kostnader, 1);

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik="Resultat"
        beskrivning="Räknat ur periodens godkända verifikat. Momsen räknas av kod ur bruttobeloppen — modellen läser bara av, den räknar aldrig."
        actions={<PeriodValjare />}
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {laddar ? (
        <SkeletonRows />
      ) : rapport ? (
        <>
          {/* Proportionerna, som en läsbar bild av samma tal. */}
          <section aria-label="Intäkter mot kostnader">
            <div className="space-y-4 border-y border-ink/15 py-5">
              {[
                { etikett: "Intäkter", varde: intakter, rag: rapport.summor.intakter, klass: "bg-moss/70" },
                { etikett: "Kostnader", varde: kostnader, rag: rapport.summor.kostnader, klass: "bg-ink/55" }
              ].map((stapel) => (
                <div key={stapel.etikett}>
                  <div className="flex items-baseline justify-between gap-4 text-[0.9375rem]">
                    <span className="text-ink/62">{stapel.etikett}</span>
                    <span className="num font-medium">{kronor(stapel.rag)}</span>
                  </div>
                  <div className="mt-1.5 h-2 rounded-full bg-ink/[0.06]">
                    <div
                      className={`h-2 rounded-full ${stapel.klass}`}
                      style={{ width: `${Math.max((stapel.varde / storst) * 100, stapel.varde > 0 ? 2 : 0)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[0.8125rem] text-ink/50">
              Staplarna visar proportioner — beloppen bredvid är de bokförda talen.
            </p>
          </section>

          {/* Resultaträkningen. */}
          <section>
            <h2 className="font-display text-[1.25rem]">Resultaträkning</h2>
            <dl className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
              {RESULTATRADER.map(({ nyckel, etikett }) => (
                <div key={nyckel} className="flex items-baseline justify-between gap-4 py-3">
                  <dt className="text-[0.9375rem] text-ink/62">{etikett}</dt>
                  <dd className="num font-display text-[1.125rem]">{kronor(rapport.summor[nyckel])}</dd>
                </div>
              ))}
            </dl>

            <h2 className="mt-8 font-display text-[1.25rem]">Moms</h2>
            <dl className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
              {MOMSRADER.map(({ nyckel, etikett }) => (
                <div key={nyckel} className="flex items-baseline justify-between gap-4 py-3">
                  <dt className="text-[0.9375rem] text-ink/62">{etikett}</dt>
                  <dd className="num font-display text-[1.125rem]">{kronor(rapport.summor[nyckel])}</dd>
                </div>
              ))}
            </dl>
          </section>

          {/* Skatteuppskattningen — märkt som en sådan. */}
          <section>
            <h2 className="font-display text-[1.25rem]">Preliminär skatt</h2>
            <dl className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
              <div className="flex items-baseline justify-between gap-4 py-3">
                <dt className="text-[0.9375rem] text-ink/62">Preliminär bolagsskatt (20,6 %)</dt>
                <dd className="num font-display text-[1.125rem]">
                  {skatt === null ? "—" : kronor(skatt)}
                </dd>
              </div>
            </dl>
            <p className="mt-2 max-w-[70ch] text-[0.8125rem] leading-5 text-ink/50">
              En uppskattning räknad som 20,6 procent av periodens resultat före skatt, utan
              hänsyn till avdrag, periodiseringsfonder eller tidigare underskott. Den är ett
              riktmärke, inte ett deklarationsunderlag.
            </p>
          </section>

          {rapport.brister.length ? (
            <section>
              <p className="flex items-center gap-2 text-[0.9375rem] font-semibold text-ink">
                <AlertTriangle className="h-4 w-4 text-ochre" aria-hidden />
                {rapport.brister.length} sak{rapport.brister.length === 1 ? "" : "er"} att titta på
                innan perioden går ihop
              </p>
              <ul className="mt-2 max-w-[78ch] space-y-1 text-[0.9375rem] text-ink/70">
                {rapport.brister.map((brist) => (
                  <li key={brist}>{brist}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
