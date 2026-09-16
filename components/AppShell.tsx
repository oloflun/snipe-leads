"use client";

import {
  ArrowLeftRight,
  FileText,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Mail,
  MessagesSquare,
  ScanLine,
  Settings,
  Target,
  Users
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Logo } from "@/components/Logo";
import { mejlaOss } from "@/components/marketing/copy";
import { AgentMenu } from "@/components/snajp/AgentMenu";
import { useDashboard } from "@/components/dashboard/DashboardContext";
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
  "/dashboard/support": "/demo/support",
  "/dashboard/bokforing": "/demo/bokforing"
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

/**
 * Ikon per menypost. Railen bär ikoner även i smalt läge, så varje route som
 * kan stå i menyn behöver en — okänd route får LayoutDashboard hellre än att
 * railen renderar ett hål.
 */
const RUTT_IKONER: Record<string, typeof LayoutDashboard> = {
  "/dashboard": LayoutDashboard,
  "/dashboard/leads": Target,
  "/dashboard/leads/listor": ListChecks,
  "/dashboard/support": MessagesSquare,
  "/dashboard/emails": Mail,
  "/dashboard/companies": Users,
  "/dashboard/contacts": Users,
  "/dashboard/inbox": Mail,
  "/dashboard/larande": FileText,
  "/dashboard/analytics": ArrowLeftRight,
  "/dashboard/assistant": MessagesSquare,
  "/dashboard/bokforing": ScanLine,
  "/settings": Settings
};

