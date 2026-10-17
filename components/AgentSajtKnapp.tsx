import { AgentSajtLank } from "@/components/AgentSajtLank";
import { type AgentSajt, externUrlFor } from "@/lib/agentsajt";

/**
 * "Kör agent"-knappen — vägen från arbetsytans flik till agentens egen sajt.
 *
 * Samma mönster för alla tre agenterna (bokföring, leads, support): en
 * KNAPP i vyn, aldrig en redirect på menyklicket (Sebbes ord 2026-09-15).
 * Länken går via /api/agentsajt/<agent>/sso som skapar en färsk
 * engångsbiljett vid klicket, så kunden landar på sajten som sig själv.
 *
 * Renderas bara när miljön pekat ut agentens sajt — utan URL finns ingen
 * knapp, och fliken ser ut exakt som innan sajten fanns.
 */
export function AgentSajtKnapp({ agent }: Readonly<{ agent: AgentSajt }>) {
  if (!externUrlFor(agent)) return null;

  // Bara knappen sedan 2026-10-07 (Sebbe): rubriken "Supportagenten har fått
  // en egen arbetsyta" togs bort, och utan text bredvid behövs ingen banner
  // med linjer runt.
  return (
    <div className="mb-8 flex justify-end">
      <AgentSajtLank agent={agent} />
    </div>
  );
}
