import type { ProductKey } from "@/lib/routes";

/**
 * De fristående agentsajterna — ETT register, så att knappen, SSO-routen
 * och miljövariabelnamnen aldrig glider isär. En ny agentsajt är en rad
 * här plus en <AgentSajtKnapp agent="..."/> i flikens vy.
 */

export type AgentSajt = "bokforing" | "leads" | "support";

export const AGENTSAJTER: Record<
  AgentSajt,
  { produkt: ProductKey; envUrl: string; rubrik: string; beskrivning: string; knapp: string }
> = {
  // Nyckeln "bokforing" står kvar fast produkten heter Kvittohanteraren:
  // den sitter i SSO-routens URL, i miljövariabelnamnet och i sajtens
  // biljettkontrakt — deployade ytor som inte ska bytas i takt med ett
  // produktnamn. Det kunden ser är rubriken nedan.
  bokforing: {
    produkt: "bookkeeping",
    envUrl: "BOKFORING_EXTERN_URL",
    rubrik: "Kvittohanteraren har fått en egen arbetsyta",
    beskrivning:
      "Samma kvitton och summor som här, med mer plats: inkorgen, kvittolistan och assistenten som egna flikar. Du loggas in automatiskt.",
    knapp: "Kör Agent"
  },
  leads: {
    produkt: "leads",
    envUrl: "LEADS_EXTERN_URL",
    // Leadsagenten heter Iris sedan 2026-09-16 — namnet bor HÄR och i
    // leads-webb/lib/iris.ts; glider de isär är det den här raden som vinner
    // på Snajp-webben.
    rubrik: "Iris, din leadsagent, har fått en egen arbetsyta",
    beskrivning:
      "Iris letar fram bolagen, gör research med synliga källor och skriver utkasten. Prospekten, granskningskön och hennes demo som egna flikar. Du loggas in automatiskt.",
    knapp: "Kör Iris"
  },
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
