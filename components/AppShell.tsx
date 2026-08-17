"use client";

import { LogOut, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Logo } from "@/components/Logo";
import { AgentMenu } from "@/components/snajp/AgentMenu";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { signOut } from "@/lib/actions/auth";
import { ScopeSwitch } from "@/components/dashboard/ScopeSwitch";
import { useLocale } from "@/lib/i18n";
import { routesForProducts } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Operate mode. Same tokens as the marketing surfaces, product cadence: fixed
 * type scale, dense rows, no hero, no reveals, no daylight wash.
 *
 * The nav renders only what the workspace is entitled to, so a Support-only
 * customer never learns that Leads exists.
 */

/**
 * Länkarna i skalet pekar på /dashboard. På demo-ytan (/demo) finns ingen
 * session, så en sådan länk studsar besökaren till /login — mitt i det de
 * skulle prova.
 *
 * Kartan är explicit och inte en strängersättning: /dashboard/leads/kontroll
 * ligger under /demo/kontroll, alltså inte en ren prefixbyte. En regex hade
 * tyst gett /demo/leads/kontroll, som är en 404.
 */
const DEMO_VAGAR: Record<string, string> = {
  "/dashboard": "/demo",
  "/dashboard/leads": "/demo/leads",
  "/dashboard/leads/kontroll": "/demo/kontroll",
  "/dashboard/companies": "/demo/companies",
  "/dashboard/contacts": "/demo/contacts",
  "/dashboard/emails": "/demo/emails",
  "/dashboard/inbox": "/demo/inbox",
  "/dashboard/analytics": "/demo/analytics",
  "/dashboard/assistant": "/demo/assistant",
  "/dashboard/support": "/demo/support"
};

function iDemolage(pathname: string): boolean {
  return pathname === "/demo" || pathname.startsWith("/demo/");
}

