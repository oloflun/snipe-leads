"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { useLocale } from "@/lib/i18n";
import { settingsGroupsForProducts } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Inställningarnas navigation, grupperad per agent.
 *
 * Den fanns inte förut. Sex inställningssidor låg under /settings utan någon
 * flikrad — de gick bara att nå genom att skriva adressen, och `settingsRoutes`
 * i lib/routes.ts exporterades utan att någon renderade den.
 *
 * Grupperingen är poängen, inte dekoration: "Röst och tonläge" och "Inkorgar"
 * är inte samma sorts inställning, och en platt lista med sex poster tvingar
 * läsaren att veta vilken agent varje sida gäller innan hen klickar.
 *
 * Grupper filtreras på entitlement — en Support-only-arbetsyta ser inte
 * leads-agentens rubrik. Det är en artighet; grinden som räknar sitter i
 * respektive sida.
 */
export function SettingsNav() {
  const pathname = usePathname();
  const { products } = useDashboard();
  const { text } = useLocale();

  const grupper = settingsGroupsForProducts(products);

  return (
    <nav aria-label="Inställningar" className="grid gap-7">
      {grupper.map((grupp) => (
        <div key={grupp.label.sv}>
          <p className="kicker text-mineral">{text(grupp.label)}</p>
          <ul className="mt-3 grid gap-1">
            {grupp.routes.map((route) => {
              // Exakt matchning för /settings: annars vore den "aktiv" på varje
              // undersida, eftersom alla börjar med samma prefix.
              const aktiv =
                route.href === "/settings"
                  ? pathname === "/settings"
                  : pathname === route.href || pathname.startsWith(`${route.href}/`);
              return (
                <li key={route.href}>
                  <Link
                    href={route.href}
                    aria-current={aktiv ? "page" : undefined}
                    className={cn(
                      "focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-[15px] transition-colors",
                      aktiv ? "bg-paper2 text-ink" : "text-ink/60 hover:bg-paper2/60 hover:text-ink"
                    )}
                  >
                    {text(route.label)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
