"use client";

import {
  Activity,
  ArrowLeftRight,
  FileText,
  LayoutDashboard,
  ListTodo,
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
import { LasrollBanner } from "@/components/LasrollBanner";
import { VyVaxel } from "@/components/VyVaxel";
import { useLocale, type Localized } from "@/lib/i18n";
import { appRoutes, produktForInstallningsvag, routesForProducts, tillAdminvag } from "@/lib/routes";
import type { Scope } from "@/lib/routes";
import { cn } from "@/lib/utils";
import { rubrikSida } from "@/components/ui";

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
  "/dashboard/att-gora": "/demo/att-gora",
  "/dashboard/leads": "/demo/leads",
  "/settings/leads": "/demo/installningar",
  "/dashboard/companies": "/demo/companies",
  "/dashboard/contacts": "/demo/contacts",
  "/dashboard/inbox": "/demo/inbox",
  "/dashboard/analytics": "/demo/analytics",
  "/dashboard/assistant": "/demo/assistant",
  "/dashboard/support": "/demo/support",
  "/dashboard/kvitton": "/demo/kvitton"
};

/**
 * Lägesväxeln är pensionerad (Snajp Suite 2026-10-03).
 *
 * Fram till i dag smalnade ett klick på Iris eller Kundtjänst av HELA vyn
 * (`snajp.scope`), och menyn filtrerades på läget. Följden var uppmätt: i
 * adminytan försvann Kundtjänst och Kvitton ur railen när man klickade Iris,
 * och en Trio-kund som stod i Iris kunde inte nå Kvitton alls. Menyn är nu
 * platt och visar alltid allt arbetsytan har; varje menyklick återställer
 * läget till helvyn, så att en gammal cookie inte lämnar inställningarna
 * avsmalnade. Scope-mekanismen står kvar för vyer som läser `shows()`.
 */
export function aterstallLage(availableScopes: readonly Scope[], setScope: (scope: Scope) => void): void {
  if (availableScopes.includes("both")) setScope("both");
}

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
  "/dashboard/att-gora": ListTodo,
  "/dashboard/leads": Target,
  "/dashboard/aktivitet": Activity,
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
  "att-gora": ListTodo,
  leads: Target,
  support: MessagesSquare,
  kvitton: ScanLine,
  installningar: Settings
};

function iDemolage(pathname: string): boolean {
  return pathname === "/demo" || pathname.startsWith("/demo/");
}