function demoAnpassa(href: string, pathname: string): string {
  return iDemolage(pathname) ? (DEMO_VAGAR[href] ?? href) : href;
}

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { t, locale, toggleLocale } = useLocale();
  const { products, workspaceName, availableScopes, shows, isPlatformAdmin, isDemo, signedIn } =
    useDashboard();

  // Entitlement decides what exists; the scope switch decides what is on screen
  // right now. A nav listing eight Leads sections while the scope reads "Support"
  // contradicts the control the user just used.
  const navRoutes = routesForProducts(products).filter(
    (route) => route.product === "shared" || shows(route.product)
  );

  // Narrowing the scope while standing on a section it excludes would strand the
  // user on a page they can no longer navigate back to.
  const stranded = navRoutes.every(
    (route) => route.href === "/dashboard" || !pathname.startsWith(route.href)
  );

  useEffect(() => {
    if (pathname.startsWith("/dashboard/") && stranded) {
      router.replace("/dashboard");
    }
  }, [pathname, stranded, router]);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 bg-paper/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3 md:px-6">
          <Link
            href={demoAnpassa("/dashboard", pathname)}
            className="focus-ring inline-flex min-h-11 items-center rounded-input"
          >
            <Logo />
          </Link>

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
            {/* Samma meny som på kundserviceytan. Den ligger i AppShell och
                inte per sida: kontaktuppgifter, dataskydd och möjligheten att
                anmäla ett felaktigt svar är lika relevanta på leads-vyn som på
                supportvyn, och en meny som bara finns på hälften av ytorna är
                en meny användaren slutar leta efter. */}
            <AgentMenu yta="leads" kontext={`dashboard${pathname ? `:${pathname}` : ""}`} />

            {/* Utloggning. Fanns inte alls: signOut() i lib/actions/auth.ts var
                skriven och fungerande, men ingen komponent anropade den. Enda
                sättet att byta konto var att rensa cookies för hand.
                Samma sorts lucka som den saknade /admin-länken — funktionen var
                byggd, vägen dit var det inte.

                Formulär och inte onClick: signOut är en server action, och ett
                formulär gör att den fungerar även innan JavaScript laddat. */}
            {signedIn ? (
              <form action={signOut}>
                <button
                  type="submit"
                  className="focus-ring inline-flex min-h-11 items-center gap-1.5 rounded-input px-3 text-sm font-medium text-ink/55 transition-colors hover:text-ink"
                >
                  <LogOut className="h-4 w-4" aria-hidden />
                  <span className="hidden sm:inline">Logga ut</span>
                </button>
              </form>
            ) : null}
          </div>

          <nav
            aria-label={t("nav.dashboard")}
            className="thin-scrollbar order-last -mx-1 flex w-full min-w-0 gap-1 overflow-x-auto px-1 pb-1"
          >
            {navRoutes.map((route) => {
              const active =
                route.href === "/dashboard"
                  ? pathname === "/dashboard"
                  : pathname === route.href || pathname.startsWith(`${route.href}/`);
              return (
                <Link
                  key={route.href}
                  href={demoAnpassa(route.href, pathname)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "focus-ring inline-flex min-h-11 shrink-0 items-center rounded-input px-3 text-sm font-medium transition-colors",
                    active ? "bg-paper2 text-ink" : "text-ink/55 hover:bg-paper2/60 hover:text-ink"
                  )}
                >
                  {t(route.labelKey)}
                </Link>
              );
            })}

            {/* Plattformsadmin. Sist och visuellt skild från produktnavigationen:
                den leder ut ur den egna arbetsytan och in i ALLA kunders siffror,
                och ska inte se ut som ännu en flik bland de andra.

                Villkoret är en ledtråd, inte en grind. Grinden är
                getPlatformAdmin() i app/dashboard/admin/layout.tsx, som svarar 404
                — en manipulerad flagga ger alltså en länk till en 404, ingenting mer.

                Adminvyn ligger nu under /dashboard/admin, så den delar den vanliga
                navigeringen i stället för att vara en egen yta. */}
            {isPlatformAdmin ? (
              <Link
                href="/dashboard/admin"
                aria-current={pathname.startsWith("/dashboard/admin") ? "page" : undefined}
                className={cn(
                  "focus-ring ml-auto inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-input px-3 text-sm font-medium transition-colors",
                  pathname.startsWith("/dashboard/admin")
                    ? "bg-ochre/15 text-ink"
                    : "text-ochre hover:bg-ochre/10"
                )}
              >
                <ShieldCheck className="h-4 w-4" aria-hidden />
                Admin
              </Link>
            ) : null}
          </nav>
        </div>
      </header>

      <main>
        {/* Demo-banner: en demo-workspace ska veta vad den är och vad som
            begränsar den. Uppgraderingen till fullt konto (med planval) är
            uppskjuten — vägen ut är kontakt just nu. */}
        {isDemo ? (
          <div className="border-b border-ochre/30 bg-ochre/10">
            <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 md:px-6">
              <span className="kicker text-ochre">Demo</span>
              <span className="text-[13px] text-ink/70">
                Du testar Snajp med ett begränsat antal körningar.
              </span>
              <a
                href="mailto:hej@snajp.se"
                className="kicker ml-auto text-ochre underline underline-offset-4 hover:text-ink"
              >
                Kontakta oss
              </a>
            </div>
          </div>
        ) : null}
        {children}
      </main>
    </div>
  );
}

/**
 * Section wrapper. Signature is unchanged from the editorial version so every
 * workspace view keeps working; only the register changed. `kicker` is now a
 * product label rather than a mono eyebrow, and the title is a fixed rem size:
 * a clamp-sized heading that shrinks inside a dense layout looks worse, not
 * better.
 */
export function PageShell({
  kicker,
  title,
  description,
  children,
  action
}: Readonly<{
  kicker: string;
  title: string;
  description: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}>) {
  return (
    <AppShell>
      <section className="mx-auto max-w-[1400px] px-4 py-8 md:px-6 md:py-10">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[0.8125rem] font-medium text-ink/45">{kicker}</p>
            <h1 className="mt-1 text-[1.5rem] font-semibold leading-tight tracking-[-0.02em]">{title}</h1>
            <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink/65">{description}</p>
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
        <div className="mt-8">{children}</div>
      </section>
    </AppShell>
  );
}
