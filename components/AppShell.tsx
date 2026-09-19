"use client";

import {
  ArrowLeftRight,
  FileText,
  LayoutDashboard,
  LogOut,
  Mail,
  MessagesSquare,
  ScanLine,
  Settings,
  Target,
  Users
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { mejlaOss } from "@/components/marketing/copy";
import { AgentMenu } from "@/components/snajp/AgentMenu";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Rail, RailRad } from "@/components/shell/Rail";
import type { RailNavItem } from "@/components/shell/Rail";
import { signOut } from "@/lib/actions/auth";
import { DEMO_NAV, demoSektionsVag } from "@/lib/demo/sektioner";
import { BytKund } from "@/components/admin/BytKund";
import { ImpersonationBanner } from "@/components/ImpersonationBanner";
import { VyVaxel } from "@/components/VyVaxel";
import { useLocale } from "@/lib/i18n";
import { produktForInstallningsvag, routesForProducts, tillAdminvag } from "@/lib/routes";
import type { Scope } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Operate mode. Samma tokens som marknadsytorna, produktens kadens: fast
 * typskala, täta rader, ingen hero, inga reveals.
 *
 * ## Skalet är en vänsterrail sedan 2026-09-15
 *
 * Arbetsytan bar tidigare en topp-header med flikrad — en tredje chrome vid
 * sidan av bokforing-webbs rail och demons band. Nu delar alla produktytor
 * bokforing-webbs struktur (components/Sidebar.tsx där): en fast ink-rail till
 * vänster — sajtens EN tonala inversion — med ochre-markör på aktiv flik, och
 * en smal kontrollrad överst i innehållskolumnen. På smala skärmar krymper
 * railen till en ikonrail i stället för att gömmas bakom en hamburgare:
 * menyn ÄR ytans karta.
 *
 * Navigationen renderar bara det arbetsytan har rätt till, så en Support-kund
 * aldrig får veta att Leads finns.
 */

/**
 * Länkarna i skalet pekar på /dashboard. På demo-ytan (/demo) finns ingen
 * session, så en sådan länk studsar besökaren till /login — mitt i det de
 * skulle prova.
 *
 * Kartan är explicit och inte en strängersättning: den täcker alla ytor och
 * hindrar att en ny /dashboard-route glöms bort och tyst pekar in i /login.
 */
const DEMO_VAGAR: Record<string, string> = {
  "/dashboard": "/demo",
  "/dashboard/iris": "/demo/iris",
  "/dashboard/iris/granskning": "/demo/iris/granskning",
  "/dashboard/iris/installningar": "/demo/iris/installningar",
  "/dashboard/companies": "/demo/companies",
  "/dashboard/contacts": "/demo/contacts",
  "/dashboard/inbox": "/demo/inbox",
  "/dashboard/analytics": "/demo/analytics",
  "/dashboard/assistant": "/demo/assistant",
  "/dashboard/support": "/demo/support",
  "/dashboard/kvitton": "/demo/kvitton"
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
  "/dashboard/iris": "leads",
  "/dashboard/support": "support"
};

/**
 * Ikon per menypost. Railen bär ikoner även i smalt läge, så varje route som
 * kan stå i menyn behöver en — okänd route får LayoutDashboard hellre än att
 * railen renderar ett hål.
 *
 * Exporterad: `AdminShell` återanvänder samma karta för sin "Arbetsyta"-grupp,
 * så att samma /dashboard/*-route alltid bär samma ikon oavsett vilken yta
 * den renderas på.
 */
export const RUTT_IKONER: Record<string, LucideIcon> = {
  "/dashboard": LayoutDashboard,
  "/dashboard/iris": Target,
  "/dashboard/support": MessagesSquare,
  "/dashboard/companies": Users,
  "/dashboard/contacts": Users,
  "/dashboard/inbox": Mail,
  "/dashboard/larande": FileText,
  "/dashboard/analytics": ArrowLeftRight,
  "/dashboard/assistant": MessagesSquare,
  "/dashboard/kvitton": ScanLine,
  "/settings": Settings
};

