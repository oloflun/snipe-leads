"use client";

import { LeadsControls } from "@/components/leads/LeadsControls";
import { IrisEskalering } from "@/components/leads/IrisEskalering";

/**
 * Iris › Inställningar — målgrupp och autonomi (LeadsControls, oförändrad)
 * och eskaleringsreglerna (redigerbara i drift, läsbara i demo).
 *
 * Gränslistan (GRANSER i lib/iris.ts) och "Så arbetar Iris"-sektionen togs
 * bort ur arbetsytan 2026-09-19: förklarande text, inget att ställa in.
 */
export function IrisInstallningar({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <div className="grid gap-12">
      <section>
        {/* Kicker, inte rubrik: en h3 direkt under sidans h1 utan
            mellanliggande h2 bryter axe heading-order (moderate, 2026-09-19). */}
        <p className="kicker text-mineral">Målgrupp och autonomi</p>
        <div className="mt-5">
          {/* Kön hör hemma i Iris › Granskning, inte här också — se
              components/leads/IrisGranskning.tsx. */}
          <LeadsControls demo={demo} visaKo={false} />
        </div>
      </section>

      {demo ? (
        <p className="border-t border-ink/15 pt-8 text-[13px] leading-6 text-ink-subtle">
          Eskaleringsreglerna redigeras inte i demon.
        </p>
      ) : (
        <div className="border-t border-ink/15 pt-8">
          <IrisEskalering />
        </div>
      )}
    </div>
  );
}
