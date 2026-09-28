"use client";

import { LeadsControls } from "@/components/leads/LeadsControls";
import { IrisEskalering } from "@/components/leads/IrisEskalering";
import { Rad, Radlista, Sektion, Tomt, rubrikPanel } from "@/components/ui";
import { GRANSER } from "@/lib/iris";
import { cn } from "@/lib/utils";

/**
 * Iris › Inställningar — målgrupp och autonomi (LeadsControls),
 * gränserna Iris alltid håller (GRANSER, läsbara), och eskaleringsreglerna
 * (redigerbara i drift, läsbara i demo).
 *
 * `#granser` är ankaret Bolag-sidans "Så arbetar Iris"-länk pekar på.
 *
 * Varje del är en `Sektion` (h2) sedan 2026-09-27. Kickrarna som stod här i
 * stället för rubriker (axe heading-order 2026-09-19) var mikrotext enligt
 * F-016. Överraden "Målgrupp och autonomi" är borta helt: LeadsControls bär
 * sina två sektionsrubriker själv, och en tredje ovanför dem sa samma sak.
 */
export function IrisInstallningar({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <div>
      {/* Kön hör hemma i Iris › Granskning, inte här också — se
          components/leads/IrisGranskning.tsx. */}
      <LeadsControls demo={demo} visaKo={false} />

      <div id="granser" className="mt-12 scroll-mt-6">
        <Sektion title="Det här gör Iris aldrig utan din granskning">
          <Radlista>
            {GRANSER.map((grans) => (
              <Rad key={grans.rubrik} className="flex flex-wrap gap-x-8 gap-y-1">
                <h3 className={cn(rubrikPanel, "w-64 shrink-0")}>{grans.rubrik}</h3>
                <p className="min-w-0 flex-1 basis-72 text-[0.9375rem] leading-6 text-ink-muted">
                  {grans.text}
                </p>
              </Rad>
            ))}
          </Radlista>
        </Sektion>
      </div>

      {demo ? (
        <Sektion title="När Iris lämnar över till dig">
          <Tomt>Eskaleringsreglerna ställer du in när du har ett eget konto.</Tomt>
        </Sektion>
      ) : (
        <IrisEskalering />
      )}
    </div>
  );
}