const DEMO_IKONER: Record<string, typeof LayoutDashboard> = {
  "": LayoutDashboard,
  iris: Target,
  crm: Users,
  support: MessagesSquare,
  kvitton: ScanLine
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
  const {
    products,
    workspaceName,
    shows,
    isDemo,
    signedIn,
    vy,
    availableScopes,
    setScope,
    isPlatformAdmin
  } = useDashboard();

  // Entitlement decides what exists; the scope switch decides what is on screen
  // right now. A nav listing eight Leads sections while the scope reads "Support"
  // contradicts the control the user just used.
  //
  // MEN: lägesflikarna själva undantas från det filtret.
  //
  // Flikarna ÄR växeln (FLIKENS_LAGE). Filtrerades de på `shows()` göms den
  // kontroll man skulle ha tryckt på: står man i Leads försvinner
  // Kundtjänst-fliken, och enda vägen till kundtjänst blir att först gå via
  // Översikt — vilket inte står någonstans. Uppmätt i skärmdump från demovyn,
  // där menyn saknade Kundtjänst helt.
  //
  // Regeln: en kontroll får aldrig gömma sig själv. Entitlement styr att
  // fliken finns; läget styr vad innehållet visar.
  const navRoutes = routesForProducts(products, { isAdmin: isPlatformAdmin }).filter(
    (route) =>
      route.product === "shared" || route.href in FLIKENS_LAGE || shows(route.product)
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
  const natbaraRoutes = routesForProducts(products, {
    includePreview: true,
    isAdmin: isPlatformAdmin
  }).filter(
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
  // ~20 vyer som inte vet vilken yta den renderas i — och inte ska behöva veta.
  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    return <>{children}</>;
  }

  const demolage = iDemolage(pathname);

  // Railens huvudlista och bottenlista. Inställningar dras ut ur huvudflödet
  // och står i en egen grupp vid botten, som i bokforing-webb: den hör till
  // ramen, inte till arbetet. Demon har ingen inställningspost alls — se
  // lib/demo/sektioner.ts för varför.
  const huvudRoutes = navRoutes.filter((route) => route.href !== "/settings");
  const settingsRoute = navRoutes.find((route) => route.href === "/settings");

  // Railens navposter, omsatta till Rail-komponentens generiska form. Samma
  // beräkning som innan extraktionen (se components/shell/Rail.tsx) — bara
  // flyttad hit så att markupen kan delas med AdminShell.
  const navItems: RailNavItem[] = demolage
    ? DEMO_NAV.map((item) => {
        const href = demoSektionsVag(item.slug);
        const children = item.children?.map((child) => {
          const childHref = demoSektionsVag(child.slug);
          return { href: childHref, label: child.label, active: pathname === childHref };
        });
        return {
          href,
          label: item.label,
          Icon: DEMO_IKONER[item.slug] ?? LayoutDashboard,
          // Föräldern räknas aktiv om man står på den, ELLER på ett av dess
          // barn — CRM-listan har t.ex. sökvägen /demo/crm, alltså inte under
          // /demo/iris/, och ett prefix-test hade missat den.
          active: pathname === href || Boolean(children?.some((c) => c.active)),
          children
        };
      })
    : huvudRoutes.map((route) => {
        const aktiv =
          route.href === "/dashboard"
            ? pathname === "/dashboard"
            : pathname === route.href || pathname.startsWith(`${route.href}/`);
        return {
          href: demoAnpassa(route.href, pathname),
          label: t(route.labelKey),
          Icon: RUTT_IKONER[route.href] ?? LayoutDashboard,
          active: aktiv,
          // Läget sätts vid klicket, inte i en effekt på den nya sidan: en
          // effekt hade hunnit rendera målsidan i det gamla läget först, och
          // bytet hade synts som ett hopp.
          onClick: () => {
            const lage = FLIKENS_LAGE[route.href];
            if (lage && availableScopes.includes(lage)) {
              setScope(lage);
            }
          },
          // Barnen (Iris: Bolag/Granskning/Inställningar) — exakt match, inte
          // prefix: /dashboard/iris/granskning ska inte markera /dashboard/iris.
          children: route.children?.map((child) => {
            const childHref = demoAnpassa(child.href, pathname);
            return { href: childHref, label: t(child.labelKey), active: pathname === childHref };
          })
        };
      });

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* Före allt annat i DOM och med högre z-index: bannern ska ligga ÖVER
          det klistrade innehållet, inte försvinna bakom det vid scroll. */}
      <ImpersonationBanner />

      <div className="flex min-h-dvh">
        {/* Vänsterrailen — sajtens EN tonala inversion (DESIGN.md: en per
            sida). Alltid synlig: på smala skärmar krymper den till en ikonrail
            i stället för att gömmas bakom en hamburgare, eftersom menyn ÄR
            ytans karta. Delad med AdminShell via components/shell/Rail.tsx. */}
        <Rail
          logoHref={demoAnpassa("/dashboard", pathname)}
          logoAriaLabel={demolage ? "Snajp demo — till översikten" : "Snajp — till översikten"}
          brand={
            // Arbetsytans namn — samma plats som "Bokföring"-etiketten i
            // bokforing-webbs rail. I demon står demomarkören här i stället:
            // den säger vad ytan ÄR, alltså hör den ihop med märket.
            demolage ? (
              <p className="hidden px-5 pb-4 lg:block">
                {/* Renderas inuti railen (bg-ink) via Rail-komponentens
                    brand-slot — text-warning är kalibrerad mot ljusa ytor och
                    gav bara 2.51:1 här. text-ochre ger 6.54:1 mot den
                    ochre-tonade railbakgrunden. */}
                <span className="inline-flex items-center rounded-input border border-ochre/40 bg-ochre/10 px-2 py-0.5 text-[0.75rem] font-medium text-ochre">
                  Demo · exempeldata
                </span>
              </p>
            ) : (
              <p className="hidden truncate px-5 pb-4 text-[0.75rem] font-medium uppercase tracking-[0.14em] text-paper-subtle lg:block">
                {workspaceName}
              </p>
            )
          }
          navLabel={t("nav.dashboard")}
          groups={[{ items: navItems }]}
          footer={
            <>
              {settingsRoute && !demolage ? (
                <RailRad
                  href={settingsRoute.href}
                  etikett={t(settingsRoute.labelKey)}
                  Ikon={Settings}
                  aktiv={pathname === "/settings" || pathname.startsWith("/settings/")}
                />
              ) : null}
              {demolage ? (
                <p className="hidden px-3 pb-1 pt-3 text-[0.75rem] leading-5 text-paper-subtle lg:block">
                  Snajp — prova utan konto
                </p>
              ) : null}
            </>
          }
        />

        <div className="flex min-w-0 flex-1 flex-col">
          {/* Kontrollraden. Railen bär navigationen; det här är allt som inte
              är navigation — kontosaker, växlar, språk. De bor i en ljus rad
              överst i innehållet i stället för på railen: BytKund, VyVaxel och
              AgentMenu är ritade för ljus yta, och en mörk rail med tre ljusa
              öar hade varit sämre än två renodlade ytor. */}
          <header className="safe-top sticky top-0 z-30 border-b border-ink/10 bg-paper/85 backdrop-blur-xl">
            <div className="flex min-h-[52px] flex-wrap items-center justify-end gap-x-1.5 gap-y-1 px-4 py-1.5 md:px-6">
              {/* Demomarkören igen, för smala skärmar där railens etikett inte
                  får plats — utan den vet en mobil besökare inte vad ytan är. */}
              {demolage ? (
                <span className="mr-auto inline-flex items-center rounded-input border border-ochre/40 bg-ochre/10 px-2.5 py-1 text-[13px] font-medium text-warning lg:hidden">
                  Demo · exempeldata
                </span>
              ) : (
                <span className="mr-auto truncate text-[13px] font-medium text-ink-subtle lg:hidden">
                  {workspaceName}
                </span>
              )}

              {/* Admin / Demo. Ersätter både den gamla /admin-länken längst ut
                  i flikraden och lägesväxlaren: läget styrs numera av Leads-
                  och Support-posterna i railen, se ovan. */}
              <BytKund />
              <VyVaxel />
              <button
                type="button"
                onClick={toggleLocale}
                className="focus-ring min-h-11 rounded-input px-3 text-sm font-medium text-ink-subtle transition-colors hover:text-ink"
              >
                {locale === "sv" ? "EN" : "SV"}
              </button>
              {/* Samma meny som på kundserviceytan. Den ligger i AppShell och
                  inte per sida: kontaktuppgifter, dataskydd och möjligheten att
                  anmäla ett felaktigt svar är lika relevanta på leads-vyn som
                  på supportvyn, och en meny som bara finns på hälften av
                  ytorna är en meny användaren slutar leta efter. */}
              <AgentMenu yta="leads" kontext={`dashboard${pathname ? `:${pathname}` : ""}`} />

              {/* Utloggning. Formulär och inte onClick: signOut är en server
                  action, och ett formulär gör att den fungerar även innan
                  JavaScript laddat. */}
              {signedIn ? (
                <form action={signOut}>
                  <button
                    type="submit"
                    className="focus-ring inline-flex min-h-11 items-center gap-1.5 rounded-input px-3 text-sm font-medium text-ink-subtle transition-colors hover:text-ink"
                  >
                    <LogOut className="h-4 w-4" aria-hidden />
                    <span className="hidden sm:inline">Logga ut</span>
                  </button>
                </form>
              ) : null}

              {/* Demons två utvägar, i samma register som varje annan
                  kontroll. */}
              {demolage ? (
                <>
                  <Link
                    href="/"
                    className="focus-ring hidden min-h-11 items-center rounded-input px-3 text-sm font-medium text-ink-subtle transition-colors hover:text-ink sm:inline-flex"
                  >
                    Till startsidan
                  </Link>
                  <Link
                    href="/login"
                    className="focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-sm font-medium text-ink-subtle transition-colors hover:text-ink"
                  >
                    Logga in
                  </Link>
                </>
              ) : null}
            </div>
          </header>

          <main className="min-w-0 flex-1">
            {/* Den öppna demons väg vidare. Demon är första steget från
                "Prova agenten"-länkarna på marknadssidorna; nästa steg är
                testkundsläget — den kompletta arbetsytan med egna data, via
                inloggningslänk. Frågan ställs HÄR, i ytan besökaren redan
                bestämt sig för att utforska, inte bara på inloggningssidan. */}
            {demolage ? (
              <div className="border-b border-ochre/30 bg-ochre/10">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 md:px-6">
                  <span className="text-[13px] text-ink-muted">
                    Allt här är exempeldata. Klicka fritt, inget skickas.
                  </span>
                  {/* Ink-knapp, inte ochre-text: --ochre (L 0.74) ger 2.17:1
                      mot paper och duger aldrig som 13px text — se DESIGN.md
                      om uppmätt kontrast. */}
                  <Link
                    href="/login"
                    className="focus-ring ml-auto inline-flex min-h-8 items-center rounded-input bg-ink px-3 py-1 text-[13px] font-semibold text-paper transition-colors hover:bg-ink2"
                  >
                    Testa fullständiga tjänsten med era egna data, kostnadsfritt
                  </Link>
                </div>
              </div>
            ) : null}

            {/* Demo-banner: en demo-workspace ska veta vad den är och vad som
                begränsar den. Uppgraderingen till fullt konto (med planval) är
                uppskjuten — vägen ut är kontakt just nu. */}
            {isDemo || vy === "demo" ? (
              <div className="border-b border-ochre/30 bg-ochre/10">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 md:px-6">
                  <span className="kicker text-warning">Demo</span>
                  {/* Demovyn bär ingen förklarande rad längre. Märkningen
                      "Demo" räcker där; texten om demokontot namngav dessutom
                      exempelbutiken i en yta som visas för kunder. */}
                  {vy === "demo" ? null : (
                    <span className="text-[13px] text-ink-muted">
                      Du testar Snajp med ett begränsat antal körningar.
                    </span>
                  )}
                  {vy === "demo" ? null : (
                    /* Samma adress som marknadssidan, via samma konstant.
                       Hårdkodad här stod den utanför bytet i copy.ts. */
                    <a
                      href={mejlaOss()}
                      className="kicker ml-auto text-warning underline underline-offset-4 hover:text-ink"
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
      </div>
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
  /** Överraden. Utelämnas när sidan inte ska ha någon — se nedan. */
  kicker?: string;
  title: string;
  /** Ingressen. Samma sak: en vy utan ingress renderar ingen tom rad. */
  description?: string;
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
      {/* 1200 och inte 1400: innehållet delar numera raden med railen, och
          1400 hade gett över 90 tecken per rad i tabellerna på en bred skärm. */}
      <section className={iAdmin ? "" : "mx-auto w-full max-w-[1200px] px-4 py-8 md:px-8 md:py-10"}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            {/* Tomma rader renderas inte alls. Flera vyer har fått sin
                överrad eller ingress borttagen, och ett tomt <p> lämnar kvar
                sin marginal — rubriken hade legat och flutit en rad för lågt
                utan något som förklarar varför. */}
            {kicker ? <p className="text-[0.8125rem] font-medium text-ink-subtle">{kicker}</p> : null}
            <h1 className={cn("font-display text-[1.625rem] font-semibold leading-tight tracking-[-0.02em]", kicker && "mt-1")}>
              {title}
            </h1>
            {description ? (
              <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink-muted">{description}</p>
            ) : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
        <div className="mt-8">{children}</div>
      </section>
    </AppShell>
  );
}
