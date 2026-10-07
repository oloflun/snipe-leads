"use client";

import { useCallback, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";
import { flik, flikAktiv, flikInaktiv, fliklista } from "@/components/ui";
import { Dashboard } from "./Dashboard";
import { SupportChat } from "./SupportChat";
import { SupportOversikt } from "./SupportOversikt";

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
  const { text } = useLocale();
  const [tab, setTab] = useState<"oversikt" | "kundtjanst" | "testmail" | "dolda" | "testchatt">("oversikt");
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
      // Översikten (2026-10-07): Leads-översiktens layout för support,
      // se components/snajp/SupportOversikt.tsx. Först, som på Leads.
      { id: "oversikt", label: { sv: "Översikt", en: "Overview" } },
      { id: "kundtjanst", label: { sv: "Ärenden", en: "Cases" } },
      // Eskaleringar och larm (migration 078) bor i Att göra sedan Snajp
      // Suite 2026-10-03 (components/leads/AttGora.tsx), fortfarande skilda
      // från kundärendena och utan AI-utkast.
      ...(visarTestIArenden === false
        ? [{ id: "testmail" as const, label: { sv: "Testmail", en: "Test mail" } }]
        : []),
      // Dolda (plan 2026-10-05): det klassningen sorterade bort som utskick
      // eller ej relaterat — synligt och möjligt att flytta tillbaka.
      { id: "dolda", label: { sv: "Dolda", en: "Hidden" } },
      { id: "testchatt", label: { sv: "Testchatt", en: "Test chat" } }
      // Journalen (körningar, kostnad, överlämningar) flyttade till
      // Aktivitet 2026-10-03, Snajp Suite: alla agenters körningar på ett
      // ställe. Se components/dashboard/Aktivitet.tsx.
    ] as const
  );

  return (
    <div>
      <div className={fliklista}>
        {flikar.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={cn(flik, tab === item.id ? flikAktiv : flikInaktiv)}
          >
            {text(item.label)}
          </button>
        ))}
      </div>

      <div className="mt-8">
        {tab === "kundtjanst" ? (
          <Dashboard onMeta={onMeta} />
        ) : null}
        {tab === "oversikt" ? <SupportOversikt onOppnaArenden={() => setTab("kundtjanst")} onMeta={onMeta} /> : null}
        {tab === "testmail" ? <Dashboard lager="testmail" /> : null}
        {tab === "dolda" ? <Dashboard lager="ej_relaterat" /> : null}
        {tab === "testchatt" ? (
          <div className="mx-auto max-w-3xl">
            <SupportChat testMode workspaceLabel={workspaceName ?? undefined} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