const DEMO_IKONER: Record<string, typeof LayoutDashboard> = {
  "": LayoutDashboard,
  leads: Target,
  crm: Users,
  support: MessagesSquare,
  emails: Mail,
  bokforing: ScanLine
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

/**
 * En rad i railen. Ochre-markör på aktiv flik — DESIGN.md:s "current
 * selection" — och etikett bara från lg; under det bär `title` namnet.
 */
function RailRad({
  href,
  etikett,
  Ikon,
  aktiv,
  onClick
}: Readonly<{
  href: string;
  etikett: string;
  Ikon: typeof LayoutDashboard;
  aktiv: boolean;
  onClick?: () => void;
}>) {
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={aktiv ? "page" : undefined}
      title={etikett}
      className={cn(
        "focus-ring relative flex h-11 shrink-0 items-center gap-3 rounded-input px-3 text-[0.9375rem] transition-colors",
        "justify-center lg:justify-start",
        aktiv
          ? "bg-paper/10 font-semibold text-paper"
          : "text-paper/60 hover:bg-paper/5 hover:text-paper"
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute bottom-2 left-0 top-2 w-[2px] rounded-full bg-ochre transition-opacity",
          aktiv ? "opacity-100" : "opacity-0"
        )}
      />
      <Ikon className={cn("h-[18px] w-[18px] shrink-0", aktiv && "text-ochre")} aria-hidden />
      <span className="hidden truncate lg:inline">{etikett}</span>
    </Link>
  );
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

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* Före allt annat i DOM och med högre z-index: bannern ska ligga ÖVER
          det klistrade innehållet, inte försvinna bakom det vid scroll. */}
      <ImpersonationBanner />

      <div className="flex min-h-dvh">
        {/* Vänsterrailen — sajtens EN tonala inversion (DESIGN.md: en per
            sida). Alltid synlig: på smala skärmar krymper den till en ikonrail
            i stället för att gömmas bakom en hamburgare, eftersom menyn ÄR
            ytans karta. Samma struktur som bokforing-webb/components/Sidebar. */}
        <aside className="rail sticky top-0 flex h-dvh w-[64px] shrink-0 flex-col bg-ink text-paper lg:w-[260px]">
          <div className="flex items-center gap-3 px-3 pb-4 pt-6 lg:px-5">
            <Link
              href={demoAnpassa("/dashboard", pathname)}
              className="focus-ring rounded-[6px]"
              aria-label={demolage ? "Snajp demo — till översikten" : "Snajp — till översikten"}
            >
              <span className="hidden lg:block">
                <Logo tone="paper" />
              </span>
              <span className="lg:hidden">
                <Logo tone="paper" compact />
              </span>
            </Link>
          </div>

          {/* Arbetsytans namn — samma plats som "Bokföring"-etiketten i
              bokforing-webbs rail. I demon står demomarkören här i stället:
              den säger vad ytan ÄR, alltså hör den ihop med märket. */}
          {demolage ? (
            <p className="hidden px-5 pb-4 lg:block">
              <span className="inline-flex items-center rounded-input border border-ochre/40 bg-ochre/10 px-2 py-0.5 text-[0.75rem] font-medium text-ochre">
                Demo · exempeldata
              </span>
            </p>
          ) : (
            <p className="hidden truncate px-5 pb-4 text-[0.75rem] font-medium uppercase tracking-[0.14em] text-paper/40 lg:block">
              {workspaceName}
            </p>
          )}

          <nav
            aria-label={t("nav.dashboard")}
            className="thin-scrollbar flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-2 lg:px-3"
          >
            {demolage
              ? DEMO_NAV.map(([vag, etikett]) => {
                  const href = demoSektionsVag(vag);
                  return (
                    <RailRad
                      key={href}
                      href={href}
                      etikett={etikett}
                      Ikon={DEMO_IKONER[vag] ?? LayoutDashboard}
                      aktiv={pathname === href}
                    />
                  );
                })
              : huvudRoutes.map((route) => {
                  const aktiv =
                    route.href === "/dashboard"
                      ? pathname === "/dashboard"
                      : pathname === route.href || pathname.startsWith(`${route.href}/`);
                  return (
                    <RailRad
                      key={route.href}
                      href={demoAnpassa(route.href, pathname)}
                      etikett={t(route.labelKey)}
                      Ikon={RUTT_IKONER[route.href] ?? LayoutDashboard}
                      aktiv={aktiv}
                      // Läget sätts vid klicket, inte i en effekt på den nya
                      // sidan: en effekt hade hunnit rendera målsidan i det
                      // gamla läget först, och bytet hade synts som ett hopp.
                      onClick={() => {
                        const lage = FLIKENS_LAGE[route.href];
                        if (lage && availableScopes.includes(lage)) {
                          setScope(lage);
                        }
                      }}
                    />
                  );
                })}
          </nav>

          <div className="flex flex-col gap-1 border-t border-paper/10 px-2 py-3 lg:px-3">
            {settingsRoute && !demolage ? (
              <RailRad
                href={settingsRoute.href}
                etikett={t(settingsRoute.labelKey)}
                Ikon={Settings}
                aktiv={pathname === "/settings" || pathname.startsWith("/settings/")}
              />
            ) : null}
            <p className="hidden px-3 pb-1 pt-3 text-[0.75rem] leading-5 text-paper/35 lg:block">
              {demolage ? "Snajp — prova utan konto" : "En tjänst från Snajp"}
            </p>
          </div>
        </aside>

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
                <span className="mr-auto inline-flex items-center rounded-input border border-ochre/40 bg-ochre/10 px-2.5 py-1 text-[13px] font-medium text-ochre lg:hidden">
                  Demo · exempeldata
                </span>
              ) : (
                <span className="mr-auto truncate text-[13px] font-medium text-ink/45 lg:hidden">
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
                className="focus-ring min-h-11 rounded-input px-3 text-sm font-medium text-ink/55 transition-colors hover:text-ink"
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
                    className="focus-ring inline-flex min-h-11 items-center gap-1.5 rounded-input px-3 text-sm font-medium text-ink/55 transition-colors hover:text-ink"
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
                    className="focus-ring hidden min-h-11 items-center rounded-input px-3 text-sm font-medium text-ink/55 transition-colors hover:text-ink sm:inline-flex"
                  >
                    Till startsidan
                  </Link>
                  <Link
                    href="/login"
                    className="focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-sm font-medium text-ink/55 transition-colors hover:text-ink"
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
                  <span className="text-[13px] text-ink/70">
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
                  <span className="kicker text-ochre">Demo</span>
                  {/* Demovyn bär ingen förklarande rad längre. Märkningen
                      "Demo" räcker där; texten om demokontot namngav dessutom
                      exempelbutiken i en yta som visas för kunder. */}
                  {vy === "demo" ? null : (
                    <span className="text-[13px] text-ink/70">
                      Du testar Snajp med ett begränsat antal körningar.
                    </span>
                  )}
                  {vy === "demo" ? null : (
                    /* Samma adress som marknadssidan, via samma konstant.
                       Hårdkodad här stod den utanför bytet i copy.ts. */
                    <a
                      href={mejlaOss()}
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
            {kicker ? <p className="text-[0.8125rem] font-medium text-ink/45">{kicker}</p> : null}
            <h1 className={cn("font-display text-[1.625rem] font-semibold leading-tight tracking-[-0.02em]", kicker && "mt-1")}>
              {title}
            </h1>
            {description ? (
              <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink/65">{description}</p>
            ) : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
        <div className="mt-8">{children}</div>
      </section>
    </AppShell>
  );
}
