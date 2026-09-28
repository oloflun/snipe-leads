"use client";

import { useCallback, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { Dashboard } from "./Dashboard";
import { JournalVy } from "./JournalVy";
import { SupportChat } from "./SupportChat";

/**
 * "Kundtjänst" och "Testchatt" bredvid varandra i arbetsytans supportflik
 * (Fas 5, plan 2026-08-28 §6.1, bd snipe-0r9).
 *
 * Mönstret är hämtat rakt av från components/snajp/SnajpSupportDemo.tsx,
 * som redan gör exakt det här för marknadssidans demo (flikraden med
 * border-ochre på den aktiva) — i dag oanvänd i produkten, men färdigt och
 * beprövat, så det byggs inte om.
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
  const [tab, setTab] = useState<"kundtjanst" | "att_hantera" | "testmail" | "testchatt" | "journal">("kundtjanst");
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
      { id: "kundtjanst", label: "Kundtjänst" },
      // Eskaleringar och larm (migration 078): egen flik så att de aldrig
      // blandas med kundärenden eller får ett AI-utkast (kundtest 2026-09-22).
      { id: "att_hantera", label: "Att hantera" },
      ...(visarTestIArenden === false ? [{ id: "testmail" as const, label: "Testmail" }] : []),
      { id: "testchatt", label: "Testchatt" },
      // Journalen (Livrustning-piloten): körningar, kostnad och
      // överlämningar för den egna tenanten — vyn kundens kontaktperson
      // (läsrollen) följer piloten i. Ren läsning, se JournalVy.tsx.
      { id: "journal", label: "Journal" }
    ] as const
  );

  return (
    <div>
      <div className="flex flex-wrap gap-2 border-b border-ink/12 pb-px">
        {flikar.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={cn(
              "focus-ring -mb-px border-b-2 px-4 py-3 text-sm font-semibold transition",
              tab === item.id ? "border-ochre text-ink" : "border-transparent text-ink-subtle hover:text-ink"
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="mt-8">
        {tab === "kundtjanst" ? (
          <Dashboard onMeta={onMeta} />
        ) : null}
        {tab === "att_hantera" ? <Dashboard lager="att_hantera" /> : null}
        {tab === "testmail" ? <Dashboard lager="testmail" /> : null}
        {tab === "testchatt" ? (
          <div className="mx-auto max-w-3xl">
            <SupportChat testMode workspaceLabel={workspaceName ?? undefined} />
          </div>
        ) : null}
        {tab === "journal" ? <JournalVy /> : null}
      </div>
    </div>
  );
}
