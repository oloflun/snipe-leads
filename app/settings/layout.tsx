import { DashboardProvider } from "@/components/dashboard/DashboardContext";
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
 */
export default async function SettingsLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  await requireOnboarded();
  const state = await resolveDashboardState();

  return <DashboardProvider state={state}>{children}</DashboardProvider>;
}
