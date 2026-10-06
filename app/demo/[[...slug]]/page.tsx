import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/components/AppShell";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { StartView } from "@/components/dashboard/StartView";
import { CrmDemo } from "@/components/crm/CrmDemo";
import { KvittoDemoYta } from "@/components/kvitton/KvittoDemoYta";
import { DemoSupportYta } from "@/components/snajp/DemoSupportYta";
import { AttGora } from "@/components/leads/AttGora";
import { IrisBolag } from "@/components/leads/LeadsSida";
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
 * Sidhuvudena här bär bara en rubrik sedan 2026-09-27: `PageShell` tar inte
 * längre `kicker` eller `description` (plans/2026-09-27-appytor-enhetlighet.md).
 * Rubrikerna är desamma som arbetsytans och railens ("Kvitton", "CRM-lista"),
 * inte egna säljmeningar.
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
 *  * `IrisBolag`/`AttGora`/`IrisInstallningar` läser demo-fixturer
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
  title: "Snajp · prova utan konto",
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
  userEmail: null,
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
    // Samma sidor som arbetsytan (Snajp Suite 2026-10-03), se
    // components/dashboard/WorkspaceSection.tsx.
    case "leads":
      return undersektion ? null : <IrisBolag demo />;
    case "att-gora":
      return undersektion ? null : (
        <PageShell title={{ sv: "Att göra", en: "To do" }}>
          <AttGora demo />
        </PageShell>
      );
    case "installningar":
      return undersektion ? null : (
        <PageShell title={{ sv: "Inställningar", en: "Settings" }}>
          <IrisInstallningar demo />
        </PageShell>
      );
    // Gamla adresserna. Bokmärken ska landa rätt, inte i en 404.
    case "iris": {
      const ny: Record<string, string> = {
        "": "/demo/leads",
        pipeline: "/demo/leads?vy=pipeline",
        granskning: "/demo/att-gora",
        installningar: "/demo/installningar"
      };
      const mal = ny[undersektion ?? ""];
      if (!mal) return null;
      redirect(mal);
    }
    // eslint-disable-next-line no-fallthrough -- redirect kastar, nås aldrig
    case "emails":
      redirect("/demo/leads");
    // eslint-disable-next-line no-fallthrough -- redirect kastar, nås aldrig
    case "kontroll":
      redirect("/demo/installningar");
    // eslint-disable-next-line no-fallthrough -- redirect kastar, nås aldrig
    case "crm":
      // Den omgjorda leadsagenten i demoform: kundens egen CRM-lista in
      // (CSV, parsas i webbläsaren), en isolerad Email studio per kund ut.
      // Följer filens regel — CrmDemo når varken session eller databas.
      // Att listan stannar i webbläsaren står i CrmDemos egen uppladdningsyta.
      return (
        <PageShell title={{ sv: "CRM-lista", en: "CRM list" }}>
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
      // renderar handräknade konstanter och spelar upp dem; Översikten
      // (KvittoDemoYta) räknar på lib/demo/kvitto-oversikt.ts.
      return (
        <PageShell title={{ sv: "Kvitton", en: "Receipts" }}>
          <KvittoDemoYta />
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
        <PageShell title={{ sv: "Kundtjänst", en: "Customer service" }}>
          <DemoSupportYta />
        </PageShell>
      );
    default:
      return null;
  }
}

function ReglerDemo() {
  return (
    <PageShell title={{ sv: "När agenten får svara själv", en: "When the agent may answer on its own" }}>
      <SupportRegler demo />
    </PageShell>
  );
}

