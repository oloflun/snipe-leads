import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/components/AppShell";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { StartView } from "@/components/dashboard/StartView";
import { CrmDemo } from "@/components/crm/CrmDemo";
import { KvittoDemo } from "@/components/kvitton/KvittoDemo";
import { DemoSupportYta } from "@/components/snajp/DemoSupportYta";
import { IrisBolag } from "@/components/leads/IrisBolag";
import { IrisGranskning } from "@/components/leads/IrisGranskning";
import { IrisInstallningar } from "@/components/leads/IrisInstallningar";
import { SupportRegler } from "@/components/settings/SupportRegler";
import {
  AnalyticsView,
  AssistantView,
  CompaniesView,
  ContactsView,
  InboxView
} from "@/components/WorkspaceViews";
import { notFoundOnTenant } from "@/lib/tenants/server";

/**
 * Hela arbetsytan att prova UTAN inloggning.
 *
 * ## Varför det här är en egen route och inte en lucka i grinden
 *
 * Det uppenbara sättet att göra funktionerna provbara vore att släppa
 * proxy-grinden på `/dashboard`. Det vore ett DATALÄCKAGE, inte en demo:
 * `/dashboard` renderar en riktig arbetsyta med riktiga kunders ärenden,
 * mejladresser och prospekt. Grinden står kvar orörd.
 *
 * Den här routen renderar SAMMA komponenter mot `lib/mock-data`. Skillnaden
 * ligger i vad som matas in, inte i vad som visas.
 *
 * ## Regeln som gör den ofarlig, och som inte får brytas
 *
 * INGENTING här får sträcka sig efter en session eller databasen.
 *
 *  * `resolveDashboardState()` anropas INTE — state är en konstant nedan.
 *  * `IrisBolag`/`IrisGranskning`/`IrisInstallningar` läser demo-fixturer
 *    (`lib/demo/oversikt.ts`, `lib/demo/iris-exempel.ts`) i stället för
 *    `/api/snajp-support/*` när `demo` är satt — se respektive komponent.
 *  * Vyerna under `WorkspaceViews` är klientkomponenter som läser
 *    `lib/mock-data`. Kontrollera det innan du lägger till en ny sektion här.
 *
 * Byter någon ut en av de raderna mot en riktig hämtning blir det här en
 * oautentiserad läcka av kunddata. Därför står regeln i filen och inte i en
 * handoff.
 *
 * `notFoundOnTenant()` gör att sidan inte finns på en kunds egen domän.
 */

export const metadata = {
  title: "Snajp — prova utan konto",
  description: "Hela arbetsytan med exempeldata. Ingen inloggning, ingen kunddata."
};

const DEMO_STATE = {
  // Demon är aldrig plattformsadmin: den ytan visar ALLA kunders siffror.
  isPlatformAdmin: false,
  vy: "admin" as const,
  impersonation: null,
  arLasare: false,
  initialScope: "both" as const,
  isDemo: false,
  products: ["leads", "support", "bookkeeping"] as const,
  addons: [],
  workspaceName: "Demo AB",
  // Styr om vyerna erbjuder åtgärder som kräver session. En demo som låtsas
  // vara inloggad visar knappar som inte kan göra något.
  signedIn: false
};

export default async function Page({
  params
}: Readonly<{ params: Promise<{ slug?: string[] }> }>) {
  await notFoundOnTenant();
  const { slug = [] } = await params;
  const [sektion, undersektion] = slug;

  const innehall = renderSektion(sektion, undersektion);
  if (innehall === null) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* Ingen egen chrome här. Sektionsraden, demomarkören och de två
          utvägarna ritas av AppShell, i samma header som arbetsytan har —
          se lib/demo/sektioner.ts. Sidan bidrar bara med innehållet. */}
      <DashboardProvider state={{ ...DEMO_STATE, products: [...DEMO_STATE.products] }}>
        {innehall}
      </DashboardProvider>
    </div>
  );
}

