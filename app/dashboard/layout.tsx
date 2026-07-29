import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { resolveDashboardState } from "@/lib/data/dashboard";

/**
 * Entitlement and fresh/demo are resolved once per request on the server, then
 * handed to the client tree. Nothing below this point re-decides what the user
 * is allowed to see.
 */
export default async function DashboardLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  const state = await resolveDashboardState();

  return <DashboardProvider state={state}>{children}</DashboardProvider>;
}
