import type { ProductKey } from "@/lib/routes";

/**
 * De fristående agentsajterna — ETT register, så att knappen, SSO-routen
 * och miljövariabelnamnen aldrig glider isär. En ny agentsajt är en rad
 * här plus en <AgentSajtKnapp agent="..."/> i flikens vy.
 */

export type AgentSajt = "bokforing" | "leads" | "support";

export const AGENTSAJTER: Record<
  AgentSajt,
  { produkt: ProductKey; envUrl: string; rubrik: string; beskrivning: string }
> = {
  bokforing: {
    produkt: "bookkeeping",
    envUrl: "BOKFORING_EXTERN_URL",
    rubrik: "Bokföringsagenten har fått en egen arbetsyta",
    beskrivning:
      "Samma underlag och siffror som här, med mer plats: resultat, intäkter och utgifter, PDF-filer och assistenten som egna flikar. Du loggas in automatiskt."
  },
  leads: {
    produkt: "leads",
    envUrl: "LEADS_EXTERN_URL",
    rubrik: "Leadsagenten har fått en egen arbetsyta",
    beskrivning:
      "Prospekten, utkasten och granskningskön som egna flikar, med mer plats att arbeta. Du loggas in automatiskt."
  },
  support: {
    produkt: "support",
    envUrl: "SUPPORT_EXTERN_URL",
    rubrik: "Supportagenten har fått en egen arbetsyta",
    beskrivning:
      "Ärendena, utkasten och kunskapsbasen som egna flikar, med mer plats att arbeta. Du loggas in automatiskt."
  }
};

export function arAgentSajt(varde: string): varde is AgentSajt {
  return varde in AGENTSAJTER;
}

export function externUrlFor(agent: AgentSajt): string {
  return (process.env[AGENTSAJTER[agent].envUrl] ?? "").replace(/\/$/, "");
}
