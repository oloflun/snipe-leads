import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { CrmRam } from "@/components/crm/app/CrmRam";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { requireOnboarded } from "@/lib/auth/onboarding-gate";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { TEMA_COOKIE, parseTema } from "@/lib/tema";
// Förladdar Fraunces på den här sidan (lib/fonts-rubrik.ts säger varför).
import "@/lib/fonts-rubrik";

export const metadata: Metadata = { title: "Snajp CRM" };

/**
 * Snajp CRM är en egen app bredvid arbetsytan, inte en flik i den: eget skal,
 * egen navigering, samma inloggning och samma kund. Inloggningen grindas av
 * proxy.ts (`/crm` står i matchern och i `protectedRoutePrefixes`), och kunden
 * avgörs av samma `resolveDashboardState()` som arbetsytan använder. Varje
 * anrop vyerna gör går genom `/api/snajp-support/…`, som bär kundens nyckel.
 *
 * Plattformsadmin skickas INTE vidare till /admin här, till skillnad från
 * app/dashboard/layout.tsx: CRM:et har ingen adminvariant, och adminen ser den
 * kund som vyväxeln pekar på.
 */
export default async function CrmLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const state = await resolveDashboardState();
  // Bara plattformsadmin når CRM:et tills Anton säger annat (hans svar
  // 2026-11-26). `adminOnly` i lib/routes.ts döljer bara menyposten: utan den
  // här grinden nådde varje inloggad kund sidan via adressen, vilket
  // kartläggningen av skalet hittade. 404 och inte en omdirigering, som
  // adminytan: en sida kunden inte har ska inte avslöja att den finns.
  //
  // Tillägget (`crm` i lib/addons.ts, fritt under provperioden) grindas inte
  // här utan i backenden (snajp-support/app/crm/tillgang.py), eftersom CRM:et
  // har ett publikt API som inte passerar webben. Vyerna visar backendens
  // besked (`addon_missing`). Den dag kunderna släpps in tas raden nedan bort,
  // och tillägget är då den grind som återstår.
  if (!state.isPlatformAdmin) {
    notFound();
  }
  if (state.vy !== "demo") {
    await requireOnboarded();
  }
  const tema = parseTema((await cookies()).get(TEMA_COOKIE)?.value);

  return (
    <DashboardProvider state={state}>
      <CrmRam tema={tema} arbetsyta={state.workspaceName ?? undefined} hjalp={state.signedIn && !state.isDemo && state.vy !== "demo"}>
        {children}
      </CrmRam>
    </DashboardProvider>
  );
}
