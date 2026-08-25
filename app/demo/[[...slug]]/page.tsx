import { notFound } from "next/navigation";
import { PageShell } from "@/components/AppShell";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { StartView } from "@/components/dashboard/StartView";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { BokforingDemo } from "@/components/bookkeeping/BokforingDemo";
import { Dashboard as SupportDashboard } from "@/components/snajp/Dashboard";
import { LeadsControls } from "@/components/leads/LeadsControls";
import { SupportRegler } from "@/components/settings/SupportRegler";
import {
  AnalyticsView,
  AssistantView,
  CompaniesView,
  ContactsView,
  InboxView,
  LeadsView
} from "@/components/WorkspaceViews";
import { loadPublicEmailStudioData } from "@/lib/data/emails";
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
 *  * `loadEmailStudioData()` anropas INTE — den läser `generated_emails` för
 *    inloggat workspace. Vi använder `loadPublicEmailStudioData()`, som är
 *    synkron och Supabase-fri av exakt det skälet.
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
  const [sektion] = slug;

  const innehall = renderSektion(sektion);
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
function renderSektion(sektion: string | undefined): React.ReactNode | null {
  switch (sektion) {
    case undefined:
      return <StartView demo />;
    case "leads":
      return <LeadsView demo />;
    case "emails":
      return <EmailStudioDemo />;
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
    case "kontroll":
      return <LeadsControls demo />;
    case "bokforing":
      // Egen demokomponent och inte `BookkeepingView`. Den vyn anropar
      // backenden för underlag och period, och regeln för den här routen är att
      // INGENTING här får sträcka sig efter en session eller databasen — se
      // filens docstring. BokforingDemo renderar handräknade konstanter.
      return (
        <PageShell
          kicker="Bokföring"
          title="Ett kvitto, hela vägen till periodrapport"
          description="Avläsningen, verifikatet och summorna för ett påhittat underlag. Ingen modell körs på den här sidan."
        >
          <BokforingDemo />
        </PageShell>
      );
    case "regler":
      return <ReglerDemo />;
    case "support":
      return <SupportDashboard demo />;
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

function EmailStudioDemo() {
  // Den PUBLIKA laddaren. Se filens docstring — den authade varianten läser
  // generated_emails för inloggat workspace och hör inte hemma här.
  const data = loadPublicEmailStudioData();

  return (
    <PageShell
      kicker="Email studio"
      title="Skriv och skriv om"
      description="Exempelmejl. Skriv om det, korta det, ändra tonläget — inget sparas och inget skickas."
    >
      <EmailStudioEditor data={data} />
    </PageShell>
  );
}
