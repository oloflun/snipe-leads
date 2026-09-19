"use client";

import { LeadsControls } from "@/components/leads/LeadsControls";
import { IrisEskalering } from "@/components/leads/IrisEskalering";
import { GRANSER } from "@/lib/iris";

/**
 * Iris › Inställningar — målgrupp och autonomi (LeadsControls, oförändrad),
 * gränserna Iris alltid håller (GRANSER, läsbara), och eskaleringsreglerna
 * (redigerbara i drift, läsbara i demo).
 *
 * `#granser` är ankaret Bolag-sidans "Så arbetar Iris"-länk pekar på.
 */
export function IrisInstallningar({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <div className="grid gap-12">
      <section>
        {/* Kicker, inte rubrik — se motiveringen i sektionen nedan. */}
        <p className="kicker text-mineral">Målgrupp och autonomi</p>
        <div className="mt-5">
          {/* Kön hör hemma i Iris › Granskning, inte här också — se
              components/leads/IrisGranskning.tsx. */}
          <LeadsControls demo={demo} visaKo={false} />
        </div>
      </section>

      <section id="granser" className="scroll-mt-6 border-t border-ink/15 pt-8">
        {/* Kicker, inte rubrik: sidans enda rubrikkedja går h1 → h2 → h3 via
            raden nedan, inte via kickern. Låg det som h3 direkt under sidans
            h1 utan mellanliggande h2 — axe heading-order, moderate,
            2026-09-19. */}
        <p className="kicker text-mineral">Så arbetar Iris</p>
        <h2 className="mt-2 font-display text-[1.25rem]">
          Det här gör Iris <span className="italic text-warning">aldrig</span> utan din granskning
        </h2>
        <ul className="mt-4 divide-y divide-ink/12 border-y border-ink/15">
          {GRANSER.map((grans) => (
            <li key={grans.rubrik} className="flex flex-wrap gap-x-8 gap-y-1 py-4">
              <h3 className="w-64 shrink-0 text-[0.9375rem] font-semibold text-ink">{grans.rubrik}</h3>
              <p className="min-w-0 flex-1 basis-72 text-[0.9375rem] leading-6 text-ink-muted">
                {grans.text}
              </p>
            </li>
          ))}
        </ul>
        <p className="mt-3 max-w-[70ch] text-[0.8125rem] leading-5 text-ink-subtle">
          Gränserna sitter i systemet, inte i en policytext: granskningskön, avregistreringen och
          källkravet är spärrar i koden.
        </p>
      </section>

      {demo ? (
        <p className="border-t border-ink/15 pt-8 text-[13px] leading-6 text-ink-subtle">
          Eskaleringsreglerna är kundens riktiga inställningar och redigeras inte i demon. I
          drift ställer ni in dem här, under samma rubrik.
        </p>
      ) : (
        <div className="border-t border-ink/15 pt-8">
          <IrisEskalering />
        </div>
      )}
    </div>
  );
}
