import Link from "next/link";
import { notFound } from "next/navigation";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { routesForProducts } from "@/lib/routes";

export const dynamic = "force-dynamic";

/**
 * Adminytan, grindad server-side — och numera en SUPERSET av kundens arbetsyta.
 *
 * `notFound()` och inte en redirect till /login: ett 403 eller en redirect
 * bekräftar att /admin finns och vem den är till för. En 404 säger ingenting.
 *
 * Det här är grind ETT av tre. De andra två är `/api/admin/*`-proxyns egen
 * kontroll och backendens `require_master_key`. Ingen av dem litar på att de
 * andra gjorde sitt jobb.
 *
 * ## Varför arbetsytans flikar hänger här
 *
 * En plattformsadmin behöver båda sakerna samtidigt: de egna körningarna och
 * alla kunders siffror. Att växla mellan /dashboard och /admin för att göra ett
 * jobb är två inloggade ytor för en person, och den som gör det slutar använda
 * den ena.
 *
 * `/dashboard` är OFÖRÄNDRAD för vanliga kunder. Flikarna nedan renderas av
 * samma `WorkspaceSection` som kundens yta använder — ingen vy är kopierad, och
 * entitlement-kontrollen sitter kvar inuti den.
 *
 * DashboardProvider måste finnas här: arbetsytans komponenter läser
 * `useDashboard()`, och utan provider faller de tillbaka på FALLBACK-kontexten
 * och visar demo-data i adminytan.
 */

const ADMIN_TABS = [
  { href: "/admin", label: "Översikt" },
  { href: "/admin/kunder", label: "Kunder" },
  { href: "/admin/korningar", label: "Körningar" },
  { href: "/admin/handelser", label: "Händelser" }
];

/** Arbetsytans flikar, samma lista som kundens meny, med /admin som prefix. */
function workspaceTabs(products: Parameters<typeof routesForProducts>[0]) {
  return routesForProducts(products)
    .filter((route) => route.href.startsWith("/dashboard"))
    .map((route) => ({
      href: route.href.replace("/dashboard", "/admin"),
      labelKey: route.labelKey
    }));
}

/** Etiketterna hämtas server-side; useLocale är en klienthook. */
const WORKSPACE_LABELS: Record<string, string> = {
  "nav.dashboard": "Min arbetsyta",
  "nav.leads": "Leads",
  "nav.emails": "Email studio",
  "nav.leadsControl": "Leads-kontroll",
  "nav.support": "Kundtjänst",
  "nav.companies": "Företag",
  "nav.contacts": "Kontakter",
  "nav.inbox": "Svar",
  "nav.analytics": "Analys",
  "nav.assistant": "Assistant"
};

export default async function AdminLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  const admin = await getPlatformAdmin();
  if (!admin) {
    notFound();
  }

  const state = await resolveDashboardState();
  const arbetsyta = workspaceTabs(state.products);

  return (
    <DashboardProvider state={state}>
      <div className="min-h-screen bg-paper text-ink">
        <header className="border-b border-ink/15">
          <div className="mx-auto flex max-w-[1400px] min-w-0 flex-wrap items-baseline gap-x-8 gap-y-3 px-4 py-4 md:px-6">
            <span className="kicker text-mineral">Snajp · admin</span>

            {/* Plattformsflikarna först: det är de som skiljer den här ytan
                från kundens, och de ska inte behöva letas upp bland tio
                arbetsytesflikar. */}
            <nav aria-label="Plattform" className="flex min-w-0 flex-wrap gap-6">
              {ADMIN_TABS.map((tab) => (
                <Link key={tab.href} href={tab.href} className="text-[15px] hover:text-ochre">
                  {tab.label}
                </Link>
              ))}
            </nav>

            <span className="kicker ml-auto shrink-0 text-mineral">{admin.email}</span>
          </div>

          {arbetsyta.length > 0 ? (
            <div className="mx-auto max-w-[1400px] px-4 pb-3 md:px-6">
              <nav
                aria-label="Min arbetsyta"
                className="thin-scrollbar -mx-1 flex min-w-0 gap-5 overflow-x-auto px-1"
              >
                {arbetsyta.map((tab) => (
                  <Link
                    key={tab.href}
                    href={tab.href}
                    className="shrink-0 text-[14px] text-ink/55 transition-colors hover:text-ink"
                  >
                    {WORKSPACE_LABELS[tab.labelKey] ?? tab.labelKey}
                  </Link>
                ))}
              </nav>
            </div>
          ) : null}
        </header>

        <main className="mx-auto max-w-[1400px] px-4 py-10 md:px-6">{children}</main>
      </div>
    </DashboardProvider>
  );
}
