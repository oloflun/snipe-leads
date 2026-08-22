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
 *
 * SettingsNav tillkom 2026-08-18 och renderades FÖRST här, i en egen aside
 * bredvid `children`. Det gav två fel samtidigt, båda synliga i pixlar:
 *
 *  1. Två navigationer staplade. Sidan renderar sin EGEN lista via
 *     SettingsView — sex poster, oöversatta ("General", "Mailboxes",
 *     "Billing") och ogrupperade — ovanpå den grupperade i asiden. Två listor
 *     över samma sex sidor är inte redundans utan en gissningslek.
 *  2. Skalet hamnade i fel kolumn. Varje arbetsytesvy renderar sitt eget
 *     AppShell via PageShell, och asiden låg UTANFÖR det. Logotypen och
 *     flikraden började därför inte vid sidans vänsterkant utan vid
 *     innehållskolumnens.
 *
 * Navigationen bor nu inuti SettingsView, där den gamla listan låg. Under
 * /admin renderar AppShell bara innehåll (se den filen), så samma sida
 * fungerar oförändrad på båda ytorna.
 */
export default async function SettingsLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  await requireOnboarded();
  const state = await resolveDashboardState();

  return (
    <DashboardProvider state={state}>
      {children}
    </DashboardProvider>
  );
}
