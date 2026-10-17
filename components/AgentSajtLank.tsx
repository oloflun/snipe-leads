"use client";

import { ArrowUpRight } from "lucide-react";
import { btnPrimary } from "@/components/ui";
import { AGENTSAJTER, type AgentSajt } from "@/lib/agentsajt";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/** Knappen till agentens egen sajt, på kundens språk. Serverdelen
 *  (AgentSajtKnapp) avgör om sajten finns; den här bara ritar länken. */
export function AgentSajtLank({ agent }: Readonly<{ agent: AgentSajt }>) {
  const { text } = useLocale();
  return (
    <a href={`/api/agentsajt/${agent}/sso`} className={cn(btnPrimary, "shrink-0")}>
      {text(AGENTSAJTER[agent].knapp)}
      <ArrowUpRight className="h-4 w-4" aria-hidden />
    </a>
  );
}
