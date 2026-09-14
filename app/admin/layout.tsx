import { notFound, redirect } from "next/navigation";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { AdminShell } from "@/components/admin/AdminShell";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { resolveDashboardState } from "@/lib/data/dashboard";

export const dynamic = "force-dynamic";

/**
 * Adminytan, grindad server-side — och en SUPERSET av kundens arbetsyta.
 *
 * `notFound()` och inte en redirect till /login: ett 403 eller en redirect
 * bekräftar att /admin finns och vem den är till för. En 404 säger ingenting.
 *
 * Det här är grind ETT av tre. De andra två är `/api/admin/*`-proxyns egen
 * kontroll och backendens `require_master_key`. Ingen av dem litar på att de
 * andra gjorde sitt jobb.
 *
 * ## Varför arbetsytans flikar hänger här
 *
 * En plattformsadmin behöver båda sakerna samtidigt: de egna körningarna och
 * alla kunders siffror. Att växla mellan /dashboard och /admin för att göra ett
 * jobb är två inloggade ytor för en person, och den som gör det slutar använda
 * den ena.
 *
 * `/dashboard` är OFÖRÄNDRAD för vanliga kunder. Flikarna renderas av samma
 * `WorkspaceSection` som kundens yta använder — ingen vy är kopierad, och
 * entitlement-kontrollen sitter kvar inuti den.
 *
 * DashboardProvider måste finnas här: arbetsytans komponenter läser
 * `useDashboard()`, och utan provider faller de tillbaka på FALLBACK-kontexten
 * och visar demo-data i adminytan.
 *
 * Skalet (header, flikar, språkval, utloggning) bor i `AdminShell`, som är en
 * klientkomponent. Layouten kan inte vara det: grinden ovan ställer en fråga.
 */
export default async function AdminLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  const admin = await getPlatformAdmin();
  if (!admin) {
    notFound();
  }

  const state = await resolveDashboardState();

  // Demovyn har inga adminkontroller — då är AdminShell fel skal. Utan den här
  // raden gick det att stå kvar i plattformsramen med demokontots nyckel,
  // alltså adminflikar ovanpå någon annans data: den sämsta av två vyer.
  if (state.vy === "demo") {
    redirect("/dashboard");
  }

  return (
    <DashboardProvider state={state}>
      <AdminShell email={admin.email}>
        <div className="mx-auto max-w-[1400px] px-4 py-8 md:px-6 md:py-10">{children}</div>
      </AdminShell>
    </DashboardProvider>
  );
}
