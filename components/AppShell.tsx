"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Logo } from "@/components/Logo";
import { useDashboard } from "@/components/dashboard/DashboardContext";
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
export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { t, locale, toggleLocale } = useLocale();
  const { products, workspaceName, availableScopes, shows } = useDashboard();

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
          <Link href="/dashboard" className="focus-ring inline-flex min-h-11 items-center rounded-input">
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
                  href={route.href}
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
          </nav>
        </div>
      </header>

      <main>{children}</main>
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
