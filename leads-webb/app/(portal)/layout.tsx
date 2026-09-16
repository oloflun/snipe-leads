import { cookies } from "next/headers";
import { Sidebar } from "@/components/Sidebar";
import {
  KUND_KAKA,
  KUNDSESSION_MAX_MS,
  dekrypteraKundsession,
  type Kundsession
} from "@/lib/kundsession";

/**
 * Portalens skal: sidomenyn och innehållsytan. Inloggningssidan (/logga-in)
 * ligger utanför gruppen och står utan meny. Kundens namn läses ur
 * SSO-kakan på servern och går som prop till railen.
 */
export default async function PortalLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  let kundnamn: string | null = null;
  const kaka = (await cookies()).get(KUND_KAKA)?.value;
  const hemlighet = process.env.AGENTSAJT_SSO_SECRET;
  if (kaka && hemlighet) {
    const kund = await dekrypteraKundsession<Kundsession>(kaka, hemlighet);
    if (kund?.apiKey && Date.now() - kund.utfardad < KUNDSESSION_MAX_MS) {
      kundnamn = kund.namn || kund.slug || null;
    }
  }

  return (
    <div className="flex min-h-dvh">
      <Sidebar kundnamn={kundnamn} />
      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-[1060px] px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
