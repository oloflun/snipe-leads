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
  // ... men bara i det SKARPA läget. Står vyväxeln på Demo är hela poängen att
  // adminen ska stå kvar här, i kundens skal, utan adminflikar — se lib/vy.ts.
  // Ingen loop: /admin skickar tillbaka hit i exakt det motsatta fallet, och
  // `vy` har bara två värden.
  if (state.isPlatformAdmin && state.vy === "admin") {
    redirect("/admin");
  }

  // Grinden läses här och inte i proxyn: onboardingstatus är föränderligt
  // tillstånd, och ett anspråk i sessions-token blir inaktuellt utan att
  // något felar. Se lib/auth/onboarding-gate.ts.
  //
  // Hoppas över i demovyn: grinden mäter ADMINENS arbetsyta, och demovyn
  // handlar inte om den. En admin med ofullständig egen onboarding hade
  // annars studsat till /onboarding varje gång de försökte visa produkten.
  if (state.vy !== "demo") {
    await requireOnboarded();
  }

  return <DashboardProvider state={state}>{children}</DashboardProvider>;
}