function iAdminlage(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

function demoAnpassa(href: string, pathname: string): string {
  if (!iDemolage(pathname)) return href;
  // Sökvägen mappas, frågan följer med: `/dashboard/leads?vy=listor` ska bli
  // `/demo/leads?vy=listor`, inte falla igenom kartan och lämna demon.
  const i = href.search(/[?#]/);
  const vag = i === -1 ? href : href.slice(0, i);
  const resten = i === -1 ? "" : href.slice(i);
  return (DEMO_VAGAR[vag] ?? vag) + resten;
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
  const { t, text, locale, toggleLocale } = useLocale();
  const {
    products,
    workspaceName,
    shows,
    isDemo,
    signedIn,
    userEmail,
    vy,
    availableScopes,
    setScope,
    isPlatformAdmin
  } = useDashboard();

  // Entitlement styr menyn, inget annat (Snajp Suite 2026-10-03, se
  // aterstallLage ovan). En meny som döljer poster efter läget gömmer den
  // kontroll man skulle ha tryckt på.
  const navRoutes = routesForProducts(products, { isAdmin: isPlatformAdmin });

  /**
   * Agenterna arbetsytan INTE har — de MÖRKLÄGGS i menyn i stället för att
   * döljas. Den som köpt Support ska se att Iris och Kvitton finns (klicket
   * leder till agentens upsell-vy i WorkspaceSection), men nedtonade så att
   * det egna paketet är det som lyser. Bara de tre riktiga agentflikarna:
   * preview-ytor och delade poster berörs inte, och scope-växeln lämnar dem
   * ifred — en agent man inte äger har inget läge att visa.
   */
  const morkaRoutes = appRoutes.filter(
    (route) =>
      route.product !== "shared" &&
      !route.preview &&
      !products.includes(route.product)
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
  // Sedan Snajp Suite filtreras det inte längre på läget: menyn visar allt
  // arbetsytan äger, och en sida man når från menyn ska aldrig studsa.
  const natbaraRoutes = routesForProducts(products, {
    includePreview: true,
    isAdmin: isPlatformAdmin
  });

  const stranded =
    natbaraRoutes.every(
      (route) => route.href === "/dashboard" || !pathname.startsWith(route.href)
    ) &&
    // En mörklagd agents upsell-vy är en giltig plats att stå på — den som
    // klickade på Kvitton utan paketet ska läsa erbjudandet, inte studsas
    // tillbaka till översikten av scope-skyddet.
    !morkaRoutes.some((route) => pathname.startsWith(route.href));

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
          return { href: childHref, label: text(child.label), active: pathname === childHref };
        });
        return {
          href,
          label: text(item.label),
          Icon: DEMO_IKONER[item.slug] ?? LayoutDashboard,
          // Föräldern räknas aktiv om man står på den, ELLER på ett av dess
          // barn — CRM-listan har t.ex. sökvägen /demo/crm, alltså inte under
          // /demo/iris/, och ett prefix-test hade missat den.
          active: pathname === href || Boolean(children?.some((c) => c.active)),
          children
        };
      })
    : [
        ...huvudRoutes.map((route) => {
          const aktiv =
            route.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname === route.href || pathname.startsWith(`${route.href}/`);
          return {
            grundHref: route.href,
            href: demoAnpassa(route.href, pathname),
            label: t(route.labelKey),
            Icon: RUTT_IKONER[route.href] ?? LayoutDashboard,
            active: aktiv,
            // Läget sätts vid klicket, inte i en effekt på den nya sidan: en
            // effekt hade hunnit rendera målsidan i det gamla läget först, och
            // bytet hade synts som ett hopp.
            onClick: () => aterstallLage(availableScopes, setScope)
          };
        }),
        // De mörklagda agenterna — syns, men nedtonade (se morkaRoutes ovan).
        // Inget onClick: en agent utan paket har inget scope att växla till,
        // och inga barn — upsell-vyn är EN sida.
        ...morkaRoutes.map((route) => ({
          grundHref: route.href,
          href: route.href,
          label: t(route.labelKey),
          Icon: RUTT_IKONER[route.href] ?? LayoutDashboard,
          active: pathname === route.href || pathname.startsWith(`${route.href}/`),
          dimmad: true,
          dimmadTitel: "Ingår inte i ert paket ännu — klicka och läs mer"
        }))
      ]
        // Menyn ska stå i appRoutes ordning oavsett vilka poster som är
        // mörklagda — Iris före Support före Kvitton, som för en Trio-kund.
        .sort(
          (a, b) =>
            appRoutes.findIndex((r) => r.href === a.grundHref) -
            appRoutes.findIndex((r) => r.href === b.grundHref)
        )
        .map(({ grundHref: _grundHref, ...item }) => item);

  return (
    <div className="appyta min-h-screen bg-paper text-ink">
      {/* Före allt annat i DOM och med högre z-index: bannern ska ligga ÖVER
          det klistrade innehållet, inte försvinna bakom det vid scroll. */}
      <ImpersonationBanner />
      <LasrollBanner />

      <div className="flex min-h-dvh">
        {/* Vänsterrailen — sajtens EN tonala inversion (DESIGN.md: en per
            sida). Alltid synlig: på smala skärmar krymper den till en ikonrail
            i stället för att gömmas bakom en hamburgare, eftersom menyn ÄR
            ytans karta. Delad med AdminShell via components/shell/Rail.tsx. */}
        <Rail
          logoHref={demoAnpassa("/dashboard", pathname)}
          logoAriaLabel={
            demolage
              ? text({ sv: "Snajp demo, till översikten", en: "Snajp demo, to the overview" })
              : text({ sv: "Snajp, till översikten", en: "Snajp, to the overview" })
          }
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
                  {text({ sv: "Demo · exempeldata", en: "Demo · sample data" })}
                </span>
              </p>
            ) : (
              <p className="hidden truncate px-5 pb-4 text-[0.8125rem] font-medium text-paper-muted lg:block">
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

              {/* Kontrollerna bor i railen sedan 2026-10-01, i exakt samma
                  komposition som AdminShell: kunduppslag, vy-växel, menyn
                  (kontakt, dataskydd, anmäl felaktigt svar), kontoadressen,
                  och utloggning + språk på EN rad. Antons beställning: menyn
                  ska inte ta plats överst på sidan. Bara vid lg+ — i ikonläget
                  saknar kontrollerna ett ikon-only-läge, och mobilraden
                  nedanför bär det som måste nås där. */}
              <div className="hidden flex-col gap-1.5 border-t border-paper/10 px-1 pt-3 lg:flex">
                {(isPlatformAdmin && !demolage) ? (
                  <div className="flex flex-wrap items-center gap-1">
                    <BytKund ton="rail" />
                    <VyVaxel ton="rail" />
                  </div>
                ) : null}
                <AgentMenu yta="leads" kontext={`dashboard${pathname ? `:${pathname}` : ""}`} ton="rail" />
                {userEmail && !demolage ? (
                  <p title={userEmail} className="truncate px-1 pt-0.5 text-[0.75rem] text-paper-subtle">{userEmail}</p>
                ) : null}
              </div>
              <div className="hidden flex-col items-center gap-1 lg:flex lg:flex-row lg:justify-between">
                {signedIn ? (
                  <form action={signOut} className="w-full lg:w-auto lg:flex-1">
                    <button
                      type="submit"
                      className="focus-ring flex min-h-11 w-full items-center gap-1.5 rounded-input px-3 text-sm font-medium text-paper-muted transition-colors hover:bg-paper/5 hover:text-paper lg:justify-start"
                    >
                      <LogOut className="h-4 w-4 shrink-0" aria-hidden />
                      <span>{text({ sv: "Logga ut", en: "Sign out" })}</span>
                    </button>
                  </form>
                ) : demolage ? (
                  <div className="flex w-full flex-col lg:w-auto lg:flex-1">
                    <Link
                      href="/login"
                      className="focus-ring flex min-h-11 items-center rounded-input px-3 text-sm font-medium text-paper-muted transition-colors hover:bg-paper/5 hover:text-paper"
                    >
                      {text({ sv: "Logga in", en: "Sign in" })}
                    </Link>
                    <Link
                      href="/"
                      className="focus-ring flex min-h-11 items-center rounded-input px-3 text-sm font-medium text-paper-muted transition-colors hover:bg-paper/5 hover:text-paper"
                    >
                      {text({ sv: "Till startsidan", en: "To the start page" })}
                    </Link>
                  </div>
                ) : null}
                <button
                  type="button"
                  onClick={toggleLocale}
                  className="focus-ring min-h-11 shrink-0 rounded-input px-3 text-[13px] font-medium text-paper-muted transition-colors hover:bg-paper/5 hover:text-paper"
                >
                  {locale === "sv" ? "EN" : "SV"}
                </button>
              </div>
            </>
          }
        />

        <div className="flex min-w-0 flex-1 flex-col">
          {/* Mobilraden. Vid lg+ bär railens fot kontrollerna (samma
              komposition som AdminShell, Antons beställning 2026-10-01: menyn
              ska inte ta plats överst på sidan). Under lg är railen en ikonrail
              utan plats för dem, så det som MÅSTE nås på en telefon står här:
              ytans namn, menyn (kontakt, dataskydd, anmäl felaktigt svar),
              språk och utloggning. Kunduppslag och vy-växel är adminverktyg
              och saknas på mobilen — samma avgränsning som adminytan gör. */}
          <header className="safe-top sticky top-0 z-30 border-b border-ink/10 bg-paper/85 backdrop-blur-xl lg:hidden">
            <div className="flex min-h-[52px] flex-wrap items-center justify-end gap-x-1.5 gap-y-1 px-4 py-1.5 md:px-6">
              {/* Demomarkören för smala skärmar där railens etikett inte får
                  plats — utan den vet en mobil besökare inte vad ytan är. */}
              {demolage ? (
                <span className="mr-auto inline-flex items-center rounded-input border border-ochre/40 bg-ochre/10 px-2.5 py-1 text-[13px] font-medium text-warning">
                  {text({ sv: "Demo · exempeldata", en: "Demo · sample data" })}
                </span>
              ) : (
                <span className="mr-auto truncate text-[13px] font-medium text-ink-subtle">
                  {workspaceName}
                </span>
              )}

              <AgentMenu yta="leads" kontext={`dashboard${pathname ? `:${pathname}` : ""}`} />
              <button
                type="button"
                onClick={toggleLocale}
                className="focus-ring min-h-11 rounded-input px-3 text-sm font-medium text-ink-subtle transition-colors hover:text-ink"
              >
                {locale === "sv" ? "EN" : "SV"}
              </button>

              {/* Utloggning. Formulär och inte onClick: signOut är en server
                  action, och ett formulär gör att den fungerar även innan
                  JavaScript laddat. */}
              {signedIn ? (
                <form action={signOut}>
                  <button
                    type="submit"
                    aria-label={text({ sv: "Logga ut", en: "Sign out" })}
                    className="focus-ring inline-flex min-h-11 items-center gap-1.5 rounded-input px-3 text-sm font-medium text-ink-subtle transition-colors hover:text-ink"
                  >
                    <LogOut className="h-4 w-4" aria-hidden />
                    <span className="hidden sm:inline">{text({ sv: "Logga ut", en: "Sign out" })}</span>
                  </button>
                </form>
              ) : null}

              {demolage ? (
                <Link
                  href="/login"
                  className="focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-sm font-medium text-ink-subtle transition-colors hover:text-ink"
                >
                  {text({ sv: "Logga in", en: "Sign in" })}
                </Link>
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
                    {text({
                      sv: "Allt här är exempeldata. Klicka fritt, inget skickas.",
                      en: "Everything here is sample data. Click freely, nothing is sent."
                    })}
                  </span>
                  {/* Ink-knapp, inte ochre-text: --ochre (L 0.74) ger 2.17:1
                      mot paper och duger aldrig som 13px text — se DESIGN.md
                      om uppmätt kontrast. */}
                  <Link
                    href="/login"
                    className="focus-ring ml-auto inline-flex min-h-8 items-center rounded-input bg-ink px-3 py-1 text-[13px] font-semibold text-paper transition-colors hover:bg-ink2"
                  >
                    {text({
                      sv: "Testa hela tjänsten med era egna data, kostnadsfritt",
                      en: "Try the full service with your own data, free of charge"
                    })}
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
                  <span className="text-[0.8125rem] font-semibold text-warning">Demo</span>
                  {/* Demovyn bär ingen förklarande rad längre. Märkningen
                      "Demo" räcker där; texten om demokontot namngav dessutom
                      exempelbutiken i en yta som visas för kunder. */}
                  {vy === "demo" ? null : (
                    <span className="text-[13px] text-ink-muted">
                      {text({
                        sv: "Du testar Snajp med ett begränsat antal körningar.",
                        en: "You are trying Snajp with a limited number of runs."
                      })}
                    </span>
                  )}
                  {vy === "demo" ? null : (
                    /* Samma adress som marknadssidan, via samma konstant.
                       Hårdkodad här stod den utanför bytet i copy.ts. */
                    <a
                      href={mejlaOss()}
                      className="ml-auto text-[0.8125rem] font-medium text-warning underline underline-offset-4 hover:text-ink"
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
 * Arbetsytans sidram: skalet, containern och sidhuvudet.
 *
 * `kicker` och `description` togs bort 2026-09-28. Överraden och ingressen under
 * rubriken var mikrotext enligt F-016 — de beskrev sidan i mindre storlek än
 * brödtexten. Nödvändig information flyttades till varje anropsställe: in i
 * rubriken, i en meta-rad, eller bort där railen redan sa samma sak.
 */
export function PageShell({
  title,
  children,
  action
}: Readonly<{
  title: string | Localized;
  children: React.ReactNode;
  action?: React.ReactNode;
}>) {
  const pathname = usePathname();
  const { text } = useLocale();
  // Under /admin bär `app/admin/layout.tsx` redan containern. Två containers
  // gav dubbel padding och en innerbredd 48px smalare än resten av ytan —
  // syns direkt när man växlar mellan en plattformsflik och en arbetsytesflik.
  const iAdmin = pathname === "/admin" || pathname.startsWith("/admin/");

  return (
    <AppShell>
      {/* 1200 och inte 1400: innehållet delar numera raden med railen, och
          1400 hade gett över 90 tecken per rad i tabellerna på en bred skärm. */}
      <section className={iAdmin ? "" : "mx-auto w-full max-w-[1200px] px-4 py-6 md:px-8 md:py-8"}>
        {/* Sidans namn och dess enda handling på en rad, sedan datan. Samma
            skala som Sidhuvud (ui.tsx rubrikSida). */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className={cn(rubrikSida, "min-w-0 break-words")}>
            {typeof title === "string" ? title : text(title)}
          </h1>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
        <div className="mt-6">{children}</div>
      </section>
    </AppShell>
  );
}
