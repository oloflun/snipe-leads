import { ArrowUpRight } from "lucide-react";
import { btnPrimary } from "@/components/ui";
import { cn } from "@/lib/utils";
import { AGENTSAJTER, type AgentSajt, externUrlFor } from "@/lib/agentsajt";

/**
 * "Kör Agent"-bannern — vägen från arbetsytans flik till agentens egen sajt.
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
  const text = AGENTSAJTER[agent];

  return (
    <div className="mb-12 flex flex-wrap items-center justify-between gap-x-8 gap-y-4 border-y border-ink/15 py-5">
      <div className="min-w-0 max-w-[62ch]">
        <p className="text-[0.9375rem] font-semibold text-ink">{text.rubrik}</p>
      </div>
      <a href={`/api/agentsajt/${agent}/sso`} className={cn(btnPrimary, "shrink-0")}>
        {text.knapp}
        <ArrowUpRight className="h-4 w-4" aria-hidden />
      </a>
    </div>
  );
}
