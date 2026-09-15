import { cookies } from "next/headers";
import { Sidebar } from "@/components/Sidebar";
import {
  KUND_KAKA,
  KUNDSESSION_MAX_MS,
  dekrypteraKundsession,
  type Kundsession
} from "@/lib/kundsession";
import { PeriodProvider } from "@/lib/period";
import { ProfilProvider } from "@/lib/profil";

/**
 * Portalens skal: sidomenyn och innehållsytan. Ligger i route-gruppen
 * (portal) och inte i rotlayouten, eftersom inloggningssidan (/logga-in)
 * ska stå UTAN meny — en utloggad besökare ska inte se sajtens karta.
 *
 * Kundens namn läses ur SSO-kakan på SERVERN och går som prop till railen:
 * kunden ska se vems bokföring den står i, särskilt den som har flera bolag.
 */
export default async function PortalLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  let kundnamn: string | null = null;
  const kaka = (await cookies()).get(KUND_KAKA)?.value;
  const hemlighet = process.env.BOKFORING_SSO_SECRET;
  if (kaka && hemlighet) {
    const kund = await dekrypteraKundsession<Kundsession>(kaka, hemlighet);
    if (kund?.apiKey && Date.now() - kund.utfardad < KUNDSESSION_MAX_MS) {
      kundnamn = kund.namn || kund.slug || null;
    }
  }

  return (
    <PeriodProvider>
      <ProfilProvider>
        <div className="flex min-h-dvh">
          <Sidebar kundnamn={kundnamn} />
          <main className="min-w-0 flex-1">
            <div className="mx-auto max-w-[1060px] px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
              {children}
            </div>
          </main>
        </div>
      </ProfilProvider>
    </PeriodProvider>
  );
}
