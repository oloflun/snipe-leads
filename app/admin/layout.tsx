import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { getPlatformAdmin, getPlatformAdminUtanTvafaktorkrav } from "@/lib/auth/admin";
import { AdminShell } from "@/components/admin/AdminShell";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { resolveDashboardState } from "@/lib/data/dashboard";
// Förladdar Fraunces på den här sidan (lib/fonts-rubrik.ts säger varför).
import "@/lib/fonts-rubrik";

export const dynamic = "force-dynamic";

/**
 * Adminytan, grindad server-side — och en SUPERSET av kundens arbetsyta.
 *
 * Tre utfall, i den här ordningen (ändrat säkerhetsval 2026-11-24, Antons
 * krav efter kunddemon: en felsida får inte dyka upp, och har sessionen gått
 * ut ska man till inloggningen):
 *
 *  1. Ingen session → /login?next=/admin. Avgörs med `auth()`, inte med
 *     admin-uppslaget: det svarar null både utan session och för icke-admin,
 *     och då blandades fallen ihop. Proxyn gör samma sak först; det här är
 *     skyddsnätet för en återkallad eller trasig session (INV-AUTH-002).
 *  2. En admin som stoppas av tvåfaktorn → /settings/tvafaktor.
 *  3. En inloggad icke-admin → /dashboard, sin egen arbetsyta. Förut var det
 *     en 404, för att inte bekräfta att /admin finns. Men en kund som backade
 *     till /admin/** efter ett kontobyte fick då en felsida, och historiken går
 *     inte att tömma. Omdirigeringen säger bara att sökvägen är speciell; vad
 *     som finns där skyddas fortfarande av grindarna nedan. /api/admin
 *     behåller sin 404, eftersom ett API inte ska omdirigeras.
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
  const session = await auth();
  if (!session?.user?.id) {
    redirect("/login?next=/admin");
  }

  const admin = await getPlatformAdmin();
  if (!admin) {
    redirect((await getPlatformAdminUtanTvafaktorkrav()) ? "/settings/tvafaktor" : "/dashboard");
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
