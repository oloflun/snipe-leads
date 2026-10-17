"use client";

import { useEffect, useRef, useState } from "react";
import { ImportCsv, type ImporteradLista } from "@/components/leads/ImportCsv";
import { btnSecondary } from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * "Ladda upp befintlig CRM-kundlista" (Sebbes beställning 2026-10-06).
 *
 * Kunden — eller Snajp-admin i kundens vy — laddar upp sina befintliga kunder
 * ur sitt CRM. De sparas som en lista med `kalla='crm'` (migration 098) och
 * blir en uteslutningsmängd: Iris och listbygget hoppar över varje bolag i den
 * (snajp-support/app/leads/upptagna.py). Inget prospekteras ur den.
 *
 * Står överst i Leads › Listor, även utan listtillägget: uteslutningen gäller
 * Iris också. `startOppen` kommer från `?crm=1`, länken på översikten.
 */

const T = {
  rubrik: { sv: "Befintliga kunder från ditt CRM", en: "Existing customers from your CRM" },
  hjalp: {
    sv: "Ladda upp en CSV-export av din kundlista ur HubSpot, Pipedrive, Salesforce, Upsales eller ett eget kalkylark. Iris och leadslistorna hoppar sedan över de bolagen, så att du aldrig får en befintlig kund som lead.",
    en: "Upload a CSV export of your customer list from HubSpot, Pipedrive, Salesforce, Upsales or your own spreadsheet. Iris and the lead lists then skip those companies, so an existing customer never shows up as a lead."
  },
  ladda: { sv: "Ladda upp befintlig CRM-kundlista", en: "Upload existing CRM customer list" },
  stang: { sv: "Stäng uppladdningen", en: "Close the upload" }
} satisfies Record<string, Localized>;

export function CrmKundlista({
  demo = false,
  startOppen = false,
  onKlar
}: Readonly<{ demo?: boolean; startOppen?: boolean; onKlar?: (lista: ImporteradLista) => void }>) {
  const { text } = useLocale();
  const [oppen, setOppen] = useState(startOppen);
  const ref = useRef<HTMLElement | null>(null);

  // Från översiktens länk: panelen ska synas direkt, inte ligga under vecket.
  useEffect(() => {
    if (startOppen) ref.current?.scrollIntoView({ block: "start" });
  }, [startOppen]);

  return (
    <section ref={ref} aria-labelledby="crm-kundlista" className="scroll-mt-32 rounded-card border border-ink/12 bg-paper2/40 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0 max-w-[64ch]">
          <h2 id="crm-kundlista" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
            {text(T.rubrik)}
          </h2>
          <p className="mt-1 text-[14px] leading-6 text-ink-subtle">{text(T.hjalp)}</p>
        </div>
        <button
          type="button"
          aria-expanded={oppen}
          aria-controls="crm-kundlista-uppladdning"
          onClick={() => setOppen((v) => !v)}
          className={btnSecondary}
        >
          {oppen ? text(T.stang) : text(T.ladda)}
        </button>
      </div>
      {oppen ? (
        <div id="crm-kundlista-uppladdning" className="mt-5 border-t border-ink/12 pt-5">
          <ImportCsv kalla="crm" demo={demo} onKlar={(lista) => onKlar?.(lista)} />
        </div>
      ) : null}
    </section>
  );
}
