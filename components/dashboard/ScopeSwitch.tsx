"use client";

import { useDashboard, type Scope } from "@/components/dashboard/DashboardContext";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const labels: Record<Scope, Localized> = {
  both: { sv: "Allt", en: "All" },
  leads: { sv: "Leads", en: "Leads" },
  support: { sv: "Support", en: "Support" }
};

/**
 * Product-register sibling of the marketing hero switch: same selected-state
 * vocabulary, none of the marketing scale. Only rendered when the workspace owns
 * more than one product, since a switch with one option is noise.
 */
export function ScopeSwitch() {
  const { text } = useLocale();
  const { scope, setScope, availableScopes } = useDashboard();

  return (
    <div
      role="group"
      aria-label={text({ sv: "Visa", en: "Show" })}
      className="inline-flex items-center gap-0.5 rounded-input bg-paper2/70 p-0.5"
    >
      {availableScopes.map((option) => {
        const selected = option === scope;
        return (
          <button
            key={option}
            type="button"
            aria-pressed={selected}
            onClick={() => setScope(option)}
            className={cn(
              "focus-ring min-h-9 rounded-[6px] px-3 text-[0.8125rem] font-medium transition-colors",
              selected ? "bg-paper text-ink" : "text-ink/55 hover:text-ink"
            )}
          >
            {text(labels[option])}
          </button>
        );
      })}
    </div>
  );
}
