"use client";

import { ShieldAlert } from "lucide-react";
import { useState } from "react";
import { Dashboard as SupportDashboard } from "@/components/snajp/Dashboard";
import { CHATTFRAGOR } from "@/lib/demo/support-chatt";
import { cn } from "@/lib/utils";

/**
 * Demons kundtjänst: inkorgen OCH kundchatten, i samma flikmönster som
 * arbetsytans SupportWorkspaceTabs (border-ochre på aktiv flik).
 *
 * ## Varför chatten är förladdad
 *
 * Arbetsytans testchatt kör riktig AI mot den inloggade tenantens kunskapsbas.
 * Här finns ingen tenant och ingen session, och en LLM-körning per anonym
 * besökare kostar pengar och kan svara olika varje gång. Besökaren väljer
 * i stället fråga och svaret fälls ut — samma mönster som bokföringsdemons
 * chatt, och det står på sidan. En av frågorna eskalerar med flit: gränsen
 * är en del av produkten.
 */

function Kundchatt() {
  const [stallda, setStallda] = useState<number[]>([]);
  const kvar = CHATTFRAGOR.map((_, i) => i).filter((i) => !stallda.includes(i));

  return (
    <div className="max-w-[720px]">
      <p className="text-[0.8125rem] leading-6 text-ink/55">
        <strong className="font-semibold text-ink/70">Exempel.</strong> Butiken
        Nordlys Handel är påhittad och svaren skrivna i förväg ur dess
        kunskapsbas — ingen modell körs på den här sidan. I produkten svarar
        agenten ur ER kunskapsbas, på riktigt.
      </p>

      <div className="mt-4 grid gap-3">
        {stallda.map((i) => (
          <div key={i} className="grid gap-3">
            <p className="ml-auto max-w-[92%] rounded-card bg-paper2 px-3.5 py-2.5 text-[0.875rem] leading-6 text-ink">
              {CHATTFRAGOR[i].fraga}
            </p>
            <div className="max-w-[92%]">
              {CHATTFRAGOR[i].eskalerar ? (
                <p className="mb-1.5 inline-flex items-center gap-1.5 text-[0.75rem] font-medium text-danger">
                  <ShieldAlert className="h-3.5 w-3.5" aria-hidden />
                  Eskalerat till en människa
                </p>
              ) : null}
              <p className="whitespace-pre-wrap rounded-card border border-ink/15 px-3.5 py-2.5 text-[0.875rem] leading-6 text-ink/85">
                {CHATTFRAGOR[i].svar}
              </p>
            </div>
          </div>
        ))}
      </div>

      {kvar.length ? (
        <div className={stallda.length ? "mt-5" : "mt-4"}>
          <p className="text-[0.8125rem] text-mineral">
            {stallda.length ? "Fråga något mer:" : "Klicka på en fråga, som kund:"}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {kvar.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => setStallda((f) => [...f, i])}
                className="focus-ring rounded-input border border-ink/15 px-3 py-2 text-left text-[0.8125rem] text-ink/70 hover:border-ochre hover:text-ink"
              >
                {CHATTFRAGOR[i].fraga}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-5 text-[0.8125rem] text-mineral">
          Det var frågorna i exemplet. I produkten skriver kunderna fritt, och
          agenten svarar ur er kunskapsbas eller eskalerar.
        </p>
      )}
    </div>
  );
}

export function DemoSupportYta() {
  const [flik, setFlik] = useState<"inkorg" | "chatt">("inkorg");

  return (
    <div>
      {/* Samma flikmönster som SupportWorkspaceTabs: border-ochre bär valet. */}
      <div className="flex gap-1 border-b border-ink/12" role="tablist" aria-label="Kundtjänstens ytor">
        {(
          [
            ["inkorg", "Inkorgen"],
            ["chatt", "Kundchatten"]
          ] as const
        ).map(([id, etikett]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={flik === id}
            onClick={() => setFlik(id)}
            className={cn(
              "focus-ring -mb-px inline-flex min-h-11 items-center border-b-2 px-4 text-[0.9375rem] font-medium transition-colors",
              flik === id
                ? "border-ochre text-ink"
                : "border-transparent text-ink/55 hover:text-ink"
            )}
          >
            {etikett}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {flik === "inkorg" ? <SupportDashboard demo /> : <Kundchatt />}
      </div>
    </div>
  );
}
