import { Info, LifeBuoy } from "lucide-react";
import { PageShell } from "@/components/AppShell";
import { KvittoChatt } from "@/components/kvitton/KvittoChatt";
import { KvittoSammanfattning, KvittoYta } from "@/components/kvitton/KvittoYta";
import { KONTAKT_MEJL } from "@/components/marketing/copy";

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
  return (
    <PageShell
      title="Kvitton, direkt ur inkorgen"
      description="Koppla mejlen, så läser agenten inkommande kvitton och utlägg åt dig: belopp, moms, datum, butik och kategori — med dublettkontroll och en sammanfattning som går ihop. Du kan också ladda upp kvitton själv."
    >
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
          Förslag, inte bokföring
          <span aria-hidden className="text-ink-subtle transition-transform group-open:rotate-90">
            ›
          </span>
        </summary>
        <p className="mt-3 max-w-[78ch] text-[0.8125rem] leading-6 text-ink-subtle">
          Kvittohanteraren läser av och sammanställer dina kvitton. Beloppen är
          avlästa maskinellt och ska granskas av en människa innan de används i
          bokföring eller deklaration.
        </p>
      </details>

      <section className="mt-8 border-t border-ink/15 pt-6">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.875rem] leading-6 text-ink-muted">
          <LifeBuoy className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
          Ser något fel ut i en avläsning eller en summa?
          <a
            href={`mailto:${KONTAKT_MEJL}?subject=${encodeURIComponent("Snajp Kvittohanteraren — felanmälan")}&body=${encodeURIComponent(
              ["Beskriv gärna kort:", "", "1. Vilket kvitto eller vilken period gäller det?", "2. Vad blev fel?", "3. Vad hade du förväntat dig i stället?", ""].join("\n")
            )}`}
            className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-ochre"
          >
            Anmäl det till oss
          </a>
          <span className="text-ink-subtle">så tittar vi på det.</span>
        </p>
      </section>
    </PageShell>
  );
}
