import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { SettingsNav } from "@/components/settings/SettingsNav";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { requireOnboarded } from "@/lib/auth/onboarding-gate";

/**
 * Speglar app/dashboard/layout.tsx.
 *
 * Utan den här filen saknade hela /settings-trädet en DashboardProvider, och
 * useDashboard() föll tillbaka på FALLBACK-kontexten i DashboardContext.tsx.
 * Den är permissiv med flit (den finns för marknadsföringsytorna) — följden
 * var att inställningssidorna i praktiken inte visste vem som var inloggad
 * eller vad arbetsytan äger, och grindade därför ingenting.
 *
 * SettingsNav tillkom 2026-08-18. Sidorna hade dessförinnan ingen flikrad alls
 * och gick bara att nå genom att skriva adressen.
 */
export default async function SettingsLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  await requireOnboarded();
  const state = await resolveDashboardState();

  return (
    <DashboardProvider state={state}>
      <div className="mx-auto grid max-w-[1400px] gap-10 px-4 py-10 md:grid-cols-[220px_1fr] md:px-6">
        <aside className="md:sticky md:top-6 md:self-start">
          <SettingsNav />
        </aside>
        <div className="min-w-0">{children}</div>
      </div>
    </DashboardProvider>
  );
}
