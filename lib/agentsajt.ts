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
  { produkt: ProductKey; envUrl: string; rubrik: string; beskrivning: string; knapp: string }
> = {
  support: {
    produkt: "support",
    envUrl: "SUPPORT_EXTERN_URL",
    rubrik: "Supportagenten har fått en egen arbetsyta",
    beskrivning:
      "Ärendena, utkasten och kunskapsbasen som egna flikar, med mer plats att arbeta. Du loggas in automatiskt.",
    knapp: "Kör Agent"
  }
};

export function arAgentSajt(varde: string): varde is AgentSajt {
  return varde in AGENTSAJTER;
}

export function externUrlFor(agent: AgentSajt): string {
  return (process.env[AGENTSAJTER[agent].envUrl] ?? "").replace(/\/$/, "");
}