/** null = okänd sektion, alltså 404. */
function renderSektion(
  sektion: string | undefined,
  undersektion?: string
): React.ReactNode | null {
  switch (sektion) {
    case undefined:
      return <StartView demo />;
    case "iris":
      // Samma tre undersidor som /dashboard/iris — se
      // components/dashboard/WorkspaceSection.tsx. Ett okänt tredje
      // slugsegment är en 404, inte en tyst fallback till Bolag.
      if (undersektion === "granskning") {
        return (
          <PageShell kicker="Iris" title="Granskning" description="Utkasten Iris skrivit, i väntan på ditt ja eller nej.">
            <IrisGranskning demo />
          </PageShell>
        );
      }
      if (undersektion === "installningar") {
        return (
          <PageShell kicker="Iris" title="Inställningar" description="Målgrupp, autonomi och gränserna Iris alltid håller.">
            <IrisInstallningar demo />
          </PageShell>
        );
      }
      if (undersektion) {
        return null;
      }
      return <IrisBolag demo />;
    // Gamla adresserna — Iris flyttade in från tre separata ställen
    // 2026-09-19 (se HANDOFF/plan). Bokmärken ska landa rätt, inte i en 404.
    case "leads":
    case "emails":
      redirect("/demo/iris");
    // eslint-disable-next-line no-fallthrough -- redirect kastar, nås aldrig
    case "kontroll":
      redirect("/demo/iris/installningar");
    // eslint-disable-next-line no-fallthrough -- redirect kastar, nås aldrig
    case "crm":
      // Den omgjorda leadsagenten i demoform: kundens egen CRM-lista in
      // (CSV, parsas i webbläsaren), en isolerad Email studio per kund ut.
      // Följer filens regel — CrmDemo når varken session eller databas.
      return (
        <PageShell
          kicker="Iris"
          title="Din CRM-lista, en studio per kund"
          description="Ladda upp kundlistan ur ert CRM som CSV. Iris bevakar kundernas signaler, och varje kund får en egen, isolerad Email studio som skriver utifrån signalerna och er produkt. Listan stannar i webbläsaren och inget skickas."
        >
          <CrmDemo />
        </PageShell>
      );
    case "companies":
      return <CompaniesView demo />;
    case "contacts":
      return <ContactsView demo />;
    case "inbox":
      return <InboxView demo />;
    case "analytics":
      return <AnalyticsView demo />;
    case "assistant":
      return <AssistantView />;
    case "bokforing":
      // Gamla adressen — Kvittohanteraren ersatte bokföringsdemon 2026-09-16.
      redirect("/demo/kvitton");
    // eslint-disable-next-line no-fallthrough -- redirect kastar, nås aldrig
    case "kvitton":
      // Egen demokomponent och inte `KvittoVy`. Den vyn anropar backenden,
      // och regeln för den här routen är att INGENTING här får sträcka sig
      // efter en session eller databasen — se filens docstring. KvittoDemo
      // renderar handräknade konstanter och spelar upp dem.
      return (
        <PageShell
          kicker="Kvittohanteraren"
          title="Inkorgen läses, kvittona plockas ut"
          description="Tryck på Skanna inkorgen och se agenten identifiera kvitton, lyfta ut beloppen och sammanställa perioden. Påhittade mejl, förberedda svar. Ingen modell körs på den här sidan."
        >
          <KvittoDemo />
        </PageShell>
      );
    case "regler":
      return <ReglerDemo />;
    case "support":
      // Samma skal som /dashboard/support (SupportSection i WorkspaceSection):
      // utan PageShell stod inkorgen ensam i viewporten, utan rail och utan
      // väg tillbaka — den enda demosektionen med en helt egen chrome.
      // DemoSupportYta lägger kundchatten (förladdade svar) som flik bredvid
      // inkorgen, samma flikmönster som arbetsytans SupportWorkspaceTabs.
      return (
        <PageShell title="Inkorg och utkast">
          <DemoSupportYta />
        </PageShell>
      );
    default:
      return null;
  }
}

function ReglerDemo() {
  return (
    <PageShell
      kicker="Kundtjänst"
      title="Fack och autosvar"
      description="Vilka ärenden agenterna får besvara själva, och vilka som alltid går till en människa. Ändringarna sparas inte i demon."
    >
      <SupportRegler demo />
    </PageShell>
  );
}

