"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useArbetsvag } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { useLocale } from "@/lib/i18n";
import { settingsGroupsForProducts } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Inställningarnas navigation, grupperad efter vad inställningen ÄR.
 *
 * Den fanns inte förut. Sex inställningssidor låg under /settings utan någon
 * flikrad — de gick bara att nå genom att skriva adressen, och `settingsRoutes`
 * i lib/routes.ts exporterades utan att någon renderade den.
 *
 * ## Varför länkarna går genom useArbetsvag
 *
 * Samma sidor renderas på två ytor: /settings (kunden) och /admin/installningar
 * (plattformsadmin). En hårdkodad `/settings/...` är därför rätt på EN av dem —
 * på adminytan tog den admin ur adminskalet, och plattformsraden försvann mitt
 * i ett arbetsmoment. Samma fel som flikraden en gång hade, fast i sidokolumnen.
 *
 * Grupper filtreras på entitlement — en Support-only-arbetsyta ser inte
 * leads-agentens rubrik. Det är en artighet; grinden som räknar sitter i
 * SettingsSection.
 */
export function SettingsNav() {
  const pathname = usePathname();
  const vag = useArbetsvag();
  const { products, shows, vy } = useDashboard();
  const { text } = useLocale();

  // Tre filter, tre olika frågor: rättighet (products), vad läget visar just nu
  // (shows) och vad demovyn inte får avslöja (vy). Kolumnen listade tidigare
  // bara på det första, så Support-läget visade fortfarande leads-agentens
  // inställningar — och Team, med våra egna mejladresser, syntes i demon.
  const grupper = settingsGroupsForProducts(products, { visar: shows, vy });

  return (
    <nav aria-label="Inställningar" className="grid gap-7">
      {grupper.map((grupp) => (
        <div key={grupp.label.sv}>
          <p className="kicker text-mineral">{text(grupp.label)}</p>
          <ul className="mt-3 grid gap-1">
            {grupp.routes.map((route) => {
              const href = vag(route.href);
              // Exakt matchning för rotsidan: annars vore den "aktiv" på varje
              // undersida, eftersom alla börjar med samma prefix. Jämförelsen
              // görs mot den YTANPASSADE vägen, inte mot /settings/... — under
              // /admin/installningar hade ingen post annars markerats.
              const rot = vag("/settings");
              const aktiv =
                href === rot
                  ? pathname === rot
                  : pathname === href || pathname.startsWith(`${href}/`);
              return (
                <li key={route.href}>
                  <Link
                    href={href}
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
