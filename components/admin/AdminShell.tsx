"use client";

import {
  Activity,
  Bell,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  LogOut,
  Users
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { usePathname } from "next/navigation";
import { FLIKENS_LAGE, RUTT_IKONER } from "@/components/AppShell";
import { BytKund } from "@/components/admin/BytKund";
import { VyVaxel } from "@/components/VyVaxel";
import { Rail } from "@/components/shell/Rail";
import type { RailNavGroup } from "@/components/shell/Rail";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { AgentMenu } from "@/components/snajp/AgentMenu";
import { signOut } from "@/lib/actions/auth";
import { useLocale } from "@/lib/i18n";
import { routesForProducts, tillAdminvag } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Adminytans skal — samma vänsterrail som kundens AppShell, sedan 2026-09-18.
 *
 * ## Varför skalet bor här och inte i layouten
 *
 * `app/admin/layout.tsx` är en server-komponent (den måste vara det: grinden
 * `getPlatformAdmin()` ställer en databasfråga). Skalet behöver `usePathname`
 * för aktiv flik, `useLocale` för språkväxlaren och en form-action för
 * utloggning — alltså klientsidan. Layouten grindar och hämtar; det här
 * renderar.
 *
 * ## Historik: topp-header med flikrad, ersatt av railen
 *
 * Adminytan bar tidigare en egen topp-header med två flikrader (plattform +
 * arbetsyta) — en tredje chrome vid sidan av kundytans rail och demons band.
 * Nu delar admin components/shell/Rail.tsx med AppShell: samma komponent,
 * två navgrupper. Grupp 1 är plattformssidorna (Översikt, Kunder, …), grupp 2
 * är arbetsytans sektioner under en hårlinje och etiketten "Arbetsyta" — se
 * `arbetsyta` nedan, byggd av samma routekarta som kundens nav.
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
 * det inte blir två staplade railer. Uppmätt: det var det innan.
 */

/**
 * Plattformssidorna — det som skiljer adminytan från kundens arbetsyta.
 *
 * Etiketterna är Localized och inte svenska strängar: arbetsytans grupp
 * översätts redan av `t()`, och en plattformsgrupp som stod kvar på svenska
 * gjorde EN-läget till ett halvöversatt gränssnitt.
 *
 * `/admin/bokforingsanvandning` står MEDVETET utanför listan: sidan finns
 * kvar som en redirect till `/admin/agentanvandning` (bokmärken ska landa
 * rätt), men `agentanvandning` är dess efterträdare och den enda som hör
 * hemma i navigationen.
 */
const PLATTFORM: Array<{ href: string; label: { sv: string; en: string }; Icon: LucideIcon }> = [
  { href: "/admin", label: { sv: "Översikt", en: "Overview" }, Icon: LayoutDashboard },
  { href: "/admin/kunder", label: { sv: "Kunder", en: "Customers" }, Icon: Users },
  { href: "/admin/korningar", label: { sv: "Körningar", en: "Runs" }, Icon: Activity },
  {
    href: "/admin/testkorningar",
    label: { sv: "Testkörningar", en: "Test runs" },
    Icon: FlaskConical
  },
  {
    href: "/admin/agentanvandning",
    label: { sv: "Agentanvändning", en: "Agent usage" },
    Icon: Gauge
  },
  { href: "/admin/handelser", label: { sv: "Händelser", en: "Events" }, Icon: Bell }
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
  const { products, workspaceName, shows, availableScopes, setScope } = useDashboard();

  // Samma entitlement- och scope-filter som kundens nav. Adminytan är en
  // superset av arbetsytan, inte en genväg förbi dess regler.
  //
  // `isAdmin: true` som literal, och det är inte en genväg förbi grinden:
  // AdminShell renderas BARA inifrån app/admin/layout.tsx, som svarar
  // notFound() för den som inte är plattformsadmin. Kommer man hit ÄR man
  // admin — att fråga en gång till hade varit ett andra svar på en fråga som
  // redan är avgjord, och två svar blir förr eller senare olika.
  //
  // Utan raden försvinner adminOnly-routerna helt: filtret är fail-closed, och
  // en plattformsadmin skickas dessutom hit från /dashboard
  // (app/dashboard/layout.tsx). Bokföringsfliken fanns alltså ingenstans för
  // just den publik den är byggd för.
  const arbetsyta = routesForProducts(products, { isAdmin: true })
    .filter((route) => route.product === "shared" || shows(route.product))
    .map((route) => ({
      // Originalrouten (före tillAdminvag) — nyckeln RUTT_IKONER känner igen,
      // så samma /dashboard/*-route bär samma ikon på båda ytorna.
      origHref: route.href,
      href: tillAdminvag(route.href),
      // Samma flik, samma läge. Utan den här raden byter Iris-fliken vy på
      // kundens yta men inte på adminens, och samma knapp gör då olika saker
      // beroende på var man står.
      lage: FLIKENS_LAGE[route.href],
      // "Min arbetsyta" och inte t("nav.dashboard") ("Översikt"): plattforms-
      // gruppen har redan en post som heter Översikt, och två poster med
      // samma namn i samma rail är inte en etikett utan en gissningslek.
      // Localized och inte en svensk sträng — resten av railen byter språk
      // med EN/SV-knappen, och en post som inte gör det ser ut som en bugg.
      label:
        route.href === "/dashboard"
          ? text({ sv: "Min arbetsyta", en: "My workspace" })
          : t(route.labelKey),
      // Iris tre barn, körda genom samma tillAdminvag-karta som föräldern —
      // /dashboard/iris/granskning blir /admin/iris/granskning, inte en
      // hårdkodad andra karta som kan glida isär från den här.
      children: route.children?.map((child) => ({
        href: tillAdminvag(child.href),
        label: t(child.labelKey)
      }))
    }));

  // Alla hrefs, INKLUSIVE barnens — annars markerar t.ex.
  // /admin/iris/granskning bara "Iris" som aktiv utan att någon barnrad lyser.
  const aktiv = aktivHref(pathname, [
    ...PLATTFORM.map((f) => f.href),
    ...arbetsyta.map((f) => f.href),
    ...arbetsyta.flatMap((f) => f.children?.map((c) => c.href) ?? [])
  ]);

  const plattformGroup: RailNavGroup = {
    key: "plattform",
    items: PLATTFORM.map((flik) => ({
      href: flik.href,
      label: text(flik.label),
      Icon: flik.Icon,
      active: aktiv === flik.href
    }))
  };

  const arbetsytaGroup: RailNavGroup = {
    key: "arbetsyta",
    label: text({ sv: "Arbetsyta", en: "Workspace" }),
    items: arbetsyta.map((flik) => {
      const barnAktiva = flik.children?.some((c) => aktiv === c.href) ?? false;
      return {
        href: flik.href,
        label: flik.label,
        Icon: RUTT_IKONER[flik.origHref] ?? LayoutDashboard,
        active: aktiv === flik.href || barnAktiva,
        onClick: () => {
          if (flik.lage && availableScopes.includes(flik.lage)) {
            setScope(flik.lage);
          }
        },
        children: flik.children?.map((child) => ({
          href: child.href,
          label: child.label,
          active: aktiv === child.href
        }))
      };
    })
  };

  return (
    <div className="min-h-screen bg-paper text-ink">
      <div className="flex min-h-dvh">
        <Rail
          logoHref="/admin"
          logoAriaLabel={text({
            sv: "Snajp admin, till översikten",
            en: "Snajp admin, go to overview"
          })}
          brand={
            <p className="hidden truncate px-5 pb-4 text-[0.75rem] font-medium uppercase tracking-[0.14em] text-paper-subtle lg:block">
              {workspaceName ? `Admin · ${workspaceName}` : "Admin"}
            </p>
          }
          navLabel={text({ sv: "Adminnavigering", en: "Admin navigation" })}
          groups={arbetsyta.length > 0 ? [plattformGroup, arbetsytaGroup] : [plattformGroup]}
          footer={
            <>
              {/* Alltid nåbart, oavsett railbredd: språkval och utloggning
                  behöver ingen bredd att gömma sig bakom. */}
              <div className="flex items-center justify-center gap-1 lg:justify-start">
                <button
                  type="button"
                  onClick={toggleLocale}
                  className="focus-ring min-h-9 shrink-0 rounded-input px-2 text-[13px] font-medium text-paper-muted transition-colors hover:bg-paper/5 hover:text-paper lg:px-3"
                >
                  {locale === "sv" ? "EN" : "SV"}
                </button>
              </div>

              {/* Kunduppslag, vy-växel, kontaktmeny och kontoadress, i
                  railens egen mörka ton (`ton="rail"`) sedan 2026-09-22 — den
                  ljusa plattan de stod på förut bröt mot resten av panelen.
                  Bara vid lg+: platsen räcker inte i ikonläget, och
                  kontrollerna saknar ett ikon-only-läge. */}
              <div className="hidden flex-col gap-1.5 border-t border-paper/10 px-1 pt-3 lg:flex">
                <div className="flex flex-wrap items-center gap-1">
                  <BytKund ton="rail" />
                  <VyVaxel ton="rail" />
                </div>
                <AgentMenu yta="leads" kontext={`admin:${pathname}`} ton="rail" />
                {email ? (
                  <p className="truncate px-1 pt-0.5 text-[0.75rem] text-paper-subtle">{email}</p>
                ) : null}
              </div>

              {/* Utloggning fanns inte alls i adminytan från början. signOut()
                  var skriven och fungerande, men ingen komponent i skalet
                  anropade den — samma lucka som en gång saknade länken TILL
                  /admin. Formulär och inte onClick: signOut är en server
                  action och fungerar utan JS. */}
              <form action={signOut}>
                <button
                  type="submit"
                  title={text({ sv: "Logga ut", en: "Sign out" })}
                  className={cn(
                    "focus-ring flex min-h-11 w-full items-center justify-center gap-1.5 rounded-input px-3 text-sm font-medium transition-colors",
                    "text-paper-muted hover:bg-paper/5 hover:text-paper lg:justify-start"
                  )}
                >
                  <LogOut className="h-4 w-4 shrink-0" aria-hidden />
                  <span className="hidden lg:inline">{text({ sv: "Logga ut", en: "Sign out" })}</span>
                </button>
              </form>
            </>
          }
        />

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
