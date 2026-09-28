"use client";

import { Eye } from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";

/**
 * "Du har läsbehörighet" — läsrollens diskreta markör.
 *
 * Samma plats och mekanik som ImpersonationBanner men lugnare i tonen:
 * läsaren gör inget fel genom att vara här, bannern förklarar bara varför
 * knappar saknas eller svarar nej. Utan den ser ett nekat sparande ut som en
 * bugg — med den är det ett förväntat svar.
 *
 * Villkoret på `arLasare` är en ritregel, inte en grind. Spärren sitter
 * serverside (proxyAsTenant och server actions, se lib/auth/lasroll.ts) —
 * en manipulerad flagga i klienten ritar bort en banner utan att ge
 * skrivrätt till någonting.
 */
export function LasrollBanner() {
  const { arLasare } = useDashboard();

  if (!arLasare) {
    return null;
  }

  return (
    <div
      role="status"
      className="safe-top sticky top-0 z-40 border-b border-ink/15 bg-paper2"
    >
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-2 md:px-6">
        <Eye className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
        <p className="text-[13px] font-medium text-ink">Du har läsbehörighet.</p>
        <p className="text-[13px] text-ink-muted">
          Du ser allt som händer i arbetsytan, men kan inte ändra något.
        </p>
      </div>
    </div>
  );
}
