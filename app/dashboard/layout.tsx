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
  // Grinden läses här och inte i proxyn: onboardingstatus är föränderligt
  // tillstånd, och ett anspråk i sessions-token blir inaktuellt utan att
  // något felar. Se lib/auth/onboarding-gate.ts.
  await requireOnboarded();
  const state = await resolveDashboardState();

  return <DashboardProvider state={state}>{children}</DashboardProvider>;
}
