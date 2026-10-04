"use client";

import { Info, LifeBuoy } from "lucide-react";
import { PageShell } from "@/components/AppShell";
import { KvittoChatt } from "@/components/kvitton/KvittoChatt";
import { KvittoSammanfattning, KvittoYta } from "@/components/kvitton/KvittoYta";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { useLocale } from "@/lib/i18n";

/**
 * Kvittohanterarens flik i arbetsytan. Serverskal, klientpanel — samma
 * delning som resten av arbetsytan, och samma tvåkolumnsresonemang som den
 * gamla bokföringsvyn: arbetet till vänster (skanning, kvitton, uppladdning),
 * frågan om arbetet till höger (sammanfattning + assistent), klistrad så att
 * den följer med genom kvittolistan.
 *
 * Grinden sitter INTE här utan i WorkspaceSection, på servern.
 */
export function KvittoVy() {
  const { text } = useLocale();
  return (
    <PageShell title={{ sv: "Kvitton", en: "Receipts" }}>
      <div className="grid grid-cols-12 gap-x-0 gap-y-12 lg:gap-x-10">
        <div className="col-span-12 lg:col-span-7">
          <KvittoYta />
        </div>

        <aside className="col-span-12 lg:col-span-5">
          <div className="space-y-6 lg:sticky lg:top-24">
            <KvittoSammanfattning />
            <KvittoChatt />
          </div>
        </aside>
      </div>

      {/* Förbehållet, hopfällt — en rad stängd, hela texten ett klick bort.
          Originalet är FORBEHALL i app/agent/kvitto_agent.py. */}
      <details className="group mt-10 border-t border-ink/15 pt-4">
        <summary className="focus-ring flex cursor-pointer list-none items-center gap-2 rounded-input text-[0.8125rem] text-ink-subtle hover:text-ink-muted">
          <Info className="h-3.5 w-3.5 shrink-0" aria-hidden />
          {text({ sv: "Förslag, inte bokföring", en: "Suggestions, not bookkeeping" })}
          <span aria-hidden className="text-ink-subtle transition-transform group-open:rotate-90">
            ›
          </span>
        </summary>
        <p className="mt-3 max-w-[78ch] text-[0.8125rem] leading-6 text-ink-subtle">
          {text({
            sv: "Beloppen är maskinellt avlästa och ska granskas av en människa innan de används i bokföring eller deklaration.",
            en: "The amounts are read by machine and must be checked by a person before they are used in bookkeeping or a tax return."
          })}
        </p>
      </details>

      <section className="mt-8 border-t border-ink/15 pt-6">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.875rem] leading-6 text-ink-muted">
          <LifeBuoy className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
          {text({ sv: "Fel i en avläsning?", en: "Wrong reading?" })}
          <a
            href={`mailto:${KONTAKT_MEJL}?subject=${encodeURIComponent(text({ sv: "Snajp Kvittohanteraren — felanmälan", en: "Snajp Receipts: error report" }))}&body=${encodeURIComponent(
              text({
                sv: "Beskriv gärna kort:\n\n1. Vilket kvitto eller vilken period gäller det?\n2. Vad blev fel?\n3. Vad hade du förväntat dig i stället?\n",
                en: "Please describe briefly:\n\n1. Which receipt or period is it about?\n2. What went wrong?\n3. What did you expect instead?\n"
              })
            )}`}
            className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-ochre"
          >
            {text({ sv: "Anmäl det", en: "Report it" })}
          </a>
        </p>
      </section>
    </PageShell>
  );
}
