"use client";

import Link from "next/link";
import { useArbetsvag } from "@/components/AppShell";
import { LeadsControls } from "@/components/leads/LeadsControls";
import { IrisAutomation } from "@/components/leads/IrisAutomation";
import { IrisEskalering } from "@/components/leads/IrisEskalering";
import { IrisProdukter } from "@/components/leads/IrisProdukter";
import { IrisProfil } from "@/components/leads/IrisProfil";
import { AgentOnskemal } from "@/components/settings/AgentOnskemal";
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
  const arbetsvag = useArbetsvag();
  return (
    <div className="grid gap-12">
      <IrisProfil demo={demo} />

      <section className="border-t border-ink/15 pt-8">
        <div>
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
            <IrisProdukter />
          </div>
          {/* Erbjudandena flyttade till Leads › Erbjudanden (Anton 2026-10-25). */}
          <p className="border-t border-ink/15 pt-8 text-[0.9375rem] leading-6 text-ink-muted">
            {text({
              sv: "Erbjudandena i mejlen och kampanjerna ställer du in under ",
              en: "The offers in the emails and the campaigns are set up under "
            })}
            <Link href={arbetsvag("/dashboard/leads?vy=erbjudanden")} className="focus-ring underline underline-offset-4">
              {text({ sv: "Leads › Erbjudanden", en: "Leads › Offers" })}
            </Link>
            .
          </p>
          <div className="border-t border-ink/15 pt-8">
            <IrisAutomation />
          </div>
          <div className="border-t border-ink/15 pt-8">
            <AgentOnskemal agent="leads" />
          </div>
        </>
      )}
    </div>
  );
}
