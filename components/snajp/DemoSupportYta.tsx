"use client";

import { ShieldAlert } from "lucide-react";
import { useState } from "react";
import { Dashboard as SupportDashboard } from "@/components/snajp/Dashboard";
import { SupportOversikt } from "@/components/snajp/SupportOversikt";
import { Badge, etikett, flik, flikAktiv, flikInaktiv, fliklista } from "@/components/ui";
import { CHATTFRAGOR } from "@/lib/demo/support-chatt";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";

/**
 * Demons kundtjänst: inkorgen OCH kundchatten, i samma flikform som
 * arbetsytans SupportWorkspaceTabs (`flik` i components/ui.tsx).
 *
 * ## Varför chatten är förladdad
 *
 * Arbetsytans testchatt kör riktig AI mot den inloggade tenantens kunskapsbas.
 * Här finns ingen tenant och ingen session, och en LLM-körning per anonym
 * besökare kostar pengar och kan svara olika varje gång. Besökaren väljer
 * i stället fråga och svaret fälls ut — samma mönster som bokföringsdemons
 * chatt. En av frågorna eskalerar med flit: gränsen är en del av produkten.
 *
 * Exempelnotisen ovanför chatten ("Butiken Nordlys Handel är påhittad …")
 * och slutraden ("Det var frågorna i exemplet …") togs bort 2026-09-27
 * (plans/2026-09-27-appytor-enhetlighet.md, regel 1): de handlade om
 * exemplet, inte om kunden, och demoskalet märker redan hela ytan som demo.
 */

function Kundchatt() {
  const { text } = useLocale();
  const [stallda, setStallda] = useState<number[]>([]);
  const kvar = CHATTFRAGOR.map((_, i) => i).filter((i) => !stallda.includes(i));

  return (
    <div className="max-w-[720px]">
      <div className="grid gap-3">
        {stallda.map((i) => (
          <div key={i} className="grid gap-3">
            <p className="ml-auto max-w-[92%] rounded-card bg-paper2 px-3.5 py-2.5 text-[0.9375rem] leading-6 text-ink">
              {CHATTFRAGOR[i].fraga}
            </p>
            <div className="max-w-[92%]">
              {CHATTFRAGOR[i].eskalerar ? (
                <p className="mb-1.5">
                  <Badge tone="danger">
                    <ShieldAlert className="h-3 w-3" aria-hidden />
                    {text({ sv: "Eskalerat till en människa", en: "Escalated to a human" })}
                  </Badge>
                </p>
              ) : null}
              <p className="whitespace-pre-wrap rounded-card border border-ink/15 px-3.5 py-2.5 text-[0.9375rem] leading-6 text-ink-muted">
                {CHATTFRAGOR[i].svar}
              </p>
            </div>
          </div>
        ))}
      </div>

      {kvar.length ? (
        <div className={stallda.length ? "mt-5" : ""}>
          <p className={etikett}>
            {stallda.length
              ? text({ sv: "Fråga något mer:", en: "Ask something else:" })
              : text({ sv: "Klicka på en fråga, som kund:", en: "Click a question, as the customer:" })}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {kvar.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => setStallda((f) => [...f, i])}
                className="focus-ring rounded-input border border-ink/15 px-3 py-2 text-left text-[0.8125rem] text-ink-muted hover:border-ochre hover:text-ink"
              >
                {CHATTFRAGOR[i].fraga}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function DemoSupportYta({ visaDrift = false }: Readonly<{ visaDrift?: boolean }>) {
  const { text } = useLocale();
  // `valdFlik` och inte `flik`: det namnet är klassen ur components/ui.tsx.
  const [valdFlik, setFlik] = useState<"oversikt" | "inkorg" | "chatt">("oversikt");

  return (
    <div>
      {/* Samma flikform som SupportWorkspaceTabs. */}
      <div className={fliklista} role="tablist" aria-label={text({ sv: "Kundtjänstens ytor", en: "Customer service areas" })}>
        {(
          [
            ["oversikt", text({ sv: "Översikt", en: "Overview" })],
            ["inkorg", text({ sv: "Inkorgen", en: "The inbox" })],
            ["chatt", text({ sv: "Kundchatten", en: "The customer chat" })]
          ] as const
        ).map(([id, etikett]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={valdFlik === id}
            onClick={() => setFlik(id)}
            className={cn(flik, valdFlik === id ? flikAktiv : flikInaktiv)}
          >
            {etikett}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {valdFlik === "oversikt" ? (
          <SupportOversikt demo visaDrift={visaDrift} onOppnaArenden={() => setFlik("inkorg")} />
        ) : valdFlik === "inkorg" ? (
          <SupportDashboard demo />
        ) : (
          <Kundchatt />
        )}
      </div>
    </div>
  );
}
