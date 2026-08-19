"use client";

import { LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/Logo";
import { ScopeSwitch } from "@/components/dashboard/ScopeSwitch";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { AgentMenu } from "@/components/snajp/AgentMenu";
import { signOut } from "@/lib/actions/auth";
import { useLocale } from "@/lib/i18n";
import { routesForProducts, tillAdminvag } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Adminytans skal — samma chrome som kundens AppShell, plus plattformsraden.
 *
 * ## Varför skalet bor här och inte i layouten
 *
 * `app/admin/layout.tsx` är en server-komponent (den måste vara det: grinden
 * `getPlatformAdmin()` ställer en databasfråga). Skalet behöver `usePathname`
 * för aktiv flik, `useLocale` för språkväxlaren och en form-action för
 * utloggning — alltså klientsidan. Layouten grindar och hämtar; det här
 * renderar.
 *
 * ## Varför det inte räcker att återanvända AppShell rakt av
 *
 * AppShells länkar pekar på `/dashboard/*`. För en plattformsadmin studsar den
 * vägen tillbaka till `/admin` (`app/dashboard/layout.tsx`), så varje flik i
 * kundskalet tog admin UT ur den flik de stod i. Samma flikar med `/admin`-
 * prefix gör att arbetsytan går att använda inifrån adminytan — vilket är hela
 * poängen med att adminytan är en superset och inte en andra yta.
 *
 * AppShell renderar därför BARA innehåll under /admin (se den filen), så att
 * det inte blir två staplade headers. Uppmätt: det var det innan.
 */

/** Plattformsflikarna — det som skiljer adminytan från kundens arbetsyta. */
const PLATTFORM = [
  { href: "/admin", label: "Översikt" },
  { href: "/admin/kunder", label: "Kunder" },
  { href: "/admin/korningar", label: "Körningar" },
  { href: "/admin/testkorningar", label: "Testkörningar" },
  { href: "/admin/handelser", label: "Händelser" }
];

function matchar(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Aktiv flik = den LÄNGSTA träffen, inte varje träff.
 *
 * `/admin/leads/kontroll` matchar både "Leads" och "Kontroll" på prefix, och
 * två markerade flikar pekar inte ut någon. Samma sak gör `/admin` mot allt
 * under sig. Längsta match ger exakt en, alltid.
 */
function aktivHref(pathname: string, hrefs: string[]): string | null {
  let bast: string | null = null;
  for (const href of hrefs) {
    if (matchar(pathname, href) && (bast === null || href.length > bast.length)) {
      bast = href;
    }
  }
  return bast;
}

export function AdminShell({
  email,
  children
}: Readonly<{ email: string | null; children: React.ReactNode }>) {
  const pathname = usePathname();
  const { t, text, locale, toggleLocale } = useLocale();
  const { products, workspaceName, availableScopes, shows } = useDashboard();

  // Samma entitlement- och scope-filter som kundens nav. Adminytan är en
  // superset av arbetsytan, inte en genväg förbi dess regler.
  const arbetsyta = routesForProducts(products)
    .filter((route) => route.product === "shared" || shows(route.product))
    .map((route) => ({
      href: tillAdminvag(route.href),
      // "Min arbetsyta" och inte t("nav.dashboard") ("Översikt"): plattforms-
      // raden har redan en flik som heter Översikt, och två flikar med samma
      // namn i samma header är inte en etikett utan en gissningslek.
      // Localized och inte en svensk sträng — resten av raden byter språk med
      // EN/SV-knappen, och en flik som inte gör det ser ut som en bugg.
      label:
        route.href === "/dashboard"
          ? text({ sv: "Min arbetsyta", en: "My workspace" })
          : t(route.labelKey)
    }));

  // Båda raderna räknas som EN uppsättning: annars markerar plattformsradens
  // "Översikt" (/admin) sig själv samtidigt som arbetsytans flik är den man
  // faktiskt står på.
  const aktiv = aktivHref(pathname, [
    ...PLATTFORM.map((f) => f.href),
    ...arbetsyta.map((f) => f.href)
  ]);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 bg-paper/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3 md:px-6">
          <Link href="/admin" className="focus-ring inline-flex min-h-11 items-center rounded-input">
            <Logo />
          </Link>

          <span className="kicker text-ochre">Admin</span>

          {workspaceName ? (
            <span className="hidden text-sm text-ink/45 sm:inline">{workspaceName}</span>
          ) : null}

          <div className="ml-auto flex items-center gap-1.5">
            {availableScopes.length > 1 ? <ScopeSwitch /> : null}

            <button
              type="button"
              onClick={toggleLocale}
              className="focus-ring min-h-11 rounded-input px-3 text-sm font-medium text-ink/55 transition-colors hover:text-ink"
            >
              {locale === "sv" ? "EN" : "SV"}
            </button>

            <AgentMenu yta="leads" kontext={`admin:${pathname}`} />

            {email ? (
              <span className="hidden text-sm text-ink/45 lg:inline">{email}</span>
            ) : null}

            {/* Utloggning fanns inte alls i adminytan. signOut() var skriven och
                fungerande, men ingen komponent i adminskalet anropade den — samma
                lucka som en gång saknade länken TILL /admin. Formulär och inte
                onClick: signOut är en server action och fungerar utan JS. */}
            <form action={signOut}>
              <button
                type="submit"
                className="focus-ring inline-flex min-h-11 items-center gap-1.5 rounded-input px-3 text-sm font-medium text-ink/55 transition-colors hover:text-ink"
              >
                <LogOut className="h-4 w-4" aria-hidden />
                <span className="hidden sm:inline">Logga ut</span>
              </button>
            </form>
          </div>

          {/* Plattformsraden först: det är den som skiljer ytan från kundens,
              och den ska inte behöva letas upp bland arbetsytans flikar. */}
          <nav
            aria-label="Plattform"
            className="thin-scrollbar order-last -mx-1 flex w-full min-w-0 gap-1 overflow-x-auto px-1 pb-1"
          >
            {PLATTFORM.map((flik) => {
              const på = aktiv === flik.href;
              return (
                <Link
                  key={flik.href}
                  href={flik.href}
                  aria-current={på ? "page" : undefined}
                  className={cn(
                    "focus-ring inline-flex min-h-11 shrink-0 items-center rounded-input px-3 text-sm font-medium transition-colors",
                    på ? "bg-ochre/15 text-ink" : "text-ochre hover:bg-ochre/10"
                  )}
                >
                  {flik.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {arbetsyta.length > 0 ? (
          <div className="mx-auto max-w-[1400px] px-4 pb-2 md:px-6">
            <nav
              aria-label="Min arbetsyta"
              className="thin-scrollbar -mx-1 flex min-w-0 gap-1 overflow-x-auto px-1"
            >
              {arbetsyta.map((flik) => {
                const på = aktiv === flik.href;
                return (
                  <Link
                    key={flik.href}
                    href={flik.href}
                    aria-current={på ? "page" : undefined}
                    className={cn(
                      "focus-ring inline-flex min-h-11 shrink-0 items-center rounded-input px-3 text-sm font-medium transition-colors",
                      på ? "bg-paper2 text-ink" : "text-ink/55 hover:bg-paper2/60 hover:text-ink"
                    )}
                  >
                    {flik.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        ) : null}
      </header>

      <main>{children}</main>
    </div>
  );
}
