import { redirect } from "next/navigation";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { requireOnboarded } from "@/lib/auth/onboarding-gate";

/**
 * Entitlement and fresh/demo are resolved once per request on the server, then
 * handed to the client tree. Nothing below this point re-decides what the user
 * is allowed to see.
 */
export default async function DashboardLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  const state = await resolveDashboardState();

  // Plattformsadmin skickas till /admin, som numera bär BÅDE arbetsytans flikar
  // och plattformsflikarna. Två inloggade ytor för samma person betyder att den
  // ena slutar användas, och det är alltid den som saknar något man behövde.
  //
  // Omdirigeringen ligger här och inte i proxy.ts av en teknisk anledning:
  // proxyn kör på Edge och gör noll databasfrågor — medvetet, `pg` finns inte
  // där. Adminstatus kräver ett uppslag i platform_admins, alltså en fråga, och
  // den kan bara ställas i en server-komponent.
  //
  // Ingen loop: /admin använder inte den här layouten.
  if (state.isPlatformAdmin) {
    redirect("/admin");
  }

  // Grinden läses här och inte i proxyn: onboardingstatus är föränderligt
  // tillstånd, och ett anspråk i sessions-token blir inaktuellt utan att
  // något felar. Se lib/auth/onboarding-gate.ts.
  await requireOnboarded();

  return <DashboardProvider state={state}>{children}</DashboardProvider>;
}
