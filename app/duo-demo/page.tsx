import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { StartView } from "@/components/dashboard/StartView";
import { notFoundOnTenant } from "@/lib/tenants/server";

/**
 * Duo-ytan att titta på, utan inloggning.
 *
 * ## Varför den finns
 *
 * Duo-vyn — båda agenterna i samma dashboard — gick tidigare bara att se genom
 * att logga in på en arbetsyta som äger båda produkterna. Det gör den omöjlig
 * att visa i ett säljsamtal, omöjlig att granska när inloggningen krånglar, och
 * omöjlig att peka på i en handoff.
 *
 * ## Varför den är ofarlig
 *
 * Den rör ALDRIG en session och ALDRIG databasen. `state` nedan är en
 * hårdkodad konstant, och `variant: "demo"` gör att de underliggande vyerna
 * renderar sitt inbyggda exempeldataset i stället för att hämta något.
 *
 * Det är samma regel som `components/marketing/ProductPage.tsx` följer och
 * skriver ut: en publik sida får aldrig sträcka sig efter en session eller en
 * databas. Skulle någon senare koppla in en riktig hämtning här blir det här
 * en läcka av kunddata på en oautentiserad route — därför står regeln kvar.
 *
 * `notFoundOnTenant()` gör att sidan inte finns på en kunds egen domän. På
 * livrustning.se ska Snajps produktdemo inte gå att nå.
 */

export const metadata = {
  title: "Snajp Duo — båda agenterna i samma vy",
  description: "Demo av duo-dashboarden. Exempeldata, ingen inloggning."
};

const DEMO_STATE = {
  // Demon är aldrig plattformsadmin: den ytan visar ALLA kunders siffror.
  isPlatformAdmin: false,
  vy: "admin" as const,
  initialScope: "both" as const,
  isDemo: false,
  // BÅDA produkterna. Det är hela poängen med ytan.
  products: ["leads", "support"] as const,
  addons: [],
  workspaceName: "Duo Demo AB",
  // false, och det är inte kosmetik: signedIn styr om vyerna erbjuder
  // åtgärder som kräver en session. En demo som låtsas vara inloggad hade
  // visat knappar som inte kan göra något.
  signedIn: false
};

export default async function Page() {
  await notFoundOnTenant();

  return (
    <div className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-[1480px] px-4 py-6 md:px-6">
        <p className="kicker rounded-input border border-ochre/40 bg-ochre/10 px-3 py-2 text-ochre">
          Demo · exempeldata, ingen inloggning och ingen kunddata
        </p>
      </div>
      <DashboardProvider state={{ ...DEMO_STATE, products: [...DEMO_STATE.products] }}>
        <StartView />
      </DashboardProvider>
    </div>
  );
}
