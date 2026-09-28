"use client";

import { useCallback, useEffect, useState } from "react";
import { flik, flikAktiv, flikInaktiv } from "@/components/ui";
import { cn } from "@/lib/utils";
import { Dashboard } from "./Dashboard";
import { SupportChat } from "./SupportChat";

/**
 * "Kundtjänst" och "Testchatt" bredvid varandra i arbetsytans supportflik
 * (Fas 5, plan 2026-08-28 §6.1, bd snipe-0r9).
 *
 * Flikraden bär husets flikform (`flik` i components/ui.tsx) sedan
 * 2026-09-27. Den hade tidigare en egen understrykningsrad med ochre på den
 * aktiva, och var därmed den enda flikraden i appen som såg annorlunda ut
 * (plans/2026-09-27-appytor-enhetlighet.md).
 *
 * "Kundtjänst" är den befintliga interna inkorgen. På riktiga konton finns
 * dessutom "Testmail" — testärenden som inte ska blandas med skarpa. Demo-
 * och testkonton visar testmailen under Ärenden i stället. "Testchatt" renderar
 * SupportChat med testMode: riktig AI mot DEN INLOGGADE tenantens egen
 * kunskapsbas, inte demo, inte en publik länk. Körningar därifrån märks
 * is_test: true i agent_runs (se app/api/schemas.ChatRequest) så de aldrig
 * räknas som kundvolym.
 */
export function SupportWorkspaceTabs({ workspaceName }: Readonly<{ workspaceName: string | null }>) {
  const [tab, setTab] = useState<"kundtjanst" | "testmail" | "testchatt">("kundtjanst");
  /** null = vet inte än. false = riktig kund, Testmail-fliken ska synas. */
  const [visarTestIArenden, setVisarTestIArenden] = useState<boolean | null>(null);

  const onMeta = useCallback((meta: { visar_test_i_arenden: boolean }) => {
    setVisarTestIArenden(meta.visar_test_i_arenden);
  }, []);

  useEffect(() => {
    if (tab === "testmail" && visarTestIArenden !== false) {
      setTab("kundtjanst");
    }
  }, [tab, visarTestIArenden]);

  const flikar = (
    [
      // "Inkorg" och inte "Kundtjänst": sidan heter redan Kundtjänst, och en
      // flik med sidans namn säger inte vad den visar.
      { id: "kundtjanst", label: "Inkorg" },
      ...(visarTestIArenden === false ? [{ id: "testmail" as const, label: "Testmail" }] : []),
      { id: "testchatt", label: "Testchatt" }
    ] as const
  );

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {flikar.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            aria-pressed={tab === item.id}
            className={cn(flik, tab === item.id ? flikAktiv : flikInaktiv)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="mt-8">
        {tab === "kundtjanst" ? (
          <Dashboard onMeta={onMeta} />
        ) : null}
        {tab === "testmail" ? <Dashboard lager="testmail" /> : null}
        {tab === "testchatt" ? (
          <div className="mx-auto max-w-3xl">
            <SupportChat testMode workspaceLabel={workspaceName ?? undefined} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
