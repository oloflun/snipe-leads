"use client";

import { LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Logo } from "@/components/Logo";
import { AgentMenu } from "@/components/snajp/AgentMenu";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { signOut } from "@/lib/actions/auth";
import { VyVaxel } from "@/components/VyVaxel";
import { useLocale } from "@/lib/i18n";
import { produktForInstallningsvag, routesForProducts, tillAdminvag } from "@/lib/routes";
import type { Scope } from "@/lib/routes";
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

/**
 * Flikarna ÄR lägesväxeln.
 *
 * Tidigare fanns en separat kontroll (ScopeSwitch) bredvid flikraden, och den
 * gjorde en annan sak än flikarna: "Leads" tog dig till leads-sidan men lämnade
 * resten av appen i Duo, så inställningarna bakom fliken visade fortfarande
 * båda agenterna. Två kontroller för en sak, där den ena bara gjorde halva
 * jobbet.
 *
 * Nu smalnar Leads och Support av hela vyn, och Översikt tar tillbaka Duo.
 * Kartan är explicit: en route utan post här rör inte läget.
 */
export const FLIKENS_LAGE: Record<string, Scope> = {
  "/dashboard": "both",
  "/dashboard/leads": "leads",
  "/dashboard/support": "support"
};

function iDemolage(pathname: string): boolean {
  return pathname === "/demo" || pathname.startsWith("/demo/");
}

