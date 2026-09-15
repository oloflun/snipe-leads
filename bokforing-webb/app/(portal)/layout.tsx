import { Sidebar } from "@/components/Sidebar";
import { PeriodProvider } from "@/lib/period";
import { ProfilProvider } from "@/lib/profil";

/**
 * Portalens skal: sidomenyn och innehållsytan. Ligger i route-gruppen
 * (portal) och inte i rotlayouten, eftersom inloggningssidan (/logga-in)
 * ska stå UTAN meny — en utloggad besökare ska inte se sajtens karta.
 */
export default function PortalLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <PeriodProvider>
      <ProfilProvider>
        <div className="flex min-h-dvh">
          <Sidebar />
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
