"use client";

import { LeadsControls } from "@/components/leads/LeadsControls";
import { IrisAutomation } from "@/components/leads/IrisAutomation";
import { IrisEskalering } from "@/components/leads/IrisEskalering";
import { IrisProfil } from "@/components/leads/IrisProfil";
import { useLocale } from "@/lib/i18n";

/**
 * Inställningar › Iris — målgrupp och autonomi (LeadsControls, oförändrad)
 * och eskaleringsreglerna (redigerbara i drift, läsbara i demo). Bodde som
 * egen sida under Iris fram till Snajp Suite 2026-10-03; nu renderas den av
 * /settings/leads (WorkspaceViews) och demons /demo/installningar.
 *
 * Gränslistan (GRANSER i lib/iris.ts) och "Så arbetar Iris"-sektionen togs
 * bort ur arbetsytan 2026-09-19: förklarande text, inget att ställa in.
 */
export function IrisInstallningar({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  return (
    <div className="grid gap-12">
      <IrisProfil demo={demo} />

      <section className="border-t border-ink/15 pt-8">
        {/* Kicker, inte rubrik: en h3 direkt under sidans h1 utan
            mellanliggande h2 bryter axe heading-order (moderate, 2026-09-19). */}
        <p className="kicker text-mineral">{text({ sv: "Målgrupp och autonomi", en: "Target group and autonomy" })}</p>
        <div className="mt-5">
          {/* Kön hör hemma i Att göra, inte här också — se
              components/leads/IrisGranskning.tsx. */}
          <LeadsControls demo={demo} visaKo={false} />
        </div>
      </section>

      {demo ? (
        <p className="border-t border-ink/15 pt-8 text-[13px] leading-6 text-ink-subtle">
          {text({
            sv: "Överlämning och automation redigeras inte i demon.",
            en: "Handover and automation are not editable in the demo."
          })}
        </p>
      ) : (
        <>
          <div className="border-t border-ink/15 pt-8">
            <IrisEskalering />
          </div>
          <div className="border-t border-ink/15 pt-8">
            <IrisAutomation />
          </div>
        </>
      )}
    </div>
  );
}