function iAdminlage(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

function demoAnpassa(href: string, pathname: string): string {
  return iDemolage(pathname) ? (DEMO_VAGAR[href] ?? href) : href;
}

/**
 * Arbetsytans länkar, anpassade till ytan de renderas på.
 *
 * Samma vyer renderas på tre ytor: /dashboard (kunden), /admin (plattforms-
 * admin) och /demo (utan session). En hårdkodad `/dashboard/...` i en vy är
 * därför rätt på en av tre. På /admin studsade den dessutom tillbaka till
 * /admin (app/dashboard/layout.tsx skickar plattformsadmin dit), så varje
 * innehållslänk tog admin ur den vy de stod i — samma fel som flikraden hade,
 * fast i brödtexten.
 *
 * `/dashboard` mappas till `/admin/arbetsyta`; se AdminShell för varför.
 * Kartan bor i lib/routes.ts, delad med AdminShell — se `tillAdminvag`.
 */
export function useArbetsvag(): (href: string) => string {
  const pathname = usePathname();
  return (href: string) => {
    if (iAdminlage(pathname)) {
      return tillAdminvag(href);
    }
    return demoAnpassa(href, pathname);
  };
}

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { t, locale, toggleLocale } = useLocale();
  const { products, workspaceName, shows, isDemo, signedIn, vy, availableScopes, setScope } =
    useDashboard();

  // Entitlement decides what exists; the scope switch decides what is on screen
  // right now. A nav listing eight Leads sections while the scope reads "Support"
  // contradicts the control the user just used.
  const navRoutes = routesForProducts(products).filter(
    (route) => route.product === "shared" || shows(route.product)
  );

  // Narrowing the scope while standing on a section it excludes would strand the
  // user on a page they can no longer navigate back to.
  //
  // Räknas mot ALLA routes arbetsytan äger, inte bara de som står i menyn.
  // Skillnaden är `preview`-routerna: `lib/routes.ts` säger att de "nås
  // fortfarande direkt" och att flaggan bara styr vad som VISAS i menyn — men
  // eftersom de saknades här studsade varje sådan adress tillbaka till
  // /dashboard. Alltså gick /dashboard/companies, /contacts, /inbox,
  // /analytics och /assistant inte att öppna alls som kund, och koden på båda
  // ställena såg rätt ut var för sig.
  //
  // Scope-skyddet står kvar orört: filtret på `shows()` gäller fortfarande, så
  // den som smalnar av vyn till Support medan de står på en leads-sida
  // dirigeras som förut.
  const natbaraRoutes = routesForProducts(products, { includePreview: true }).filter(
    (route) => route.product === "shared" || shows(route.product)
  );

  const stranded = natbaraRoutes.every(
    (route) => route.href === "/dashboard" || !pathname.startsWith(route.href)
  );

  // Samma resonemang för inställningarna, som skyddet aldrig täckte: filtret
  // där grindade på `products` (rättighet) och aldrig på läget, så den som
  // smalnade av till Support stod kvar på /settings/leads med en sidokolumn
  // som inte längre listade sidan de befann sig på. Gäller båda ytorna —
  // hjälparen känner igen /admin/installningar också.
  const installningsProdukt = produktForInstallningsvag(pathname);
  const strandadIInstallningar = installningsProdukt !== null && !shows(installningsProdukt);

  useEffect(() => {
    if (pathname.startsWith("/dashboard/") && stranded) {
      router.replace("/dashboard");
    } else if (strandadIInstallningar) {
      router.replace(pathname.startsWith("/admin/") ? "/admin/installningar" : "/settings");
    }
  }, [pathname, stranded, strandadIInstallningar, router]);

  // Inuti adminytan äger AdminShell skalet, och det här ska bara vara innehåll.
  //
  // Varje arbetsytesvy renderar sitt eget AppShell via PageShell. Under /admin
  // gav det TVÅ staplade headers, och den inre navigationen pekade på
  // /dashboard/* — vilket för en plattformsadmin studsar tillbaka till /admin
  // (app/dashboard/layout.tsx). Alltså: varje flik i den inre raden tog
  // användaren ur den flik de stod i. Uppmätt i skärmdump, inte antaget.
  //
  // Villkoret läser pathname och inte en prop, för att PageShell anropas från
  // ~20 vyer som inte vet vilken yta de renderas i — och inte ska behöva veta.
  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    return <>{children}</>;
  }

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
            {/* Admin / Demo. Ersätter både den gamla /admin-länken längst ut i
                flikraden och läges­växlaren: läget styrs numera av Leads- och
                Support-flikarna själva, se nedan. */}
            <VyVaxel />
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
                  // Läget sätts vid klicket, inte i en effekt på den nya sidan:
                  // en effekt hade hunnit rendera målsidan i det gamla läget
                  // först, och bytet hade synts som ett hopp.
                  onClick={() => {
                    const lage = FLIKENS_LAGE[route.href];
                    if (lage && availableScopes.includes(lage)) {
                      setScope(lage);
                    }
                  }}
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

      <main>
        {/* Demo-banner: en demo-workspace ska veta vad den är och vad som
            begränsar den. Uppgraderingen till fullt konto (med planval) är
            uppskjuten — vägen ut är kontakt just nu. */}
        {isDemo || vy === "demo" ? (
          <div className="border-b border-ochre/30 bg-ochre/10">
            <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 md:px-6">
              <span className="kicker text-ochre">Demo</span>
              <span className="text-[13px] text-ink/70">
                {vy === "demo"
                  ? "Demokontot Nordlys Handel. Allt du gör här skrivs till demokontot, aldrig till en kund."
                  : "Du testar Snajp med ett begränsat antal körningar."}
              </span>
              {vy === "demo" ? null : (
                <a
                  href="mailto:hej@snajp.se"
                  className="kicker ml-auto text-ochre underline underline-offset-4 hover:text-ink"
                >
                  Kontakta oss
                </a>
              )}
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
  const pathname = usePathname();
  // Under /admin bär `app/admin/layout.tsx` redan containern. Två containers
  // gav dubbel padding och en innerbredd 48px smalare än resten av ytan —
  // syns direkt när man växlar mellan en plattformsflik och en arbetsytesflik.
  const iAdmin = pathname === "/admin" || pathname.startsWith("/admin/");

  return (
    <AppShell>
      <section className={iAdmin ? "" : "mx-auto max-w-[1400px] px-4 py-8 md:px-6 md:py-10"}>
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
