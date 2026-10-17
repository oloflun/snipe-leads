import type { Localized } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";

/**
 * De fristående agentsajterna — ETT register, så att knappen, SSO-routen
 * och miljövariabelnamnen aldrig glider isär. En ny agentsajt är en rad
 * här plus en <AgentSajtKnapp agent="..."/> i flikens vy.
 */

// Bokförings- och leadssajterna vek in i huvudappen 2026-09-19 (Kvitton och
// Iris). Supportportalen står kvar tills Anton och Sebbe avgjort den.
export type AgentSajt = "support";

export const AGENTSAJTER: Record<
  AgentSajt,
  { produkt: ProductKey; envUrl: string; knapp: Localized }
> = {
  // Rubriken ("Supportagenten har fått en egen arbetsyta") och beskrivningen
  // togs bort 2026-10-07 på Sebbes begäran: knappen står ensam.
  support: {
    produkt: "support",
    envUrl: "SUPPORT_EXTERN_URL",
    knapp: { sv: "Kör agent", en: "Run agent" }
  }
};

export function arAgentSajt(varde: string): varde is AgentSajt {
  return varde in AGENTSAJTER;
}

export function externUrlFor(agent: AgentSajt): string {
  return (process.env[AGENTSAJTER[agent].envUrl] ?? "").replace(/\/$/, "");
}
